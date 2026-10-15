#!/usr/bin/env python
import re
import pytest
import pytz
import uuid6
import logging
import datetime
import ipaddress
import pickle
from copy import deepcopy
from decimal import Decimal
from typing import Union
from pathlib import Path
from collections import namedtuple
from functools import partial
from enum import Enum
from deepdiff import DeepDiff, DeepHash
from deepdiff.deephash import (
    prepare_string_for_hashing, unprocessed,
    UNPROCESSED_KEY, BoolObj, HASH_LOOKUP_ERR_MSG, combine_hashes_lists)
from deepdiff.helper import pypy3, get_id, number_to_string, np, py_major_version, py_minor_version
from deepdiff.serialization import pickle_dump, pickle_load
from tests import CustomClass2

logging.disable(logging.CRITICAL)


class ClassC:
    class_attr = 0

    def __init__(self, a, b=None):
        self.a = a
        self.b = b

    def __str__(self):
        return "({}, {})".format(self.a, self.b)

    __repr__ = __str__


# Only the prep part of DeepHash. We don't need to test the actual hash function.
DeepHashPrep = partial(DeepHash, apply_hash=False)


def prep_str(obj, ignore_string_type_changes=True):
    return obj if ignore_string_type_changes else 'str:{}'.format(obj)


class TestDeepHash:

    def test_dictionary(self):

        obj = {1: 1}
        result = DeepHash(obj)
        assert set(result.keys()) == {1, get_id(obj)}

    def test_get_hash_by_obj_is_the_same_as_by_obj_get_id(self):
        a = "a"
        obj = {1: a}
        result = DeepHash(obj)
        assert result[a]

    def test_deephash_repr(self):
        obj = "a"
        result = DeepHash(obj)
        assert '{"a":"980410da9522db17c3ab8743541f192a5ab27772a6154dbc7795ee909e653a5c"}' == repr(result)

    def test_deephash_values(self):
        obj = "a"
        result = list(DeepHash(obj).values())
        assert ['980410da9522db17c3ab8743541f192a5ab27772a6154dbc7795ee909e653a5c'] == result

    def test_deephash_keys(self):
        obj = "a"
        result = list(DeepHash(obj).keys())
        assert ["a"] == result

    def test_deephash_items(self):
        obj = "a"
        result = list(DeepHash(obj).items())
        assert [('a', '980410da9522db17c3ab8743541f192a5ab27772a6154dbc7795ee909e653a5c')] == result

    def test_get_hash_by_obj_when_does_not_exist(self):
        a = "a"
        obj = {1: a}
        result = DeepHash(obj)
        with pytest.raises(KeyError):
            result[2]

    def test_datetime(self):
        now = datetime.datetime.now()
        a = b = now
        a_hash = DeepHash(a)
        b_hash = DeepHash(b)
        assert a_hash[a] == b_hash[b]

    def test_date1(self):
        date = datetime.date(2024, 2, 1)
        date_hash = DeepHash(date)
        assert 'd90e95901f85ca09b2536d3cb81a49747c3a4fb14906d6fa0d492713ebb4309c' == date_hash[date]

    def test_date2(self):
        item = {'due_date': datetime.date(2024, 2, 1)}

        result = DeepHash(
            item,
            significant_digits=12,
            number_format_notation='f',
            ignore_numeric_type_changes=True,
            ignore_type_in_groups=[{int, float, complex, datetime.datetime, datetime.date, datetime.timedelta, datetime.time}],
            ignore_type_subclasses=False,
            ignore_encoding_errors=False,
            ignore_repetition=True,
            number_to_string_func=number_to_string,
        )
        assert 'e0d7ec984a0eda44ceb1e3c595f9b805530d715c779483e63a72c67cbce68615' == result[item]

    def test_datetime_truncate(self):
        a = datetime.datetime(2020, 5, 17, 22, 15, 34, 913070)
        b = datetime.datetime(2020, 5, 17, 22, 15, 39, 296583)
        c = datetime.datetime(2020, 5, 17, 22, 15, 34, 500000)

        a_hash = DeepHash(a, truncate_datetime='minute')
        b_hash = DeepHash(b, truncate_datetime='minute')
        assert a_hash[a] == b_hash[b]

        a_hash = DeepHash(a, truncate_datetime='second')
        c_hash = DeepHash(c, truncate_datetime='second')
        assert a_hash[a] == c_hash[c]

    def test_get_reserved_keyword(self):
        hashes = {UNPROCESSED_KEY: 'full item', 'key1': ('item', 'count')}
        result = DeepHash._getitem(hashes, obj='key1')
        assert 'item' == result
        # For reserved keys, it should just grab the object instead of grabbing an item in the tuple object.
        result = DeepHash._getitem(hashes, obj=UNPROCESSED_KEY)
        assert 'full item' == result

    def test_get_key(self):
        hashes = {'key1': ('item', 'count')}
        result = DeepHash.get_key(hashes, key='key2', default='banana')
        assert 'banana' == result

    def test_list_of_sets(self):
        a = {1}
        b = {2}
        obj = [a, b]
        result = DeepHash(obj)
        expected_result = {1, 2, get_id(a), get_id(b), get_id(obj)}
        assert set(result.keys()) == expected_result

    def test_bad_attribute(self):
        class Bad:
            __slots__ = ['x', 'y']

            def __getattr__(self, key):
                raise AttributeError("Bad item")

            def __str__(self):
                return "Bad Object"

            def __repr__(self):
                return "<Bad obj id {}>".format(id(self))

        t1 = Bad()

        result = DeepHash(t1)
        expected_result = {t1: unprocessed, UNPROCESSED_KEY: [t1]}
        assert expected_result == result

    def test_built_in_hash_not_sensitive_to_bytecode_vs_unicode(self):
        a = 'hello'
        b = b'hello'
        a_hash = DeepHash(a, ignore_string_type_changes=True)[a]
        b_hash = DeepHash(b, ignore_string_type_changes=True)[b]
        assert a_hash == b_hash

    def test_sha1_hash_not_sensitive_to_bytecode_vs_unicode(self):
        a = 'hello'
        b = b'hello'
        a_hash = DeepHash(a, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)[a]
        b_hash = DeepHash(b, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)[b]
        assert a_hash == b_hash

    def test_path(self):
        a = Path('testdir')
        b = Path('testdir2')
        a_hash = DeepHash(a)[a]
        b_hash = DeepHash(b)[b]
        assert a_hash != b_hash

    def test_re(self):
        import re
        a = re.compile("asdf.?")
        a_hash = DeepHash(a)[a]
        assert not( a_hash is unprocessed)

    # https://github.com/seperman/deepdiff/issues/494
    def test_numpy_bool(self):
        a = {'b': np.array([True], dtype='bool')}
        a_hash = DeepHash(a)[a]
        assert not( a_hash is unprocessed)

    def test_numpy_datetime64(self):
        now_dt = datetime.datetime.now()
        now = np.datetime64(now_dt)
        later = np.datetime64(now_dt + datetime.timedelta(seconds=10))
        a = b = now
        a_hash = DeepHash(a)
        b_hash = DeepHash(b)
        assert a_hash[a] == b_hash[b]

        later_hash = DeepHash(later)
        assert a_hash[a] != later_hash[later]

    def test_uuid6_hash_positive(self):
        """Positive test case: Same UUID objects should produce the same hash."""
        uuid_obj = uuid6.uuid7()
        hash1 = DeepHash(uuid_obj)
        hash2 = DeepHash(uuid_obj)
        assert hash1[uuid_obj] == hash2[uuid_obj]

        import uuid
        regular_uuid = uuid.uuid4()
        hash_regular = DeepHash(regular_uuid)
        assert hash_regular[regular_uuid] is not unprocessed

    def test_uuid6_deepdiff_negative(self):
        """Negative test case: DeepDiff should detect differences between sets containing different UUID objects."""
        dummy_id_1 = uuid6.uuid7()
        dummy_id_2 = uuid6.uuid7()
        set1 = {dummy_id_1}
        set2 = {dummy_id_1, dummy_id_2}
        diff = DeepDiff(set1, set2)
        assert diff != {}
        assert 'set_item_added' in diff
        assert str(dummy_id_2) in str(diff)

    def test_slots_with_uninitialized_attributes(self):
        """Test that DeepHash handles classes with __slots__ where not all slots are initialized."""
        class PartiallyInitialized:
            __slots__ = ['x', 'y', 'z']

            def __init__(self, x):
                self.x = x

        obj = PartiallyInitialized(10)
        result = DeepHash(obj)
        # Should not raise AttributeError iternally, and should successfully hash the object
        assert result[obj] is not unprocessed

    def test_slots_fully_initialized(self):
        """Test that DeepHash correctly hashes classes with __slots__ where all slots are initialized."""
        class FullyInitialized:
            __slots__ = ['x', 'y']

            def __init__(self, x, y):
                self.x = x
                self.y = y

        obj1 = FullyInitialized(1, 2)
        obj2 = FullyInitialized(1, 2)
        obj3 = FullyInitialized(3, 4)

        hash1 = DeepHash(obj1)
        hash2 = DeepHash(obj2)
        hash3 = DeepHash(obj3)

        # Same values should produce same hash
        assert hash1[obj1] == hash2[obj2]
        # Different values should produce different hash
        assert hash1[obj1] != hash3[obj3]

    def test_slots_with_no_initialized_attributes(self):
        """Test that DeepHash handles classes with __slots__ where no slots are initialized."""
        class EmptySlots:
            __slots__ = ['a', 'b', 'c']

            def __init__(self):
                pass

        obj = EmptySlots()
        result = DeepHash(obj)
        assert result[obj] is not unprocessed

    def test_slots_inheritance(self):
        """Test that DeepHash handles inherited __slots__ correctly."""
        class Base:
            __slots__ = ['x']

            def __init__(self, x):
                self.x = x

        class Derived(Base):
            __slots__ = ['y', 'z']

            def __init__(self, x, y):
                super().__init__(x)
                self.y = y

        obj = Derived(1, 2)
        result = DeepHash(obj)
        # Should still not raise AttributeError internally for uninitialized 'z'
        assert result[obj] is not unprocessed

    def test_slots_deepdiff_comparison(self):
        """Test that DeepDiff also works correctly with __slots__ classes (incl inherited and uninitialized attributes)."""
        class Base:
            __slots__ = ['x']

            def __init__(self, x):
                self.x = x

        class Derived(Base):
            __slots__ = ['y', 'z']

            def __init__(self, x, y):
                super().__init__(x)
                self.y = y

        obj1 = Derived(1, 2)
        obj2 = Derived(1, 2)
        obj3 = Derived(3, 4)

        # Same initialized values should show no difference
        diff1 = DeepDiff(obj1, obj2)
        assert diff1 == {}

        # Different values should show difference
        diff2 = DeepDiff(obj1, obj3)
        assert diff2 == {
            'values_changed': {
                'root.x': {'new_value': 3, 'old_value': 1},
                'root.y': {'new_value': 4, 'old_value': 2},
            }
        }

class TestDeepHashPrep:
    """DeepHashPrep Tests covering object serialization."""

    def test_prep_bool_vs_num1(self):
        assert {BoolObj.TRUE: 'bool:true'} == DeepHashPrep(True)
        assert {1: 'int:1'} == DeepHashPrep(1)

    def test_prep_bool_vs_num2(self):
        item1 = {
            "Value One": True,
            "Value Two": 1,
        }
        item2 = {
            "Value Two": 1,
            "Value One": True,
        }
        assert DeepHashPrep(item1)[item1] == DeepHashPrep(item2)[item2]

    def test_prep_str1(self):
        obj = "a"
        obj2 = b"a"
        expected_result = {obj: prep_str(obj)}
        result = DeepHashPrep(obj, ignore_string_type_changes=True)
        assert expected_result == result
        assert result[obj] == 'a'
        expected_result2 = {obj: prep_str(obj, ignore_string_type_changes=False)}
        result = DeepHashPrep(obj, ignore_string_type_changes=False)
        assert expected_result2 == result
        assert result[obj] == 'str:a'

        expected_result3 = {obj2: prep_str(obj2, ignore_string_type_changes=True)}
        result = DeepHashPrep(obj2, ignore_string_type_changes=True)
        assert expected_result3 != result
        assert result[obj2] == 'a'
        result = DeepHashPrep(obj2, ignore_string_type_changes=False)
        assert {b'a': 'bytes:a'} == result
        assert result[obj2] == 'bytes:a'

    def test_prep_number1(self):
        obj_int = 1
        obj_float = 1.0
        # By default, type is included in the prep
        result_int = DeepHashPrep(obj_int)
        result_float = DeepHashPrep(obj_float)
        assert result_int[obj_int] == 'int:1'
        assert result_float[obj_float] == 'float:1.0'
        # When ignoring numeric type changes, both get the same "number:" prefix
        result_int2 = DeepHashPrep(obj_int, ignore_numeric_type_changes=True)
        result_float2 = DeepHashPrep(obj_float, ignore_numeric_type_changes=True)
        assert result_int2[obj_int] == result_float2[obj_float]
        assert result_int2[obj_int] == 'number:1.000000000000'

    def test_dictionary_key_type_change(self):
        obj1 = {"b": 10}
        obj2 = {b"b": 10}

        result1 = DeepHashPrep(obj1, ignore_string_type_changes=True)
        result2 = DeepHashPrep(obj2, ignore_string_type_changes=True)
        assert result1[obj1] == result2[obj2]
        assert result1["b"] == result2[b"b"]

    def test_number_type_change(self):
        obj1 = 10
        obj2 = 10.0

        result1 = DeepHashPrep(obj1)
        result2 = DeepHashPrep(obj2)
        assert result1[obj1] != result2[obj2]

        result1 = DeepHashPrep(obj1, ignore_numeric_type_changes=True)
        result2 = DeepHashPrep(obj2, ignore_numeric_type_changes=True)
        assert result1[obj1] == result2[obj2]

    @pytest.mark.parametrize('number', [1, 1.0, 1j, Decimal('1'), np.int64(1)])
    @pytest.mark.parametrize('reverse', [False, True])
    def test_numeric_cache_key_does_not_collide_with_tuple(self, number, reverse):
        item = (type(number), number)
        objects = [item, number] if reverse else [number, item]
        result = DeepHash(objects)
        number_hash = DeepHash(number)[number]
        tuple_hash = DeepHash(item)[item]

        assert result[number] == number_hash
        assert result[item] == tuple_hash
        assert result[number] != result[item]
        assert result.get(item) == tuple_hash
        assert DeepHash.get_key(result.hashes, number) == number_hash
        assert DeepHash.get_key(result.hashes, item) == tuple_hash
        assert number in result
        assert item in result
        assert item in set(result.keys())
        assert dict(result.items())[item] == tuple_hash
        assert result._get_objects_to_hashes_dict()[item] == tuple_hash

    def test_numeric_cache_does_not_contain_unhashed_tuple(self):
        result = DeepHash(1)
        item = (int, 1)

        assert item not in result
        assert result.get(item) is None
        with pytest.raises(KeyError):
            result[item]

    @pytest.mark.parametrize('copy_cache', [
        deepcopy,
        pytest.param(lambda value: pickle.loads(pickle.dumps(value)), id='pickle'),
        pytest.param(lambda value: pickle_load(pickle_dump(value)), id='restricted_pickle'),
    ])
    def test_numeric_cache_key_survives_copy(self, copy_cache):
        original = DeepHash([1, 1.0])
        hashes = copy_cache(original.hashes)

        for item in [1, 1.0]:
            assert DeepHash.get_key(hashes, item) == original[item]
        result = DeepHash((int, 1), hashes=hashes)
        assert result[1] != result[(int, 1)]
        assert result[1] != result[1.0]

    def test_prep_str_fail_if_deephash_leaks_results(self):
        """
        This test fails if DeepHash is getting a mutable copy of hashes
        which means each init of the DeepHash will have hashes from
        the previous init.
        """
        obj1 = "a"
        expected_result = {obj1: prep_str(obj1)}
        result = DeepHashPrep(obj1, ignore_string_type_changes=True)
        assert expected_result == result
        obj2 = "b"
        result = DeepHashPrep(obj2, ignore_string_type_changes=True)
        assert obj1 not in result

    def test_dict_in_dict(self):
        obj2 = {2: 3}
        obj = {'a': obj2}
        result = DeepHashPrep(obj, ignore_string_type_changes=True)
        assert 'a' in result
        assert obj2 in result

    def do_list_or_tuple(self, func, func_str):
        string1 = "a"
        obj = func([string1, 10, 20])
        if func is list:
            obj_id = get_id(obj)
        else:
            obj_id = obj
        string1_prepped = prep_str(string1)
        expected_result = {
            10: 'int:10',
            20: 'int:20',
            string1: string1_prepped,
            obj_id: '{}:{},int:10,int:20'.format(func_str, string1_prepped),
        }
        result = DeepHashPrep(obj, ignore_string_type_changes=True)
        assert expected_result == result

    def test_list_and_tuple(self):
        for func, func_str in ((list, 'list'), (tuple, 'tuple')):
            self.do_list_or_tuple(func, func_str)

    def test_named_tuples(self):
        # checking if pypy3 is running the test
        # in that case due to a difference of string interning implementation
        # the id of x inside the named tuple changes.
        x = "x"
        x_prep = prep_str(x)
        Point = namedtuple('Point', [x])
        obj = Point(x=11)
        result = DeepHashPrep(obj, ignore_string_type_changes=True)
        if pypy3:
            assert result[obj] == "ntPoint:{%s:int:11}" % x
        else:
            expected_result = {
                x: x_prep,
                obj: "ntPoint:{%s:int:11}" % x,
                11: 'int:11',
            }
            assert expected_result == result

    def test_hash_enum(self):
        class MyEnum(Enum):
            A = 1
            B = 2

        if (py_major_version, py_minor_version) >= (3, 11):
            assert DeepHashPrep(MyEnum.A)[MyEnum.A] == r'objMyEnum:{str:_name_:str:A;str:_sort_order_:int:0;str:_value_:int:1}'
        else:
            assert DeepHashPrep(MyEnum.A)[MyEnum.A] == r'objMyEnum:{str:_name_:str:A;str:_value_:int:1}'
        assert DeepHashPrep(MyEnum.A) == DeepHashPrep(MyEnum(1))
        assert DeepHashPrep(MyEnum.A) != DeepHashPrep(MyEnum.A.name)
        assert DeepHashPrep(MyEnum.A) != DeepHashPrep(MyEnum.A.value)
        assert DeepHashPrep(MyEnum.A) != DeepHashPrep(MyEnum.B)

        assert DeepHashPrep(MyEnum.A, use_enum_value=True)[MyEnum.A] == 'int:1'

    def test_dict_hash(self):
        string1 = "a"
        string1_prepped = prep_str(string1)
        key1 = "key1"
        key1_prepped = prep_str(key1)
        obj = {key1: string1, 1: 10, 2: 20}
        expected_result = {
            1: 'int:1',
            10: 'int:10',
            2: 'int:2',
            20: 'int:20',
            key1: key1_prepped,
            string1: string1_prepped,
            get_id(obj): 'dict:{{int:1:int:10;int:2:int:20;{}:{}}}'.format(key1, string1)
        }
        result = DeepHashPrep(obj, ignore_string_type_changes=True)
        assert expected_result == result

    def test_dict_in_list(self):
        string1 = "a"
        key1 = "key1"
        dict1 = {key1: string1, 1: 10, 2: 20}
        obj = [0, dict1]
        expected_result = {
            0: 'int:0',
            1: 'int:1',
            10: 'int:10',
            2: 'int:2',
            20: 'int:20',
            key1: key1,
            string1: string1,
            get_id(dict1): 'dict:{int:1:int:10;int:2:int:20;%s:%s}' %
            (key1, string1),
            get_id(obj):
            'list:dict:{int:1:int:10;int:2:int:20;%s:%s},int:0' %
            (key1, string1)
        }
        result = DeepHashPrep(obj, ignore_string_type_changes=True)
        assert expected_result == result

    def test_nested_lists_same_hash(self):
        t1 = [1, 2, [3, 4]]
        t2 = [[4, 3], 2, 1]
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)

        assert t1_hash[get_id(t1)] == t2_hash[get_id(t2)]

    def test_nested_lists_same_hash2(self):
        t1 = [1, 2, [3, [4, 5]]]
        t2 = [[[5, 4], 3], 2, 1]
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)

        assert t1_hash[get_id(t1)] == t2_hash[get_id(t2)]

    def test_nested_lists_same_hash3(self):
        t1 = [{1: [2, 3], 4: [5, [6, 7]]}]
        t2 = [{4: [[7, 6], 5], 1: [3, 2]}]
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)

        assert t1_hash[get_id(t1)] == t2_hash[get_id(t2)]

    def test_nested_lists_in_dictionary_same_hash(self):
        t1 = [{"c": 4}, {"c": 3}]
        t2 = [{"c": 3}, {"c": 4}]
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)

        assert t1_hash[get_id(t1)] == t2_hash[get_id(t2)]

    def test_same_sets_same_hash(self):
        t1 = {1, 3, 2}
        t2 = {2, 3, 1}
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)

        assert t1_hash[get_id(t1)] == t2_hash[get_id(t2)]
        
    @pytest.mark.parametrize("list1, list2, ignore_iterable_order, is_equal", [
        ([1, 2], [2, 1], False, False),
        ([1, 2], [2, 1], True, True),
        ([1, 2, 3], [1, 3, 2], False, False),
        ([1, [1, 2, 3]], [1, [3, 2, 1]], False, False),
        ([1, [1, 2, 3]], [1, [3, 2, 1]], True, True),
        ((1, 2), (2, 1), False, False),
        ((1, 2), (2, 1), True, True),
    ])
    def test_ignore_iterable_order(self, list1, list2, ignore_iterable_order, is_equal):
        list1_hash = DeepHash(list1, ignore_iterable_order=ignore_iterable_order)
        list2_hash = DeepHash(list2, ignore_iterable_order=ignore_iterable_order)
        
        assert is_equal == (list1_hash[list1] == list2_hash[list2])

    @pytest.mark.parametrize("t1, t2, significant_digits, number_format_notation, result", [
        ({0.012, 0.98}, {0.013, 0.99}, 1, "f", 'set:float:0.0,float:1.0'),
        (100000, 100021, 3, "e", 'int:1.000e+5'),
    ])
    def test_similar_significant_hash(self, t1, t2, significant_digits,
                                      number_format_notation, result):
        t1_hash = DeepHashPrep(t1, significant_digits=significant_digits,
                               number_format_notation=number_format_notation)
        t2_hash = DeepHashPrep(t2, significant_digits=significant_digits,
                               number_format_notation=number_format_notation)

        if result:
            assert result == t1_hash[t1] == t2_hash[t2]
        else:
            assert t1_hash[t1] != t2_hash[t2]

    def test_number_to_string_func(self):
        def custom_number_to_string(number, *args, **kwargs):
            number = 100 if number < 100 else number
            return number_to_string(number, *args, **kwargs)

        t1 = [10, 12, 100000]
        t2 = [50, 63, 100021]
        t1_hash = DeepHashPrep(t1, significant_digits=4, number_format_notation="e",
                               number_to_string_func=custom_number_to_string)
        t2_hash = DeepHashPrep(t2, significant_digits=4, number_format_notation="e",
                               number_to_string_func=custom_number_to_string)

        assert t1_hash[10] == t2_hash[50] == t1_hash[12] == t2_hash[63] != t1_hash[100000]

    def test_same_sets_in_lists_same_hash(self):
        t1 = ["a", {1, 3, 2}]
        t2 = [{2, 3, 1}, "a"]
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)

        assert t1_hash[get_id(t1)] == t2_hash[get_id(t2)]

    def test_unknown_parameters(self):
        with pytest.raises(ValueError):
            DeepHashPrep(1, wrong_param=2)

    def test_bad_attribute_prep(self):
        class Bad:
            __slots__ = ['x', 'y']

            def __getattr__(self, key):
                raise AttributeError("Bad item")

            def __str__(self):
                return "Bad Object"

        t1 = Bad()

        result = DeepHashPrep(t1)
        expected_result = {t1: unprocessed, UNPROCESSED_KEY: [t1]}
        assert expected_result == result

    class Burrito:
        bread = 'flour'

        def __init__(self):
            self.spicy = True

    class Taco:
        bread = 'flour'

        def __init__(self):
            self.spicy = True

    class ClassA:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class ClassB:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class ClassC(ClassB):
        pass

    obj_a = ClassA(1, 2)
    obj_b = ClassB(1, 2)
    obj_c = ClassC(1, 2)

    burrito = Burrito()
    taco = Taco()

    @pytest.mark.parametrize("test_num, t1, t2, ignore_type_in_groups, ignore_type_subclasses, is_qual", [
        (1, taco, burrito, [], False, False),
        (2, taco, burrito, [(Taco, Burrito)], False, True),
        (3, [taco], [burrito], [(Taco, Burrito)], False, True),
        (4, [obj_a], [obj_c], [(ClassA, ClassB)], False, True),
        (5, [obj_a], [obj_c], [(ClassA, ClassB)], True, False),
        (6, [obj_b], [obj_c], [(ClassB, )], True, False),
    ])
    def test_objects_with_same_content(self, test_num, t1, t2, ignore_type_in_groups, ignore_type_subclasses, is_qual):
        t1_result = DeepHashPrep(t1, ignore_type_in_groups=ignore_type_in_groups,
                                 ignore_type_subclasses=ignore_type_subclasses)
        t2_result = DeepHashPrep(t2, ignore_type_in_groups=ignore_type_in_groups,
                                 ignore_type_subclasses=ignore_type_subclasses)
        assert is_qual == (t1_result[t1] == t2_result[t2]), f"test_objects_with_same_content #{test_num} failed."

    def test_custom_object(self):
        cc_a = CustomClass2(prop1=["a"], prop2=["b"])
        t1 = [cc_a, CustomClass2(prop1=["c"], prop2=["d"])]
        t1_result = DeepHashPrep(t1)
        expected = 'list:objCustomClass2:{str:prop1:list:str:a;str:prop2:list:str:b},objCustomClass2:{str:prop1:list:str:c;str:prop2:list:str:d}'  # NOQA
        assert expected == t1_result[t1]

    def test_repetition_by_default_does_not_effect(self):
        list1 = [3, 4]
        list1_id = get_id(list1)
        a = [1, 2, list1]
        a_id = get_id(a)

        list2 = [4, 3, 3]
        list2_id = get_id(list2)
        b = [list2, 2, 1]
        b_id = get_id(b)

        hash_a = DeepHashPrep(a)
        hash_b = DeepHashPrep(b)

        assert hash_a[list1_id] == hash_b[list2_id]
        assert hash_a[a_id] == hash_b[b_id]

    def test_setting_repetition_off_unequal_hash(self):
        list1 = [3, 4]
        list1_id = get_id(list1)
        a = [1, 2, list1]
        a_id = get_id(a)

        list2 = [4, 3, 3]
        list2_id = get_id(list2)
        b = [list2, 2, 1]
        b_id = get_id(b)

        hash_a = DeepHashPrep(a, ignore_repetition=False)
        hash_b = DeepHashPrep(b, ignore_repetition=False)

        assert not hash_a[list1_id] == hash_b[list2_id]
        assert not hash_a[a_id] == hash_b[b_id]

        assert hash_a[list1_id].replace('3|1', '3|2') == hash_b[list2_id]

    def test_already_calculated_hash_wont_be_recalculated(self):
        hashes = (i for i in range(10))

        def hasher(obj):
            return str(next(hashes))
        obj = "a"
        expected_result = {obj: '0'}
        result = DeepHash(obj, hasher=hasher)
        assert expected_result == result

        # we simply feed the last result to DeepHash
        # So it can re-use the results.
        result2 = DeepHash(obj, hasher=hasher, hashes=result)
        # if hashes are not cached and re-used,
        # then the next time hasher runs, it returns
        # number 1 instead of 0.
        assert expected_result == result2

        result3 = DeepHash(obj, hasher=hasher)
        expected_result = {obj: '1'}
        assert expected_result == result3

    def test_skip_type(self):
        l1 = logging.getLogger("test")
        obj = {"log": l1, 2: 1337}
        result = DeepHashPrep(obj, exclude_types={logging.Logger})
        assert get_id(l1) not in result

    def test_skip_type2(self):
        l1 = logging.getLogger("test")
        result = DeepHashPrep(l1, exclude_types={logging.Logger})
        assert not result

    def test_prep_dic_with_loop(self):
        obj = {2: 1337}
        obj[1] = obj
        result = DeepHashPrep(obj)
        expected_result = {get_id(obj): 'dict:{int:2:int:1337}', 1: 'int:1', 2: 'int:2', 1337: 'int:1337'}
        assert expected_result == result

    def test_prep_iterable_with_loop(self):
        obj = [1]
        obj.append(obj)
        result = DeepHashPrep(obj)
        expected_result = {get_id(obj): 'list:int:1', 1: 'int:1'}
        assert expected_result == result

    def test_prep_iterable_with_excluded_type(self):
        l1 = logging.getLogger("test")
        obj = [1, l1]
        result = DeepHashPrep(obj, exclude_types={logging.Logger})
        assert get_id(l1) not in result

    def test_skip_str_type_in_dict_on_list(self):
        dic1 = {1: "a"}
        t1 = [dic1]
        dic2 = {}
        t2 = [dic2]
        t1_hash = DeepHashPrep(t1, exclude_types=[str])
        t2_hash = DeepHashPrep(t2, exclude_types=[str])
        assert 1 in t1_hash
        assert t1_hash[dic1] == t2_hash[dic2]

    def test_skip_path_in_hash(self):
        dic1 = {1: "a"}
        t1 = [dic1, 2]
        dic2 = {}
        t2 = [dic2, 2]
        t1_hash = DeepHashPrep(t1, exclude_paths=['root[0]'])
        t2_hash = DeepHashPrep(t2, exclude_paths='root[0]')
        t2_hash_again = DeepHashPrep(t2, include_paths='1')
        assert 1 not in t1_hash
        assert 2 in t1_hash
        assert t1_hash[2] == t2_hash[2]
        assert t1_hash[2] == t2_hash_again[2]

    def test_skip_path2(self):

        obj10 = {'a': 1, 'b': 'f', 'e': "1111", 'foo': {'bar': 'baz'}}
        obj11 = {'c': 1, 'd': 'f', 'e': 'Cool'}

        obj20 = {'a': 1, 'b': 'f', 'e': 'Cool', 'foo': {'bar': 'baz2'}}
        obj21 = {'c': 1, 'd': 'f', 'e': "2222"}

        t1 = [obj10, obj11]
        t2 = [obj20, obj21]

        exclude_paths = ["root[0]['e']", "root[1]['e']", "root[0]['foo']['bar']"]

        t1_hash = DeepHashPrep(t1, exclude_paths=exclude_paths)
        t2_hash = DeepHashPrep(t2, exclude_paths=exclude_paths)
        assert t1_hash[t1] == t2_hash[t2]

    def test_hash_include_path_nested(self):

        obj10 = {'a': 1, 'b': 'f', 'e': "1111", 'foo': {'bar': 'baz'}}
        obj11 = {'c': 1, 'd': 'f', 'e': 'Cool'}

        obj20 = {'a': 1, 'b': 'f', 'e': 'Cool', 'foo': {'bar': 'baz'}}
        obj21 = {'c': 1, 'd': 'f', 'e': "2222"}

        t1 = [obj10, obj11]
        t2 = [obj20, obj21]

        include_paths = ["root[0]['foo']['bar']"]

        t1_hash = DeepHashPrep(t1, include_paths=include_paths)
        t2_hash = DeepHashPrep(t2, include_paths=include_paths)
        assert t1_hash[t1] == t2_hash[t2]

    def test_skip_regex_path(self):
        dic1 = {1: "a"}
        t1 = [dic1, 2]
        exclude_re = re.compile(r'\[0\]')
        t1_hash = DeepHashPrep(t1, exclude_regex_paths=r'\[0\]')
        t2_hash = DeepHashPrep(t1, exclude_regex_paths=[exclude_re])
        assert 1 not in t1_hash
        assert 2 in t1_hash
        assert t1_hash[2] == t2_hash[2]

    def test_skip_hash_exclude_obj_callback(self):
        def exclude_obj_callback(obj, parent):
            return True if parent == "root[0]['x']" or obj == 2 else False

        dic1 = {"x": 1, "y": 2, "z": 3}
        t1 = [dic1]
        t1_hash = DeepHashPrep(t1, exclude_obj_callback=exclude_obj_callback)
        assert t1_hash == {'y': 'str:y', 'z': 'str:z', 3: 'int:3',
                           get_id(dic1): 'dict:{str:z:int:3}', get_id(t1): 'list:dict:{str:z:int:3}'}
        dic2 = {"z": 3}
        t2 = [dic2]
        t2_hash = DeepHashPrep(t2, exclude_obj_callback=exclude_obj_callback)
        assert t1_hash[t1] == t2_hash[t2]

    def test_string_case(self):
        t1 = "Hello"

        t1_hash = DeepHashPrep(t1)
        assert t1_hash == {'Hello': 'str:Hello'}

        t1_hash = DeepHashPrep(t1, ignore_string_case=True)
        assert t1_hash == {'Hello': 'str:hello'}

    def test_hash_class(self):
        t1 = ClassC
        t1_hash = DeepHashPrep(t1)
        assert t1_hash['class_attr'] == 'str:class_attr'
        assert t1_hash[0] == 'int:0'
        # Note: we ignore private names in calculating hashes now. So you dont see __init__ here for example.
        assert t1_hash[t1] == r'objClassC:{str:class_attr:int:0}'

    def test_hash_set_in_list(self):
        t1 = [{1, 2, 3}, {4, 5}]
        t1_hash = DeepHashPrep(t1)
        assert t1_hash[t1] == 'list:set:int:1,int:2,int:3,set:int:4,int:5'

    def test_hash_numpy_array1(self):
        t1 = np.array([[1, 2]], np.int8)
        t2 = np.array([[2, 1]], np.int8)
        t1_hash = DeepHashPrep(t1)
        t2_hash = DeepHashPrep(t2)
        assert t1_hash[t1] == 'ndarray:ndarray:int8:1,int8:2'
        assert t2_hash[t2] == t1_hash[t1]

    def test_hash_numpy_array_ignore_numeric_type_changes(self):
        t1 = np.array([[1, 2]], np.int8)
        t1_hash = DeepHashPrep(t1, ignore_numeric_type_changes=True)
        assert t1_hash[t1] == 'ndarray:ndarray:number:1.000000000000,number:2.000000000000'

    def test_hash_numpy_array2_multi_dimensional_can_not_retrieve_individual_array_item_hashes(self):
        """
        This is a very interesting case. When DeepHash extracts t1[0] to create a hash for it,
        Numpy creates an array. But that array will only be technically available during the DeepHash run.
        Once DeepHash is run, the array is marked to be deleted by the garbage collector.
        However depending on the version of the python and the machine that runs it, by the time we get
        to the line that is t1_hash[t1[0]], the t1[0] may or may not be still in memory.
        If it is still in the memory, t1_hash[t1[0]] works without a problem.
        If it is already garbage collected, t1_hash[t1[0]] will throw a key error since there will be
        a new t1[0] by the time t1_hash[t1[0]] is called. Hence it will have a new ID and thus it
        will not be available anymore in t1_hash. Remember that since Numpy arrays are not hashable,
        the ID of the array is stored in t1_hash as a key and not the object itself.
        """
        t1 = np.array([[1, 2, 3, 4], [4, 2, 2, 1]], np.int8)
        t1_hash = DeepHashPrep(t1)
        try:
            t1_hash[t1[0]]
        except Exception as e:
            assert str(e).strip("'") == HASH_LOOKUP_ERR_MSG.format(t1[0])

    def test_pandas(self):
        import pandas as pd
        df = pd.DataFrame({"a": [1]})
        equal_df = pd.DataFrame({"a": [1]})
        df_same_column_names = pd.DataFrame({"a": [1, 2]})
        other_df = pd.DataFrame({"b": [1]})
        df_hash = DeepHashPrep(df)[df]
        equal_df_hash = DeepHashPrep(equal_df)[equal_df]
        df_same_column_names_hash = DeepHashPrep(df_same_column_names)[df_same_column_names]
        other_df_hash = DeepHashPrep(other_df)[other_df]
        assert df_hash == equal_df_hash
        assert df_hash != df_same_column_names_hash
        assert df_hash != other_df_hash

        df_mixed = pd.DataFrame({'a': [1], 'b': ['two'], 'c': [(1, 2)]})
        df_mixed_2 = pd.DataFrame({'a': [1], 'b': ['two'], 'c': [(1, 2)]})
        df_mixed_3 = pd.DataFrame({'a': [1], 'b': ['one'], 'c': [(1, 2)]})
        df_mixed_4 = pd.DataFrame({'a': [1], 'b': ['two'], 'c': [(1, 3)]})
        df_mixed_hash = DeepHashPrep(df_mixed)[df_mixed]
        df_mixed_2_hash = DeepHashPrep(df_mixed_2)[df_mixed_2]
        df_mixed_3_hash = DeepHashPrep(df_mixed_3)[df_mixed_3]
        df_mixed_4_hash = DeepHashPrep(df_mixed_4)[df_mixed_4]
        assert df_mixed_hash == df_mixed_2_hash
        assert df_mixed_hash != df_mixed_3_hash
        assert df_mixed_hash != df_mixed_4_hash

        df_u8 = pd.DataFrame({'a': np.array([1], dtype=np.uint8)})
        df_u16 = pd.DataFrame({'a': np.array([1], dtype=np.uint16)})
        df_float = pd.DataFrame({'a': np.array([1], dtype=np.float32)})
        df_u8_hash = DeepHashPrep(df_u8)[df_u8]
        df_u16_hash = DeepHashPrep(df_u16)[df_u16]
        df_float_hash = DeepHashPrep(df_float)[df_float]
        assert df_u8_hash != df_float_hash
        assert df_u8_hash != df_u16_hash

        df_index = pd.DataFrame({'a': [1, 2, 3]}, index=[1, 2, 3])
        df_index_diff = pd.DataFrame({'a': [1, 2, 3]}, index=[1, 2, 4])
        df_index_hash = DeepHashPrep(df_index)[df_index]
        df_index_diff_hash = DeepHashPrep(df_index_diff)[df_index_diff]
        assert df_index_hash != df_index_diff_hash

    def test_polars(self):
        import polars as pl
        df = pl.DataFrame({"a": [1]})
        equal_df = pl.DataFrame({"a": [1]})
        df_same_column_names = pl.DataFrame({"a": [1, 2]})
        other_df = pl.DataFrame({"b": [1]})
        df_hash = DeepHashPrep(df)[df]
        equal_df_hash = DeepHashPrep(equal_df)[equal_df]
        df_same_column_names_hash = DeepHashPrep(df_same_column_names)[df_same_column_names]
        other_df_hash = DeepHashPrep(other_df)[other_df]
        assert df_hash == equal_df_hash
        assert df_hash != df_same_column_names_hash
        assert df_hash != other_df_hash

        df_mixed = pl.DataFrame({'a': [1], 'b': ['two'], 'c': [(1, 2)]})
        df_mixed_2 = pl.DataFrame({'a': [1], 'b': ['two'], 'c': [(1, 2)]})
        df_mixed_3 = pl.DataFrame({'a': [1], 'b': ['one'], 'c': [(1, 2)]})
        df_mixed_4 = pl.DataFrame({'a': [1], 'b': ['two'], 'c': [(1, 3)]})
        df_mixed_hash = DeepHashPrep(df_mixed)[df_mixed]
        df_mixed_2_hash = DeepHashPrep(df_mixed_2)[df_mixed_2]
        df_mixed_3_hash = DeepHashPrep(df_mixed_3)[df_mixed_3]
        df_mixed_4_hash = DeepHashPrep(df_mixed_4)[df_mixed_4]
        assert df_mixed_hash == df_mixed_2_hash
        assert df_mixed_hash != df_mixed_3_hash
        assert df_mixed_hash != df_mixed_4_hash

        df_u8 = pl.DataFrame({'a': np.array([1], dtype=np.uint8)})
        df_u16 = pl.DataFrame({'a': np.array([1], dtype=np.uint16)})
        df_float = pl.DataFrame({'a': np.array([1], dtype=np.float32)})
        df_u8_hash = DeepHashPrep(df_u8)[df_u8]
        df_u16_hash = DeepHashPrep(df_u16)[df_u16]
        df_float_hash = DeepHashPrep(df_float)[df_float]
        assert df_u8_hash != df_float_hash
        assert df_u8_hash != df_u16_hash

        lazy_1 = pl.DataFrame({"foo": ["a", "b", "c"], "bar": [0, 1, 2]}).lazy()
        lazy_2 = pl.DataFrame({"foo": ["a", "b", "c"], "bar": [0, 1, 2]}).lazy()
        lazy_3 = pl.DataFrame({"foo": ["a", "b", "c"], "bar": [0, 1, 2], "foobar": 5}).lazy()
        with pytest.raises(TypeError):
            DeepHashPrep(lazy_1)[lazy_1]  # lazy dfs can not be compared
        df_1 = lazy_1.collect()
        df_2 = lazy_2.collect()
        df_3 = lazy_3.collect()
        df_1_hash = DeepHashPrep(df_1)[df_1]
        df_2_hash = DeepHashPrep(df_2)[df_2]
        df_3_hash = DeepHashPrep(df_3)[df_3]
        assert df_1_hash == df_2_hash
        assert df_1_hash != df_3_hash


class TestDeepHashSHA:
    """DeepHash with SHA Tests."""

    def test_str_sha1(self):
        obj = "a"
        expected_result = {
            obj: '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8'
        }
        result = DeepHash(obj, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert expected_result == result

    def test_str_sha256(self):
        obj = "a"
        expected_result = {
            obj: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'
        }
        result = DeepHash(obj, ignore_string_type_changes=True, hasher=DeepHash.sha256hex)
        assert expected_result == result

    def test_prep_str_sha1_fail_if_mutable(self):
        """
        This test fails if DeepHash is getting a mutable copy of hashes
        which means each init of the DeepHash will have hashes from
        the previous init.
        """
        obj1 = "a"
        expected_result = {
            obj1: '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8'
        }
        result = DeepHash(obj1, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert expected_result == result
        obj2 = "b"
        result = DeepHash(obj2, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert obj1 not in result

    def test_bytecode(self):
        obj = b"a"
        expected_result = {
            obj: '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8'
        }
        result = DeepHash(obj, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert expected_result == result

    def test_list1(self):
        string1 = "a"
        obj = [string1, 10, 20]
        expected_result = {
            string1: '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8',
            get_id(obj): 'eac61cbd194e5e03c210a3dce67b9bfd6a7b7acb',
            10: DeepHash.sha1hex('int:10'),
            20: DeepHash.sha1hex('int:20'),
        }
        result = DeepHash(obj, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert expected_result == result

    def test_datetime_hash(self):
        dt_utc = datetime.datetime(2025, 2, 3, 12, 0, 0, tzinfo=pytz.utc)  # UTC timezone
        # Convert it to another timezone (e.g., New York)
        dt_ny = dt_utc.astimezone(pytz.timezone('America/New_York'))
        assert dt_utc == dt_ny

        result_utc = DeepHash(dt_utc, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        result_ny = DeepHash(dt_ny, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert result_utc[dt_utc] == result_ny[dt_ny]

    def test_dict1(self):
        string1 = "a"
        key1 = "key1"
        obj = {key1: string1, 1: 10, 2: 20}
        expected_result = {
            1: DeepHash.sha1hex('int:1'),
            10: DeepHash.sha1hex('int:10'),
            2: DeepHash.sha1hex('int:2'),
            20: DeepHash.sha1hex('int:20'),
            key1: '1073ab6cda4b991cd29f9e83a307f34004ae9327',
            string1: '86f7e437faa5a7fce15d1ddcb9eaeaea377667b8',
            get_id(obj): '11e23f096df81b1ccab0c309cdf8b4ba5a0a6895'
        }
        result = DeepHash(obj, ignore_string_type_changes=True, hasher=DeepHash.sha1hex)
        assert expected_result == result


class TestCleaningString:

    @pytest.mark.parametrize("text, ignore_string_type_changes, expected_result", [
        (b'hello', True, 'hello'),
        (b'hello', False, 'bytes:hello'),
        ('hello', True, 'hello'),
        ('hello', False, 'str:hello'),
    ])
    def test_clean_type(self, text, ignore_string_type_changes, expected_result):
        result = prepare_string_for_hashing(text, ignore_string_type_changes=ignore_string_type_changes)
        assert expected_result == result


class TestCounts:

    @pytest.mark.parametrize('obj, expected_count', [
        (
            {1: 1, 2: 3},
            5
        ),
        (
            {"key": {1: 1, 2: 4}, "key2": ["a", "b"]},
            11
        ),
        (
            [{1}],
            3
        ),
        (
            [ClassC(a=10, b=11)],
            6
        )
    ])
    def test_dict_count(self, obj, expected_count):
        """
        How many object went to build this dict?
        """

        result = DeepHash(obj).get(obj, extract_index=1)
        assert expected_count == result


class TestOtherHashFuncs:

    @pytest.mark.parametrize('items, prefix, expected', [
        ([[1], [2]], 'pre', 'pre583852d84b3482edf53408b64724a37289d7af458c44bb989a8abbffe24d2d2b'),
        ([[1], [2]], b'pre', 'pre583852d84b3482edf53408b64724a37289d7af458c44bb989a8abbffe24d2d2b'),
    ])
    def test_combine_hashes_lists(self, items, prefix, expected):
        result = combine_hashes_lists(items, prefix)
        assert expected == result

    EXPECTED_MESSAGE1 = (
        "'utf-8' codec can't decode byte 0xc3 in position 0: invalid continuation byte in '('. "
        "Please either pass ignore_encoding_errors=True or pass the encoding via encodings=['utf-8', '...'].")

    EXPECTED_MESSAGE2 = (
        "'utf-8' codec can't decode byte 0xbc in position 0: invalid start byte in ' cup of flour'. "
        "Please either pass ignore_encoding_errors=True or pass the encoding via encodings=['utf-8', '...'].")

    EXPECTED_MESSAGE3 = (
        "'utf-8' codec can't decode byte 0xc3 in position 34: invalid continuation byte in '...up of potatos. Then ( cup of flour'. Please either pass ignore_encoding_errors=True or "
        "pass the encoding via encodings=['utf-8', '...']."
    )

    @pytest.mark.parametrize('test_num, item, encodings, ignore_encoding_errors, expected_result, expected_message', [
        (1, b'\xc3\x28', None, False, UnicodeDecodeError, EXPECTED_MESSAGE1),
        (2, b'\xc3\x28', ['utf-8'], False, UnicodeDecodeError, EXPECTED_MESSAGE1),
        (3, b'\xc3\x28', ['utf-8'], True, {b'\xc3(': '640da73f0d9b268a0a7ae884d77063d1193f43a651352f9032d99a8fe1705546'}, None),
        (4, b"\xbc cup of flour", ['utf-8'], False, UnicodeDecodeError, EXPECTED_MESSAGE2),
        (5, b"\xbc cup of flour", ['utf-8'], True, {b'\xbc cup of flour': '86ac12eb5e35db88cf93baca1d62098023b2d93d634e75fb4e37657e514f3d51'}, None),
        (6, b"\xbc cup of flour", ['utf-8', 'latin-1'], False, {b'\xbc cup of flour': 'cfc354ae2232a8983bf59b2004f44fcb4036f57df1d08b9cde9950adea3f8d3e'}, None),
        (7, b"First have a cup of potatos. Then \xc3\x28 cup of flour", None, False, UnicodeDecodeError, EXPECTED_MESSAGE3),
    ])
    def test_hash_encodings(self, test_num, item, encodings, ignore_encoding_errors, expected_result, expected_message):
        if UnicodeDecodeError == expected_result:  # NOQA
            with pytest.raises(expected_result) as exc_info:
                DeepHash(item, encodings=encodings, ignore_encoding_errors=ignore_encoding_errors)
            assert expected_message == str(exc_info.value), f"test_encodings test #{test_num} failed."
        else:
            result = DeepHash(item, encodings=encodings, ignore_encoding_errors=ignore_encoding_errors)
            assert expected_result == result, f"test_encodings test #{test_num} failed."

    def test_ip_addresses(self):

        class ClassWithIp:
            """Class containing single data member to demonstrate deepdiff infinite iterate over IPv6Interface"""

            def __init__(self, addr: str):
                self.field: Union[
                    ipaddress.IPv4Network,
                    ipaddress.IPv6Network,
                    ipaddress.IPv4Interface,
                    ipaddress.IPv6Interface,
                ] = ipaddress.IPv6Network(addr)


        obj1 = ClassWithIp("2002:db8::/30")
        obj1_hash = DeepHashPrep(obj1)
        repr(obj1_hash)  # shouldn't raise error
        assert r"objClassWithIp:{str:field:iprange:2002:db8::/30}" == obj1_hash[obj1]
        obj2 = ClassWithIp("2001:db8::/32")
        diff = DeepDiff(obj1, obj2)
        assert {
            "values_changed": {
                "root.field": {
                    "new_value": ipaddress.IPv6Network("2001:db8::/32"),
                    "old_value": ipaddress.IPv6Network("2002:db8::/30"),
                }
            }
        } == diff
