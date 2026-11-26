#!/usr/bin/env python
import pytest
import ipaddress
import logging
from typing import Union
from deepdiff import DeepSearch, grep
from datetime import datetime
logging.disable(logging.CRITICAL)

item = "somewhere"


class CustomClass:
    def __init__(self, a, b=None):
        self.a = a
        self.b = b

    def __str__(self):
        return "({}, {})".format(self.a, self.b)

    def __repr__(self):
        return self.__str__()


class ClassWithIp:
    """Class containing single data member to demonstrate deepdiff infinite iterate over IPv6Interface"""

    def __init__(self, addr: str):
        self.field: Union[
            ipaddress.IPv4Network,
            ipaddress.IPv6Network,
            ipaddress.IPv4Interface,
            ipaddress.IPv6Interface,
        ] = ipaddress.IPv6Network(addr)



class TestDeepSearch:
    """DeepSearch Tests."""

    def test_number_in_list(self):
        obj = ["a", 10, 20]
        item = 10
        result = {"matched_values": {'root[1]'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_number_in_list2(self):
        obj = ["a", "10", 10, 20]
        item = 10
        result = {"matched_values": {'root[2]'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_number_in_list3(self):
        obj = ["a", "10", 10, 20]
        item = "10"
        result = {"matched_values": {'root[1]'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_number_in_list_strict_false(self):
        obj = ["a", "10", 10, 20]
        item = "20"
        result = {"matched_values": {'root[3]'}}
        assert DeepSearch(obj, item, verbose_level=1, strict_checking=False) == result

    def test_string_in_root(self):
        obj = "long string somewhere"
        result = {"matched_values": {'root'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_string_in_root_verbose(self):
        obj = "long string somewhere"
        result = {"matched_values": {'root': "long string somewhere"}}
        assert DeepSearch(obj, item, verbose_level=2) == result

    def test_string_in_tuple(self):
        obj = ("long", "string", 0, "somewhere")
        result = {"matched_values": {'root[3]'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_string_in_list(self):
        obj = ["long", "string", 0, "somewhere"]
        result = {"matched_values": {'root[3]'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_string_in_list_verbose(self):
        obj = ["long", "string", 0, "somewhere"]
        result = {"matched_values": {'root[3]': "somewhere"}}
        assert DeepSearch(obj, item, verbose_level=2) == result

    def test_string_in_list_verbose2(self):
        obj = ["long", "string", 0, "somewhere great!"]
        result = {"matched_values": {'root[3]': "somewhere great!"}}
        assert DeepSearch(obj, item, verbose_level=2) == result

    def test_string_in_list_verbose3(self):
        obj = ["long somewhere", "string", 0, "somewhere great!"]
        result = {
            "matched_values": {
                'root[0]': 'long somewhere',
                'root[3]': "somewhere great!"
            }
        }
        assert DeepSearch(obj, item, verbose_level=2) == result

    def test_int_in_dictionary(self):
        obj = {"long": "somewhere", "num": 2, 0: 0, "somewhere": "around"}
        item = 2
        result = {'matched_values': {"root['num']"}}
        ds = DeepSearch(obj, item, verbose_level=1)
        assert ds == result

    def test_string_in_dictionary(self):
        obj = {"long": "somewhere", "string": 2, 0: 0, "somewhere": "around"}
        result = {
            'matched_paths': {"root['somewhere']"},
            'matched_values': {"root['long']"}
        }
        ds = DeepSearch(obj, item, verbose_level=1)
        assert ds == result

    def test_string_in_dictionary_case_insensitive(self):
        obj = {"long": "Somewhere over there!", "string": 2, 0: 0, "SOMEWHERE": "around"}
        result = {
            'matched_paths': {"root['SOMEWHERE']"},
            'matched_values': {"root['long']"}
        }
        ds = DeepSearch(obj, item, verbose_level=1, case_sensitive=False)
        assert ds == result

    def test_string_in_dictionary_key_case_insensitive_partial(self):
        obj = {"SOMEWHERE here": "around"}
        result = {
            'matched_paths': {"root['SOMEWHERE here']"}
        }
        ds = DeepSearch(obj, item, verbose_level=1, case_sensitive=False)
        assert ds == result

    def test_string_in_dictionary_verbose(self):
        obj = {"long": "somewhere", "string": 2, 0: 0, "somewhere": "around"}
        result = {
            'matched_paths': {
                "root['somewhere']": "around"
            },
            'matched_values': {
                "root['long']": "somewhere"
            }
        }
        ds = DeepSearch(obj, item, verbose_level=2)
        assert ds == result

    def test_string_in_dictionary_in_list_verbose(self):
        obj = [
            "something somewhere", {
                "long": "somewhere",
                "string": 2,
                0: 0,
                "somewhere": "around"
            }
        ]
        result = {
            'matched_paths': {
                "root[1]['somewhere']": "around"
            },
            'matched_values': {
                "root[1]['long']": "somewhere",
                "root[0]": "something somewhere"
            }
        }
        ds = DeepSearch(obj, item, verbose_level=2)
        assert ds == result

    def test_custom_object(self):
        obj = CustomClass('here, something', 'somewhere')
        result = {'matched_values': {'root.b'}}
        ds = DeepSearch(obj, item, verbose_level=1)
        assert ds == result

    def test_custom_object_verbose(self):
        obj = CustomClass('here, something', 'somewhere out there')
        result = {'matched_values': {'root.b': 'somewhere out there'}}
        ds = DeepSearch(obj, item, verbose_level=2)
        assert ds == result

    def test_custom_object_in_dictionary_verbose(self):
        obj = {1: CustomClass('here, something', 'somewhere out there')}
        result = {'matched_values': {'root[1].b': 'somewhere out there'}}
        ds = DeepSearch(obj, item, verbose_level=2)
        assert ds == result

    def test_named_tuples_verbose(self):
        from collections import namedtuple
        Point = namedtuple('Point', ['x', 'somewhere_good'])
        obj = Point(x="my keys are somewhere", somewhere_good=22)
        ds = DeepSearch(obj, item, verbose_level=2)
        result = {
            'matched_values': {
                'root.x': 'my keys are somewhere'
            },
            'matched_paths': {
                'root.somewhere_good': 22
            }
        }
        assert ds == result

    def test_string_in_set_verbose(self):
        obj = {"long", "string", 0, "somewhere"}
        # result = {"matched_values": {'root[3]': "somewhere"}}
        ds = DeepSearch(obj, item, verbose_level=2)
        assert list(ds["matched_values"].values())[0] == item

    def test_loop(self):
        class LoopTest:
            def __init__(self, a):
                self.loop = self
                self.a = a

        obj = LoopTest("somewhere around here.")

        ds = DeepSearch(obj, item, verbose_level=1)
        result = {'matched_values': {'root.a'}}
        assert ds == result

    def test_loop_in_lists(self):
        obj = [1, 2, 'somewhere']
        obj.append(obj)

        ds = DeepSearch(obj, item, verbose_level=1)
        result = {'matched_values': {'root[2]'}}
        assert ds == result

    def test_skip_path1(self):
        obj = {
            "for life": "vegan",
            "ingredients": ["no meat", "no eggs", "no dairy", "somewhere"]
        }
        ds = DeepSearch(obj, item, exclude_paths={"root['ingredients']"})
        assert ds == {}

    def test_custom_object_skip_path(self):
        obj = CustomClass('here, something', 'somewhere')
        result = {}
        ds = DeepSearch(obj, item, verbose_level=1, exclude_paths=['root.b'])
        assert ds == result

    def test_skip_list_path(self):
        obj = ['a', 'somewhere']
        ds = DeepSearch(obj, item, exclude_paths=['root[1]'])
        result = {}
        assert ds == result

    def test_skip_dictionary_path(self):
        obj = {1: {2: "somewhere"}}
        ds = DeepSearch(obj, item, exclude_paths=['root[1][2]'])
        result = {}
        assert ds == result

    @pytest.mark.parametrize('verbose_level', [1, 2])
    @pytest.mark.parametrize('exclude', [
        {'exclude_paths': ["root['container']['needle']"]},
        {'exclude_paths': ["root[*]['needle']"]},
        {'exclude_regex_paths': [r"\['needle'\]$"]},
    ])
    def test_excluded_dictionary_key_is_not_reported(self, verbose_level, exclude):
        obj = {'container': {'needle': {'nested': 'needle'}}, 'keep': 'needle'}
        expected = {'matched_values': (
            {"root['keep']": 'needle'} if verbose_level == 2 else {"root['keep']"}
        )}

        assert DeepSearch(obj, 'needle', verbose_level=verbose_level, **exclude) == expected

    @pytest.mark.parametrize('verbose_level', [1, 2])
    def test_excluded_attribute_name_is_not_reported(self, verbose_level):
        obj = CustomClass('a', 'a')
        expected = {'matched_values': (
            {'root.b': 'a'} if verbose_level == 2 else {'root.b'}
        )}

        assert DeepSearch(obj, 'a', exclude_paths=['root.a'], verbose_level=verbose_level) == expected

    @pytest.mark.parametrize('verbose_level', [1, 2])
    def test_excluded_dictionary_value_type_does_not_report_key(self, verbose_level):
        obj = {'needle': 1, 'needle_keep': 'needle'}
        matches = {"root['needle_keep']": 'needle'} if verbose_level == 2 else {"root['needle_keep']"}
        expected = {'matched_paths': matches, 'matched_values': matches}

        assert DeepSearch(obj, 'needle', exclude_types=[int], verbose_level=verbose_level) == expected

    def test_skip_type_str(self):
        obj = "long string somewhere"
        result = {}
        ds = DeepSearch(obj, item, verbose_level=1, exclude_types=[str])
        assert ds == result

    def test_skip_regexp(self):
        obj = [{'a': 1, 'b': "somewhere"}, {'c': 4, 'b': "somewhere"}]
        ds = DeepSearch(obj, item, exclude_regex_paths=[r"root\[\d+\]"])
        result = {}
        assert ds == result

    def test_skip_regexp2(self):
        obj = {'a': [1, 2, [3, [item]]]}
        ds = DeepSearch(obj, item, exclude_regex_paths=[r"\[\d+\]"])
        result = {}
        assert ds == result

    def test_unknown_parameters(self):
        with pytest.raises(ValueError):
            DeepSearch(1, 1, wrong_param=2)

    def test_bad_attribute(self):
        class Bad:
            __slots__ = ['x', 'y']

            def __getattr__(self, key):
                raise AttributeError("Bad item")

            def __str__(self):
                return "Bad Object"

        obj = Bad()

        ds = DeepSearch(obj, item, verbose_level=1)
        result = {'unprocessed': ['root']}
        assert ds == result
        ds = DeepSearch(obj, item, verbose_level=2)
        assert ds == result

    def test_case_insensitive_of_str_in_list(self):
        obj = ["a", "bb", "BBC", "aBbB"]
        item = "BB"
        result = {"matched_values": {'root[1]', 'root[2]', 'root[3]'}}
        assert DeepSearch(obj, item, verbose_level=1, case_sensitive=False) == result

    def test_case_sensitive_of_str_in_list(self):
        obj = ["a", "bb", "BBC", "aBbB"]
        item = "BB"
        result = {"matched_values": {'root[2]'}}
        assert DeepSearch(obj, item, verbose_level=1, case_sensitive=True) == result

    def test_case_sensitive_of_str_in_one_liner(self):
        obj = "Hello, what's up?"
        item = "WHAT"
        result = {}
        assert DeepSearch(obj, item, verbose_level=1, case_sensitive=True) == result

    def test_case_insensitive_of_str_in_one_liner(self):
        obj = "Hello, what's up?"
        item = "WHAT"
        result = {'matched_values': {'root'}}
        assert DeepSearch(obj, item, verbose_level=1, case_sensitive=False) == result

    def test_none(self):
        obj = item = None
        result = {'matched_values': {'root'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_complex_obj(self):
        obj = datetime(2017, 5, 4, 1, 1, 1)
        item = datetime(2017, 5, 4, 1, 1, 1)
        result = {'matched_values': {'root'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_keep_searching_after_obj_match(self):

        class AlwaysEqual:

            def __init__(self, recurse=True):
                if recurse:
                    self.some_attr = AlwaysEqual(recurse=False)

            def __eq__(self, other):
                return True

        obj = AlwaysEqual()
        item = AlwaysEqual()
        result = {'matched_values': {'root', 'root.some_attr'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_search_inherited_attributes(self):
        class Parent:
            a = 1

        class Child(Parent):
            b = 2

        obj = Child()
        item = 1
        result = {'matched_values': {'root.a'}}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_dont_use_regex_by_default(self):
        obj = "long string somewhere"
        item = "some.*"
        result = {}
        assert DeepSearch(obj, item, verbose_level=1) == result

    def test_regex_in_string(self):
        obj = "long string somewhere"
        item = "some.*"
        result = {"matched_values": {"root"}}
        assert DeepSearch(obj, item, verbose_level=1, use_regexp=True) == result

    def test_regex_does_not_match_the_regex_string_itself(self):
        obj = ["We like python", "but not (?:p|t)ython"]
        item = "(?:p|t)ython"
        result = {'matched_values': ['root[0]']}
        assert DeepSearch(obj, item, verbose_level=1, use_regexp=True) == result

    def test_regex_in_string_in_tuple(self):
        obj = ("long", "string", 0, "somewhere")
        item = "some.*"
        result = {"matched_values": {"root[3]"}}
        assert DeepSearch(obj, item, verbose_level=1, use_regexp=True) == result

    def test_regex_in_string_in_list(self):
        obj = ["long", "string", 0, "somewhere"]
        item = "some.*"
        result = {"matched_values": {"root[3]"}}
        assert DeepSearch(obj, item, verbose_level=1, use_regexp=True) == result

    def test_regex_in_string_in_dictionary(self):
        obj = {"long": "somewhere", "string": 2, 0: 0, "somewhere": "around"}
        result = {
            "matched_paths": {"root['somewhere']"},
            "matched_values": {"root['long']"},
        }
        item = "some.*"
        ds = DeepSearch(obj, item, verbose_level=1, use_regexp=True)
        assert ds == result

    def test_regex_in_string_in_dictionary_in_list_verbose(self):
        obj = [
            "something somewhere",
            {"long": "somewhere", "string": 2, 0: 0, "somewhere": "around"},
        ]
        result = {
            "matched_paths": {"root[1]['somewhere']": "around"},
            "matched_values": {
                "root[1]['long']": "somewhere",
                "root[0]": "something somewhere",
            },
        }
        item = "some.*"
        ds = DeepSearch(obj, item, verbose_level=2, use_regexp=True)
        assert ds == result

    def test_regex_in_custom_object(self):
        obj = CustomClass("here, something", "somewhere")
        result = {"matched_values": {"root.b"}}
        item = "somew.*"
        ds = DeepSearch(obj, item, verbose_level=1, use_regexp=True)
        assert ds == result

    def test_regex_in_custom_object_in_dictionary_verbose(self):
        obj = {1: CustomClass("here, something", "somewhere out there")}
        result = {"matched_values": {"root[1].b": "somewhere out there"}}
        item = "somew.*"
        ds = DeepSearch(obj, item, verbose_level=2, use_regexp=True)
        assert ds == result

    def test_regex_in_named_tuples_verbose(self):
        from collections import namedtuple

        Point = namedtuple("Point", ["x", "somewhere_good"])
        obj = Point(x="my keys are somewhere", somewhere_good=22)
        item = "some.*"
        ds = DeepSearch(obj, item, verbose_level=2, use_regexp=True)
        result = {
            "matched_values": {"root.x": "my keys are somewhere"},
            "matched_paths": {"root.somewhere_good": 22},
        }
        assert ds == result

    def test_regex_in_string_in_set_verbose(self):
        obj = {"long", "string", 0, "somewhere"}
        item = "some.*"
        ds = DeepSearch(obj, item, verbose_level=2, use_regexp=True)
        assert list(ds["matched_values"].values())[0] == "somewhere"

    def test_regex_in_int_in_dictionary_with_strict_checking(self):
        obj = {"long": "somewhere", "num": 232, 0: 0, "somewhere": "around"}
        item = "2.*"
        result = {}
        ds = DeepSearch(obj, item, verbose_level=1, use_regexp=True)
        assert ds == result

    def test_regex_in_int_in_dictionary(self):
        obj = {"long": "somewhere", "num": 232, 0: 0, "somewhere": "around"}
        item = "2.*"
        result = {"matched_values": {"root['num']"}}
        ds = DeepSearch(obj, item, verbose_level=1, use_regexp=True, strict_checking=False)
        assert ds == result

    def test_regex_in_int_in_dictionary_returns_partial_match(self):
        obj = {"long": "somewhere", "num": 1123456, 0: 0, "somewhere": "around"}
        item = "1234"
        result = {"matched_values": {"root['num']"}}
        ds = DeepSearch(obj, item, verbose_level=1, use_regexp=True, strict_checking=False)
        assert ds == result

    def test_int_cant_become_regex(self):
        obj = {"long": "somewhere", "num": "1123456", 0: 0, "somewhere": "around"}
        item = CustomClass(a=10)
        with pytest.raises(TypeError) as exp:
            DeepSearch(obj, item, verbose_level=1, use_regexp=True, strict_checking=False)
        assert str(exp.value).startswith("The passed item of (10, None) is not usable for regex")

    def test_searching_for_int_in_dictionary_when_strict_false(self):
        obj = {"long": "somewhere", "num": "1234", 0: 0, "somewhere": "around"}
        item = 1234
        result = {"matched_values": {"root['num']"}}
        ds = DeepSearch(obj, item, verbose_level=1, strict_checking=False)
        assert ds == result


class TestGrep:

    def test_grep_dict(self):
        obj = {
            "for life": "vegan",
            "ingredients": ["no meat", "no eggs", "no dairy", "somewhere"]
        }
        ds = obj | grep(item)
        assert ds == {'matched_values': {"root['ingredients'][3]"}}

    def test_grep_dict_in_dict(self):
        obj = {
            "x": {
                "y": [
                    "aaaaaa\u0142 bbbbb"
                ]
            },
            "z": "z",
        }
        item = {"z": "z"}
        result = obj | grep(item)
        assert {} == result

    def test_grep_with_non_utf8_chars(self):
        obj = "aaaaaa\u0142 bbbbb"
        item = {"z": "z"}
        result = obj | grep(item)
        assert {} == result

    def test_grep_regex_in_string_in_tuple(self):
        obj = ("long", "string", 0, "somewhere")
        item = "some.*"
        result = {"matched_values": {"root[3]"}}
        assert obj | grep(item, verbose_level=1, use_regexp=True) == result

    def test_search_ip_addresses(self):
        obj1 = [ClassWithIp("2002:db8::/30"),  ClassWithIp("2002:db8::/32")]
        assert obj1 | grep("2002:db8::/32") == {'matched_values': ['root[1].field']}
