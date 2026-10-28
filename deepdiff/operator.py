import re
from abc import ABCMeta, abstractmethod
from typing import Any, TYPE_CHECKING
from deepdiff.helper import convert_item_or_items_into_compiled_regexes_else_none

if TYPE_CHECKING:
    from deepdiff import DeepDiff
    from deepdiff.model import DiffLevel


class BaseOperatorPlus(metaclass=ABCMeta):

    @abstractmethod
    def match(self, level: "DiffLevel") -> bool:
        """
        Given a level which includes t1 and t2 in the tree view, is this operator a good match to compare t1 and t2?
        If yes, we will run the give_up_diffing to compare t1 and t2 for this level.
        """
        pass

    @abstractmethod
    def give_up_diffing(self, level: "DiffLevel", diff_instance: "DeepDiff") -> bool:
        """
        Given a level which includes t1 and t2 in the tree view, and the "distance" between l1 and l2.
        do we consider t1 and t2 to be equal or not. The distance is a number between zero to one and is calculated by DeepDiff to measure how similar objects are.
        """

    @abstractmethod
    def normalize_value_for_hashing(self, parent: Any, obj: Any) -> Any:
        """
        You can use this function to normalize values for ignore_order=True

        For example, you may want to turn all the words to be lowercase. Then you return obj.lower()
        """
        pass



class BaseOperator:
    regex_paths: list[re.Pattern[str]] | None
    types: list[type] | None

    def __init__(self, regex_paths: list[str] | None = None, types: list[type] | None = None):
        if regex_paths:
            self.regex_paths = convert_item_or_items_into_compiled_regexes_else_none(regex_paths)
        else:
            self.regex_paths = None
        self.types = types

    def match(self, level: "DiffLevel") -> bool:
        if self.regex_paths:
            for pattern in self.regex_paths:
                matched = re.search(pattern, level.path()) is not None
                if matched:
                    return True
        if self.types:
            for type_ in self.types:
                if isinstance(level.t1, type_) and isinstance(level.t2, type_):
                    return True
        return False

    def give_up_diffing(self, level: "DiffLevel", diff_instance: "DeepDiff") -> bool:
        raise NotImplementedError('Please implement the diff function.')


class PrefixOrSuffixOperator:

    def match(self, level: "DiffLevel") -> bool:
        return level.t1 and level.t2 and isinstance(level.t1, str) and isinstance(level.t2, str)

    def give_up_diffing(self, level: "DiffLevel", diff_instance: "DeepDiff") -> bool:
        t1 = level.t1
        t2 = level.t2
        return t1.startswith(t2) or t2.startswith(t1)
