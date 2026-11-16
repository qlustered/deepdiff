#!/usr/bin/env python3
"""Turn the logs of a sandboxed PR test run into a findings report.

Trusted code, untrusted input: everything in the logs (paths, argv, addresses) is
attacker-controlled text. It is parsed, never executed, and control characters are
stripped before anything is printed to a terminal or written as Markdown.

Usage:
    analyze.py snapshot DIR OUT.json
    analyze.py report --strace LOG [--audit LOG] --home HOME --src-root /work \
        [--allow-root PATH ...] [--home-before A.json --home-after B.json] \
        [--markdown OUT.md] [--json OUT.json] [--fail-on high]

Exit status of `report`: 0 if nothing at or above --fail-on was found, 2 otherwise.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

CRITICAL, HIGH, MEDIUM, LOW = "CRITICAL", "HIGH", "MEDIUM", "LOW"
SEVERITIES = [CRITICAL, HIGH, MEDIUM, LOW]
RANK = {s: i for i, s in enumerate(SEVERITIES)}

# Relative to $HOME. Reading these (or trying to) is never needed to test DeepDiff.
SECRET_HOME_PATHS = [
    ".ssh", ".aws", ".azure", ".config/gcloud", ".config/gh", ".config/hub", ".git-credentials",
    ".netrc", ".pypirc", ".npmrc", ".yarnrc", ".yarnrc.yml", ".docker", ".kube", ".gnupg",
    ".password-store", ".local/share/keyrings", ".claude", ".claude.json", ".codex",
    ".config/github-copilot", ".config/op", ".vault-token", ".terraform.d", ".cargo/credentials",
    ".cargo/credentials.toml", ".m2/settings.xml", ".gem/credentials", ".mozilla",
    ".config/google-chrome", ".config/chromium", ".config/BraveSoftware", ".thunderbird",
    ".bash_history", ".zsh_history", ".python_history", ".psql_history", ".mysql_history",
    ".envrc", ".env", ".config/direnv", ".config/uv/uv.toml", ".config/pip", ".pip",
    ".local/share/python_keyring", ".config/python_keyring",
]
# Relative to $HOME. Writing these is how code survives the test run on a real machine.
PERSISTENCE_HOME_PATHS = [
    ".bashrc", ".bash_profile", ".bash_login", ".profile", ".zshrc", ".zprofile", ".zshenv",
    ".zlogin", ".config/fish", ".config/autostart", ".config/systemd", ".local/bin",
    ".ssh/authorized_keys", ".ssh/rc", ".ssh/config", ".gitconfig", ".config/git", ".vimrc",
    ".config/nvim", ".pythonrc", ".pythonstartup", ".local/lib", ".ipython/profile_default/startup",
    ".config/direnv", ".envrc", ".claude", ".claude.json",
]
SECRET_ABS_PATHS = [
    "/etc/shadow", "/etc/gshadow", "/etc/sudoers", "/root", "/var/run/docker.sock",
    "/run/docker.sock", "/run/user", "/var/run/user", "/run/containerd", "/run/podman",
    "/proc/kcore", "/var/lib/docker",
]
# Read-only system paths the interpreter and test suite legitimately read.
QUIET_READ_ROOTS = [
    "/usr", "/lib", "/lib32", "/lib64", "/libx32", "/bin", "/sbin", "/opt/pr-sandbox", "/audit",
    "/proc/self", "/proc/thread-self", "/sys/devices/system/cpu", "/sys/fs/cgroup",
    "/dev/null", "/dev/zero", "/dev/urandom", "/dev/random", "/dev/full", "/dev/shm", "/dev/tty",
    "/dev/pts", "/etc/ld.so.cache", "/etc/ld.so.preload", "/etc/localtime", "/etc/nsswitch.conf",
    "/etc/passwd", "/etc/group", "/etc/host.conf", "/etc/gai.conf", "/etc/mime.types",
    "/etc/timezone", "/sys/kernel/mm/transparent_hugepage", "/tmp", "/var/tmp",
    # Seen in a clean run of the test suite: allocator/CPU probing (numpy, polars/jemalloc),
    # and config lookups by the helper programs in KNOWN_BENIGN_EXEC.
    "/proc/meminfo", "/proc/stat", "/proc/cpuinfo", "/proc/sys/vm/overcommit_memory",
    "/etc/_rjem_malloc.conf", "/etc/malloc.conf", "/etc/ssl/openssl.cnf", "/etc/terminfo",
    "/etc/magic", "/etc/magic.mgc", "/etc/gitconfig", "/etc/mercurial", "/.git", "/.hg",
]
# Relative to $HOME. Config lookups made by libraries/helpers during a clean run.
BENIGN_HOME_READS = [
    ".editrc", ".inputrc", ".terminfo", ".magic", ".magic.mgc", ".gitconfig", ".config/git", ".hgrc",
]
# Programs a clean test run executes (platform.architecture() and pytest-benchmark's machine info).
# Matched on the exact argv; "{python}" stands for any python interpreter path.
KNOWN_BENIGN_EXEC = [
    ["file", "-b", "{python}"],
    ["git", "rev-parse", "--git-dir"],
    ["hg", "path", "default"],
    ["uname", "-p"],
]
WRITABLE_ROOTS = ["/tmp", "/var/tmp", "/dev/null", "/dev/shm", "/dev/tty", "/dev/pts", "/audit"]
# Writes a clean run makes outside the writable roots (they fail harmlessly in the sandbox).
KNOWN_BENIGN_WRITES = ["/var/lib/libuuid/clock.txt"]  # libuuid's time-based UUID state
# CPython's startup search for its stdlib walks up from the interpreter path, probing
# paths like /home/lib/python315.zip that don't exist.
INTERPRETER_PROBE_RE = re.compile(
    r"/lib(?:64)?/python3\d*(?:\.zip|\.\d+t?(?:/os\.py|/lib-dynload)?)$|/pybuilddir\.txt$")

PRIVILEGED_SYSCALLS = {
    "ptrace", "process_vm_readv", "process_vm_writev", "mount", "umount2", "pivot_root", "chroot",
    "unshare", "setns", "bpf", "init_module", "finit_module", "delete_module", "kexec_load",
    "kexec_file_load", "perf_event_open", "keyctl", "add_key", "request_key", "open_by_handle_at",
    "name_to_handle_at", "fanotify_init", "mount_setattr", "fsopen", "fsmount", "move_mount",
    "open_tree", "userfaultfd",
}
WRITE_SYSCALLS = {
    "mkdir", "mkdirat", "unlink", "unlinkat", "rename", "renameat", "renameat2", "rmdir", "symlink",
    "symlinkat", "link", "linkat", "chmod", "fchmodat", "fchmodat2", "chown", "lchown", "fchownat",
    "truncate", "utime", "utimes", "utimensat", "futimesat", "creat", "mknod", "mknodat",
    "setxattr", "lsetxattr", "removexattr", "lremovexattr", "setxattrat", "removexattrat",
}
NETWORK_ADDR_SYSCALLS = {"connect", "sendto", "sendmsg", "sendmmsg", "bind"}
PYTHON_BYPASS_FLAGS = set("IES")  # -I isolated, -E ignore PYTHON* env, -S no site: all skip the audit hook

STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"(\.\.\.)?')
LINE_RE = re.compile(r"^(\d+)\s+(?:\d\d:\d\d:\d\d(?:\.\d+)?\s+)?(.*)$")
CALL_RE = re.compile(r"^([a-z_0-9]+)\((.*)$")
RESUMED_RE = re.compile(r"^<\.\.\. ([a-z_0-9]+) resumed>(.*)$")
RESULT_RE = re.compile(r"\)\s+=\s+(-?\d+|0x[0-9a-f]+|\?)(?:<[^>]*>)?(?:\s+(E[A-Z0-9]+)\b.*)?$")
DIRFD_RE = re.compile(r"^(?:AT_FDCWD|-?\d+)<((?:[^>\\]|\\.)*)>")
FAMILY_RE = re.compile(r"sa_family=(AF_[A-Z0-9]+)")
PORT_RE = re.compile(r"(?:sin6?_port)=htons\((\d+)\)")
INET_ADDR_RE = re.compile(r'(?:inet_addr|inet_pton)\((?:AF_INET6?,\s*)?"([^"]*)"')
SUN_PATH_RE = re.compile(r'sun_path=(@?)"((?:[^"\\]|\\.)*)"')
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def clean(text, limit=400):
    """Make attacker-controlled text safe to print to a terminal or embed in Markdown."""
    text = CONTROL_RE.sub("?", str(text)).replace("`", "'")
    return text if len(text) <= limit else text[:limit] + "..."


def unescape(s):
    try:
        raw = s.encode("latin-1", "backslashreplace").decode("unicode_escape").encode("latin-1")
        return raw.decode("utf-8", "backslashreplace")
    except (UnicodeError, ValueError):
        return s


def under(path, root):
    root = root.rstrip("/") or "/"
    return path == root or path.startswith(root + "/")


def under_any(path, roots):
    return any(under(path, r) for r in roots)


def looks_like_python(path):
    return bool(re.match(r"^python(\d+(\.\d+)?)?t?$", os.path.basename(path)))


def benign_exec(argv):
    if not argv:
        return False
    argv = [os.path.basename(argv[0])] + list(argv[1:])
    for pattern in KNOWN_BENIGN_EXEC:
        if len(pattern) == len(argv) and all(
                p == a or (p == "{python}" and looks_like_python(a)) for p, a in zip(pattern, argv)):
            return True
    return False


class Analyzer:
    def __init__(self, home, src_root, allow_roots):
        self.home = os.path.normpath(home)
        self.src_root = os.path.normpath(src_root)
        self.allow_roots = [os.path.normpath(r) for r in allow_roots if r]
        self.findings = {}  # key -> finding
        self.executed = defaultdict(int)
        self.python_execs = 0
        self.audit_starts = 0
        self.unexpected_paths = defaultdict(int)

    # ---------- findings ----------
    def add(self, severity, category, detail, source, example=None):
        key = (severity, category, detail)
        f = self.findings.get(key)
        if f is None:
            f = self.findings[key] = {
                "severity": severity, "category": category, "detail": detail,
                "count": 0, "sources": set(), "examples": [],
            }
        f["count"] += 1
        f["sources"].add(source)
        if example and len(f["examples"]) < 3 and example not in f["examples"]:
            f["examples"].append(example)

    # ---------- path policy ----------
    def home_rel(self, path):
        if under(path, self.home):
            return os.path.relpath(path, self.home)
        return None

    def classify_path(self, path, write, source, example, failed=None):
        """Apply the file policy to one path access."""
        if not path or path.startswith(("pipe:", "socket:", "anon_inode:")):
            return
        path = os.path.normpath(path)
        status = f" ({failed})" if failed else ""
        if not write and (under_any(path, self.allow_roots) or any(under(r, path) for r in self.allow_roots)):
            return  # the read-only venv / interpreter (and the dirs above them), which may live under $HOME
        if not write and self.is_interpreter_probe(path):
            return  # CPython's startup search for its stdlib, e.g. ~/lib/python315.zip when Python lives under $HOME
        rel = self.home_rel(path)

        if rel is not None and rel != ".":
            if any(under(rel, p) for p in SECRET_HOME_PATHS):
                verb = "write to" if write else "access to"
                self.add(CRITICAL, "credentials", f"{verb} ~/{rel}{status}", source, example)
                return
            if write:
                if any(under(rel, p) for p in PERSISTENCE_HOME_PATHS):
                    self.add(CRITICAL, "persistence", f"write to ~/{rel}{status}", source, example)
                else:
                    self.add(HIGH, "home-write", f"write to ~/{rel}{status}", source, example)
                return
            if any(under(rel, p) for p in BENIGN_HOME_READS):
                self.add(LOW, "home-read", f"access to ~/{rel}{status}", source, example)
            else:
                self.add(MEDIUM, "home-read", f"access to ~/{rel}{status}", source, example)
            return
        if rel == ".":
            self.add(LOW, "home-read", f"access to $HOME itself{status}", source, example)
            return

        if under_any(path, SECRET_ABS_PATHS):
            self.add(CRITICAL, "credentials", f"access to {path}{status}", source, example)
            return
        if re.match(r"^/proc/(\d+|self|thread-self)/(environ|mem)$", path):
            self.add(HIGH, "process-snooping", f"access to {path}{status}", source, example)
            return
        if re.match(r"^/proc/\d+(/|$)", path) and not write:
            return  # the sandbox has its own PID namespace: only its own processes are visible

        if write:
            if under(path, self.src_root) or under_any(path, WRITABLE_ROOTS):
                return
            if path in KNOWN_BENIGN_WRITES:
                self.add(LOW, "unexpected-write", f"write to {path}{status}", source, example)
                return
            self.add(HIGH, "unexpected-write", f"write to {path}{status}", source, example)
            return

        expected = [
            path == "/", under(path, self.src_root), under_any(path, QUIET_READ_ROOTS),
            under_any(path, self.allow_roots), self.is_interpreter_probe(path),
        ]
        if any(expected):
            return
        if under(path, "/etc"):
            self.add(LOW, "system-recon", f"read {path}{status}", source, example)
        elif under_any(path, ["/home", "/var", "/mnt", "/media", "/srv", "/opt", "/run"]):
            self.add(HIGH, "outside-sandbox-read", f"access to {path}{status}", source, example)
        else:
            self.add(LOW, "unexpected-read", f"access to {path}{status}", source, example)
        self.unexpected_paths[path] += 1

    def is_interpreter_probe(self, path):
        """CPython looks for <prefix>/lib/pythonXY.zip etc. in every directory above its executable."""
        m = INTERPRETER_PROBE_RE.search(path)
        if not m:
            return False
        prefix = path[:m.start()] or "/"
        return any(under(root, prefix) for root in self.allow_roots)

    def is_python(self, path):
        return looks_like_python(path) and under_any(path, self.allow_roots + ["/usr/bin"])

    # ---------- strace ----------
    def feed_strace(self, lines):
        pending = {}
        armed = False  # ignore bwrap's own setup (mounts, unshare...) before the sandboxed command starts
        for line in lines:
            line = line.rstrip("\n")
            m = LINE_RE.match(line)
            if not m:
                continue
            pid, body = m.group(1), m.group(2)
            if body.startswith(("---", "+++")):
                continue
            rm = RESUMED_RE.match(body)
            if rm:
                name, rest = rm.groups()
                prev = pending.pop(pid, None)
                if prev is None or prev[0] != name:
                    continue
                args = prev[1] + rest
            else:
                cm = CALL_RE.match(body)
                if not cm:
                    continue
                name, args = cm.groups()
                if args.endswith("<unfinished ...>"):
                    pending[pid] = (name, args[: -len("<unfinished ...>")])
                    continue
            res = RESULT_RE.search(args)
            ret, err = (res.group(1), res.group(2)) if res else ("?", None)
            if not armed:
                if name in ("execve", "execveat") and ret == "0":
                    strings = STRING_RE.findall(args)
                    if strings and not unescape(strings[0][0]).endswith("/bwrap"):
                        armed = True
                    else:
                        continue
                else:
                    continue
            self.strace_event(pid, name, args, err, line)

    def strace_event(self, pid, name, args, err, line):
        source = "strace"
        example = clean(f"pid {pid}: {line.split(' ', 2)[-1]}", 300)
        failed = err

        if name in PRIVILEGED_SYSCALLS:
            self.add(HIGH, "privileged-syscall", f"{name}()", source, example)
            return

        if name in ("execve", "execveat"):
            strings = [unescape(s) for s, _ in STRING_RE.findall(args)]
            if not strings:
                return
            path = strings[0]
            argv = strings[1:12]
            if self.is_python(path):
                self.python_execs += 1
                flags = {c for a in argv[1:] if re.match(r"^-[A-Za-z]+$", a) for c in a[1:]}
                if flags & PYTHON_BYPASS_FLAGS:
                    self.add(MEDIUM, "audit-bypass",
                             f"python started with -{''.join(sorted(flags & PYTHON_BYPASS_FLAGS))} "
                             "(skips the audit hook; strace still sees it)", source, example)
                return
            self.executed[clean(" ".join(argv) or path)] += 1
            if benign_exec(argv):
                self.add(LOW, "exec", f"known helper: {clean(' '.join(argv), 120)}", source, example)
            else:
                self.add(HIGH, "exec", f"executed {path}{' (' + failed + ')' if failed else ''}",
                         source, clean(" ".join(argv)))
            return

        if name in NETWORK_ADDR_SYSCALLS:
            fam = FAMILY_RE.search(args)
            if not fam:
                return
            family = fam.group(1)
            if family in ("AF_INET", "AF_INET6"):
                addr_m = INET_ADDR_RE.search(args)
                port_m = PORT_RE.search(args)
                addr = addr_m.group(1) if addr_m else "?"
                port = port_m.group(1) if port_m else "?"
                where = f"{addr}:{port}"
                if name == "bind":
                    self.add(MEDIUM, "network", f"bind {family} {where}", source, example)
                elif port == "53":
                    self.add(HIGH, "network", f"DNS query attempt to {where}", source, example)
                elif addr.startswith("127.") or addr in ("::1", "0.0.0.0", "::"):
                    self.add(MEDIUM, "network", f"loopback {name} {where}", source, example)
                else:
                    self.add(HIGH, "network", f"outbound {name} to {where}", source, example)
            elif family == "AF_UNIX":
                sm = SUN_PATH_RE.search(args)
                if not sm:
                    return
                abstract, path = sm.group(1), unescape(sm.group(2))
                if abstract:
                    self.add(MEDIUM, "network", f"{name} abstract unix socket @{path}", source, example)
                elif not (under(path, "/tmp") or under(path, self.src_root)):
                    self.add(HIGH, "network", f"{name} unix socket {path}", source, example)
            elif family not in ("AF_NETLINK", "AF_UNSPEC"):
                self.add(HIGH, "network", f"{name} {family}", source, example)
            return

        if name == "socket":
            first = args.split(",", 1)[0].strip()
            if first in ("AF_PACKET", "AF_BLUETOOTH", "AF_CAN", "AF_VSOCK") or "SOCK_RAW" in args:
                self.add(HIGH, "network", f"socket({first}{', SOCK_RAW' if 'SOCK_RAW' in args else ''})",
                         source, example)
            return

        strings = STRING_RE.findall(args)
        if not strings:
            return
        dirfd = DIRFD_RE.match(args)
        base = unescape(dirfd.group(1)) if dirfd else self.src_root
        is_open = name in ("open", "openat", "openat2", "creat")
        write = name in WRITE_SYSCALLS or (is_open and re.search(r"O_(WRONLY|RDWR|CREAT|TRUNC|APPEND)", args))
        paths = [unescape(s) for s, _ in strings]
        if name in ("rename", "renameat", "renameat2", "link", "linkat", "symlink", "symlinkat"):
            paths = paths[:2]
            if name in ("symlink", "symlinkat"):
                paths = paths[1:]  # the link location is what gets written; the target is just a string
        else:
            paths = paths[:1]
        for p in paths:
            full = p if p.startswith("/") else os.path.join(base, p)
            self.classify_path(full, bool(write), source, example, failed)

    # ---------- audit hook ----------
    def feed_audit(self, lines):
        for line in lines:
            try:
                rec = json.loads(line)
            except ValueError:
                self.add(MEDIUM, "audit-log", "unparseable line in audit log (tampering?)", "audit")
                continue
            if not isinstance(rec, dict):
                continue
            self.audit_event(rec)

    def audit_event(self, rec):
        event = str(rec.get("event"))
        where = rec.get("where") or "(not called from PR code directly)"
        source = "audit"
        example = clean(f"{where}  [{event} {rec.get('args', rec.get('path', ''))}]", 300)
        args = [str(a) for a in rec.get("args", [])] if isinstance(rec.get("args"), list) else []

        if event == "pr-sandbox.start":
            self.audit_starts += 1
            return
        if "path" in rec:
            path = str(rec["path"])
            mode = str(rec.get("mode", "r"))
            write = event != "open" and event not in ("os.listdir", "os.scandir") or any(c in mode for c in "wax+")
            self.classify_path(path, write, source, example)
            return
        if event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex",
                     "socket.gethostbyaddr", "socket.getnameinfo"):
            host = args[0] if args else "?"
            if host.strip("'\"") in ("localhost", "127.0.0.1", "::1", "None", ""):
                self.add(LOW, "network", f"{event}({clean(host, 80)})", source, example)
            else:
                self.add(HIGH, "network", f"{event}({clean(host, 80)})", source, example)
            return
        if event.startswith("socket."):
            if args and "family=1," in args[0]:  # AF_UNIX; strace reports the socket paths precisely
                if "/tmp/" not in " ".join(args):
                    self.add(MEDIUM, "network", f"{event} unix socket {clean(args[-1], 120)}", source, example)
                return  # multiprocessing's sockets live in /tmp
            self.add(HIGH, "network", f"{event} {clean(args[-1] if args else '', 120)}", source, example)
            return
        if event in ("urllib.Request", "http.client.connect", "ftplib.connect", "smtplib.connect",
                     "poplib.connect", "imaplib.open", "nntplib.connect", "webbrowser.open"):
            self.add(HIGH, "network", f"{event} {clean(' '.join(args), 120)}", source, example)
            return
        if event in ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
                     "pty.spawn", "os.startfile", "os.forkpty"):
            target = args[0] if args else ""
            try:
                argv = ast.literal_eval(args[1]) if event == "subprocess.Popen" and len(args) > 1 else None
            except (ValueError, SyntaxError):
                argv = None
            if isinstance(argv, (list, tuple)) and benign_exec([str(a) for a in argv]):
                self.add(LOW, "exec", f"known helper: {clean(' '.join(map(str, argv)), 120)}", source, example)
            elif looks_like_python(target.strip("'\"")):
                self.add(LOW, "exec", f"{event} python", source, example)
            else:
                self.add(HIGH, "exec", f"{event} {clean(' '.join(args[:2]), 160)}", source, example)
            return
        if event in ("os.kill", "os.killpg"):
            self.add(LOW, "exec", event, source, example)
            return
        if event.startswith("ctypes."):
            # Locked dependencies use ctypes legitimately (e.g. polars' CPU feature check).
            sev = LOW if rec.get("origin") == "dependency" else MEDIUM
            what = clean(args[-1] if event.startswith("ctypes.dlsym") and args else " ".join(args[:1]), 80)
            self.add(sev, "native-code", f"{event} {what} (from {rec.get('origin', '?')} code)", source, example)
            return
        if event == "sys.remote_exec":
            self.add(HIGH, "process-snooping", event, source, example)
            return
        if event == "sys.addaudithook":
            self.add(MEDIUM, "audit-bypass", "another audit hook was added", source, example)
            return
        if event == "pickle.find_class":
            # multiprocessing ships bound methods as builtins.getattr(obj, name): routine when not PR-initiated.
            sev = LOW if args == ["builtins", "getattr"] and rec.get("origin") != "pr" else HIGH
            self.add(sev, "unsafe-pickle", f"pickle loads {'.'.join(args)} (from {rec.get('origin', '?')} code)",
                     source, example)
            return
        if event == "import":
            name = args[0] if args else "?"
            sev = LOW if name in ("base64", "zlib", "codecs", "marshal", "getpass", "pwd") else MEDIUM
            self.add(sev, "suspicious-import", f"PR code imports {name}", source, example)
            return
        if event in ("compile", "exec"):
            self.add(MEDIUM, "dynamic-code", f"PR code calls {event}()", source, example)
            return

    # ---------- home snapshot ----------
    def feed_home_diff(self, before, after):
        for rel in sorted(set(before) | set(after)):
            if before.get(rel) == after.get(rel):
                continue
            change = "created" if rel not in before else "deleted" if rel not in after else "modified"
            persistent = any(under(rel, p) for p in PERSISTENCE_HOME_PATHS)
            sev = CRITICAL if persistent or any(under(rel, p) for p in SECRET_HOME_PATHS) else HIGH
            self.add(sev, "persistence" if persistent else "home-write", f"~/{rel} was {change}", "home-diff")

    # ---------- output ----------
    def sanity_checks(self):
        if self.python_execs and not self.audit_starts:
            self.add(MEDIUM, "audit-log", "Python ran but the audit log has no start records "
                     "(hook not loaded, or log deleted/truncated)", "analyzer")

    def sorted_findings(self):
        return sorted(self.findings.values(), key=lambda f: (RANK[f["severity"]], f["category"], f["detail"]))

    def text_report(self):
        out = []
        findings = self.sorted_findings()
        counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
        out.append("PR sandbox monitor: " + ", ".join(f"{counts[s]} {s}" for s in SEVERITIES))
        for f in findings:
            out.append(f"  [{f['severity']:8}] {f['category']:20} {clean(f['detail'], 200)}"
                       f"  x{f['count']} via {'+'.join(sorted(f['sources']))}")
            for ex in f["examples"]:
                out.append(f"             e.g. {clean(ex, 250)}")
        if self.executed:
            out.append("Programs executed (other than python):")
            out.extend(f"  {clean(k, 200)}  x{v}" for k, v in sorted(self.executed.items()))
        return "\n".join(out)

    def markdown_report(self):
        findings = self.sorted_findings()
        counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
        out = ["## PR sandbox monitor", "",
               "| " + " | ".join(SEVERITIES) + " |", "|" + "---|" * len(SEVERITIES),
               "| " + " | ".join(str(counts[s]) for s in SEVERITIES) + " |", ""]
        if not findings:
            out.append("No suspicious behaviour was observed.")
            return "\n".join(out)
        out.append("Details contain text the PR controls. They are shown verbatim in code blocks.")
        out.append("")
        out.append("```text")
        for f in findings:
            out.append(f"[{f['severity']}] {f['category']}: {clean(f['detail'], 200)}  x{f['count']}")
            for ex in f["examples"]:
                out.append(f"    e.g. {clean(ex, 250)}")
        out.append("```")
        return "\n".join(out)

    def json_report(self):
        return [dict(f, sources=sorted(f["sources"])) for f in self.sorted_findings()]


def snapshot(directory, out_path):
    result = {}
    for root, _, files in os.walk(directory):
        for name in files:
            full = os.path.join(root, name)
            if os.path.islink(full) or not os.path.isfile(full):
                result[os.path.relpath(full, directory)] = "special:" + os.path.realpath(full)
                continue
            h = hashlib.sha256()
            with open(full, "rb") as fh:
                while chunk := fh.read(65536):
                    h.update(chunk)
            result[os.path.relpath(full, directory)] = h.hexdigest()
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("directory")
    snap.add_argument("out")
    rep = sub.add_parser("report")
    rep.add_argument("--strace")
    rep.add_argument("--audit")
    rep.add_argument("--home", required=True)
    rep.add_argument("--src-root", default="/work")
    rep.add_argument("--allow-root", action="append", default=[])
    rep.add_argument("--home-before")
    rep.add_argument("--home-after")
    rep.add_argument("--markdown")
    rep.add_argument("--json")
    rep.add_argument("--fail-on", choices=[s.lower() for s in SEVERITIES], default="high")
    args = parser.parse_args(argv)

    if args.cmd == "snapshot":
        snapshot(args.directory, args.out)
        return 0

    analyzer = Analyzer(args.home, args.src_root, args.allow_root)
    if args.strace:
        with open(args.strace, encoding="utf-8", errors="backslashreplace") as fh:
            analyzer.feed_strace(fh)
    if args.audit and os.path.exists(args.audit):
        with open(args.audit, encoding="utf-8", errors="backslashreplace") as fh:
            analyzer.feed_audit(fh)
    if args.home_before and args.home_after:
        with open(args.home_before) as a, open(args.home_after) as b:
            analyzer.feed_home_diff(json.load(a), json.load(b))
    analyzer.sanity_checks()
    if (args.strace and analyzer.python_execs == 0) or (not args.strace and analyzer.audit_starts == 0):
        print("ERROR: the sandboxed Python never started, so nothing was monitored. "
              "Check the output above for a bwrap/strace error.", file=sys.stderr)
        return 1

    print(analyzer.text_report())
    if args.markdown:
        with open(args.markdown, "w") as fh:
            fh.write(analyzer.markdown_report() + "\n")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(analyzer.json_report(), fh, indent=1)

    threshold = RANK[args.fail_on.upper()]
    return 2 if any(RANK[f["severity"]] <= threshold for f in analyzer.findings.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
