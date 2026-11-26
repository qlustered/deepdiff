import pytest
from deepdiff import DeepDiff, Delta
from deepdiff.helper import np
from tests import parameterize_cases

"""
These are numpy specific test cases.
There are more numpy tests for delta additions in the test_delta.py
"""

NUMPY_CASES = {
    'numpy_bools': {
        't1': np.array([True, False, True, False], dtype=bool),
        't2': np.array([False, True, True, False], dtype=bool),
        'deepdiff_kwargs': {},
        'expected_result': {'values_changed': {'root[0]': {'new_value': False, 'old_value': True},
                            'root[1]': {'new_value': True, 'old_value': False}}},
    },
    'numpy_bools_ignore_order': {
        't1': np.array([True, False, True, False], dtype=bool),
        't2': np.array([False, True, True, False], dtype=bool),
        'deepdiff_kwargs': {'ignore_order': True},
        'expected_result': {},
    },
    'numpy_multi_dimensional1': {
        't1': np.array([[[1, 2, 3], [4, 5, 6]]], np.int32),
        't2': np.array([[[1, 2, 5], [3, 5, 6]]], np.int32),
        'deepdiff_kwargs': {},
        'expected_result': {'values_changed':
                            {'root[0][0][2]': {'new_value': 5, 'old_value': 3},
                             'root[0][1][0]': {'new_value': 3, 'old_value': 4}}},
    },
    'numpy_array2_type_change': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 5], np.int32),
        'deepdiff_kwargs': {'verbose_level': 0},
        'expected_result': {'type_changes': {'root': {'old_type': np.int8, 'new_type': np.int32}}},
    },
    'numpy_array3_ignore_number_type_changes': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([1, 2, 5], np.int32),
        'deepdiff_kwargs': {'ignore_numeric_type_changes': True},
        'expected_result': {'values_changed': {'root[2]': {'new_value': 5, 'old_value': 3}}},
    },
    'numpy_array4_ignore_number_type_changes_and_ignore_order': {
        't1': np.array([1, 2, 3], np.int8),
        't2': np.array([3, 1, 2], np.int32),
        'deepdiff_kwargs': {'ignore_numeric_type_changes': True, 'ignore_order': True},
        'expected_result': {},
    },
    'numpy_array5_ignore_number_type_changes_and_ignore_order': {
        't1': np.array([1, 2, 4, 3], np.int8),
        't2': np.array([3, 1, 2, 5], np.int32),
        'deepdiff_kwargs': {'ignore_numeric_type_changes': True, 'ignore_order': True},
        'expected_result': {'values_changed': {'root[2]': {'new_value': 5, 'old_value': 4}}},
    },
    'numpy_array6_ignore_order_and_report_repetition': {
        't1': np.array([1, 2, 3, 3], np.int8),
        't2': np.array([3, 1, 2, 5], np.int8),
        'deepdiff_kwargs': {'report_repetition': True, 'ignore_order': True},
        'expected_result': {'iterable_item_added': {'root[3]': 5},
                            'repetition_change': {'root[2]': {'old_repeat': 2, 'new_repeat': 1,
                                                              'old_indexes': [2, 3], 'new_indexes': [0], 'value': 3}}},
    },
    'numpy_array7_ignore_order_multi_dimensional_array': {
        't1': np.array([[1, 2, 3, 4], [4, 2, 2, 1]], np.int8),
        't2': np.array([[4, 1, 1, 1], [1, 3, 2, 4]], np.int8),
        'deepdiff_kwargs': {'report_repetition': True, 'ignore_order': True},
        'expected_result': {
            'iterable_item_removed': {
                'root[1][1]': 2,
                'root[1][2]': 2
            },
            'repetition_change': {
                'root[1][3]': {
                    'old_repeat': 1,
                    'new_repeat': 3,
                    'old_indexes': [3],
                    'new_indexes': [1, 2, 3],
                    'value': 1
                }
            }
        },
    },
    'numpy_array8_ignore_order_multi_dimensional_array_converted_to_list': {
        't1': np.array([[1, 2, 3, 4], [4, 2, 2, 1]], np.int8).tolist(),
        't2': np.array([[4, 1, 1, 1], [1, 3, 2, 4]], np.int8).tolist(),
        'deepdiff_kwargs': {
            'report_repetition': True,
            'ignore_order': True
        },
        'expected_result': {
            'iterable_item_removed': {
                'root[1][1]': 2,
                'root[1][2]': 2
            },
            'repetition_change': {
                'root[1][3]': {
                    'old_repeat': 1,
                    'new_repeat': 3,
                    'old_indexes': [3],
                    'new_indexes': [1, 2, 3],
                    'value': 1
                }
            }
        },
    },
    'numpy_array9_ignore_nan_inequality_float32': {
        't1': np.array([1, 2, 3, np.nan], np.float32),
        't2': np.array([1, 2, 4, np.nan], np.float32),
        'deepdiff_kwargs': {
            'ignore_nan_inequality': True,
        },
        'expected_result': {'values_changed': {'root[2]': {'new_value': 4.0, 'old_value': 3.0}}}
    },
    'numpy_almost_equal': {
        't1': np.array([1.0, 2.3333333333333]),
        't2': np.array([1.0, 2.33333334]),
        'deepdiff_kwargs': {'significant_digits': 3},
        'expected_result': {},
    },
    'numpy_almost_equal2': {
        't1': np.array(['a', 'b'], dtype=object),
        't2': np.array(['a', 'b'], dtype=object),
        'deepdiff_kwargs': {'significant_digits': 6},
        'expected_result': {},
    },
    'numpy_different_shape': {
        't1': np.array([[1, 1], [2, 3]]),
        't2': np.array([1]),
        'deepdiff_kwargs': {},
        'expected_result': {
            'type_changes': {
                'root[0]': {
                    'old_type': list,
                    'new_type': int,
                    'old_value': [1, 1],
                    'new_value': 1
                }
            },
            'iterable_item_removed': {
                'root[1]': [2, 3]
            }
        },
    },
    'numpy_datetime_equal': {
        't1': np.datetime64('2023-07-05T10:11:12'),
        't2': np.datetime64('2023-07-05T10:11:12'),
        'deepdiff_kwargs': {},
        'expected_result': {},
    },
    'numpy_datetime_unequal': {
        't1': np.datetime64('2023-07-05T10:11:12'),
        't2': np.datetime64('2024-07-05T10:11:12'),
        'deepdiff_kwargs': {},
        'expected_result': {
            'values_changed': {
                'root': {
                    'new_value': np.datetime64('2024-07-05T10:11:12'),
                    'old_value': np.datetime64('2023-07-05T10:11:12'),
                }
            },
        },
    },
}


NUMPY_CASES_PARAMS = parameterize_cases('test_name, t1, t2, deepdiff_kwargs, expected_result', NUMPY_CASES)


class TestNumpy:

    @pytest.mark.parametrize(**NUMPY_CASES_PARAMS)
    def test_numpy(self, test_name, t1, t2, deepdiff_kwargs, expected_result):
        diff = DeepDiff(t1, t2, **deepdiff_kwargs)
        assert expected_result == diff, f"test_numpy {test_name} failed."


@pytest.mark.parametrize('ignore_order', [False, True])
@pytest.mark.parametrize('before, after', [(1, 2), (1.5, 2.5), ('a', 'b'), (True, False)])
def test_zero_dimensional_array_values(before, after, ignore_order):
    options = {'ignore_order': ignore_order}
    assert DeepDiff(np.array(before), np.array(after), **options) == {
        'values_changed': {'root': {'old_value': before, 'new_value': after}}
    }
    assert not DeepDiff(np.array(before), np.array(before), **options)
    assert DeepDiff({'value': np.array(before)}, {'value': np.array(after)}, **options) == {
        'values_changed': {"root['value']": {'old_value': before, 'new_value': after}}
    }


@pytest.mark.parametrize('ignore_order', [False, True])
def test_zero_dimensional_array_comparison_options(ignore_order):
    assert not DeepDiff(np.array(1.01), np.array(1.02), significant_digits=1, ignore_order=ignore_order)
    assert not DeepDiff(np.array(1.01), np.array(1.02), math_epsilon=0.1, ignore_order=ignore_order)
    assert not DeepDiff(np.array(float('nan')), np.array(float('nan')),
                        ignore_nan_inequality=True, ignore_order=ignore_order)
    assert not DeepDiff(np.array(1), np.array(1.0), ignore_numeric_type_changes=True, ignore_order=ignore_order)


@pytest.mark.parametrize('before, after', [(1, 2), (1.5, 2.5), (True, False), (1, [1]), ([1], 1)])
def test_zero_dimensional_array_delta(before, after):
    t1, t2 = np.array(before), np.array(after)
    result = Delta(DeepDiff(t1, t2)) + t1
    assert isinstance(result, np.ndarray)
    assert result.shape == t2.shape
    np.testing.assert_array_equal(result, t2)


def test_nested_zero_dimensional_array_delta():
    t1 = {'value': np.array(1)}
    t2 = {'value': np.array(2)}
    result = Delta(DeepDiff(t1, t2)) + t1
    assert isinstance(result['value'], np.ndarray)
    assert result['value'].shape == ()
    np.testing.assert_array_equal(result['value'], t2['value'])


def test_zero_dimensional_array_delta_rejects_invalid_dtype():
    from deepdiff.delta import DeltaError

    delta = Delta({'values_changed': {'root': {'new_value': 2}},
                   '_numpy_paths': {'root': 'invalid_dtype'}}, raise_errors=True)
    with pytest.raises(DeltaError, match='not a valid numpy type'):
        delta + np.array(1)
