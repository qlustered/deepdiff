#!/usr/bin/env python
import pytest
import datetime
import numpy as np
from enum import Enum
from decimal import Decimal
from deepdiff.helper import (
    short_repr, number_to_string, get_numpy_ndarray_rows,
    cartesian_product_of_shape, literal_eval_extended,
    not_found, diff_numpy_array, cartesian_product_numpy,
    get_truncate_datetime, datetime_normalize,
    detailed__dict__, ENUM_INCLUDE_KEYS, add_root_to_paths,
    get_semvar_as_integer,
)


class MyEnum(Enum):
    A = 1
    B = 2


class TestHelper:
    """Helper Tests."""

    def test_short_repr_when_short(self):

        item = {1: 2}
        output = short_repr(item)
        assert output == '{1: 2}'

    def test_short_repr_when_long(self):

        item = {'Eat more': 'burritos'}
        output = short_repr(item)
        assert output == "{'Eat more':...}"

    @pytest.mark.parametrize("t1, t2, significant_digits, number_format_notation, expected_result",
                             [
                                 (10, 10.0, 5, "f", True),
                                 (10, 10.0, 5, "e", True),
                                 (10, 10.2, 5, "f", ('10.00000', '10.20000')),
                                 (10, 10.2, 5, "e", ('1.00000e+1', '1.02000e+1')),
                                 (10, 10.2, 0, "f", True),
                                 (10, 10.2, 0, "e", True),
                                 (Decimal(10), 10, 0, "f", True),
                                 (Decimal(10), 10, 0, "e", True),
                                 (Decimal(10), 10, 10, "f", True),
                                 (Decimal(10), 10, 10, "e", True),
                                 (Decimal(10), 10.0, 0, "f", True),
                                 (Decimal(10), 10.0, 0, "e", True),
                                 (Decimal(10), 10.0, 10, "f", True),
                                 (Decimal(10), 10.0, 10, "e", True),
                                 (Decimal('10.0'), 10.0, 5, "f", True),
                                 (Decimal('10.0'), 10.0, 5, "e", True),
                                 (Decimal('10.01'), 10.01, 1, "f", True),
                                 (Decimal('10.01'), 10.01, 1, "e", True),
                                 (Decimal('10.01'), 10.01, 2, "f", True),
                                 (Decimal('10.01'), 10.01, 2, "e", True),
                                 (Decimal('10.01'), 10.01, 5, "f", True),
                                 (Decimal('10.01'), 10.01, 5, "e", True),
                                 (Decimal('10.01'), 10.01, 8, "f", True),
                                 (Decimal('10.01'), 10.01, 8, "e", True),
                                 (Decimal('10.010'), 10.01, 3, "f", True),
                                 (Decimal('10.010'), 10.01, 3, "e", True),
                                 (Decimal('100000.1'), 100000.1, 0, "f", True),
                                 (Decimal('100000.1'), 100000.1, 0, "e", True),
                                 (Decimal('100000.1'), 100000.1, 1, "f", True),
                                 (Decimal('100000.1'), 100000.1, 1, "e", True),
                                 (Decimal('100000.1'), 100000.1, 5, "f", True),
                                 (Decimal('100000.1'), 100000.1, 5, "e", True),
                                 (Decimal('100000'), 100000.1, 0, "f", True),
                                 (Decimal('100000'), 100000.1, 0, "e", True),
                                 (Decimal('100000'), 100000.1, 1, "f", ('100000.0', '100000.1')),
                                 (Decimal('100000'), 100000.1, 1, "e", True),
                                 (Decimal('-100000'), 100000.1, 1, "f", ('-100000.0', '100000.1')),
                                 (Decimal('-100000'), 100000.1, 1, "e", ("-1.0e+5","1.0e+5")),
                                 (0, 0.0, 5, "f", True),
                                 (0, 0.0, 5, "e", True),
                                 (0, 0.2, 5, "f", ('0.00000', '0.20000')),
                                 (0, 0.2, 5, "e", ('0.00000e+0', '2.00000e-1')),
                                 (0, 0.2, 0, "f", True),
                                 (0, 0.2, 0, "e", True),
                                 (Decimal(0), 0, 0, "f", True),
                                 (Decimal(0), 0, 0, "e", True),
                                 (Decimal(0), 0, 10, "f", True),
                                 (Decimal(0), 0, 10, "e", True),
                                 (Decimal(0), 0.0, 0, "f", True),
                                 (Decimal(0), 0.0, 0, "e", True),
                                 (Decimal(0), 0.0, 10, "f", True),
                                 (Decimal(0), 0.0, 10, "e", True),
                                 (Decimal('0.0'), 0.0, 5, "f", True),
                                 (Decimal('0.0'), 0.0, 5, "e", True),
                                 (Decimal('0.01'), 0.01, 1, "f", True),
                                 (Decimal('0.01'), 0.01, 1, "e", True),
                                 (Decimal('0.01'), 0.01, 2, "f", True),
                                 (Decimal('0.01'), 0.01, 2, "e", True),
                                 (Decimal('0.01'), 0.01, 5, "f", True),
                                 (Decimal('0.01'), 0.01, 5, "e", True),
                                 (Decimal('0.01'), 0.01, 8, "f", True),
                                 (Decimal('0.01'), 0.01, 8, "e", True),
                                 (Decimal('0.010'), 0.01, 3, "f", True),
                                 (Decimal('0.010'), 0.01, 3, "e", True),
                                 (Decimal('0.00002'), 0.00001, 0, "f", True),
                                 (Decimal('0.00002'), 0.00001, 0, "e", True),
                                 (Decimal('0.00002'), 0.00001, 1, "f", True),
                                 (Decimal('0.00002'), 0.00001, 1, "e", True),
                                 (Decimal('0.00002'), 0.00001, 5, "f", ('0.00002', '0.00001')),
                                 (Decimal('0.00002'), 0.00001, 5, "e", ('2.00000e-5', '1.00000e-5')),
                                 (Decimal('0.00002'), 0.00001, 6, "f", ('0.000020', '0.000010')),
                                 (Decimal('0.00002'), 0.00001, 6, "e", ('2.000000e-5', '1.000000e-5')),
                                 (Decimal('0'), 0.1, 0, "f", True),
                                 (Decimal('0'), 0.1, 0, "e", True),
                                 (Decimal('0'), 0.1, 1, "f", ('0.0', '0.1')),
                                 (Decimal('0'), 0.1, 1, "e", ('0.0e+0', '1.0e-1')),
                                 (-0, 0.0, 5, "f", True),
                                 (-0, 0.0, 5, "e", True),
                                 (-0, 0.2, 5, "f", ('0.00000', '0.20000')),
                                 (-0, 0.2, 5, "e", ('0.00000e+0', '2.00000e-1')),
                                 (-0, 0.2, 0, "f", True),
                                 (-0, 0.2, 0, "e", True),
                                 (Decimal(-0), 0, 0, "f", True),
                                 (Decimal(-0), 0, 0, "e", True),
                                 (Decimal(-0), 0, 10, "f", True),
                                 (Decimal(-0), 0, 10, "e", True),
                                 (Decimal(-0), 0.0, 0, "f", True),
                                 (Decimal(-0), 0.0, 0, "e", True),
                                 (Decimal(-0), 0.0, 10, "f", True),
                                 (Decimal(-0), 0.0, 10, "e", True),
                                 (Decimal('-0.0'), 0.0, 5, "f", True),
                                 (Decimal('-0.0'), 0.0, 5, "e", True),
                                 (Decimal('-0.01'), 0.01, 1, "f", True),
                                 (Decimal('-0.01'), 0.01, 1, "e", True),
                                 (Decimal('-0.01'), 0.01, 2, "f", ('-0.01', '0.01')),
                                 (Decimal('-0.01'), 0.01, 2, "e", ('-1.00e-2', '1.00e-2')),
                                 (Decimal('-0.00002'), 0.00001, 0, "f", True),
                                 (Decimal('-0.00002'), 0.00001, 0, "e", True),
                                 (Decimal('-0.00002'), 0.00001, 1, "f", True),
                                 (Decimal('-0.00002'), 0.00001, 1, "e", True),
                                 (Decimal('-0.00002'), 0.00001, 5, "f", ('-0.00002', '0.00001')),
                                 (Decimal('-0.00002'), 0.00001, 5, "e", ('-2.00000e-5', '1.00000e-5')),
                                 (Decimal('-0.00002'), 0.00001, 6, "f", ('-0.000020', '0.000010')),
                                 (Decimal('-0.00002'), 0.00001, 6, "e", ('-2.000000e-5', '1.000000e-5')),
                                 (Decimal('-0'), 0.1, 0, "f", True),
                                 (Decimal('-0'), 0.1, 0, "e", True),
                                 (Decimal('-0'), 0.1, 1, "f", ('0.0', '0.1')),
                                 (Decimal('-0'), 0.1, 1, "e", ('0.0e+0', '1.0e-1')),
                             ])
    def test_number_to_string_decimal_digits(self, t1, t2, significant_digits, number_format_notation, expected_result):
        st1 = number_to_string(t1, significant_digits=significant_digits, number_format_notation=number_format_notation)
        st2 = number_to_string(t2, significant_digits=significant_digits, number_format_notation=number_format_notation)
        if expected_result is True:
            assert st1 == st2
        else:
            assert st1 == expected_result[0]
            assert st2 == expected_result[1]

    @pytest.mark.parametrize("t1, t2, significant_digits, number_format_notation, expected_result",
                             [
                                 (10j, 10.0j, 5, "f", True),
                                 (10j, 10.0j, 5, "e", True),
                                 (4+10j, 4.0000002+10.0000002j, 5, "f", True),
                                 (4+10j, 4.0000002+10.0000002j, 5, "e", True),
                                 (4+10j, 4.0000002+10.0000002j, 7, "f", ('4.0000000+10.0000000j', '4.0000002+10.0000002j')),
                                 (4+10j, 4.0000002+10.0000002j, 7, "e", ('4.0000000e+0+1.0000000e+1j', '4.0000002e+0+1.0000000e+1j')),
                                 (0.00002+0.00002j, 0.00001+0.00001j, 0, "f", True),
                                 (0.00002+0.00002j, 0.00001+0.00001j, 0, "e", True),
                                 (0.00002+0.00002j, 0.00001+0.00001j, 5, "f", ('0.00002+0.00002j', '0.00001+0.00001j')),
                                 (0.00002+0.00002j, 0.00001+0.00001j, 5, "e", ('2.00000e-5+2.00000e-5j', '1.00000e-5+1.00000e-5j')),
                                 (-0.00002-0.00002j, 0.00001+0.00001j, 0, "f", True),
                                 (-0.00002-0.00002j, 0.00001+0.00001j, 0, "e", True),
                                 # negative imaginary parts must round-trip, not raise (issue #551)
                                 (1-1j, 2-3j, 1, "f", ('1.0-1.0j', '2.0-3.0j')),
                                 (4-10j, 4.0000002-10.0000002j, 5, "f", True),
                                 (10j, 10.2j, 5, "f", ('0.00000+10.00000j', '0.00000+10.20000j')),
                                 (10j, 10.2j, 5, "e", ('0.00000e+0+1.00000e+1j', '0.00000e+0+1.02000e+1j')),
                                 (10j, 10.2j, 0, "f", True),
                                 (10j, 10.2j, 0, "e", True),
                                 (0j, 0.0j, 5, "f", True),
                                 (0j, 0.0j, 5, "e", True),
                                 (0j, 0.2j, 5, "f", ('0.00000', '0.00000+0.20000j')),
                                 (0j, 0.2j, 5, "e", ('0.00000e+0', '0.00000e+0+2.00000e-1j')),
                                 (0j, 0.2j, 0, "f", True),
                                 (0j, 0.2j, 0, "e", True),
                                 (-0j, 0.0j, 5, "f", True),
                                 (-0j, 0.0j, 5, "e", True),
                                 (-0j, 0.2j, 5, "f", ('0.00000', '0.00000+0.20000j')),
                                 (-0j, 0.2j, 5, "e", ('0.00000e+0', '0.00000e+0+2.00000e-1j')),
                                 (-0j, 0.2j, 0, "f", True),
                                 (-0j, 0.2j, 0, "e", True),
                             ])
    def test_number_to_string_complex_digits(self, t1, t2, significant_digits, number_format_notation, expected_result):
        st1 = number_to_string(t1, significant_digits=significant_digits, number_format_notation=number_format_notation)
        st2 = number_to_string(t2, significant_digits=significant_digits, number_format_notation=number_format_notation)
        if expected_result is True:
            assert st1 == st2
        else:
            assert st1 == expected_result[0]
            assert st2 == expected_result[1]

    def test_number_to_string_with_invalid_notation(self):
        with pytest.raises(ValueError):
            number_to_string(10, significant_digits=4, number_format_notation='blah')

    def test_cartesian_product_of_shape(self):
        result = list(cartesian_product_of_shape([2, 1, 3]))
        assert [(0, 0, 0), (0, 0, 1), (0, 0, 2), (1, 0, 0), (1, 0, 1), (1, 0, 2)] == result

    def test_get_numpy_ndarray_rows(self):
        obj = np.array([[[1, 2, 3], [4, 5, 6]]], np.int32)
        path0 = (0, 0)
        row0 = np.array([1, 2, 3], dtype=np.int32)
        (path0, row0) = next(get_numpy_ndarray_rows(obj))

        path1 = (0, 1)
        row1 = np.array([4, 5, 6], dtype=np.int32)
        (path1, row1) = next(get_numpy_ndarray_rows(obj))

    @pytest.mark.parametrize('item, expected', [
        ('10', 10),
        ("Decimal('10.1')", Decimal('10.1')),
        ("datetime.datetime(2021, 10, 13, 4, 54, 48, 959835)", datetime.datetime(2021, 10, 13, 4, 54, 48, 959835)),
        ("datetime.date(2021, 10, 13)", datetime.date(2021, 10, 13)),
    ])
    def test_literal_eval_extended(self, item, expected):
        result = literal_eval_extended(item)
        assert expected == result

    def test_not_found_inequality(self):
        assert not_found != not_found

    @pytest.mark.parametrize('array1, array2, expected', [
        (np.array([3, 1, 2, 4, 3]), np.array([5, 2, 4]), [3, 1, 3]),
        (np.array([5, 2, 4]), np.array([3, 1, 2, 4, 3]), [5]),
    ])
    def test_diff_numpy_array(self, array1, array2, expected):
        result = diff_numpy_array(array1, array2)
        assert expected == result.tolist()

    def test_cartesian_product_numpy(self):
        result = cartesian_product_numpy(np.array([3, 1, 2, 4, 3]), np.array([5, 2, 4]))
        expected = [
            [3, 5],
            [3, 2],
            [3, 4],
            [1, 5],
            [1, 2],
            [1, 4],
            [2, 5],
            [2, 2],
            [2, 4],
            [4, 5],
            [4, 2],
            [4, 4],
            [3, 5],
            [3, 2],
            [3, 4]]
        assert expected == result.tolist()

    def test_get_truncate_datetime(self):
        result = get_truncate_datetime('hour')
        assert 'hour' == result
        with pytest.raises(ValueError):
            get_truncate_datetime('blah')

    @pytest.mark.parametrize('truncate_datetime, obj, expected', [
        ('hour',
         datetime.datetime(2020, 5, 30, 7, 28, 51, 698308),
         datetime.datetime(2020, 5, 30, 7, 0, tzinfo=datetime.timezone.utc)),
        ('day',
         datetime.datetime(2020, 5, 30, 7, 28, 51, 698308),
         datetime.datetime(2020, 5, 30, 0, 0, tzinfo=datetime.timezone.utc)),
    ])
    def test_datetime_normalize(self, truncate_datetime, obj, expected):
        result = datetime_normalize(truncate_datetime, obj)
        assert expected == result

    @pytest.mark.parametrize('obj, include_keys, expected', [
        (
            MyEnum.A,
            ENUM_INCLUDE_KEYS,
            {'__objclass__': MyEnum, 'name': 'A', 'value': 1},
        )
    ])
    def test_detailed__dict__(self, obj, include_keys, expected):
        result = detailed__dict__(obj, ignore_private_variables=True, include_keys=include_keys)
        assert expected == result, f"test_detailed__dict__ failed for {obj}"

    @pytest.mark.parametrize('test_num, value, expected', [
        (1, ['ab'], {'root.ab', "root['ab']"}),
        (2, ['11'], {"root['11']", 'root[11]'}),
        (3, ['1a'], {"root['1a']"}),
    ])
    def test_add_root_to_paths(self, test_num, value, expected):
        result = add_root_to_paths(value)
        assert expected == result, f"test_add_root_to_paths #{test_num} failed."

    @pytest.mark.parametrize('test_num, value, expected', [
        (1, '1.2.3', 1002003),
        (2, '1.22.3', 1022003),
        (3, '1.22.3c', 1022003),
        (4, '2.4', 2004000),
        (5, '1.19.0', 1019000),
    ])
    def test_get_semvar_as_integer(self, test_num, value, expected):
        result = get_semvar_as_integer(value)
        assert expected == result, f"test_get_semvar_as_integer #{test_num} failed."
