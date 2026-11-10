"""This module offers the DeepDiff, DeepSearch, grep, Delta and DeepHash classes."""
# flake8: noqa
__version__ = '9.1.0'
import logging

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)8s %(message)s')


from .diff import DeepDiff as DeepDiff
from .search import DeepSearch as DeepSearch, grep as grep
from .deephash import DeepHash as DeepHash
from .delta import Delta as Delta
from .path import extract as extract, parse_path as parse_path
from .json_diff import (
    CollectionStrategy as CollectionStrategy,
    CollectionStrategyError as CollectionStrategyError,
    DeepJSONDiff as DeepJSONDiff,
    DuplicateIdentityError as DuplicateIdentityError,
    DuplicateIdentityPolicy as DuplicateIdentityPolicy,
    IdentityExtractionError as IdentityExtractionError,
    MissingIdentityPolicy as MissingIdentityPolicy,
)
