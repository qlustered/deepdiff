# DeepDiff v 9.1.0

![Downloads](https://img.shields.io/pypi/dm/deepdiff.svg?style=flat)
![Python Versions](https://img.shields.io/pypi/pyversions/deepdiff.svg?style=flat)
![License](https://img.shields.io/pypi/l/deepdiff.svg?version=latest)
[![Build Status](https://github.com/seperman/deepdiff/workflows/Unit%20Tests/badge.svg)](https://github.com/seperman/deepdiff/actions)
[![codecov](https://codecov.io/gh/seperman/deepdiff/branch/master/graph/badge.svg?token=KkHZ3siA3m)](https://codecov.io/gh/seperman/deepdiff)

**DeepDiff is now part of [Qluster](/qluster).**

*If you're building workflows around data validation and correction, [Qluster](/qluster) gives your team a structured way to manage rules, review failures, approve fixes, and reuse decisions—without building the entire system from scratch.*

## Modules

- [DeepDiff](https://zepworks.com/deepdiff/current/diff.html): Deep Difference of dictionaries, iterables, strings, and ANY other object.
- [DeepSearch](https://zepworks.com/deepdiff/current/dsearch.html): Search for objects within other objects.
- [DeepHash](https://zepworks.com/deepdiff/current/deephash.html): Hash any object based on their content.
- [Delta](https://zepworks.com/deepdiff/current/delta.html): Store the difference of objects and apply them to other objects.
- [Extract](https://zepworks.com/deepdiff/current/extract.html): Extract an item from a nested Python object using its path.
- [commandline](https://zepworks.com/deepdiff/current/commandline.html): Use DeepDiff from commandline.

Tested on Python 3.11+ and PyPy3.

- **[Documentation](https://zepworks.com/deepdiff/9.1.0/)**

## What is new?

Please check the [ChangeLog](CHANGELOG.md) file for the detailed information.

DeepDiff 9-1-0
- Added multiprocessing support for DeepDiff: parallel distance computation and parallel subtree diffing with aggregated worker stats, deterministic ordering, and automatic fallback to serial when unsafe (e.g. `custom_operators`, `*_obj_callback`, `ignore_order_func`)
- Added wildcard/glob pattern support for `exclude_paths` and `include_paths` thanks to @akshat62
- Reimplemented internal cache for improved performance
- Memoized `GlobPathMatcher` to remove exponential-time matching cliff
- Comprehensive type-hint corrections across `deephash.py`, `helper.py`, `delta.py`, `diff.py`, `distance.py`, `path.py`, and `serialization.py` (also fixed real bugs: misplaced paren in `path._guess_type` call, and `len(other.indexes > 1)` → `len(other.indexes) > 1` in `diff._compare_in_order`)
- Security: Delta dunder-attribute traversal in `check_elem()` now raises immediately instead of going through `_raise_or_log()`, with full-path preflight validation in `_get_elements_and_details()` so the `set_item_added` path cannot silently skip malicious dunder paths
- Fixed nested NamedTuple set/frozenset Delta updates dropping the outer container
- Fixed tuple Deltas using iterable opcodes silently doing nothing for insert/delete-only changes
- Fixed Delta with both moved and added iterable items mutating the Delta's own internal diff data
- Fixed crash during path sorting when removing multiple dictionary items with complex keys
- Packaging: added missing files to sdist and removed obsolete `MANIFEST.in` thanks to @mgorny
- Updated GitHub Actions workflows and dependencies

## Installation

### Install from PyPi:

`pip install deepdiff`

If you want to use DeepDiff from commandline:

`pip install "deepdiff[cli]"`

If you want to improve the performance of DeepDiff with certain functionalities such as improved json serialization:

`pip install "deepdiff[optimize]"`

Install optional packages:
- [yaml](https://pypi.org/project/PyYAML/)
- [tomli-w](https://pypi.org/project/tomli-w/) for writing
- [clevercsv](https://pypi.org/project/clevercsv/) for more robust CSV parsing
- [orjson](https://pypi.org/project/orjson/) for speed and memory optimized parsing
- [pydantic](https://pypi.org/project/pydantic/)


# Documentation

<https://zepworks.com/deepdiff/current/>

# ChangeLog

Please take a look at the [CHANGELOG](CHANGELOG.md) file.

# Survey

:mega: **Please fill out our [fast 10-question survey](https://tally.so/r/J98MPY)** so that we can learn how & why you use DeepDiff, and what improvements we should make. Thank you! :dancers:

# Local dev

1. Clone the repo
2. Switch to the dev branch
3. Create your own branch
4. Install dependencies

    - Method 1: Use [`uv`](https://github.com/astral-sh/uv) to install the dependencies:  `uv sync --all-extras`.
    - Method 2: Use pip: `pip install -e ".[cli,coverage,dev,docs,static,test]"`
5. Build `uv build`

# Contribute

1. Please make your PR against the dev branch
2. Please make sure that your PR has tests. Since DeepDiff is used in many sensitive data driven projects, we strive to maintain around 100% test coverage on the code.

Please run `pytest --cov=deepdiff --runslow` to see the coverage report. Note that the `--runslow` flag will run some slow tests too. In most cases you only want to run the fast tests which so you won't add the `--runslow` flag.

Or to see a more user friendly version, please run: `pytest --cov=deepdiff --cov-report term-missing --runslow`.

Thank you!

# Authors

Please take a look at the [AUTHORS](AUTHORS.md) file.
