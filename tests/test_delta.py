import copy
import datetime
from typing import NamedTuple
import pytest
import os
import io
import json
import sys
from decimal import Decimal
from unittest import mock
from deepdiff import Delta, DeepDiff
from deepdiff.helper import np, number_to_string, TEXT_VIEW, DELTA_VIEW, CannotCompare, FlatDeltaRow, FlatDataAction, SetOrdered
from deepdiff.path import GETATTR, GET
from deepdiff.delta import (
    ELEM_NOT_FOUND_TO_ADD_MSG,
    VERIFICATION_MSG, VERIFY_BIDIRECTIONAL_MSG, not_found, DeltaNumpyOperatorOverrideError,
    BINIARY_MODE_NEEDED_MSG, DELTA_AT_LEAST_ONE_ARG_NEEDED, DeltaError,
    INVALID_ACTION_WHEN_CALLING_GET_ELEM, INVALID_ACTION_WHEN_CALLING_SIMPLE_SET_ELEM,
    INVALID_ACTION_WHEN_CALLING_SIMPLE_DELETE_ELEM, INDEXES_NOT_FOUND_WHEN_IGNORE_ORDER,
    FAIL_TO_REMOVE_ITEM_IGNORE_ORDER_MSG, UNABLE_TO_GET_PATH_MSG, NOT_VALID_NUMPY_TYPE)
from deepdiff.serialization import (
    DELTA_IGNORE_ORDER_NEEDS_REPETITION_REPORT, DELTA_ERROR_WHEN_GROUP_BY,
    json_dumps, json_loads,
)

from tests import PicklableClass, parameterize_cases, CustomClass, CustomClass2


class TestBasicsOfDelta:

    def test_from_null_delta_json(self):
        t1 = None
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        delta = Delta(diff, serializer=json_dumps)
        dump = delta.dumps()
        delta2 = Delta(dump, deserializer=json_loads)
        assert delta2 + t1 == t2
        assert t1 + delta2 == t2
        with pytest.raises(ValueError) as exc_info:
            t2 - delta
        assert 'Please recreate the delta with bidirectional=True' == str(exc_info.value)
        delta = Delta(diff, serializer=json_dumps, bidirectional=True)
        assert t2 - delta == t1

    def test_to_null_delta1_json(self):
        t1 = 1
        t2 = None
        diff = DeepDiff(t1, t2)
        delta = Delta(diff, serializer=json_dumps)
        dump = delta.dumps()
        delta2 = Delta(dump, deserializer=json_loads)
        assert delta2 + t1 == t2
        assert t1 + delta2 == t2

    def test_to_null_delta2_json(self):
        t1 = [1, 2, 3, 5]
        t2 = None
        diff = DeepDiff(t1, t2)
        delta = Delta(diff)

        assert delta + t1 == t2
        assert t1 + delta == t2

    def test_list_difference_add_delta(self):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = {'iterable_item_added': {'root[3]': 5, 'root[2]': 3}}
        delta = Delta(diff)

        assert delta + t1 == t2
        assert t1 + delta == t2

        flat_result1 = delta.to_flat_rows()
        flat_expected1 = [
            FlatDeltaRow(path=[3], value=5, action='iterable_item_added', type=int),
            FlatDeltaRow(path=[2], value=3, action='iterable_item_added', type=int),
        ]

        assert flat_expected1 == flat_result1
        delta2 = Delta(diff=diff, bidirectional=True)
        assert t1 == t2 - delta2

    def test_list_difference_dump_delta(self):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        dump = Delta(diff).dumps()
        delta = Delta(dump)

        assert delta + t1 == t2

    def test_multiple_delta(self):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        t3 = [{1}, 3, 5]
        dump1 = Delta(DeepDiff(t1, t2)).dumps()
        dump2 = Delta(DeepDiff(t2, t3)).dumps()

        delta1 = Delta(dump1)
        delta2 = Delta(dump2)

        assert t1 + delta1 + delta2 == t3

    def test_delta_dump_and_read1(self, tmp_path):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        path = os.path.join(tmp_path, 'delta_test.delta')
        with open(path, 'wb') as the_file:
            Delta(diff).dump(the_file)
        delta = Delta(delta_path=path)
        os.remove(path)
        assert delta + t1 == t2

    def test_delta_dump_and_read2(self, tmp_path):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        delta_content = Delta(diff).dumps()
        path = os.path.join(tmp_path, 'delta_test2.delta')
        with open(path, 'wb') as the_file:
            the_file.write(delta_content)
        delta = Delta(delta_path=path)
        os.remove(path)
        assert delta + t1 == t2

    def test_delta_dump_and_read3(self, tmp_path):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        delta_content = Delta(diff).dumps()
        path = os.path.join(tmp_path, 'delta_test2.delta')
        with open(path, 'wb') as the_file:
            the_file.write(delta_content)
        with pytest.raises(ValueError) as excinfo:
            with open(path, 'r') as the_file:
                delta = Delta(delta_file=the_file)
        assert BINIARY_MODE_NEEDED_MSG[:20] == str(excinfo.value)[:20]
        with open(path, 'rb') as the_file:
            delta = Delta(delta_file=the_file)
        os.remove(path)
        assert delta + t1 == t2

    def test_delta_when_no_arg_passed(self):
        with pytest.raises(ValueError) as excinfo:
            Delta()
        assert DELTA_AT_LEAST_ONE_ARG_NEEDED == str(excinfo.value)

    def test_delta_when_group_by(self):

        t1 = [
            {'id': 'AA', 'name': 'Joe', 'last_name': 'Nobody'},
            {'id': 'BB', 'name': 'James', 'last_name': 'Blue'},
        ]

        t2 = [
            {'id': 'AA', 'name': 'Joe', 'last_name': 'Nobody'},
            {'id': 'BB', 'name': 'James', 'last_name': 'Brown'},
        ]

        diff = DeepDiff(t1, t2, group_by='id')

        with pytest.raises(ValueError) as excinfo:
            Delta(diff)
        assert DELTA_ERROR_WHEN_GROUP_BY == str(excinfo.value)

    def test_delta_repr(self):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        delta = Delta(diff)
        options = {
            '<Delta: {"iterable_item_added":{"root[2]":3,"root[3]":5}}>',
            '<Delta: {"iterable_item_added":{"root[3]":5,"root[2]":3}}>',
        }
        assert repr(delta) in options

    def test_get_elem_and_compare_to_old_value(self):
        delta = Delta({})

        with pytest.raises(DeltaError) as excinfo:
            delta._get_elem_and_compare_to_old_value(
                obj=None, path_for_err_reporting=None, expected_old_value=None, action='ketchup on steak')
        assert INVALID_ACTION_WHEN_CALLING_GET_ELEM.format('ketchup on steak') == str(excinfo.value)

    def test_simple_set_elem_value(self):
        delta = Delta({}, raise_errors=True)

        with pytest.raises(DeltaError) as excinfo:
            delta._simple_set_elem_value(
                obj=None, elem=None, value=None, action='mayo on salad', path_for_err_reporting=None)
        assert INVALID_ACTION_WHEN_CALLING_SIMPLE_SET_ELEM.format('mayo on salad') == str(excinfo.value)

        with pytest.raises(DeltaError) as excinfo:
            delta._simple_set_elem_value(
                obj={}, elem={1}, value=None, action=GET, path_for_err_reporting='mypath')
        assert str(excinfo.value) in {"Failed to set mypath due to unhashable type: 'set'",
                                      "Failed to set mypath due to 'set' objects are unhashable",
                                      "Failed to set mypath due to cannot use 'set' as a dict key (unhashable type: 'set')"}

    def test_simple_delete_elem(self):
        delta = Delta({}, raise_errors=True)

        with pytest.raises(DeltaError) as excinfo:
            delta._simple_delete_elem(
                obj=None, elem=None, action='burnt oil', path_for_err_reporting=None)
        assert INVALID_ACTION_WHEN_CALLING_SIMPLE_DELETE_ELEM.format('burnt oil') == str(excinfo.value)

        with pytest.raises(DeltaError) as excinfo:
            delta._simple_delete_elem(
                obj={}, elem=1, action=GET, path_for_err_reporting='mypath')
        assert "Failed to set mypath due to 1" == str(excinfo.value)

    def test_raise_error(self):
        t1 = [1, 2, [3, 5, 6]]
        t2 = [2, 3, [3, 6, 8]]
        diff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True)
        delta = Delta(diff, raise_errors=False)
        t3 = [1, 2, 3, 5]
        t4 = t3 + delta
        assert [3, 2, 3, 5] == t4

        delta2 = Delta(diff, raise_errors=True)

        with pytest.raises(DeltaError) as excinfo:
            t3 + delta2
        assert "Unable to get the item at root[2][1]" == str(excinfo.value)

    def test_identical_delta(self):
        delta = Delta({})

        t1 = [1, 3]
        assert t1 + delta == t1

        flat_result1 = delta.to_flat_rows()
        flat_expected1 = []

        assert flat_expected1 == flat_result1

    def test_delta_mutate(self):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        diff = DeepDiff(t1, t2)
        delta = Delta(diff, mutate=True)
        t1 + delta
        assert t1 == t2

    @mock.patch('deepdiff.delta.logger.error')
    def test_list_difference_add_delta_when_index_not_valid(self, mock_logger):
        t1 = [1, 2]
        diff = {'iterable_item_added': {'root[20]': 3, 'root[3]': 5}}
        delta = Delta(diff, log_errors=False)
        assert delta + t1 == t1

        # since we sort the keys by the path elements, root[3] is gonna be processed before root[20]
        expected_msg = ELEM_NOT_FOUND_TO_ADD_MSG.format(3, 'root[3]')

        delta2 = Delta(diff, bidirectional=True, raise_errors=True, log_errors=False)
        with pytest.raises(ValueError) as excinfo:
            delta2 + t1
        assert expected_msg == str(excinfo.value)
        assert not mock_logger.called

        delta3 = Delta(diff, bidirectional=True, raise_errors=True, log_errors=True)
        with pytest.raises(ValueError) as excinfo:
            delta3 + t1
        assert expected_msg == str(excinfo.value)
        mock_logger.assert_called_once_with(expected_msg)

    def test_list_difference3_delta(self):
        t1 = {1: 1, 2: 2, 3: 3, 4: {"a": "hello", "b": [1, 2, 5]}}
        t2 = {1: 1, 2: 2, 3: 3, 4: {"a": "hello", "b": [1, 3, 2, 5]}}
        diff = {
            'values_changed': {
                "root[4]['b'][2]": {
                    'new_value': 2,
                    'old_value': 5
                },
                "root[4]['b'][1]": {
                    'new_value': 3,
                    'old_value': 2
                }
            },
            'iterable_item_added': {
                "root[4]['b'][3]": 5
            }
        }
        delta = Delta(diff)

        assert delta + t1 == t2
        assert t1 + delta == t2

        flat_result1 = delta.to_flat_rows()
        flat_expected1 = [
            FlatDeltaRow(path=[4, 'b', 2], action='values_changed', value=2, old_value=5, type=int, old_type=int),
            FlatDeltaRow(path=[4, 'b', 1], action='values_changed', value=3, old_value=2, type=int, old_type=int),
            FlatDeltaRow(path=[4, 'b', 3], value=5, action='iterable_item_added', type=int),
        ]

        assert flat_expected1 == flat_result1

        delta2 = Delta(diff=diff, bidirectional=True)
        assert t1 == t2 - delta2

    def test_list_difference_delta_raises_error_if_prev_value_does_not_match(self):
        t1 = [1, 2, 6]
        t2 = [1, 3, 2, 5]
        diff = {
            'values_changed': {
                "root[2]": {
                    'new_value': 2,
                    'old_value': 5
                },
                "root[1]": {
                    'new_value': 3,
                    'old_value': 2
                }
            },
            'iterable_item_added': {
                "root[3]": 5
            }
        }

        expected_msg = VERIFICATION_MSG.format('root[2]', 5, 6, VERIFY_BIDIRECTIONAL_MSG)

        delta = Delta(diff, bidirectional=True, raise_errors=True)
        with pytest.raises(ValueError) as excinfo:
            delta + t1
        assert expected_msg == str(excinfo.value)

        delta2 = Delta(diff, bidirectional=False)
        assert delta2 + t1 == t2

        flat_result2 = delta2.to_flat_rows()
        flat_expected2 = [
            FlatDeltaRow(path=[2], action='values_changed', value=2, old_value=5, type=int, old_type=int),
            FlatDeltaRow(path=[1], action='values_changed', value=3, old_value=2, type=int, old_type=int),
            FlatDeltaRow(path=[3], value=5, action='iterable_item_added', type=int),
        ]

        assert flat_expected2 == flat_result2

    def test_list_difference_delta1(self):
        t1 = {
            1: 1,
            2: 2,
            3: 3,
            4: {
                "a": "hello",
                "b": [1, 2, 'to_be_removed', 'to_be_removed2']
            }
        }
        t2 = {1: 1, 2: 2, 3: 3, 4: {"a": "hello", "b": [1, 2]}}

        diff = {
            'iterable_item_removed': {
                "root[4]['b'][2]": "to_be_removed",
                "root[4]['b'][3]": 'to_be_removed2'
            }
        }
        delta = Delta(diff)

        assert delta + t1 == t2

        flat_result = delta.to_flat_rows()
        flat_expected = [
            FlatDeltaRow(path=[4, 'b', 2], value='to_be_removed', action='iterable_item_removed', type=str),
            FlatDeltaRow(path=[4, 'b', 3], value='to_be_removed2', action='iterable_item_removed', type=str),
        ]

        assert flat_expected == flat_result

        delta2 = Delta(diff=diff, bidirectional=True)
        assert t1 == t2 - delta2

    @mock.patch('deepdiff.delta.logger.error')
    def test_list_difference_delta_if_item_is_already_removed(self, mock_logger):
        t1 = [1, 2, 'to_be_removed']
        t2 = [1, 2]

        diff = {
            'iterable_item_removed': {
                "root[2]": "to_be_removed",
                "root[3]": 'to_be_removed2'
            }
        }
        delta = Delta(diff, bidirectional=True, raise_errors=True)
        assert delta + t1 == t2, (
            "We used to throw errors when the item to be removed was not found. "
            "Instead, we try to look for the item to be removed even when the "
            "index of it in delta is different than the index of it in the object."
        )

        delta2 = Delta(diff, bidirectional=False, raise_errors=False)
        assert t1 + delta2 == t2
        expected_msg = UNABLE_TO_GET_PATH_MSG.format('root[3]')
        assert 0 == mock_logger.call_count

    def test_list_difference_delta_does_not_raise_error_if_prev_value_changed(self):
        t1 = {
            1: 1,
            2: 2,
            3: 3,
            4: {
                "a": "hello",
                "b": [1, 2, 'wrong', 'to_be_removed2']
            }
        }
        t2 = {1: 1, 2: 2, 3: 3, 4: {"a": "hello", "b": [1, 2]}}

        diff = {
            'iterable_item_removed': {
                "root[4]['b'][2]": "to_be_removed",
                "root[4]['b'][3]": 'to_be_removed2'
            }
        }

        # The previous behavior was to throw an error here because the original value for "root[4]['b'][2]" was not 'wrong' anymore.
        # However, I decided to change that behavior to what makes more sense and is consistent with the bidirectional flag.
        # No more verify_symmetry flag.
        delta = Delta(diff, bidirectional=True, raise_errors=True)
        assert delta + t1 != t2
        expected = {1: 1, 2: 2, 3: 3, 4: {'a': 'hello', 'b': [1, 2, 'wrong']}}
        assert expected == delta + t1

        delta2 = Delta(diff, bidirectional=False, raise_errors=True)
        assert expected == t1 + delta2

    def test_delta_dict_items_added_retain_order(self):
        t1 = {
            6: 6
        }

        t2 = {
            6: 6,
            7: 7,
            3: 3,
            5: 5,
            2: 2,
            4: 4
        }

        expected_delta_dict = {
            'dictionary_item_added': {
                'root[7]': 7,
                'root[3]': 3,
                'root[5]': 5,
                'root[2]': 2,
                'root[4]': 4
            }
        }

        diff = DeepDiff(t1, t2, threshold_to_diff_deeper=0)
        delta_dict = diff._to_delta_dict()
        assert expected_delta_dict == delta_dict
        delta = Delta(diff, bidirectional=False, raise_errors=True)

        result = t1 + delta
        assert result == t2

        assert set(result.keys()) == {6, 7, 3, 5, 2, 4}
        assert set(result.keys()) == set(t2.keys())

        delta2 = Delta(diff=diff, bidirectional=True)
        assert t1 == t2 - delta2

        delta3 = Delta(diff, always_include_values=True, bidirectional=True, raise_errors=True)
        flat_rows_list = delta3.to_flat_rows()
        delta4 = Delta(flat_rows_list=flat_rows_list,
                      always_include_values=True, bidirectional=True, raise_errors=True)
        assert t1 == t2 - delta4
        assert t1 + delta4 == t2


    def test_delta_constr_flat_dict_list_param_preserve(self):
        """
        Issue: https://github.com/seperman/deepdiff/issues/457

        Scenario:
        We found that when a flat_rows_list was provided as a constructor
        parameter for instantiating a new delta, the provided flat_rows_list
        is unexpectedly being mutated/changed, which can be troublesome for the
        caller if they were expecting the flat_rows_list to be used BY COPY
        rather than BY REFERENCE.

        Intent:
        Preserve the original value of the flat_rows_list variable within the
        calling module/function after instantiating the new delta.
        """

        t1 = {
            "individualNames": [
                {
                    "firstName": "Johnathan",
                    "lastName": "Doe",
                    "prefix": "COLONEL",
                    "middleName": "A",
                    "primaryIndicator": True,
                    "professionalDesignation": "PHD",
                    "suffix": "SR",
                    "nameIdentifier": "00001"
                },
                {
                    "firstName": "John",
                    "lastName": "Doe",
                    "prefix": "",
                    "middleName": "",
                    "primaryIndicator": False,
                    "professionalDesignation": "",
                    "suffix": "SR",
                    "nameIdentifier": "00002"
                }
            ]
        }

        t2 = {
            "individualNames": [
                {
                    "firstName": "Johnathan",
                    "lastName": "Doe",
                    "prefix": "COLONEL",
                    "middleName": "A",
                    "primaryIndicator": True,
                    "professionalDesignation": "PHD",
                    "suffix": "SR",
                    "nameIdentifier": "00001"
                },
                {
                    "firstName": "Johnny",
                    "lastName": "Doe",
                    "prefix": "",
                    "middleName": "A",
                    "primaryIndicator": False,
                    "professionalDesignation": "",
                    "suffix": "SR",
                    "nameIdentifier": "00003"
                }
            ]
        }

        def compare_func(item1, item2, level=None):
            print("*** inside compare ***")
            it1_keys = item1.keys()

            try:

                # --- individualNames ---
                if 'nameIdentifier' in it1_keys and 'lastName' in it1_keys:
                    match_result = item1['nameIdentifier'] == item2['nameIdentifier']
                    print("individualNames - matching result:", match_result)
                    return match_result
                else:
                    print("Unknown list item...", "matching result:", item1 == item2)
                    return item1 == item2
            except Exception:
                raise CannotCompare() from None
        # ---------------------------- End of nested function

        # This diff should show:
        # 1 - list item (with an index on the path) being added
        # 1 - list item (with an index on the path) being removed
        diff = DeepDiff(t1, t2, report_repetition=True,
                             ignore_order=True, iterable_compare_func=compare_func, cutoff_intersection_for_pairs=1)

        # Now create a flat_rows_list from a delta instantiated from the diff...
        temp_delta = Delta(diff, always_include_values=True, bidirectional=True, raise_errors=True)
        flat_rows_list = temp_delta.to_flat_rows()

        # Note: the list index is provided on the path value...
        assert flat_rows_list == [FlatDeltaRow(path=['individualNames', 1],
                                   value={'firstName': 'Johnny',
                                             'lastName': 'Doe',
                                             'prefix': '',
                                             'middleName': 'A',
                                             'primaryIndicator': False,
                                             'professionalDesignation': '',
                                             'suffix': 'SR',
                                             'nameIdentifier': '00003'},
                                   action='unordered_iterable_item_added',
                                   type=dict),
                                  FlatDeltaRow(path=['individualNames', 1],
                                   value={'firstName': 'John',
                                             'lastName': 'Doe',
                                             'prefix': '',
                                             'middleName': '',
                                             'primaryIndicator': False,
                                             'professionalDesignation': '',
                                             'suffix': 'SR',
                                             'nameIdentifier': '00002'},
                                   action='unordered_iterable_item_removed',
                                   type=dict),
                                  ]

        preserved_flat_dict_list = copy.deepcopy(flat_rows_list)  # Use this later for assert comparison

        # Now use the flat_rows_list to instantiate a new delta...
        delta = Delta(flat_rows_list=flat_rows_list,
                      always_include_values=True, bidirectional=True, raise_errors=True)

        flat_rows_list_again = delta.to_flat_rows()
        # if the flat_rows_list is (unexpectedly) mutated, it will be missing the list index number on the path value.
        old_mutated_list_missing_indexes_on_path = [FlatDeltaRow(path=['individualNames'],
                                         value={'firstName': 'Johnny',
                                                   'lastName': 'Doe',
                                                   'prefix': '',
                                                   'middleName': 'A',
                                                   'primaryIndicator': False,
                                                   'professionalDesignation': '',
                                                   'suffix': 'SR',
                                                   'nameIdentifier': '00003'},
                                         action='unordered_iterable_item_added'),
                                        FlatDeltaRow(path=['individualNames'],
                                         value={'firstName': 'John',
                                                   'lastName': 'Doe',
                                                   'prefix': '',
                                                   'middleName': '',
                                                   'primaryIndicator': False,
                                                   'professionalDesignation': '',
                                                   'suffix': 'SR',
                                                   'nameIdentifier': '00002'},
                                         action='unordered_iterable_item_removed')]

        # Verify that our fix in the delta constructor worked...
        assert flat_rows_list != old_mutated_list_missing_indexes_on_path
        assert flat_rows_list == preserved_flat_dict_list
        assert flat_rows_list == flat_rows_list_again

    def test_namedtuple_add_delta(self):
        class Point(NamedTuple):
           x: int
           y: int

        p1 = Point(1, 1)
        p2 = Point(1, 2)
        diff = DeepDiff(p1, p2)
        delta = Delta(diff)
        assert p2 == p1 + delta

    def test_namedtuple_frozenset_add_delta(self):
        class Article(NamedTuple):
            tags: frozenset
        a1 = Article(frozenset(["a" ]))
        a2 = Article(frozenset(["a", "b"]))
        diff = DeepDiff(a1, a2)
        delta = Delta(diff)
        assert a2 == a1 + delta

    def test_nested_namedtuple_frozenset_add_delta(self):
        class Article(NamedTuple):
            tags: frozenset

        t1 = {"article": Article(frozenset(["a"]))}
        t2 = {"article": Article(frozenset(["a", "b"]))}
        delta = Delta(DeepDiff(t1, t2))

        assert t2 == t1 + delta

    def test_tuple_iterable_opcodes_with_insert_delete_delta(self):
        t1 = tuple("A B C D H".split())
        t2 = tuple("B C D H Y Z".split())
        delta = Delta(DeepDiff(t1, t2), bidirectional=True)

        assert "_iterable_opcodes" in delta.diff
        assert t2 == t1 + delta

    def test_complex_dictionary_keys_removed_delta(self):
        t1 = {1 + 2j: "a", 3 + 4j: "b"}
        t2 = {}
        diff = DeepDiff(t1, t2, threshold_to_diff_deeper=0)
        delta = Delta(diff, raise_errors=True)

        assert t2 == t1 + delta
 
picklalbe_obj_without_item = PicklableClass(11)
del picklalbe_obj_without_item.item


DELTA_CASES = {
    'delta_case0': {
        't1': frozenset([1, 2, 'B']),
        't2': frozenset([1, 2, 'B']),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {},
    },
    'delta_case1': {
        't1': frozenset([1, 2, 'B']),
        't2': frozenset([1, 2, 3, 5]),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'set_item_removed': {'root': {'B'}}, 'set_item_added': {'root': {3, 5}}},
    },
    'delta_case2': {
        't1': [1, 2, 'B'],
        't2': [1, 2, 3, 5],
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'type_changes': {
                'root[2]': {
                    'old_type': str,
                    'new_type': int,
                    'new_value': 3
                }
            },
            'iterable_item_added': {
                'root[3]': 5
            }
        },
    },
    'delta_case3': {
        't1': [1, 2, '3'],
        't2': [1, 2, 3],
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'type_changes': {
                'root[2]': {
                    'old_type': str,
                    'new_type': int,
                }
            }
        },
    },
    'delta_case4': {
        't1': 3,
        't2': '3',
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'type_changes': {
                'root': {
                    'old_type': int,
                    'new_type': str,
                }
            }
        },
    },
    'delta_case5': {
        't1': 3.2,
        't2': Decimal('3.2'),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'type_changes': {
                'root': {
                    'old_type': float,
                    'new_type': Decimal,
                    'new_value': Decimal('3.2')
                }
            }
        },
    },
    'delta_case6': {
        't1': (1, 2),
        't2': (1, 3),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[1]': {
                    'new_value': 3
                }
            }
        },
    },
    'delta_case7': {
        't1': (1, 2, 5),
        't2': (1, ),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_item_removed': {
                'root[1]': 2,
                'root[2]': 5
            }
        },
    },
    'delta_case8': {
        't1': (1, 2, 5),
        't2': (1, 3),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_item_removed': {
                'root[2]': 5
            },
            'values_changed': {
                'root[1]': {
                    'new_value': 3
                }
            }
        },
    },
    'delta_case9': {
        't1': (1, ),
        't2': (1, 3),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_item_added': {
                'root[1]': 3
            },
        },
    },
    'delta_case10': {
        't1': {
            2: 2
        },
        't2': {
            2: 2,
            3: 3
        },
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'dictionary_item_added': {
                'root[3]': 3
            },
        },
    },
    'delta_case11': {
        't1': {
            1: 1,
            2: 2
        },
        't2': {
            2: 2,
            3: 3
        },
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'dictionary_item_added': {
                'root[3]': 3
            },
            'dictionary_item_removed': {
                'root[1]': 1
            },
        },
    },
    'delta_case12': {
        't1': PicklableClass(10),
        't2': PicklableClass(11),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root.item': {
                    'new_value': 11
                }
            }
        }
    },
    'delta_case13': {
        't1': PicklableClass(10),
        't2': picklalbe_obj_without_item,
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'attribute_removed': {
                'root.item': 10
            }
        }
    },
    'delta_case14': {
        't1': picklalbe_obj_without_item,
        't2': PicklableClass(10),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'attribute_added': {
                'root.item': 10
            }
        }
    },
    'delta_case14b_threshold_to_diff_deeper': {
        't1': picklalbe_obj_without_item,
        't2': PicklableClass(11),
        'deepdiff_kwargs': {'threshold_to_diff_deeper': 0.5},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'attribute_added': {'root.item': 11}}
    },
    'delta_case15_diffing_simple_numbers': {
        't1': 1,
        't2': 2,
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'values_changed': {'root': {'new_value': 2}}}
    },
    'delta_case16_diffmultiline_text': {
        't1': {1: 1, 2: 2, 3: 3, 4: {'a': 'hello', 'b': 'world\n1\n2\nEnd'}},
        't2': {1: 1, 2: 2, 3: 3, 4: {'a': 'hello', 'b': 'world!\nGoodbye!\n1\n2\nEnd'}},
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'values_changed': {"root[4]['b']": {'new_value': 'world!\nGoodbye!\n1\n2\nEnd'}}}
    },
    'delta_case17_numbers_and_letters': {
        't1': [0, 1, 2, 3, 4, 5, 6, 7, 8],
        't2': [0, 1, 2, 3, 4, 5, 6, 7, 8, 'a', 'b', 'c'],
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'iterable_item_added': {'root[9]': 'a', 'root[10]': 'b', 'root[11]': 'c'}}
    },
    'delta_case18_numbers_and_letters': {
        't1': [0, 1, 2, 3, 4, 5, 6, 7, 8, 'a', 'b', 'c'],
        't2': [0, 1, 2, 3, 4, 5, 6, 7, 8],
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'iterable_item_removed': {'root[9]': 'a', 'root[10]': 'b', 'root[11]': 'c'}}
    },
    'delta_case19_value_removed_from_the_middle_of_list': {
        't1': [0, 1, 2, 3, 4, 5, 6, 7, 8, 'a', 'b', 'c'],
        't2': [0, 1, 2, 3, 5, 6, 7, 8, 'a', 'b', 'c'],
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {'directed': True},
        'expected_delta_dict': {'iterable_item_removed': {'root[4]': 4}}
    },
    'delta_case20_quotes_in_path': {
        't1': {"a']['b']['c": 1},
        't2': {"a']['b']['c": 2},
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {'directed': True},
        'expected_delta_dict': {'values_changed': {'root["a\'][\'b\'][\'c"]': {'new_value': 2}}}
    },
    'delta_case21_empty_list_add': {
        't1': {'car_model': [], 'car_model_version_id': 0},
        't2': {'car_model': ['Super Duty F-250'], 'car_model_version_id': 1},
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {'directed': True},
        'expected_delta_dict': {'iterable_item_added': {"root['car_model'][0]": 'Super Duty F-250'}, 'values_changed': {"root['car_model_version_id']": {'new_value': 1}}},
    },
}


DELTA_CASES_PARAMS = parameterize_cases('test_name, t1, t2, deepdiff_kwargs, to_delta_kwargs, expected_delta_dict', DELTA_CASES)


class TestDelta:

    @pytest.mark.parametrize(**DELTA_CASES_PARAMS)
    def test_delta_cases(self, test_name, t1, t2, deepdiff_kwargs, to_delta_kwargs, expected_delta_dict):
        diff = DeepDiff(t1, t2, **deepdiff_kwargs)
        delta_dict = diff._to_delta_dict(**to_delta_kwargs)
        assert expected_delta_dict == delta_dict, f"test_delta_cases {test_name} failed."
        delta = Delta(diff, bidirectional=False, raise_errors=True)
        assert t1 + delta == t2, f"test_delta_cases {test_name} failed."

        delta2 = Delta(diff, bidirectional=True, raise_errors=True)
        assert t2 - delta2 == t1, f"test_delta_cases {test_name} failed."


DELTA_IGNORE_ORDER_CASES = {
    'delta_ignore_order_case1': {
        't1': [1, 2, 'B', 3],
        't2': [1, 2, 3, 5],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_items_added_at_indexes': {
                'root': {
                    3: 5
                }
            },
            'iterable_items_removed_at_indexes': {
                'root': {
                    2: 'B'
                }
            }
        },
        'expected_t1_plus_delta': 't2',
    },
    'delta_ignore_order_case2': {
        't1': [1, 2, 'B', 3, 'B', 'B', 4],
        't2': [1, 2, 3, 5],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[6]': {
                    'new_value': 5,
                    'new_path': 'root[3]',
                },
            },
            'iterable_items_removed_at_indexes': {
                'root': {
                    2: 'B',
                    4: 'B',
                    5: 'B'
                }
            }
        },
        'expected_t1_plus_delta': 't2',
    },
    'delta_ignore_order_case_reverse2': {
        't1': [1, 2, 3, 5],
        't2': [1, 2, 'B', 3, 'B', 'B', 4],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[3]': {
                    'new_value': 4,
                    'new_path': 'root[6]',
                },
            },
            'iterable_items_added_at_indexes': {
                'root': {
                    2: 'B',
                    4: 'B',
                    5: 'B'
                }
            }
        },
        'expected_t1_plus_delta': 't2',
    },
    'delta_ignore_order_case3': {
        't1': [5, 1, 1, 1, 6],
        't2': [7, 1, 1, 1, 8],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[4]': {
                    'new_value': 7,
                    'new_path': 'root[0]'
                },
                'root[0]': {
                    'new_value': 8,
                    'new_path': 'root[4]'
                }
            }
        },
        'expected_t1_plus_delta': [8, 1, 1, 1, 7],
    },
    'delta_ignore_order_case4': {
        't1': [5, 1, 3, 1, 4, 4, 6],
        't2': [7, 4, 4, 1, 3, 4, 8],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[6]': {
                    'new_value': 7,
                    'new_path': 'root[0]'
                },
                'root[0]': {
                    'new_value': 8,
                    'new_path': 'root[6]'
                }
            },
            'iterable_items_added_at_indexes': {
                'root': {
                    1: 4,
                    2: 4,
                    5: 4,
                    3: 1,
                }
            }
        },
        'expected_t1_plus_delta': [8, 4, 4, 1, 3, 4, 7],
    },
    'delta_ignore_order_case5': {
        't1': (5, 1, 3, 1, 4, 4, 6),
        't2': (7, 4, 4, 1, 3, 4, 8, 1),
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_items_added_at_indexes': {
                'root': {
                    1: 4,
                    2: 4,
                    5: 4
                }
            },
            'values_changed': {
                'root[6]': {
                    'new_value': 7,
                    'new_path': 'root[0]',
                },
                'root[0]': {
                    'new_value': 8,
                    'new_path': 'root[6]',
                }
            }
        },
        'expected_t1_plus_delta': (8, 4, 4, 1, 3, 4, 1, 7),
    },
    'delta_ignore_order_case6': {
        't1': [{1, 2, 3}, {4, 5}],
        't2': [{4, 5, 6}, {1, 2, 3}],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {'set_item_added': {'root[1]': {6}}},
        'expected_t1_plus_delta': [{1, 2, 3}, {4, 5, 6}],
    },
    'delta_ignore_order_case7': {
        't1': [{1, 2, 3}, {4, 5, 'hello', 'right!'}, {4, 5, (2, 4, 7)}],
        't2': [{4, 5, 6, (2, )}, {1, 2, 3}, {5, 'hello', 'right!'}],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'set_item_removed': {
                'root[1]': {4}
            },
            'iterable_items_added_at_indexes': {
                'root': {
                    0: {(2, ), 4, 5, 6}
                }
            },
            'iterable_items_removed_at_indexes': {
                'root': {
                    2: {4, 5, (2, 4, 7)}
                }
            }
        },
        'expected_t1_plus_delta': 't2',
    },
    'delta_ignore_order_case8_multi_dimensional_list': {
        't1': [[1, 2, 3, 4], [4, 2, 2, 1]],
        't2': [[4, 1, 1, 1], [1, 3, 2, 4]],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_items_added_at_indexes': {
                'root[1]': {
                    1: 1,
                    2: 1,
                    3: 1
                }
            },
            'iterable_items_removed_at_indexes': {
                'root[1]': {
                    1: 2,
                    2: 2
                }
            }
        },
        'expected_t1_plus_delta': [[1, 2, 3, 4], [4, 1, 1, 1]],
    },
    'delta_ignore_order_case9': {
        't1': [{
            "path": ["interface1", "ipv1"]
        }, {
            "path": ["interface2", "ipv2"]
        }, {
            "path": ["interface3", "ipv3"]
        }, {
            "path": [{
                "test0": "interface4.0",
                "test0.0": "ipv4.0"
            }, {
                "test1": "interface4.1",
                "test1.1": "ipv4.1"
            }]
        }, {
            "path": ["interface5", "ipv5"]
        }],
        't2': [{
            "path": ["interface1", "ipv1"]
        }, {
            "path": ["interface3", "ipv3"]
        }, {
            "path": [{
                "test0": "interface4.0",
                "test0.0": "ipv4.0"
            }, {
                "test2": "interface4.2",
                "test2.2": "ipv4.0"
            }, {
                "test1": "interface4.1",
                "test1.1": "ipv4.1"
            }]
        }, {
            "path": ["interface6", "ipv6"]
        }, {
            "path": ["interface5", "ipv5"]
        }],
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_items_added_at_indexes': {
                "root[3]['path']": {
                    1: {
                        'test2': 'interface4.2',
                        'test2.2': 'ipv4.0'
                    }
                },
                'root': {
                    3: {
                        'path': [
                            'interface6', 'ipv6'
                        ]
                    }
                }
            },
            'iterable_items_removed_at_indexes': {
                'root': {
                    1: {
                        'path': ['interface2', 'ipv2']
                    }
                }
            }
        },
        'expected_t1_plus_delta':
        't2',
    },
}

DELTA_IGNORE_ORDER_CASES_PARAMS = parameterize_cases(
    'test_name, t1, t2, deepdiff_kwargs, to_delta_kwargs, expected_delta_dict, expected_t1_plus_delta', DELTA_IGNORE_ORDER_CASES)


class TestIgnoreOrderDelta:

    @pytest.mark.parametrize(**DELTA_IGNORE_ORDER_CASES_PARAMS)
    def test_ignore_order_delta_cases(
            self, test_name, t1, t2, deepdiff_kwargs, to_delta_kwargs, expected_delta_dict, expected_t1_plus_delta, request):
        # test_name = request.node.callspec.id
        diff = DeepDiff(t1, t2, **deepdiff_kwargs)
        delta_dict = diff._to_delta_dict(**to_delta_kwargs)
        assert expected_delta_dict == delta_dict, f"test_ignore_order_delta_cases {test_name} failed"
        delta = Delta(diff, bidirectional=False, raise_errors=True)
        expected_t1_plus_delta = t2 if expected_t1_plus_delta == 't2' else expected_t1_plus_delta
        t1_plus_delta = t1 + delta
        assert t1 + delta == t1_plus_delta, f"test_ignore_order_delta_cases {test_name} 'asserting that delta is not mutated once it is applied' failed"
        # assert not DeepDiff(t1_plus_delta, expected_t1_plus_delta, ignore_order=True), f"test_ignore_order_delta_cases {test_name} failed: diff = {DeepDiff(t1_plus_delta, expected_t1_plus_delta, ignore_order=True)}"


DELTA_NUMPY_TEST_CASES = {
    'delta_case15_similar_to_delta_numpy': {
        't1': [1, 2, 3],
        't2': [1, 2, 5],
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'values_changed': {'root[2]': {'new_value': 5}}},
        'expected_result': 't2'
    },
    'delta_numpy1_operator_override': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 5], np.int8),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'values_changed': {'root[2]': {'new_value': 5}}, '_numpy_paths': {'root': 'int8'}},
        'expected_result': DeltaNumpyOperatorOverrideError
    },
    'delta_numpy2': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 5], np.int8),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'values_changed': {'root[2]': {'new_value': 5}}, '_numpy_paths': {'root': 'int8'}},
        'expected_result': 't2'
    },
    'delta_numpy3_type_change_but_no_value_change': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 3], np.int16),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {'type_changes': {'root': {'old_type': np.int8, 'new_type': np.int16}}},
        'expected_result': 't2'
    },
    'delta_numpy4_type_change_plus_value_change': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 5], np.int16),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': None,  # Not easy to compare since it throws:
        # ValueError: The truth value of an array with more than one element is ambiguous.
        # And we don't want to use DeepDiff for testing the equality inside deepdiff tests themselves!
        'expected_result': 't2'
    },
    'delta_numpy4_type_change_ignore_numeric_type_changes': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 5], np.int16),
        'deepdiff_kwargs': {
            'ignore_numeric_type_changes': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[2]': {
                    'new_value': 5
                }
            },
            '_numpy_paths': {
                'root': 'int16'
            }
        },
        'expected_result': 't2'
    },
    'delta_numpy5_multi_dimensional': {
        't1': np.array([[1, 2, 3], [4, 2, 2]], np.int8),
        't2': np.array([[1, 2, 5], [4, 1, 2]], np.int8),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[0][2]': {
                    'new_value': 5
                },
                'root[1][1]': {
                    'new_value': 1
                }
            },
            '_numpy_paths': {
                'root': 'int8'
            }
        },
        'expected_result': 't2'
    },
    'delta_numpy6_multi_dimensional_ignore_order': {
        't1': np.array([[1, 2, 3, 4], [4, 2, 2, 1]], np.int8),
        't2': np.array([[4, 1, 1, 1], [1, 3, 2, 4]], np.int8),
        'deepdiff_kwargs': {
            'ignore_order': True,
            'report_repetition': True
        },
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'iterable_items_added_at_indexes': {
                'root[1]': {
                    1: 1,
                    2: 1,
                    3: 1
                }
            },
            'iterable_items_removed_at_indexes': {
                'root[1]': {
                    1: 2,
                    2: 2
                }
            },
            '_numpy_paths': {
                'root': 'int8'
            }
        },
        'expected_result': 't2_via_deepdiff'
    },
    'delta_numpy7_arrays_of_different_sizes': {
        't1': np.array([1, 2, 3, 4]),
        't2': np.array([5, 6, 7, 8, 9, 10]),
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
            'values_changed': {
                'root[0]': {
                    'new_value': 5
                },
                'root[1]': {
                    'new_value': 6
                },
                'root[2]': {
                    'new_value': 7
                },
                'root[3]': {
                    'new_value': 8
                }
            },
            'iterable_item_added': {
                'root[4]': 9,
                'root[5]': 10
            },
            '_numpy_paths': {
                'root': np.where((sys.maxsize > 2**32), 'int64', 'int32')
            }
        },
        'expected_result': 't2'
    },
    'delta_with_null_as_key': {
        't1': { None: [1, 2], 'foo': [1, 2] },
        't2': { None: [1], 'foo': [1] },
        'deepdiff_kwargs': {},
        'to_delta_kwargs': {},
        'expected_delta_dict': {
        },
        'expected_result': 't2'
    },
}


DELTA_NUMPY_TEST_PARAMS = parameterize_cases(
    'test_name, t1, t2, deepdiff_kwargs, to_delta_kwargs, expected_delta_dict, expected_result', DELTA_NUMPY_TEST_CASES)


class TestNumpyDelta:

    @pytest.mark.parametrize(**DELTA_NUMPY_TEST_PARAMS)
    def test_numpy_delta_cases(self, test_name, t1, t2, deepdiff_kwargs, to_delta_kwargs, expected_delta_dict, expected_result):
        diff = DeepDiff(t1, t2, **deepdiff_kwargs)
        delta_dict = diff._to_delta_dict(**to_delta_kwargs)
        if expected_delta_dict:
            assert expected_delta_dict == delta_dict, f"test_numpy_delta_cases {test_name} failed."
        delta = Delta(diff, bidirectional=False, raise_errors=True)
        if expected_result == 't2':
            result = delta + t1
            assert np.array_equal(result, t2), f"test_numpy_delta_cases {test_name} failed."
        elif expected_result == 't2_via_deepdiff':
            result = delta + t1
            diff = DeepDiff(result, t2, ignore_order=True, report_repetition=True)
            assert not diff, f"test_numpy_delta_cases {test_name} failed."
        elif expected_result is DeltaNumpyOperatorOverrideError:
            with pytest.raises(DeltaNumpyOperatorOverrideError):
                t1 + delta
        else:
            result = delta + t1
            assert np.array_equal(result, expected_result), f"test_numpy_delta_cases {test_name} failed."

    def test_invalid_numpy_type(self):

        t1 = np.array([1, 2, 3], np.int8)
        delta_dict = {'iterable_item_added': {'root[2]': 5}, '_numpy_paths': {'root': 'int11'}}

        with pytest.raises(DeltaError) as excinfo:
            Delta(delta_dict, raise_errors=True) + t1

        expected_msg = NOT_VALID_NUMPY_TYPE.format("'int11'")
        assert expected_msg == str(excinfo.value)


class TestDeltaOther:

    def test_list_ignore_order_various_deltas1(self):
        t1 = [5, 1, 3, 1, 4, 4, 6]
        t2 = [7, 4, 4, 1, 3, 4, 8]

        delta_dict1 = {'iterable_items_added_at_indexes': {'root': {0: 7, 6: 8, 1: 4, 2: 4, 5: 4, 3: 1}}, 'iterable_items_removed_at_indexes': {'root': {0: 5, 6: 6}}}
        delta_dict2 = {'iterable_items_added_at_indexes': {'root': {1: 4, 2: 4, 5: 4, 3: 1}}, 'values_changed': {'root[6]': {'new_value': 7}, 'root[0]': {'new_value': 8}}}
        delta1 = Delta(delta_dict1)
        t1_plus_delta1 = t1 + delta1
        assert t1_plus_delta1 == t2
        delta2 = Delta(delta_dict2)
        t1_plus_delta2 = t1 + delta2
        assert t1_plus_delta2 == [8, 4, 4, 1, 3, 4, 7]

    def test_list_ignore_order_various_deltas2(self):
        t1 = (5, 1, 3, 1, 4, 4, 6)
        t2 = (7, 4, 4, 1, 3, 4, 8, 1)

        delta_dict1 = {'iterable_items_added_at_indexes': {'root': {0: 7, 6: 8, 1: 4, 2: 4, 5: 4}}, 'iterable_items_removed_at_indexes': {'root': {6: 6, 0: 5}}}
        delta_dict2 = {'iterable_items_added_at_indexes': {'root': {1: 4, 2: 4, 5: 4}}, 'values_changed': {'root[6]': {'new_value': 7}, 'root[0]': {'new_value': 8}}}
        delta1 = Delta(delta_dict1)
        t1_plus_delta1 = t1 + delta1
        assert t1_plus_delta1 == t2
        delta2 = Delta(delta_dict2)
        t1_plus_delta2 = t1 + delta2
        assert t1_plus_delta2 == (8, 4, 4, 1, 3, 4, 1, 7)

        flat_result1 = delta1.to_flat_rows()
        flat_expected1 = [
            {'path': [0], 'value': 7, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [6], 'value': 8, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [1], 'value': 4, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [2], 'value': 4, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [5], 'value': 4, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [6], 'value': 6, 'action': 'unordered_iterable_item_removed', 'type': int},
            {'path': [0], 'value': 5, 'action': 'unordered_iterable_item_removed', 'type': int},
        ]
        flat_expected1 = [FlatDeltaRow(**i) for i in flat_expected1]
        assert flat_expected1 == flat_result1

        delta1_again = Delta(flat_rows_list=flat_expected1)
        assert t1_plus_delta1 == t1 + delta1_again
        assert delta1.diff == delta1_again.diff

        flat_result2 = delta2.to_flat_rows()
        flat_expected2 = [
            {'path': [1], 'value': 4, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [2], 'value': 4, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [5], 'value': 4, 'action': 'unordered_iterable_item_added', 'type': int},
            {'path': [6], 'action': 'values_changed', 'value': 7, 'type': int},
            {'path': [0], 'action': 'values_changed', 'value': 8, 'type': int},
        ]
        flat_expected2 = [FlatDeltaRow(**i) for i in flat_expected2]
        assert flat_expected2 == flat_result2

        delta2_again = Delta(flat_rows_list=flat_expected2)
        assert delta2.diff == delta2_again.diff

    def test_delta_view_and_to_delta_dict_are_equal_when_parameteres_passed(self):
        """
        This is a test that passes parameters in a dictionary instead of kwargs.
        Note that when parameters are passed as a dictionary, all of them even the ones that
        have default values need to be passed.
        """
        t1 = [4, 2, 2, 1]
        t2 = [4, 1, 1, 1]
        _parameters = {
            'ignore_order': True,
            'ignore_numeric_type_changes': False,
            'ignore_string_type_changes': False,
            'ignore_type_in_groups': [],
            'report_repetition': True,
            'use_enum_value': False,
            'exclude_paths': None,
            'include_paths': None,
            'exclude_regex_paths': None,
            'exclude_types': None,
            'exclude_types_tuple': None,
            'ignore_type_subclasses': False,
            'ignore_string_case': False,
            'include_obj_callback': None,
            'include_obj_callback_strict': None,
            'exclude_obj_callback': None,
            'exclude_obj_callback_strict': None,
            'ignore_uuid_types': False,
            'ignore_private_variables': True,
            'ignore_nan_inequality': False,
            'hasher': None,
            'significant_digits': None,
            'number_format_notation': 'f',
            'verbose_level': 1,
            'view': DELTA_VIEW,
            'max_passes': 10000000,
            'max_diffs': None,
            'number_to_string': number_to_string,
            'cache_tuning_sample_size': 500,
            'cache_size': 500,
            'cutoff_intersection_for_pairs': 0.6,
            'group_by': None,
            'ignore_order_func': lambda *args, **kwargs: True,
            'custom_operators': [],
            'encodings': None,
            'ignore_encoding_errors': False,
            'iterable_compare_func': None,
            'default_timezone': datetime.timezone.utc,
        }

        expected = {'iterable_items_added_at_indexes': {'root': {1: 1, 2: 1, 3: 1}}, 'iterable_items_removed_at_indexes': {'root': {1: 2, 2: 2}}}
        diff1 = DeepDiff(t1, t2, _parameters=_parameters)
        assert expected == diff1

        _parameters['view'] = TEXT_VIEW
        diff2 = DeepDiff(t1, t2, _parameters=_parameters)
        assert expected == diff2._to_delta_dict()

    def test_verify_symmetry_and_get_elem_and_compare_to_old_value(self):
        """
        Test a specific case where path was a list of elements (in the form of tuples)
        and the item could not be found.
        """
        delta = Delta({}, bidirectional=True, raise_errors=True, log_errors=False)
        with pytest.raises(DeltaError) as excinfo:
            delta._get_elem_and_compare_to_old_value(
                obj={},
                path_for_err_reporting=(('root', GETATTR),),
                expected_old_value='Expected Value',
                action=GET,
                elem='key')
        assert VERIFICATION_MSG.format('root', 'Expected Value', 'not found', "'key'") == str(excinfo.value)

    def test_apply_delta_to_incompatible_object1(self):
        t1 = {1: {2: [4, 5]}}
        t2 = {1: {2: [4]}, 0: 'new'}

        diff = DeepDiff(t1, t2)
        delta = Delta(diff, raise_errors=True)

        t3 = []

        with pytest.raises(DeltaError) as excinfo:
            delta + t3
        assert "Unable to get the item at root[1][2][1]: list index out of range" == str(excinfo.value)
        assert [] == t3

    def test_apply_delta_to_incompatible_object3_errors_can_be_muted(self):
        t1 = {1: {2: [4]}}
        t2 = {1: {2: [4, 6]}}
        t3 = []

        diff = DeepDiff(t1, t2)

        delta2 = Delta(diff, raise_errors=False)
        t4 = delta2 + t3
        assert [] == t4

    def test_apply_delta_to_incompatible_object4_errors_can_be_muted(self):
        t1 = {1: {2: [4, 5]}}
        t2 = {1: {2: [4]}, 0: 'new'}
        t3 = []

        diff = DeepDiff(t1, t2)

        # The original delta was based on a diff between 2 dictionaries.
        # if we turn raise_errors=False, we can try to see what portions of the delta
        delta2 = Delta(diff, raise_errors=False)
        t4 = delta2 + t3
        assert ['new'] == t4

    def test_apply_delta_to_incompatible_object5_no_errors_detected(self):
        t1 = {3: {2: [4]}}
        t2 = {3: {2: [4]}, 0: 'new', 1: 'newer'}
        diff = DeepDiff(t1, t2)

        t3 = []
        # The original delta was based on a diff between 2 dictionaries.
        # if we turn raise_errors=True, and there are no errors, a delta can be applied fully to another object!
        delta2 = Delta(diff, raise_errors=True)
        t4 = delta2 + t3
        assert ['new', 'newer'] == t4

    def test_apply_delta_to_incompatible_object6_value_change(self):
        t1 = {1: {2: [4]}}
        t2 = {1: {2: [5]}}
        t3 = []

        diff = DeepDiff(t1, t2)

        delta2 = Delta(diff, raise_errors=False)
        t4 = delta2 + t3
        assert [] == t4

        flat_result2 = delta2.to_flat_rows()
        flat_expected2 = [{'path': [1, 2, 0], 'action': 'values_changed', 'value': 5, 'type': int}]
        flat_expected2 = [FlatDeltaRow(**i) for i in flat_expected2]

        assert flat_expected2 == flat_result2

        delta2_again = Delta(flat_rows_list=flat_expected2)
        assert delta2.diff == delta2_again.diff

        delta3 = Delta(diff, raise_errors=False, bidirectional=True)
        flat_result3 = delta3.to_flat_rows()
        flat_expected3 = [{'path': [1, 2, 0], 'action': 'values_changed', 'value': 5, 'old_value': 4, 'type': int, 'old_type': int}]
        flat_expected3 = [FlatDeltaRow(**i) for i in flat_expected3]

        assert flat_expected3 == flat_result3

        delta3_again = Delta(flat_rows_list=flat_expected3)
        assert delta3.diff == delta3_again.diff

    def test_apply_delta_to_incompatible_object7_type_change(self):
        t1 = ['1']
        t2 = [1]
        t3 = ['a']

        diff = DeepDiff(t1, t2)

        delta2 = Delta(diff, raise_errors=False)
        t4 = delta2 + t3
        assert ['a'] == t4

    @mock.patch('deepdiff.delta.logger.error')
    def test_apply_delta_to_incompatible_object7_verify_symmetry(self, mock_logger):
        t1 = [1]
        t2 = [2]
        t3 = [3]

        diff = DeepDiff(t1, t2)

        delta2 = Delta(diff, raise_errors=False, bidirectional=True)
        t4 = delta2 + t3

        assert [2] == t4
        expected_msg = VERIFICATION_MSG.format('root[0]', 1, 3, VERIFY_BIDIRECTIONAL_MSG)
        mock_logger.assert_called_once_with(expected_msg)

    @mock.patch('deepdiff.delta.logger.error')
    def test_apply_delta_to_incompatible_object8_verify_symmetry_ignore_order(self, mock_logger):
        t1 = [1, 2, 'B', 3]
        t2 = [1, 2, 3, 5]
        t3 = []

        diff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True)

        delta2 = Delta(diff, raise_errors=False, bidirectional=True)
        t4 = delta2 + t3

        assert [5] == t4
        expected_msg = INDEXES_NOT_FOUND_WHEN_IGNORE_ORDER.format({3: 5})
        mock_logger.assert_called_once_with(expected_msg)

    @mock.patch('deepdiff.delta.logger.error')
    def test_apply_delta_to_incompatible_object9_ignore_order_and_verify_symmetry(self, mock_logger):
        t1 = [1, 2, 'B']
        t2 = [1, 2]
        t3 = [1, 2, 'C']

        diff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True)

        delta = Delta(diff, raise_errors=False, bidirectional=True)
        t4 = delta + t3

        assert [1, 2, 'C'] == t4
        expected_msg = FAIL_TO_REMOVE_ITEM_IGNORE_ORDER_MSG.format(2, 'root', 'B', 'C')
        mock_logger.assert_called_once_with(expected_msg)

    @mock.patch('deepdiff.delta.logger.error')
    def test_apply_delta_to_incompatible_object10_ignore_order(self, mock_logger):
        t1 = [1, 2, 'B']
        t2 = [1, 2]
        t3 = [1, 2, 'C']

        diff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True)

        # when bidirectional=False, we still won't remove the item that is different
        # than what we expect specifically when ignore_order=True when generating the diff.
        # The reason is that when ignore_order=True, we can' rely too much on the index
        # of the item alone to delete it. We need to make sure we are deleting the correct value.
        # The expected behavior is exactly the same as when bidirectional=True
        # specifically for when ignore_order=True AND an item is removed.
        delta = Delta(diff, raise_errors=False, bidirectional=False)
        t4 = delta + t3

        assert [1, 2, 'C'] == t4
        expected_msg = FAIL_TO_REMOVE_ITEM_IGNORE_ORDER_MSG.format(2, 'root', 'B', 'C')
        mock_logger.assert_called_once_with(expected_msg)

    @mock.patch('deepdiff.delta.logger.error')
    def test_apply_delta_to_incompatible_object11_ignore_order(self, mock_logger):
        t1 = [[1, 2, 'B']]
        t2 = [[1, 2]]
        t3 = {}

        diff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True)
        delta = Delta(diff, raise_errors=False, bidirectional=False)
        t4 = delta + t3

        assert {} == t4
        expected_msg = UNABLE_TO_GET_PATH_MSG.format('root[0][0]')
        mock_logger.assert_called_once_with(expected_msg)

    def test_delta_to_dict(self):
        t1 = [1, 2, 'B']
        t2 = [1, 2]
        diff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True)
        delta = Delta(diff, raise_errors=False, bidirectional=False)

        result = delta.to_dict()
        expected = {'iterable_items_removed_at_indexes': {'root': {2: 'B'}}}
        assert expected == result

        flat_result = delta.to_flat_rows()
        flat_expected = [{'action': 'unordered_iterable_item_removed', 'path': [2], 'value': 'B', 'type': str}]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]

        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected)
        assert delta.diff == delta_again.diff

    def test_class_type_change(self):
        t1 = CustomClass
        t2 = CustomClass2
        diff = DeepDiff(t1, t2, view=DELTA_VIEW)
        expected = {'type_changes': {'root': {'new_type': CustomClass2,
                    'old_type': CustomClass}}}

        assert expected == diff

    def test_numpy_type_invalid(self):
        t1 = np.array([[1, 2, 3], [4, 2, 2]], np.int8)
        diff = {
            'iterable_item_added': {'root[2]': [7, 8, 9]},
            'values_changed': {
                'root[0][2]': {
                    'new_value': 5
                },
                'root[1][1]': {
                    'new_value': 1
                }
            },
            '_numpy_paths': {
                'root': 'int88'
            }
        }

        delta = Delta(diff, raise_errors=True)
        with pytest.raises(DeltaError) as excinfo:
            delta + t1
        assert "'int88' is not a valid numpy type." == str(excinfo.value)

    def test_ignore_order_but_not_report_repetition(self):
        t1 = [1, 2, 'B', 3]
        t2 = [1, 2, 3, 5]

        with pytest.raises(ValueError) as excinfo:
            Delta(DeepDiff(t1, t2, ignore_order=True))

        assert DELTA_IGNORE_ORDER_NEEDS_REPETITION_REPORT == str(excinfo.value)

    def test_none_in_delta_object(self):
        t1 = {"a": None}
        t2 = {"a": 1}

        dump = Delta(DeepDiff(t1, t2)).dumps()
        delta = Delta(dump)
        assert t2 == delta + t1

        flat_result = delta.to_flat_rows()
        flat_expected = [{'path': ['a'], 'action': 'type_changes', 'value': 1, 'type': int, 'old_type': type(None)}]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]

        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected)
        assert delta.diff == delta_again.diff

        with pytest.raises(ValueError) as exc_info:
            delta.to_flat_rows(report_type_changes=False)
        assert str(exc_info.value).startswith("When converting to flat dictionaries, if report_type_changes=False and there are type")
        delta2 = Delta(dump, always_include_values=True)
        flat_result2 = delta2.to_flat_rows(report_type_changes=False)
        flat_expected2 = [{'path': ['a'], 'action': 'values_changed', 'value': 1}]
        flat_expected2 = [FlatDeltaRow(**i) for i in flat_expected2]

        assert flat_expected2 == flat_result2

    def test_delta_set_in_objects(self):
        t1 = [[1, SetOrdered(['A', 'B'])], {1}]
        t2 = [[2, SetOrdered([10, 'C', 'B'])], {1}]
        delta = Delta(DeepDiff(t1, t2))
        flat_result = delta.to_flat_rows()
        flat_expected = [
            {'path': [0, 1], 'value': 10, 'action': 'set_item_added', 'type': int},
            {'path': [0, 0], 'action': 'values_changed', 'value': 2, 'type': int},
            {'path': [0, 1], 'value': 'A', 'action': 'set_item_removed', 'type': str},
            {'path': [0, 1], 'value': 'C', 'action': 'set_item_added', 'type': str},
        ]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]

        # Sorting because otherwise the order is not deterministic for sets,
        # even though we are using SetOrdered here. It still is converted to set at some point and loses its order.
        flat_result.sort(key=lambda x: str(x.value))
        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected)
        assert delta.diff == delta_again.diff

    def test_delta_array_of_bytes(self):
        t1 = []
        t2 = [b"hello"]
        diff = DeepDiff(t1, t2)
        expected_diff = {'iterable_item_added': {'root[0]': b'hello'}}
        assert expected_diff == diff
        delta = Delta(diff)
        flat_result = delta.to_flat_rows()
        flat_expected = [FlatDeltaRow(path=[0], action=FlatDataAction.iterable_item_added, value=b'hello', type=bytes)]
        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected)
        assert delta.diff == delta_again.diff
        assert t1 + delta_again == t2

    def test_delta_with_json_serializer(self):
        t1 = {"a": 1}
        t2 = {"a": 2}

        diff = DeepDiff(t1, t2)
        delta = Delta(diff, serializer=json.dumps)
        dump = delta.dumps()
        delta_reloaded = Delta(dump, deserializer=json.loads)
        assert t2 == delta_reloaded + t1

        the_file = io.StringIO()
        delta.dump(the_file)
        the_file.seek(0)

        delta_reloaded_again = Delta(delta_file=the_file, deserializer=json.loads)
        assert t2 == delta_reloaded_again + t1

    def test_brackets_in_keys(self):
        """
        Delta calculation not correct when bracket in Json key
        https://github.com/seperman/deepdiff/issues/265
        """
        t1 = "{ \
            \"test\": \"test1\" \
        }"

        t2 = "{ \
            \"test\": \"test1\", \
            \"test2 [uuu]\": \"test2\" \
        }"

        json1 = json.loads(t1)
        json2 = json.loads(t2)

        ddiff = DeepDiff(json1, json2)
        delta = Delta(ddiff)

        original_json2 = delta + json1
        assert json2 == original_json2


class TestDeltaCompareFunc:

    @staticmethod
    def compare_func(x, y, level):
        if (not isinstance(x, dict) or not isinstance(y, dict)):
            raise CannotCompare
        if(level.path() == "root['path2']"):
            if (x["ID"] == y["ID"]):
                return True
            return False

        if("id" in x and "id" in y):
            if (x["id"] == y["id"]):
                return True
            return False

        raise CannotCompare

    def test_compare_func1(self, compare_func_t1, compare_func_t2, compare_func_result1):

        ddiff = DeepDiff(
            compare_func_t1, compare_func_t2,
            iterable_compare_func=self.compare_func, verbose_level=1)
        assert compare_func_result1 == ddiff
        delta = Delta(ddiff)
        recreated_t2 = compare_func_t1 + delta
        assert compare_func_t2 == recreated_t2

    def test_compare_func_with_duplicates_removed(self):
        t1 = [
            {
                'id': 1,
                'val': 1,
                "nested": [
                    {"id": 1, "val": 1},
                    {"id": 2, "val": 2},
                ]
            },
            {
                'id': 2,
                'val': 2
            },
            {
                'id': 1,
                'val': 3
            },
            {
                'id': 3,
                'val': 3
            }
        ]
        t2 = [
            {
                'id': 3,
                'val': 3
            },
            {
                'id': 2,
                'val': 2
            },
            {
                'id': 1,
                'val': 3,
                "nested":[
                    {
                        "id": 2,
                        "val": 3
                    },
                ]
            }
        ]
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func, verbose_level=2)
        expected = {
            "iterable_item_removed": {
                "root[2]": {
                    "id": 1,
                    "val": 3
                },

                "root[2]['nested'][0]": {
                    "id": 1,
                    "val": 1
                }
            },
            "iterable_item_moved": {
                "root[0]": {
                    "new_path": "root[2]",
                    "value": {
                        "id": 1,
                        "val": 3,
                        "nested": [{"id": 2, "val": 3}, ]
                    },
                },
                "root[0]['nested'][1]": {
                    "new_path": "root[2]['nested'][0]",
                    "value": {
                        "id": 2,
                        "val": 3
                    }
                },
                "root[3]": {
                    "new_path": "root[0]",
                    "value": {
                        "id": 3,
                        "val": 3
                    }
                }
            },
            'values_changed': {
                "root[2]['nested'][0]['val']": {
                    'new_path': "root[0]['nested'][1]['val']",
                    'new_value': 3,
                    'old_value': 2
                },
                "root[2]['val']": {
                    'new_value': 3,
                    'old_value': 1,
                    'new_path': "root[0]['val']"
                }
            },
        }

        assert expected == ddiff
        delta = Delta(ddiff)
        recreated_t2 = t1 + delta
        assert t2 == recreated_t2

        flat_result = delta.to_flat_rows()
        flat_expected = [
            {'path': [2, 'val'], 'value': 3, 'action': 'values_changed', 'type': int, 'new_path': [0, 'val']},
            {'path': [2, 'nested', 0, 'val'], 'value': 3, 'action': 'values_changed', 'type': int, 'new_path': [0, 'nested', 1, 'val']},
            {'path': [2, 'nested', 0], 'value': {'id': 1, 'val': 1}, 'action': 'iterable_item_removed', 'type': dict},
            {'path': [2], 'value': {'id': 1, 'val': 3}, 'action': 'iterable_item_removed', 'type': dict},
            {'path': [0], 'value': {'id': 1, 'val': 3, 'nested': [{'id': 2, 'val': 3}]}, 'action': 'iterable_item_removed', 'type': dict},
            {'path': [0, 'nested', 1], 'value': {'id': 2, 'val': 3}, 'action': 'iterable_item_removed', 'type': dict},
            {'path': [3], 'value': {'id': 3, 'val': 3}, 'action': 'iterable_item_removed', 'type': dict},
            {'path': [0], 'action': 'iterable_item_moved', 'value': {'id': 1, 'val': 3, 'nested': [{'id': 2, 'val': 3}]}, 'new_path': [2], 'type': dict},
            {'path': [0, 'nested', 1], 'value': {'id': 2, 'val': 3}, 'action': 'iterable_item_moved', 'type': dict, 'new_path': [2, 'nested', 0]},
            {'path': [3], 'action': 'iterable_item_moved', 'value': {'id': 3, 'val': 3}, 'new_path': [0], 'type': dict},
        ]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]

        assert flat_expected == flat_result

        # Delta.DEBUG = True
        delta_again = Delta(flat_rows_list=flat_expected, iterable_compare_func_was_used=True)
        expected_delta_dict = {
            'iterable_item_removed': {
                'root[2]': {
                    'id': 1,
                    'val': 3
                },
                'root[0]': {
                    'id': 1,
                    'val': 3,
                    'nested': [{'id': 2, 'val': 3}]
                },
                'root[3]': {
                    'id': 3,
                    'val': 3
                },
                "root[2]['nested'][0]": {
                    "id": 1,
                    "val": 1
                },
                "root[0]['nested'][1]": {
                    "id": 2,
                    "val": 3
                }
            },
            'iterable_item_moved': {
                'root[0]': {
                    'new_path': 'root[2]',
                    'value': {
                        'id': 1,
                        'val': 3,
                        'nested': [{'id': 2, 'val': 3}]
                    }
                },
                "root[0]['nested'][1]": {
                    'new_path': "root[2]['nested'][0]",
                    'value': {
                        'id': 2,
                        'val': 3
                    }
                },
                'root[3]': {
                    'new_path': 'root[0]',
                    'value': {
                        'id': 3,
                        'val': 3
                    }
                }
            },
            'values_changed': {
                "root[2]['val']": {
                    'new_value': 3,
                    'new_path': "root[0]['val']",
                },
                "root[2]['nested'][0]['val']": {
                    'new_path': "root[0]['nested'][1]['val']",
                    'new_value': 3,
                },
            }
        }
        assert expected_delta_dict == delta_again.diff
        assert t2 == t1 + delta_again

    def test_compare_func_with_duplicates_added(self):
        t1 = [{'id': 3, 'val': 3}, {'id': 2, 'val': 2}, {'id': 1, 'val': 3}]
        t2 = [{'id': 1, 'val': 1}, {'id': 2, 'val': 2}, {'id': 1, 'val': 3}, {'id': 3, 'val': 3}]
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func, verbose_level=2)
        expected = {
            'iterable_item_added': {
                'root[2]': {
                    'id': 1,
                    'val': 3
                }
            },
            'iterable_item_moved': {
                'root[0]': {
                    'new_path': 'root[3]',
                    'value': {
                        'id': 3,
                        'val': 3
                    }
                },
                'root[2]': {
                    'new_path': 'root[0]',
                    'value': {
                        'id': 1,
                        'val': 1
                    }
                }
            },
            'values_changed': {
                "root[0]['val']": {
                    'new_value': 1,
                    'old_value': 3,
                    'new_path': "root[2]['val']"
                }
            },
        }
        assert expected == ddiff
        delta = Delta(ddiff)
        flat_rows_before_apply = delta.to_flat_rows()
        recreated_t2 = t1 + delta
        assert t2 == recreated_t2
        assert flat_rows_before_apply == delta.to_flat_rows()

    def test_compare_func_swap(self):
        t1 = [{'id': 1, 'val': 1}, {'id': 1, 'val': 3}]
        t2 = [{'id': 1, 'val': 3}, {'id': 1, 'val': 1}]
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func, verbose_level=2)
        expected = {'values_changed': {"root[0]['val']": {'new_value': 3, 'old_value': 1}, "root[1]['val']": {'new_value': 1, 'old_value': 3}}}
        assert expected == ddiff
        delta = Delta(ddiff)
        recreated_t2 = t1 + delta
        assert t2 == recreated_t2

    def test_compare_func_path_specific(self):
        t1 = {"path1": [{'id': 1, 'val': 1}, {'id': 2, 'val': 3}], "path2": [{'ID': 4, 'val': 3}, {'ID': 3, 'val': 1}, ], "path3": [{'no_id': 5, 'val': 1}, {'no_id': 6, 'val': 3}]}
        t2 = {"path1": [{'id': 1, 'val': 1}, {'id': 2, 'val': 3}], "path2": [{'ID': 3, 'val': 1}, {'ID': 4, 'val': 3}], "path3": [{'no_id': 5, 'val': 1}, {'no_id': 6, 'val': 3}]}
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func, verbose_level=2)
        expected = {'iterable_item_moved': {"root['path2'][0]": {'new_path': "root['path2'][1]", 'value': {'ID': 4, 'val': 3}},"root['path2'][1]": {'new_path': "root['path2'][0]", 'value': {'ID': 3, 'val': 1}}}}
        assert expected == ddiff
        delta = Delta(ddiff)
        recreated_t2 = t1 + delta
        assert t2 == recreated_t2

    def test_compare_func_nested_changes(self):
        t1 = {
            "TestTable": [
                {
                    "id": "022fb580-800e-11ea-a361-39b3dada34b5",
                    "name": "Max",
                    "NestedTable": [
                        {
                            "id": "022fb580-800e-11ea-a361-39b3dada34a6",
                            "NestedField": "Test Field"
                        }
                    ]
                },
                {
                    "id": "022fb580-800e-11ea-a361-12354656532",
                    "name": "Bob",
                    "NestedTable": [
                        {
                            "id": "022fb580-800e-11ea-a361-39b3dada34c7",
                            "NestedField": "Test Field 2"
                        },
                    ]
                },
            ]
        }
        t2 = {"TestTable": [
            {
                "id": "022fb580-800e-11ea-a361-12354656532",
                "name": "Bob (Changed Name)",
                "NestedTable": [
                    {
                        "id": "022fb580-800e-11ea-a361-39b3dada34c7",
                        "NestedField": "Test Field 2 (Changed Nested Field)"
                    },
                    {
                        "id": "new id",
                        "NestedField": "Test Field 3"
                    },
                    {
                        "id": "newer id",
                        "NestedField": "Test Field 4"
                    },
                ]
            },
            {
                "id": "adding_some_random_id",
                "name": "New Name",
                "NestedTable": [
                    {
                        "id": "random_nested_id_added",
                        "NestedField": "New Nested Field"
                    },
                    {
                        "id": "random_nested_id_added2",
                        "NestedField": "New Nested Field2"
                    },
                    {
                        "id": "random_nested_id_added3",
                        "NestedField": "New Nested Field43"
                    },
                ]
            }
        ]}

        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func, verbose_level=2)
        delta = Delta(ddiff)
        recreated_t2 = t1 + delta
        assert t2 == recreated_t2

    def test_compare_func_deep_nested_changes(self):

        t1 = {
            "Locations": [
                {
                    "id": "c4fa7b12-f365-42a9-9544-3efc11963558",
                    "Items": [
                        {
                            "id": "2399528f-2556-4e2c-bf9b-c8ea17bc323f"
                        },
                        {
                            "id": "2399528f-2556-4e2c-bf9b-c8ea17bc323f1",
                        },
                        {
                            "id": "2399528f-2556-4e2c-bf9b-c8ea17bc323f2"
                        },
                        {
                            "id": "2399528f-2556-4e2c-bf9b-c8ea17bc323f3"
                        }
                    ]
                },
                {
                    "id": "d9095676-bc41-4cbf-9fd2-7148bb26bcc4",
                    "Items": [
                        {
                            "id": "26b78305-df71-40c0-8e98-dcd40b7f716d"
                        },
                        {
                            "id": "3235125d-0110-4d0e-847a-24912cf73feb"
                        },
                        {
                            "id": "7699552a-add9-4338-aeb9-662bec14c175"
                        },
                        {
                            "id": "015e74f0-2c2a-45c0-a172-21758d14bf3a"
                        }
                    ]
                },
                {
                    "id": "41b38757-8984-47fd-890d-8c4ed18c3c47",
                    "Items": [
                        {
                            "id": "494e839e-37b1-4cac-b1dc-a44f3e6e7ada"
                        },
                        {
                            "id": "60547ca6-3ef0-4b67-8826-2c7b76e67011"
                        },
                        {
                            "id": "cee762a0-fbd8-48bb-ba92-be32cf3cf250"
                        },
                        {
                            "id": "7a0da2b7-c1e6-45b4-8810-fec7b4b6186d"
                        }
                    ]
                },
                {
                    "id": "c0be071a-5457-497d-9a78-ff7cb561d4d3",
                    "Items": [
                        {
                            "id": "e54dcdff-ec99-4941-92eb-c12bb3cbeb91"
                        }
                    ]
                },
                {
                    "id": "dfe4b37b-8df3-4dc6-8686-0588937fbe10",
                    "Items": [
                        {
                            "id": "27a574ae-08db-47f9-a9dc-18df59287f4d"
                        },
                        {
                            "id": "23edf031-8c4e-43d6-b5bf-4d5ee9008a36",
                            "Containers": [
                                {"id": "1", "val": 1},
                                {"id": "2", "val": 2},
                                {"id": "3", "val": 3},
                            ]
                        },
                        {
                            "id": "e1e54643-23ee-496d-b7d2-de67c4bb7d68"
                        },
                        {
                            "id": "2f910da3-8cd0-4cf5-81c9-23668fc9477f"
                        },
                        {
                            "id": "5e36d258-2a82-49ee-b4fc-db0a8c28b404"
                        },
                        {
                            "id": "4bf2ce8d-05ed-4718-a529-8c9e4704e38f"
                        },
                    ]
                },
            ]
        }

        t2 = {
            "Locations": [
                {
                    "id": "41b38757-8984-47fd-890d-8c4ed18c3c47",
                    "Items": [
                        {
                            "id": "60547ca6-3ef0-4b67-8826-2c7b76e67011"
                        },
                        {
                            "id": "cee762a0-fbd8-48bb-ba92-be32cf3cf250"
                        },
                        {
                            "id": "7a0da2b7-c1e6-45b4-8810-fec7b4b6186d"
                        }
                    ]
                },
                {
                    "id": "c0be071a-5457-497d-9a78-ff7cb561d4d3",
                    "Items": [
                        {
                            "id": "e54dcdff-ec99-4941-92eb-c12bb3cbeb91"
                        }
                    ]
                },
                {
                    "id": "dfe4b37b-8df3-4dc6-8686-0588937fbe10",
                    "Items": [
                        {
                            "id": "27a574ae-08db-47f9-a9dc-18df59287f4d"
                        },
                        {
                            "id": "27a574ae-08db-47f9-a9dc-88df59287f4d"
                        },
                        {
                            "id": "23edf031-8c4e-43d6-b5bf-4d5ee9008a36",
                            "Containers": [
                                {"id": "1", "val": 1},
                                {"id": "3", "val": 3},
                                {"id": "2", "val": 2},
                            ]
                        },
                        {
                            "id": "e1e54643-23ee-496d-b7d2-de67c4bb7d68"
                        },
                        {
                            "id": "2f910da3-8cd0-4cf5-81c9-23668fc9477f"
                        },
                        {
                            "id": "5e36d258-2a82-49ee-b4fc-db0a8c28b404"
                        },
                        {
                            "id": "4bf2ce8d-05ed-4718-a529-8c9e4704e38f"
                        },
                    ]
                },
            ]
        }

        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func, verbose_level=2)

        delta2 = Delta(ddiff)
        expected_move_1 = {'new_path': "root['Locations'][2]['Items'][2]['Containers'][2]", 'value': {'id': '2', 'val': 2}}
        expected_move_2 = {'new_path': "root['Locations'][2]['Items'][2]['Containers'][1]", 'value': {'id': '3', 'val': 3}}
        assert ddiff["iterable_item_moved"]["root['Locations'][4]['Items'][1]['Containers'][1]"] == expected_move_1
        assert ddiff["iterable_item_moved"]["root['Locations'][4]['Items'][1]['Containers'][2]"] == expected_move_2
        recreated_t2 = t1 + delta2
        assert t2 == recreated_t2

    def test_delta_force1(self):
        t1 = {
            'x': {
                'y': [1, 2, 3]
            },
            'q': {
                'r': 'abc',
            }
        }

        t2 = {
            'x': {
                'y': [1, 2, 3, 4]
            },
            'q': {
                'r': 'abc',
                't': 0.5,
            }
        }

        diff = DeepDiff(t1, t2)

        delta = Delta(diff=diff, force=True)
        result = {} + delta
        expected = {'x': {'y': {3: 4}}, 'q': {'t': 0.5}}
        assert expected == result

    def test_delta_force_fill(self):
        t1 = {
            'x': {
                'y': [{"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}]
            },
            'q': {
                'r': 'abc',
            }
        }

        t2 = {
            'x': {
                'y': [{"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}]
            },
            'q': {
                'r': 'abc',
                't': 0.5,
            }
        }

        diff = DeepDiff(t1, t2)

        delta = Delta(diff=diff, force=True)
        result = {"x": {"y": [1,]}} + delta
        expected = {'x': {'y': [1]}, 'q': {'t': 0.5}}
        assert expected == result


        delta = Delta(diff=diff, force=True, fill=None)
        result = {"x": {"y": [1,]}} + delta
        expected = {'x': {'y': [1, None, None, None, {"b": "c"}, {"b": "c"}, {"b": "c"}]}, 'q': {'t': 0.5}}
        assert expected == result


        def fill_func(obj, value, path):
            return value.copy()

        delta = Delta(diff=diff, force=True, fill=fill_func)
        result = {"x": {"y": [1,]}} + delta
        expected = {'x': {'y': [1, {"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}, {"b": "c"}]}, 'q': {'t': 0.5}}
        assert expected == result

    def test_flatten_dict_with_one_key_added(self):
        t1 = {"field1": {"joe": "Joe"}}
        t2 = {"field1": {"joe": "Joe Nobody"}, "field2": {"jimmy": "Jimmy"}}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        flat_result = delta.to_flat_rows(report_type_changes=False)
        flat_expected = [
            {'path': ['field2', 'jimmy'], 'value': 'Jimmy', 'action': 'dictionary_item_added'},
            {'path': ['field1', 'joe'], 'action': 'values_changed', 'value': 'Joe Nobody'},
        ]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]
        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected, force=True)  # We need to enable force so it creates the dictionary when added to t1
        expected_data_again_diff = {'dictionary_item_added': {"root['field2']['jimmy']": 'Jimmy'}, 'values_changed': {"root['field1']['joe']": {'new_value': 'Joe Nobody'}}}

        assert delta.diff != delta_again.diff, "Since a dictionary containing a single field was created, the flat dict acted like one key was added."
        assert expected_data_again_diff == delta_again.diff, "Since a dictionary containing a single field was created, the flat dict acted like one key was added."

        assert t2 == t1 + delta_again

    def test_flatten_dict_with_multiple_keys_added(self):
        t1 = {"field1": {"joe": "Joe"}}
        t2 = {"field1": {"joe": "Joe Nobody"}, "field2": {"jimmy": "Jimmy", "sar": "Sarah"}}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        flat_result = delta.to_flat_rows(report_type_changes=False)
        flat_expected = [
            {'path': ['field2'], 'value': {'jimmy': 'Jimmy', 'sar': 'Sarah'}, 'action': 'dictionary_item_added'},
            {'path': ['field1', 'joe'], 'action': 'values_changed', 'value': 'Joe Nobody'},
        ]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]
        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected)
        assert delta.diff == delta_again.diff

    def test_flatten_list_with_one_item_added(self):
        t1 = {"field1": {"joe": "Joe"}}
        t2 = {"field1": {"joe": "Joe"}, "field2": ["James"]}
        t3 = {"field1": {"joe": "Joe"}, "field2": ["James", "Jack"]}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        flat_result = delta.to_flat_rows(report_type_changes=False)
        flat_expected = [{'path': ['field2', 0], 'value': 'James', 'action': 'iterable_item_added'}]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]
        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected, force=True)
        assert {'iterable_item_added': {"root['field2'][0]": 'James'}} == delta_again.diff
        # delta_again.DEBUG = True
        assert t2 == t1 + delta_again

        diff2 = DeepDiff(t2, t3)
        delta2 = Delta(diff=diff2, always_include_values=True)
        flat_result2 = delta2.to_flat_rows(report_type_changes=False)
        flat_expected2 = [{'path': ['field2', 1], 'value': 'Jack', 'action': 'iterable_item_added'}]
        flat_expected2 = [FlatDeltaRow(**i) for i in flat_expected2]

        assert flat_expected2 == flat_result2

        delta_again2 = Delta(flat_rows_list=flat_expected2, force=True)

        assert {'iterable_item_added': {"root['field2'][1]": 'Jack'}} == delta_again2.diff
        assert t3 == t2 + delta_again2

    def test_flatten_set_with_one_item_added(self):
        t1 = {"field1": {"joe": "Joe"}}
        t2 = {"field1": {"joe": "Joe"}, "field2": {"James"}}
        t3 = {"field1": {"joe": "Joe"}, "field2": {"James", "Jack"}}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        assert t2 == t1 + delta
        flat_result = delta.to_flat_rows(report_type_changes=False)
        flat_expected = [{'path': ['field2'], 'value': 'James', 'action': 'set_item_added'}]
        flat_expected = [FlatDeltaRow(**i) for i in flat_expected]
        assert flat_expected == flat_result

        delta_again = Delta(flat_rows_list=flat_expected, force=True)
        assert {'set_item_added': {"root['field2']": {'James'}}} == delta_again.diff
        assert t2 == t1 + delta_again

        diff = DeepDiff(t2, t3)
        delta2 = Delta(diff=diff, always_include_values=True)
        flat_result2 = delta2.to_flat_rows(report_type_changes=False)
        flat_expected2 = [{'path': ['field2'], 'value': 'Jack', 'action': 'set_item_added'}]
        flat_expected2 = [FlatDeltaRow(**i) for i in flat_expected2]

        assert flat_expected2 == flat_result2

        delta_again2 = Delta(flat_rows_list=flat_expected2, force=True)
        assert {'set_item_added': {"root['field2']": {'Jack'}}} == delta_again2.diff
        assert t3 == t2 + delta_again2

    def test_flatten_tuple_with_one_item_added(self):
        t1 = {"field1": {"joe": "Joe"}}
        t2 = {"field1": {"joe": "Joe"}, "field2": ("James", )}
        t3 = {"field1": {"joe": "Joe"}, "field2": ("James", "Jack")}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        assert t2 == t1 + delta
        flat_expected = delta.to_flat_rows(report_type_changes=False)
        expected_result = [{'path': ['field2', 0], 'value': 'James', 'action': 'iterable_item_added'}]
        expected_result = [FlatDeltaRow(**i) for i in expected_result]

        assert expected_result == flat_expected

        delta_again = Delta(flat_rows_list=flat_expected, force=True)
        assert {'iterable_item_added': {"root['field2'][0]": 'James'}} == delta_again.diff
        assert {'field1': {'joe': 'Joe'}, 'field2': ['James']} == t1 + delta_again, "We lost the information about tuple when we convert to flat dict."

        diff = DeepDiff(t2, t3)
        delta2 = Delta(diff=diff, always_include_values=True, force=True)
        flat_result2 = delta2.to_flat_rows(report_type_changes=False)
        expected_result2 = [{'path': ['field2', 1], 'value': 'Jack', 'action': 'iterable_item_added'}]
        expected_result2 = [FlatDeltaRow(**i) for i in expected_result2]

        assert expected_result2 == flat_result2
        assert t3 == t2 + delta2

        delta_again2 = Delta(flat_rows_list=flat_result2)
        assert {'iterable_item_added': {"root['field2'][1]": 'Jack'}} == delta_again2.diff
        assert t3 == t2 + delta_again2

    def test_flatten_list_with_multiple_item_added(self):
        t1 = {"field1": {"joe": "Joe"}}
        t2 = {"field1": {"joe": "Joe"}, "field2": ["James", "Jack"]}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        flat_result = delta.to_flat_rows(report_type_changes=False)
        expected_result = [{'path': ['field2'], 'value': ['James', 'Jack'], 'action': 'dictionary_item_added'}]
        expected_result = [FlatDeltaRow(**i) for i in expected_result]

        assert expected_result == flat_result

        delta2 = Delta(diff=diff, bidirectional=True, always_include_values=True)
        flat_result2 = delta2.to_flat_rows(report_type_changes=False)
        assert expected_result == flat_result2

        delta_again = Delta(flat_rows_list=flat_result)
        assert delta.diff == delta_again.diff

    def test_flatten_attribute_added(self):
        t1 = picklalbe_obj_without_item
        t2 = PicklableClass(10)
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, always_include_values=True)
        flat_result = delta.to_flat_rows(report_type_changes=False)
        expected_result = [{'path': ['item'], 'value': 10, 'action': 'attribute_added'}]
        expected_result = [FlatDeltaRow(**i) for i in expected_result]

        assert expected_result == flat_result

        delta_again = Delta(flat_rows_list=flat_result)
        assert delta.diff == delta_again.diff

    def test_flatten_when_simple_type_change(self):
        t1 = [1, 2, '3']
        t2 = [1, 2, 3]

        diff = DeepDiff(t1, t2)
        expected_diff = {
            'type_changes': {'root[2]': {'old_type': str, 'new_type': int, 'old_value': '3', 'new_value': 3}}
        }

        assert expected_diff == diff
        delta = Delta(diff=diff)
        with pytest.raises(ValueError) as exc_info:
            delta.to_flat_rows(report_type_changes=False)
        assert str(exc_info.value).startswith("When converting to flat dictionaries")

        delta2 = Delta(diff=diff, always_include_values=True)
        flat_result2 = delta2.to_flat_rows(report_type_changes=False)
        expected_result2 = [{'path': [2], 'action': 'values_changed', 'value': 3}]
        expected_result2 = [FlatDeltaRow(**i) for i in expected_result2]

        assert expected_result2 == flat_result2

        delta3 = Delta(diff=diff, always_include_values=True, bidirectional=True)
        flat_result3 = delta3.to_flat_rows(report_type_changes=False)

        expected_result3 = [{'path': [2], 'action': 'values_changed', 'value': 3, 'old_value': '3'}]
        expected_result3 = [FlatDeltaRow(**i) for i in expected_result3]
        assert expected_result3 == flat_result3

        delta_again = Delta(flat_rows_list=flat_result3)
        assert {'values_changed': {'root[2]': {'new_value': 3, 'old_value': '3'}}} == delta_again.diff

    def test_subtract_delta1(self):
        t1 = {'field_name1': ['yyy']}
        t2 = {'field_name1': ['xxx', 'yyy']}
        delta_diff = {'iterable_items_removed_at_indexes': {"root['field_name1']": {(0, 'GET'): 'xxx'}}}
        expected_reverse_diff = {'iterable_items_added_at_indexes': {"root['field_name1']": {(0, 'GET'): 'xxx'}}}

        delta = Delta(delta_diff=delta_diff, bidirectional=True)
        reversed_diff = delta._get_reverse_diff()
        assert expected_reverse_diff == reversed_diff
        assert t2 != {'field_name1': ['yyy', 'xxx']} == t1 - delta, "Since iterable_items_added_at_indexes is used when ignore_order=True, the order is not necessarily the original order."

    def test_subtract_delta_made_from_flat_dicts1(self):
        t1 = {'field_name1': ['xxx', 'yyy']}
        t2 = {'field_name1': []}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, bidirectional=True)
        flat_rows_list = delta.to_flat_rows(include_action_in_path=False, report_type_changes=True)
        expected_flat_dicts = [{
            'path': ['field_name1', 0],
            'value': 'xxx',
            'action': 'iterable_item_removed',
            'type': str,
        }, {
            'path': ['field_name1', 1],
            'value': 'yyy',
            'action': 'iterable_item_removed',
            'type': str,
        }]
        expected_flat_dicts = [FlatDeltaRow(**i) for i in expected_flat_dicts]

        assert expected_flat_dicts == flat_rows_list

        delta1 = Delta(flat_rows_list=flat_rows_list, bidirectional=True, force=True)
        assert t1 == t2 - delta1

        delta2 = Delta(flat_rows_list=[flat_rows_list[0]], bidirectional=True, force=True)
        middle_t = t2 - delta2
        assert {'field_name1': ['xxx']} == middle_t

        delta3 = Delta(flat_rows_list=[flat_rows_list[1]], bidirectional=True, force=True)
        assert t1 == middle_t - delta3

    def test_subtract_delta_made_from_flat_dicts2(self):
        t1 = {'field_name1': []}
        t2 = {'field_name1': ['xxx', 'yyy']}
        diff = DeepDiff(t1, t2)
        delta = Delta(diff=diff, bidirectional=True)
        flat_rows_list = delta.to_flat_rows(include_action_in_path=False, report_type_changes=True)
        expected_flat_dicts = [{
            'path': ['field_name1', 0],
            'value': 'xxx',
            'action': 'iterable_item_added',
            'type': str,
        }, {
            'path': ['field_name1', 1],
            'value': 'yyy',
            'action': 'iterable_item_added',
            'type': str,
        }]
        expected_flat_dicts = [FlatDeltaRow(**i) for i in expected_flat_dicts]

        assert expected_flat_dicts == flat_rows_list

        delta1 = Delta(flat_rows_list=flat_rows_list, bidirectional=True, force=True)
        assert t1 == t2 - delta1

        # We need to subtract the changes in the reverse order if we want to feed the flat dict rows individually to Delta
        delta2 = Delta(flat_rows_list=[flat_rows_list[0]], bidirectional=True, force=True)
        middle_t = t2 - delta2
        assert {'field_name1': ['yyy']} == middle_t

        delta3 = Delta(flat_rows_list=[flat_rows_list[1]], bidirectional=True, force=True)
        delta3.DEBUG = True
        assert t1 == middle_t - delta3

    def test_list_of_alphabet_and_its_delta(self):
        l1 = "A B C D E F G D H".split()
        l2 = "B C X D H Y Z".split()
        diff = DeepDiff(l1, l2)

        # Problem: The index of values_changed should be either all for AFTER removals or BEFORE removals.
        # What we have here is that F & G transformation to Y and Z is not compatible with A and E removal
        # it is really meant for the removals to happen first, and then have indexes in L2 for values changing
        # rather than indexes in L1. Here what we need to have is:
        # A B C D E F G D H
        # A B C-X-E 
        # B C D F G D H  # removal

        # What we really need is to report is as it is in difflib for delta specifically:
        # A B C D E F G D H
        # B C D E F G D H     delete    t1[0:1] --> t2[0:0]    ['A'] --> []
        # B C D E F G D H     equal     t1[1:3] --> t2[0:2] ['B', 'C'] --> ['B', 'C']
        # B C X D H           replace   t1[3:7] --> t2[2:3] ['D', 'E', 'F', 'G'] --> ['X']
        # B C X D H           equal     t1[7:9] --> t2[3:5] ['D', 'H'] --> ['D', 'H']
        # B C X D H Y Z       insert    t1[9:9] --> t2[5:7]       [] --> ['Y', 'Z']

        # So in this case, it needs to also include information about what stays equal in the delta
        # NOTE: the problem is that these operations need to be performed in a specific order.
        # DeepDiff removes that order and just buckets all insertions vs. replace vs. delete in their own buckets.
        # For times that we use Difflib, we may want to keep the information for the array_change key
        # just for the sake of delta, but not for reporting in deepdiff itself.
        # that way we can re-apply the changes as they were reported in delta.

        delta = Delta(diff)
        assert l2 == l1 + delta
        with pytest.raises(ValueError) as exc_info:
            l1 == l2 - delta
        assert "Please recreate the delta with bidirectional=True" == str(exc_info.value)

        delta2 = Delta(diff, bidirectional=True)
        assert l2 == l1 + delta2
        assert l1 == l2 - delta2

        dump = Delta(diff, bidirectional=True).dumps()
        delta3 = Delta(dump, bidirectional=True)

        assert l2 == l1 + delta3
        assert l1 == l2 - delta3

        dump4 = Delta(diff, bidirectional=True, serializer=json_dumps).dumps()
        delta4 = Delta(dump4, bidirectional=True, deserializer=json_loads)

        assert l2 == l1 + delta4
        assert l1 == l2 - delta4

        flat_rows = delta2.to_flat_rows()

        expected_flat_rows = [
            FlatDeltaRow(path=[3], action='values_changed', value='X', old_value='D', type=str, old_type=str, new_path=[2]),
            FlatDeltaRow(path=[6], action='values_changed', value='Z', old_value='G', type=str, old_type=str),
            FlatDeltaRow(path=[5], action='values_changed', value='Y', old_value='F', type=str, old_type=str),
            FlatDeltaRow(path=[], action=FlatDataAction.iterable_items_deleted, value=[], old_value=['A'], type=list, old_type=list, t1_from_index=0, t1_to_index=1, t2_from_index=0, t2_to_index=0),
            FlatDeltaRow(path=[], action=FlatDataAction.iterable_items_equal, value=None, old_value=None, type=type(None), old_type=type(None), t1_from_index=1, t1_to_index=3, t2_from_index=0, t2_to_index=2),
            FlatDeltaRow(path=[], action=FlatDataAction.iterable_items_replaced, value=['X'], old_value=['D', 'E', 'F', 'G'], type=list, old_type=list, t1_from_index=3, t1_to_index=7, t2_from_index=2, t2_to_index=3),
            FlatDeltaRow(path=[], action=FlatDataAction.iterable_items_equal, value=None, old_value=None, type=type(None), old_type=type(None), t1_from_index=7, t1_to_index=9, t2_from_index=3, t2_to_index=5),
            FlatDeltaRow(path=[], action=FlatDataAction.iterable_items_inserted, value=['Y', 'Z'], old_value=[], type=list, old_type=list, t1_from_index=9, t1_to_index=9, t2_from_index=5, t2_to_index=7)
        ]

        # The order of the first 3 items is not deterministic
        assert not DeepDiff(expected_flat_rows[:3], flat_rows[:3], ignore_order=True)
        assert expected_flat_rows[3:] == flat_rows[3:]

        delta5 = Delta(flat_rows_list=flat_rows, bidirectional=True, force=True)


        assert l2 == l1 + delta5
        assert l1 == l2 - delta5

    def test_delta_iterable_opcodes_json_roundtrip_builtin_json(self):
        # A list diff that goes through difflib opcodes (reorder / duplicates)
        # serializes each Opcode NamedTuple. orjson emits it as a mapping, but
        # the stdlib json fallback (used when orjson is not installed) emits it
        # as a positional array; the deserializer must accept both. Forcing the
        # builtin json path exercises the array shape even where orjson is
        # installed, so a plain-install regression cannot hide behind orjson.
        t1 = ['a', 'b', 'c', 'd', 'b', 'e']
        t2 = ['b', 'c', 'x', 'b', 'e', 'f']
        diff = DeepDiff(t1, t2)

        def builtin_json_dumps(item):
            return json_dumps(item, force_use_builtin_json=True)

        dump = Delta(diff, bidirectional=True, serializer=builtin_json_dumps).dumps()
        delta = Delta(dump, bidirectional=True, deserializer=json_loads)

        assert t1 + delta == t2
        assert t2 - delta == t1

    def test_delta_flat_rows(self):
        t1 = {"key1": "value1"}
        t2 = {"field2": {"key2": "value2"}}
        diff = DeepDiff(t1, t2, verbose_level=2)
        delta = Delta(diff, bidirectional=True)
        assert t1 + delta == t2
        flat_rows = delta.to_flat_rows()
        # we need to set force=True because when we create flat rows, if a nested
        # dictionary with a single key is created, the path in the flat row will be
        # the path to the leaf node.
        delta2 = Delta(flat_rows_list=flat_rows, bidirectional=True, force=True)
        assert t1 + delta2 == t2

    def test_delta_bool(self):
        flat_rows_list = [FlatDeltaRow(path=['dollar_to_cent'], action='values_changed', value=False, old_value=True, type=bool, old_type=bool)]
        value = {'dollar_to_cent': False}
        delta = Delta(flat_rows_list=flat_rows_list, bidirectional=True, force=True)
        assert {'dollar_to_cent': True} == value - delta

    def test_detla_add_to_empty_iterable_and_flatten(self):
        t1 = {'models': [], 'version_id': 0}
        t2 = {'models': ['Super Duty F-250'], 'version_id': 1}
        t3 = {'models': ['Super Duty F-250', 'Focus'], 'version_id': 1}
        diff = DeepDiff(t1, t2, verbose_level=2)
        delta = Delta(diff, bidirectional=True)
        assert t1 + delta == t2
        flat_rows = delta.to_flat_rows()
        delta2 = Delta(flat_rows_list=flat_rows, bidirectional=True)  # , force=True
        assert t1 + delta2 == t2
        assert t2 - delta2 == t1

        diff3 = DeepDiff(t2, t3)
        delta3 = Delta(diff3, bidirectional=True)
        flat_dicts3 = delta3.to_flat_dicts()

        delta3_again = Delta(flat_dict_list=flat_dicts3, bidirectional=True)
        assert t2 + delta3_again == t3
        assert t3 - delta3_again == t2


    def test_flat_dict_and_deeply_nested_dict(self):
        beforeImage = [
            {
                "usage": "Mailing",
                "standardization": "YES",
                "primaryIndicator": True,
                "addressIdentifier": "Z8PDWBG42YC",
                "addressLines": ["871 PHILLIPS FERRY RD"],
            },
            {
                "usage": "Residence",
                "standardization": "YES",
                "primaryIndicator": False,
                "addressIdentifier": "Z8PDWBG42YC",
                "addressLines": ["871 PHILLIPS FERRY RD"],
            },
            {
                "usage": "Mailing",
                "standardization": None,
                "primaryIndicator": False,
                "addressIdentifier": "MHPP3BY0BYC",
                "addressLines": ["871 PHILLIPS FERRY RD", "APT RV92"],
            },
        ]
        allAfterImage = [
            {
                "usage": "Residence",
                "standardization": "NO",
                "primaryIndicator": False,
                "addressIdentifier": "Z8PDWBG42YC",
                "addressLines": ["871 PHILLIPS FERRY RD"],
            },
            {
                "usage": "Mailing",
                "standardization": None,
                "primaryIndicator": False,
                "addressIdentifier": "MHPP3BY0BYC",
                "addressLines": ["871 PHILLIPS FERRY RD", "APT RV92"],
            },
            {
                "usage": "Mailing",
                "standardization": "NO",
                "primaryIndicator": True,
                "addressIdentifier": "Z8PDWBG42YC",
                "addressLines": ["871 PHILLIPS FERRY RD"],
            },
        ]

        diff = DeepDiff(
            beforeImage,
            allAfterImage,
            ignore_order=True,
            report_repetition=True,
        )
        # reverse_diff = DeepDiff(
        #     allAfterImage,
        #     beforeImage,
        #     ignore_order=True,
        #     report_repetition=True,
        # )
        delta = Delta(
            diff, always_include_values=True, bidirectional=True
        )
        # reverse_delta = Delta(
        #     reverse_diff, always_include_values=True, bidirectional=True
        # )
        allAfterImageAgain = beforeImage + delta
        diff2 = DeepDiff(allAfterImage, allAfterImageAgain, ignore_order=True)
        assert not diff2

        # print("\ndelta.diff")
        # pprint(delta.diff)
        # print("\ndelta._get_reverse_diff()")
        # pprint(delta._get_reverse_diff())
        # print("\nreverse_delta.diff")
        # pprint(reverse_delta.diff)
        beforeImageAgain = allAfterImage - delta
        diff3 = DeepDiff(beforeImage, beforeImageAgain, ignore_order=True)
        assert not diff3

        # ------ now let's recreate the delta from flat dicts -------

        flat_dict_list = delta.to_flat_dicts()

        delta2 = Delta(
            flat_dict_list=flat_dict_list,
            always_include_values=True,
            bidirectional=True,
            raise_errors=False,
            force=True,
        )
        # print("\ndelta from flat dicts")
        # pprint(delta2.diff)
        allAfterImageAgain2 = beforeImage + delta2
        diff4 = DeepDiff(allAfterImage, allAfterImageAgain2, ignore_order=True)
        assert not diff4

        beforeImageAgain2 = allAfterImage - delta2
        diff4 = DeepDiff(beforeImage, beforeImageAgain2, ignore_order=True)
        assert not diff4

    def test_moved_and_changed_flat(self):
        """Items that both move (due to prepended inserts) and change values
        should produce t2 with no phantom entries after delta replay."""
        t1 = [{"id": "a", "val": 1}, {"id": "b", "val": 2},
            {"id": "c", "val": 3}]
        t2 = [
            {"id": "new1", "val": 10},  # inserted at [0]
            {"id": "new2", "val": 20},  # inserted at [1]
            {"id": "a", "val": 0.5},    # moved [0]→[2], val changed
            {"id": "b", "val": 1.0},    # moved [1]→[3], val changed
            {"id": "c", "val": 1.5},    # moved [2]→[4], val changed
        ]
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func,
                        threshold_to_diff_deeper=0)
        result = t1 + Delta(ddiff, force=True, raise_errors=True,
                            log_errors=False)
        assert [item for item in result if "id" not in item] == [], \
            "Phantom entries (dicts missing 'id') found in result"
        assert result == t2

    def test_moved_and_changed_nested(self):
        """Same bug in a nested structure: inner list items that both move and
        change values should produce no phantom entries after delta replay."""
        t1 = {"rows": [
            {"id": "r1", "items": [{"id": "a", "val": 1},
                                {"id": "b", "val": 2}]},
            ]}
        t2 = {"rows": [
            {"id": "r1", "items": [
                {"id": "new1", "val": 99},  # inserted at [0]
                {"id": "a", "val": 0.5},    # moved [0]→[1], val changed
                {"id": "b", "val": 1.0},    # moved [1]→[2], val changed
            ]},
        ]}
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func,
                        threshold_to_diff_deeper=0)
        result = t1 + Delta(ddiff, force=True, raise_errors=True,
                            log_errors=False)
        assert [item for item in result["rows"][0][
            "items"] if "id" not in item] == [], \
            "Phantom entries (dicts missing 'id') found in nested result"
        assert result == t2

    def test_appended_only_no_movement_sanity_check(self):
        """
        When new items are only appended (existing items keep their positions),
        stock Delta produces the correct result with no phantom entries.
        """
        t1 = [{"id": "a", "val": 1}, {"id": "b", "val": 2}]
        t2 = [
            {"id": "a", "val": 0.5},    # stays at [0], val changed
            {"id": "b", "val": 1.0},    # stays at [1], val changed
            {"id": "new1", "val": 10},  # appended
            {"id": "new2", "val": 20},  # appended
        ]
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func,
                        threshold_to_diff_deeper=0)
        result = t1 + Delta(ddiff, force=True, raise_errors=True,
                            log_errors=False)
        assert [item for item in result if "id" not in item] == []
        assert result == t2

    def test_moved_and_type_changed(self):
        """Items that both move and change type should apply correctly."""
        t1 = [{"id": "a", "val": "1"}, {"id": "b", "val": "2"}]
        t2 = [
            {"id": "new1", "val": 99},
            {"id": "a", "val": 1},      # moved [0]->[1], val str->int
            {"id": "b", "val": 2},      # moved [1]->[2], val str->int
        ]
        ddiff = DeepDiff(t1, t2, iterable_compare_func=self.compare_func,
                        threshold_to_diff_deeper=0)
        result = t1 + Delta(ddiff, force=True, raise_errors=True,
                            log_errors=False)
        assert [item for item in result if "id" not in item] == [], \
            "Phantom entries (dicts missing 'id') found in result"
        assert result == t2
