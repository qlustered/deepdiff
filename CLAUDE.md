# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepDiff is a Python library for deep comparison, searching, and hashing of Python objects. It provides:
- **DeepDiff**: Deep difference detection between objects
- **DeepSearch**: Search for objects within other objects  
- **DeepHash**: Content-based hashing for any object
- **Delta**: Git-like diff objects that can be applied to other objects
- **CLI**: Command-line interface via `deep` command

## Development Commands

### Setup
```bash
# Install with all development dependencies
uv pip install -e ".[cli,coverage,dev,docs,static,test]"
# OR using uv (recommended)
uv sync --all-extras
```

**Virtual Environment**: Activate with `source ~/.venvs/deep/bin/activate` before running tests or Python commands


### Testing
```bash
# Run tests with coverage
source ~/.venvs/deep/bin/activate && pytest --cov=deepdiff --cov-report term-missing

# Run tests including slow ones
source ~/.venvs/deep/bin/activate && pytest --cov=deepdiff --runslow

# Run single test file
source ~/.venvs/deep/bin/activate && pytest tests/test_diff_text.py

# Run tests across multiple Python versions. No need to use this unless getting ready for creating a new build
source ~/.venvs/deep/bin/activate && nox -s pytest
```

### **Type Checking with Pyright:**
Always use this pattern for type checking:
```bash
source ~/.venvs/deep/bin/activate && pyright {file_path}
```

Examples:
- `source ~/.venvs/deep/bin/activate && pyright deepdiff/diff.py` - Type check specific file
- `source ~/.venvs/deep/bin/activate && pyright deepdiff/` - Type check entire module
- `source ~/.venvs/deep/bin/activate && pyright .` - Type check entire repo


### Common Pitfalls to Avoid

1. **Forgetting Virtual Environment**: ALWAYS activate venv before ANY Python command:
   ```bash
   source ~/.venvs/deep/bin/activate
   ```
2. **Running pytest without venv**: This will cause import errors. Always use:
   ```bash
   source ~/.venvs/deep/bin/activate && pytest
   ```
3. **Running module commands without venv**: Commands like `capi run`, `cettings shell`, etc. all require venv to be activated first
4. **Using `pip` instead of `uv pip`**: This project uses `uv` for package management. Always use `uv pip` instead of `pip`.


### Slow quality checks only to run before creating a build
```bash
# Linting (max line length: 120)
nox -s flake8

# Type checking
nox -s mypy

# Run all quality checks
nox
```


## Architecture

### Core Structure
- **deepdiff/diff.py**: Main DeepDiff implementation (most complex component)
- **deepdiff/deephash.py**: DeepHash functionality
- **deepdiff/base.py**: Shared base classes and functionality
- **deepdiff/model.py**: Core data structures and result objects
- **deepdiff/helper.py**: Utility functions and type definitions
- **deepdiff/delta.py**: Delta objects for applying changes

### Key Patterns
- **Inheritance**: `Base` class provides common functionality with mixins
- **Result Objects**: Different result formats (`ResultDict`, `TreeResult`, `TextResult`)
- **Path Navigation**: Consistent path notation for nested object access
- **Performance**: LRU caching and numpy array optimization

### Testing
- Located in `/tests/` directory
- Organized by functionality (e.g., `test_diff_text.py`, `test_hash.py`)
- Aims for ~100% test coverage
- Uses pytest with comprehensive fixtures

## Development Notes

- **Python Support**: 3.11+ and PyPy3
- **Main Branch**: `master` (PRs typically go to `dev` branch)
- **Build System**: Modern `pyproject.toml` with `flit_core`
- **Dependencies**: Core dependency is `orderly-set>=5.4.1,<6`
- **CLI Tool**: Available as `deep` command after installation with `[cli]` extra
