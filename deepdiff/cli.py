"""Console-script entry point for the ``deep`` command.

The command line dependencies (``click``, and ``pyyaml`` for YAML files) are
optional and installed via the ``cli`` extra (``pip install deepdiff[cli]``).
The ``deep`` script itself is always installed, so importing
:mod:`deepdiff.commands` directly raises a bare
``ModuleNotFoundError: No module named 'click'`` on a default install
(see https://github.com/seperman/deepdiff/issues/594). This thin wrapper checks
for the dependency first and exits with an actionable message instead of a
traceback.
"""

import sys


def main():
    """Entry point for the ``deep`` console script."""
    try:
        import click  # noqa: F401
    except ImportError:
        sys.exit(
            "The 'deep' command line tool requires extra dependencies that are "
            "not installed.\n"
            "Install them with:\n\n    pip install deepdiff[cli]\n"
        )

    from deepdiff.commands import cli

    cli()
