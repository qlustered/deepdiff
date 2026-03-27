"""nox configuration file."""

# ruff: noqa: ANN001, D401

import nox


@nox.session
def flake8(session) -> None:
    """Run flake8."""
    posargs = session.posargs if session.posargs else ["deepdiff"]
    session.install(".[cli,dev,static]")
    session.run(
        "python",
        "-m",
        "flake8",
        *posargs,
    )


@nox.session
def mypy(session) -> None:
    """Run mypy."""
    posargs = session.posargs if session.posargs else ["deepdiff"]
    session.install(".[cli,dev,static]")
    session.run(
        "python",
        "-m",
        "mypy",
        "--install-types",
        "--non-interactive",
        *posargs,
    )


@nox.session(python=["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"])
def pytest(session) -> None:
    """Test with pytest."""
    posargs = session.posargs if session.posargs else ["-vv", "tests"]
    session.install(".[cli,dev,static,test]")
    session.run(
        "python",
        "-m",
        "pytest",
        "--cov=deepdiff",
        "--cov-report",
        "term-missing",
        *posargs,
    )
