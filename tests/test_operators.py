import re
import math
import pytest
from copy import deepcopy
from typing import List, Any
from deepdiff import DeepDiff
from deepdiff.operator import BaseOperator, PrefixOrSuffixOperator, BaseOperatorPlus


class TestOperators:
    @pytest.mark.parametrize('exclude_options', [
        {'exclude_paths': ['b']},
        {'exclude_paths': ["root['b']"]},
        {'exclude_regex_paths': [r"\['b'\]$"]},
        {'exclude_obj_callback': lambda obj, path: path == "root['b']"},
    ])
    @pytest.mark.parametrize('prevent_default', [False, True])
    def test_custom_operator_skips_excluded_paths(self, exclude_options, prevent_default):
        matched_paths = []
        compared_paths = []

        class CustomClass:
            def __init__(self, values):
                self.values = values

        class ListMatchOperator(BaseOperator):
            def match(self, level):
                matched_paths.append(level.path())
                return super().match(level)

            def give_up_diffing(self, level, diff_instance):
                compared_paths.append(level.path())
                if level.t1.values == level.t2.values:
                    diff_instance.custom_report_result('equal_lists', level, {})
                return prevent_default

        shared = CustomClass([1, 2, 3])
        t1 = {'a': shared, 'b': CustomClass([1, 2, 3])}
        t2 = {'a': shared, 'b': CustomClass([1, 2, 3, 4])}

        result = DeepDiff(t1, t2, custom_operators=[ListMatchOperator(types=[CustomClass])], **exclude_options)

        assert "root['b']" not in matched_paths
        assert compared_paths == ["root['a']"]
        assert result == {'equal_lists': {"root['a']": {}}}

    @pytest.mark.parametrize('exclude_options', [
        {'exclude_paths': ['root']},
        {'exclude_types': [dict]},
    ])
    def test_custom_operator_skips_excluded_root(self, exclude_options):
        class UnexpectedOperator(BaseOperator):
            def match(self, level):
                raise AssertionError('Excluded objects should not reach custom operators')

        result = DeepDiff({'a': 1}, {'a': 2}, custom_operators=[UnexpectedOperator()], **exclude_options)

        assert result == {}

    def test_custom_operators_prevent_default(self):
        t1 = {
            "coordinates": [
                {"x": 5, "y": 5},
                {"x": 8, "y": 8}
            ]
        }

        t2 = {
            "coordinates": [
                {"x": 6, "y": 6},
                {"x": 88, "y": 88}
            ]
        }

        class L2DistanceDifferWithPreventDefault(BaseOperator):
            def __init__(self, regex_paths: List[str], distance_threshold: float):
                super().__init__(regex_paths)
                self.distance_threshold = distance_threshold

            def _l2_distance(self, c1, c2):
                return math.sqrt(
                    (c1["x"] - c2["x"]) ** 2 + (c1["y"] - c2["y"]) ** 2
                )

            def give_up_diffing(self, level, diff_instance) -> bool:
                l2_distance = self._l2_distance(level.t1, level.t2)
                if l2_distance > self.distance_threshold:
                    diff_instance.custom_report_result('distance_too_far', level, {
                        "l2_distance": l2_distance
                    })
                return True

        ddiff = DeepDiff(t1, t2, custom_operators=[L2DistanceDifferWithPreventDefault(
            ["^root\\['coordinates'\\]\\[\\d+\\]$"],
            1
        )])

        expected = {
            'distance_too_far': {
                "root['coordinates'][0]": {'l2_distance': 1.4142135623730951},
                "root['coordinates'][1]": {'l2_distance': 113.13708498984761}
            }
        }
        assert expected == ddiff

    def test_custom_operators_not_prevent_default(self):
        t1 = {
            "coordinates": [
                {"x": 5, "y": 5},
                {"x": 8, "y": 8}
            ]
        }

        t2 = {
            "coordinates": [
                {"x": 6, "y": 6},
                {"x": 88, "y": 88}
            ]
        }

        class L2DistanceDifferWithPreventDefault(BaseOperator):
            def __init__(self, regex_paths, distance_threshold):
                super().__init__(regex_paths)
                self.distance_threshold = distance_threshold

            def _l2_distance(self, c1, c2):
                return math.sqrt(
                    (c1["x"] - c2["x"]) ** 2 + (c1["y"] - c2["y"]) ** 2
                )

            def give_up_diffing(self, level, diff_instance) -> bool:
                l2_distance = self._l2_distance(level.t1, level.t2)
                if l2_distance > self.distance_threshold:
                    diff_instance.custom_report_result('distance_too_far', level, {
                        "l2_distance": l2_distance
                    })
                #
                return False

        ddiff = DeepDiff(t1, t2, custom_operators=[L2DistanceDifferWithPreventDefault(
            ["^root\\['coordinates'\\]\\[\\d+\\]$"],
            1
        )
        ])
        expected = {
            'values_changed': {
                "root['coordinates'][0]['x']": {'new_value': 6, 'old_value': 5},
                "root['coordinates'][0]['y']": {'new_value': 6, 'old_value': 5},
                "root['coordinates'][1]['x']": {'new_value': 88, 'old_value': 8},
                "root['coordinates'][1]['y']": {'new_value': 88, 'old_value': 8}
            },
            'distance_too_far': {
                "root['coordinates'][0]": {'l2_distance': 1.4142135623730951},
                "root['coordinates'][1]": {'l2_distance': 113.13708498984761}
            }
        }
        assert expected == ddiff

    def test_custom_operators_should_not_equal(self):
        t1 = {
            "id": 5,
            "expect_change_pos": 10,
            "expect_change_neg": 10,
        }

        t2 = {
            "id": 5,
            "expect_change_pos": 100,
            "expect_change_neg": 10,
        }

        class ExpectChangeOperator(BaseOperator):
            def __init__(self, regex_paths):
                super().__init__(regex_paths)

            def give_up_diffing(self, level, diff_instance) -> bool:
                if level.t1 == level.t2:
                    diff_instance.custom_report_result('unexpected:still', level, {
                        "old": level.t1,
                        "new": level.t2
                    })

                return True

        ddiff = DeepDiff(t1, t2, custom_operators=[
            ExpectChangeOperator(regex_paths=["root\\['expect_change.*'\\]"])
        ])

        assert ddiff == {'unexpected:still': {"root['expect_change_neg']": {'old': 10, 'new': 10}}}

    def test_custom_operator2(self):

        class CustomClass:

            def __init__(self, d: dict, l: list):
                self.dict = d
                self.dict['list'] = l

            def __repr__(self):
                return "Class list is " + str(self.dict['list'])

        custom1 = CustomClass(d=dict(a=1, b=2), l=[1, 2, 3])
        custom2 = CustomClass(d=dict(c=3, d=4), l=[1, 2, 3, 2])
        custom3 = CustomClass(d=dict(a=1, b=2), l=[1, 2, 3, 4])

        class ListMatchOperator(BaseOperator):

            def give_up_diffing(self, level, diff_instance) -> bool:
                if set(level.t1.dict['list']) == set(level.t2.dict['list']):
                    return True
                return False

        ddiff = DeepDiff(custom1, custom2, custom_operators=[
            ListMatchOperator(types=[CustomClass])
        ])

        assert {} == ddiff

        ddiff2 = DeepDiff(custom2, custom3, threshold_to_diff_deeper=0, custom_operators=[
            ListMatchOperator(types=[CustomClass])
        ])

        expected = {
            'dictionary_item_added': ["root.dict['a']", "root.dict['b']"],
            'dictionary_item_removed': ["root.dict['c']", "root.dict['d']"],
            'values_changed': {"root.dict['list'][3]": {'new_value': 4, 'old_value': 2}}}

        assert expected == ddiff2

    def test_include_only_certain_path(self):

        class MyOperator:

            def __init__(self, include_paths):
                self.include_paths = include_paths

            def match(self, level) -> bool:
                return True

            def give_up_diffing(self, level, diff_instance) -> bool:
                return level.path() not in self.include_paths

        t1 = {'a': [10, 11], 'b': [20, 21], 'c': [30, 31]}
        t2 = {'a': [10, 22], 'b': [20, 33], 'c': [30, 44]}

        ddiff = DeepDiff(t1, t2, custom_operators=[
            MyOperator(include_paths="root['a'][1]")
        ])

        expected = {'values_changed': {"root['a'][1]": {'new_value': 22, 'old_value': 11}}}
        assert expected == ddiff

    def test_give_up_diffing_on_first_diff(self):

        class MyOperator:

            def match(self, level) -> bool:
                return True

            def give_up_diffing(self, level, diff_instance) -> bool:
                return any(diff_instance.tree.values())

        t1 = [[1, 2], [3, 4], [5, 6]]
        t2 = [[1, 3], [3, 5], [5, 7]]

        ddiff = DeepDiff(t1, t2, custom_operators=[
            MyOperator()
        ])

        expected = {'values_changed': {'root[0][1]': {'new_value': 3, 'old_value': 2}}}
        assert expected == ddiff

    def test_prefix_or_suffix_diff(self):

        t1 = {
            "key1": ["foo", "bar's food", "jack", "joe"]
        }
        t2 = {
            "key1": ["foo", "bar", "jill", "joe'car"]
        }

        ddiff = DeepDiff(t1, t2, custom_operators=[
            PrefixOrSuffixOperator()
        ])

        expected = {'values_changed': {"root['key1'][2]": {'new_value': 'jill', 'old_value': 'jack'}}}
        assert expected == ddiff

        with pytest.raises(NotImplementedError) as exp:
            DeepDiff(t1, t2, ignore_order=True, custom_operators=[
                PrefixOrSuffixOperator()
            ])
        expected2 = 'PrefixOrSuffixOperator needs to define a normalize_value_for_hashing method to be compatible with ignore_order=True or iterable_compare_func.'
        assert expected2 == str(exp.value)

    def test_custom_operator3_small_numbers(self):
        x = [2.0000000000000027, 2.500000000000005, 2.000000000000002, 3.000000000000001]
        y = [2.000000000000003, 2.500000000000005, 2.0000000000000027, 3.0000000000000027]
        result = DeepDiff(x, y)
        expected = {
            'values_changed': {
                'root[0]': {'new_value': 2.000000000000003, 'old_value': 2.0000000000000027},
                'root[2]': {'new_value': 2.0000000000000027, 'old_value': 2.000000000000002},
                'root[3]': {'new_value': 3.0000000000000027, 'old_value': 3.000000000000001}}}
        assert expected == result

        class CustomCompare(BaseOperatorPlus):
            def __init__(self, tolerance, types):
                self.tolerance = tolerance
                self.types = types

            def match(self, level) -> bool:
                if type(level.t1) in self.types:
                    return True
                return False

            def give_up_diffing(self, level, diff_instance) -> bool:
                relative = abs(abs(level.t1 - level.t2) / level.t1)
                if not max(relative, self.tolerance) == self.tolerance:
                    custom_report = f'relative diff: {relative:.8e}'
                    diff_instance.custom_report_result('diff', level, custom_report)
                return True

            def normalize_value_for_hashing(self, parent: Any, obj: Any) -> Any:
                return obj


        def compare_func(x, y, level):
            return True

        operators = [CustomCompare(types=[float], tolerance=5.5e-5)]
        result2 = DeepDiff(x, y, custom_operators=operators, iterable_compare_func=compare_func)
        assert {} == result2

        result3 = DeepDiff(x, y, custom_operators=operators, zip_ordered_iterables=True)
        assert {} == result3, "We should get the same result as result2 when zip_ordered_iterables is True."

    def test_custom_operator_and_ignore_order1_using_base_operator_plus(self):

        d1 = {
            "Name": "SUB_OBJECT_FILES",
            "Values": {
                "Value": [
                    "{f254498b-b752-4f35-bef5-6f1844b61eb7}",
                    "{7fb2a550-1849-45c0-b273-9aa5e4eb9f2b}",
                    "{3a614c62-4252-48eb-b279-1450ee8af182}",
                    "{208f22c4-c256-4311-9a45-e6c37d343458}",
                    "{1fcf5d37-ef19-43a7-a1ad-d17c7c1713c6}",
                ]
            }
        }

        d2 = {
            "Name": "SUB_OBJECT_FILES",
            "Values": {
                "Value": [
                    "{e5d18917-1a2c-4abe-b601-8ec002629953}",
                    "{ea71ba1f-1339-4fae-bc28-a9ce9b8a8c67}",
                    "{66bb6192-9cd2-4074-8be1-f2ac52877c70}",
                    "{0c88b900-3755-4d10-93ef-b6a96dbcba90}",
                    "{e39fdfc5-be6c-4f97-9345-9a8286381fe7}"
                ]
            }
        }


        class RemoveGUIDsOperator(BaseOperatorPlus):
            _pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
            _substitute = "guid"

            def match(self, level) -> bool:
                return isinstance(level.t1, str) and isinstance(level.t2, str)

            @classmethod
            def _remove_pattern(cls, t: str):
                return re.sub(cls._pattern, cls._substitute, t)

            def give_up_diffing(self, level, diff_instance):
                t1 = self._remove_pattern(level.t1)
                t2 = self._remove_pattern(level.t2)
                return t1 == t2

            def normalize_value_for_hashing(self, parent: Any, obj: Any) -> Any:
                """
                Used for ignore_order=True
                """
                if isinstance(obj, str):
                    return self._remove_pattern(obj)
                return obj


        operator = RemoveGUIDsOperator()

        diff1 = DeepDiff(d1, d2, custom_operators=[operator], log_stacktrace=True)
        assert not diff1


        diff2 = DeepDiff(d1, d2, ignore_order=True, custom_operators=[operator], log_stacktrace=True)
        assert not diff2


    def test_custom_operator_and_ignore_order2(self):
        d1 = {
            "Entity": {
                "Property": {
                    "Name": "SUB_OBJECT_FILES",
                    "Values": {
                        "Value": [
                            "{f254498b-b752-4f35-bef5-6f1844b61eb7}",
                            "{7fb2a550-1849-45c0-b273-9aa5e4eb9f2b}",
                            "{3a614c62-4252-48eb-b279-1450ee8af182}",
                            "{208f22c4-c256-4311-9a45-e6c37d343458}",
                            "{1fcf5d37-ef19-43a7-a1ad-d17c7c1713c6}",
                            "{a9cbecc0-21dc-49ce-8b2c-d36352dae139}"
                        ]
                    }
                }
            }
        }

        d2 = {
            "Entity": {
                "Property": {
                    "Name": "SUB_OBJECT_FILES",
                    "Values": {
                        "Value": [
                            "{e5d18917-1a2c-4abe-b601-8ec002629953}",
                            "{ea71ba1f-1339-4fae-bc28-a9ce9b8a8c67}",
                            "{d7778018-a7b5-4246-8caa-f590138d99e5}",
                            "{66bb6192-9cd2-4074-8be1-f2ac52877c70}",
                            "{0c88b900-3755-4d10-93ef-b6a96dbcba90}",
                            "{e39fdfc5-be6c-4f97-9345-9a8286381fe7}"
                        ]
                    }
                }
            }
        }

        class RemovePatternOperator(BaseOperator):
            _pattern: str = ""
            _substitute: str = ""

            @classmethod
            def _remove_pattern(cls, t: str):
                return re.sub(cls._pattern, cls._substitute, t)

            def give_up_diffing(self, level, diff_instance):
                if isinstance(level.t1, str) and isinstance(level.t2, str):
                    t1 = self._remove_pattern(level.t1)
                    t2 = self._remove_pattern(level.t2)
                    return t1 == t2
                return False

        class RemoveGUIDsOperator(RemovePatternOperator):
            _pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
            _substitute = "guid"

        diff1 = DeepDiff(deepcopy(d1), deepcopy(d2), ignore_order=False, custom_operators=[RemoveGUIDsOperator(types=[str])])
        assert not diff1

        with pytest.raises(NotImplementedError) as exp:
            DeepDiff(deepcopy(d1), deepcopy(d2), ignore_order=True, custom_operators=[RemoveGUIDsOperator(types=[str])])
        expected2 = 'RemoveGUIDsOperator needs to define a normalize_value_for_hashing method to be compatible with ignore_order=True or iterable_compare_func.'
        assert expected2 == str(exp.value)


        # --------- Let's implement the normalize_value_for_hashing to make it work with ignore_order=True ---------

        class RemoveGUIDsOperatorIgnoreOrderReady(RemoveGUIDsOperator):
            def normalize_value_for_hashing(self, parent: Any, obj: Any) -> Any:
                if isinstance(obj, str):
                    return self._remove_pattern(obj)
                return obj

        diff3 = DeepDiff(deepcopy(d1), deepcopy(d2), ignore_order=True, custom_operators=[RemoveGUIDsOperatorIgnoreOrderReady(types=[str])])
        assert not diff3, "We shouldn't have a diff because we have normalized the string values to be all the same vlues."

