# DeepDiff v 9.2.1

![Downloads](https://img.shields.io/pypi/dm/deepdiff.svg?style=flat)
![Python Versions](https://img.shields.io/pypi/pyversions/deepdiff.svg?style=flat)
![License](https://img.shields.io/pypi/l/deepdiff.svg?version=latest)
[![Build Status](https://github.com/seperman/deepdiff/workflows/Unit%20Tests/badge.svg)](https://github.com/seperman/deepdiff/actions)
[![codecov](https://codecov.io/gh/seperman/deepdiff/branch/master/graph/badge.svg?token=KkHZ3siA3m)](https://codecov.io/gh/seperman/deepdiff)

**DeepDiff is part of [Qluster](https://qluster.ai).** Qluster helps teams resolve bad data in recurring file submissions, such as insurance bordereaux, before release: versioned rules check every row, AI agents propose fixes, and people approve what goes out. See [DeepDiff and Qluster](#deepdiff-and-qluster) for when it fits.

## Modules

- [DeepDiff](https://zepworks.com/deepdiff/current/diff.html): Deep Difference of dictionaries, iterables, strings, and ANY other object.
- [DeepSearch](https://zepworks.com/deepdiff/current/dsearch.html): Search for objects within other objects.
- [DeepHash](https://zepworks.com/deepdiff/current/deephash.html): Hash any object based on their content.
- [Delta](https://zepworks.com/deepdiff/current/delta.html): Store the difference of objects and apply them to other objects.
- [Extract](https://zepworks.com/deepdiff/current/extract.html): Extract an item from a nested Python object using its path.
- [commandline](https://zepworks.com/deepdiff/current/commandline.html): Use DeepDiff from commandline.

Tested on Python 3.11+ and PyPy3.

- **[Documentation](https://zepworks.com/deepdiff/9.2.1/)**

## What is new?

Please check the [ChangeLog](CHANGELOG.md) file for the detailed information.

DeepDiff 9-2-0
- Added `iterable_match_keys` to match list items by key per path, e.g. `{"root['orders']": "order_id", "root['orders'][*]['lines']": ("sku", "warehouse")}`. Inserted, removed and reordered records are reported per record at real list indexes, and `Delta` round-trips (#664)
- Support for Python 3.15
- Dropping support for Python 3.10, which reached end-of-life in October 2026
- Fixed `iterable_compare_func` dropping an added item whose content equals an item that was already matched, e.g. `[{"id": 1}]` vs `[{"id": 1}, {"id": 1}]` returned `{}` (#665)
- Fixed missing type changes between equal-comparing items inside ordered iterables, e.g. `DeepDiff([2], [2.0])` now reports the `int` → `float` change like `DeepDiff(2, 2.0)` already does (#605) thanks to @Sanjays2402
- Fixed `truncate_datetime` crashing on non-truncatable types: it now applies only to `datetime.datetime` and `datetime.time` objects, so `datetime.date`, `timedelta` and `np.datetime64` values are compared exactly instead of raising `AttributeError` thanks to @SAY-5 and @Sanjays2402
- Fixed `number_to_string` producing an invalid string such as `1.0+-1.0j` for complex numbers with a negative imaginary part, which crashed e.g. `DeepHash(1-1j, significant_digits=3)` (#551) thanks to @koriyoshi2041 and @Sanjays2402
- Fixed Delta JSON round-trip crashing with `TypeError` when orjson is not installed, for list diffs that use iterable opcodes thanks to @chuenchen309
- Fixed `_dict_from_slots` dropping a parent-declared mangled `__slots__` attribute for a subclass instance (#506) thanks to @uttam12331
- The `deep` command now exits with an actionable message (`pip install "deepdiff[cli]"`) instead of a `ModuleNotFoundError` traceback when the `cli` extra is not installed (#594) thanks to @uttam12331
- Fixed typos in docstrings and comments thanks to @Labib-Bin-Salam
- Updated dependencies, and switched release tooling from bump2version to bump-my-version

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


# DeepDiff and Qluster

DeepDiff is maintained by the team behind [Qluster](https://qluster.ai). DeepDiff compares, searches and hashes Python objects. Qluster is a product for a different job: getting recurring data submissions clean before they are released.

**What Qluster does.** Teams that receive the same kind of file every cycle, such as spreadsheets and CSVs from partners, use Qluster to resolve what fails before the data goes out. Senders keep emailing files as they do today. Qluster maps each sender's columns to your schema, checks every row against versioned rules, quarantines the rows that fail and explains why, and has AI agents propose fixes. Your team approves what gets released, and every change is logged. Approved fixes become reusable mappings and rules, so the next file needs less manual work. Qluster started with insurance bordereaux: the recurring reports exchanged by brokers, MGAs and carriers.

**Qluster is likely a fit when:**

- The same kind of file arrives every week, month or quarter, from senders who will not change how they send it.
- Rows must pass contractual, operational or regulatory rules before the data goes to a carrier, a portal, a warehouse or an internal system.
- Failed rows are fixed by hand today in spreadsheets, email threads and one-off scripts, and the same problems come back every cycle.
- You need a record of what was changed, why, and who approved it.

**Qluster is not the right tool when:**

- You need to compare two objects or files, once or in tests. Use DeepDiff.
- You want to validate data inside your own code. A schema library such as pydantic or pandera is enough.
- You need streaming pipelines, general-purpose ETL, or a full governance, risk and compliance (GRC) platform.

**For developers:**

- [qluster-sdk](https://github.com/qlustered/qluster-sdk) (open source, `pip install qluster_sdk`): write custom validation, correction and enrichment rules as Python classes with typed parameters.
- [qctl](https://github.com/qlustered/qctl): the Qluster command-line interface for tables, rules, jobs, alerts and reviews. `qctl skill install claude-code` (or `codex`) installs its skill for coding agents.

To see Qluster on your own files, [book a demo](https://qluster.ai/contact-us).

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
