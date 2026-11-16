"""PR sandbox audit hook (PEP 578).

This file is put first on PYTHONPATH inside the sandbox, so every Python process
started there (pytest, multiprocessing workers, subprocesses that don't pass -I/-S)
loads it at startup and installs an audit hook. The hook logs security-relevant
events (file access outside the sandbox's expected paths, network, process
spawning, ctypes, dangerous pickle globals, ...) to a JSONL file, together with
the PR source line that triggered them.

Limits: this runs in the same process as the untrusted code, so treat the log as
best-effort. Untrusted code can't remove an audit hook, but it can corrupt or
truncate the log file, or start a Python with -I to skip this file. The strace
log written by the host, outside the sandbox, is the tamper-proof record. This
log adds the Python-level "which test, which line" attribution.
"""
import json
import os
import sys
import threading
from typing import TextIO

_LOG_PATH = os.environ.get("PR_SANDBOX_AUDIT_LOG")
_SRC_ROOT = os.environ.get("PR_SANDBOX_SRC_ROOT", "/work").rstrip("/") + "/"

# Paths the code under test is expected to touch. Opens under these prefixes are not logged.
_QUIET_PREFIXES = tuple(
    p.rstrip("/") + "/"
    for p in {
        _SRC_ROOT, "/tmp", "/usr", "/lib", "/lib64", "/opt/pr-sandbox", "/audit",
        sys.prefix, sys.base_prefix, os.path.realpath(sys.base_prefix),
    }
) + ("/dev/null", "/dev/urandom", "/proc/self/", "/sys/devices/system/cpu/", "/sys/fs/cgroup/")

_NETWORK_EVENTS = {
    "socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg",
    "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex",
    "socket.gethostbyaddr", "socket.getnameinfo",
    "urllib.Request", "http.client.connect", "ftplib.connect", "smtplib.connect",
    "poplib.connect", "imaplib.open", "nntplib.connect", "webbrowser.open",
}
_PROCESS_EVENTS = {
    "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
    "os.startfile", "pty.spawn", "os.forkpty", "os.kill", "os.killpg",
}
_NATIVE_EVENTS = {"ctypes.dlopen", "ctypes.dlsym", "ctypes.dlsym/handle", "sys.addaudithook", "sys.remote_exec"}
_PATH_EVENTS = {
    "open", "os.listdir", "os.scandir", "os.chmod", "os.chown", "os.remove", "os.rename",
    "os.rmdir", "os.mkdir", "os.symlink", "os.link", "os.truncate", "os.utime",
    "shutil.rmtree", "shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.move",
}
# Modules whose direct import by PR code is worth a human look (not proof of anything).
_WATCHED_IMPORTS = {
    "socket", "ssl", "subprocess", "ctypes", "pty", "urllib.request", "http.client",
    "ftplib", "smtplib", "telnetlib", "requests", "httpx", "aiohttp", "paramiko",
    "base64", "zlib", "marshal", "codecs", "webbrowser", "getpass", "pwd",
}
_DANGEROUS_PICKLE_MODULES = {
    "os", "posix", "nt", "subprocess", "sys", "socket", "shutil", "importlib",
    "runpy", "pty", "ctypes", "code", "codeop", "webbrowser", "pickle", "_pickle",
}
_DANGEROUS_PICKLE_BUILTINS = {
    "eval", "exec", "compile", "__import__", "getattr", "setattr", "open", "input", "breakpoint",
}

_tls = threading.local()
_log: "TextIO | None" = None


def _short(value, limit=300):
    try:
        if isinstance(value, bytes):
            value = value.decode("utf-8", "backslashreplace")
        text = value if isinstance(value, str) else repr(value)
    except Exception:  # noqa: BLE001 - never let the hook break the program
        text = "<unrepr-able>"
    return text if len(text) <= limit else text[:limit] + "..."


def _frames():
    """Call stack of the code that raised the event, innermost first, minus this file."""
    frame = sys._getframe(1)
    out = []
    while frame is not None and len(out) < 40:
        code = frame.f_code
        if code.co_filename != __file__:
            out.append((code.co_filename, frame.f_lineno, code.co_name))
        frame = frame.f_back
    return out


def _is_src(filename):
    return filename.startswith(_SRC_ROOT)


def _immediate_caller(frames, skip_import_machinery):
    """The frame that directly triggered the event.

    With skip_import_machinery, importlib frames are skipped, giving the frame holding the
    `import` statement. Without it, an event raised by importlib itself (e.g. the `exec`
    of every freshly imported module) is attributed to importlib, i.e. not to PR code.
    """
    for frame in frames:
        if skip_import_machinery and frame[0].startswith("<frozen importlib"):
            continue
        return frame
    return None


_STDLIB_DIRS = tuple({os.path.dirname(os.__file__) + "/", os.path.realpath(os.path.dirname(os.__file__)) + "/"})
_VENV_PREFIX = sys.prefix.rstrip("/") + "/"


def _origin(frames):
    """Who triggered the event: the innermost frame that isn't the stdlib or import machinery."""
    for filename, _lineno, _name in frames:
        if filename.startswith("<frozen") or (filename.startswith(_STDLIB_DIRS) and "-packages/" not in filename):
            continue
        if _is_src(filename):
            return "pr"
        if filename.startswith(_VENV_PREFIX):
            return "dependency"
        return "other"
    return "stdlib"


def _where(frames):
    for filename, lineno, name in frames:
        if _is_src(filename):
            return f"{filename[len(_SRC_ROOT):]}:{lineno} in {name}"
    return None


def _path_of(args):
    if not args:
        return None
    path = args[0]
    if isinstance(path, int) or path is None:
        return None
    try:
        path = os.fsdecode(path)
    except Exception:  # noqa: BLE001
        return None
    if not path.startswith("/"):
        try:
            path = os.path.join(os.getcwd(), path)
        except OSError:
            pass
    return os.path.normpath(path)


def _emit(record):
    if _log is None:
        return
    try:
        _log.write(json.dumps(record, default=_short) + "\n")
    except Exception:  # noqa: BLE001
        pass


def _hook(event, args):
    if getattr(_tls, "busy", False):
        return
    _tls.busy = True
    try:
        _handle(event, args)
    except Exception:  # noqa: BLE001
        pass
    finally:
        _tls.busy = False


def _handle(event, args):
    record: dict[str, object]
    if event in _PATH_EVENTS:
        path = _path_of(args)
        if path is None or path.startswith(_QUIET_PREFIXES):
            return
        record = {"path": path}
        if event == "open" and len(args) > 1:
            record["mode"] = _short(args[1])
    elif event in _NETWORK_EVENTS or event in _PROCESS_EVENTS or event in _NATIVE_EVENTS:
        record = {"args": [_short(a) for a in args]}
    elif event == "pickle.find_class":
        module, name = args
        if module in _DANGEROUS_PICKLE_MODULES or (module == "builtins" and name in _DANGEROUS_PICKLE_BUILTINS):
            record = {"args": [module, name]}
        else:
            return
    elif event == "import":
        name = args[0]
        if name not in _WATCHED_IMPORTS:
            return
        caller = _immediate_caller(_frames(), skip_import_machinery=True)
        if caller is None or not _is_src(caller[0]):
            return  # only flag imports made directly by PR code
        record = {"args": [name]}
    elif event in ("compile", "exec"):
        caller = _immediate_caller(_frames(), skip_import_machinery=False)
        if caller is None or not _is_src(caller[0]):
            return  # only flag dynamic code run directly by PR code (not by importlib or pytest)
        record = {"args": [_short(args[0], 200)]}
    else:
        return

    frames = _frames()
    record.update({
        "event": event,
        "pid": os.getpid(),
        "where": _where(frames),
        "origin": _origin(frames),
        "stack": [f"{f}:{ln}" for f, ln, _ in frames[:8]],
    })
    _emit(record)


def _install():
    global _log
    if not _LOG_PATH:
        return
    try:
        _log = open(_LOG_PATH, "a", buffering=1, encoding="utf-8")
    except OSError:
        return
    sys.addaudithook(_hook)
    # Lets the analyzer notice when Python ran but the log stayed empty (hook bypassed or log wiped).
    _emit({"event": "pr-sandbox.start", "pid": os.getpid(), "argv": list(getattr(sys, "argv", []))[:6]})


_install()
