import logging

import pytest

from deepdiff import DeepDiff, Delta
from deepdiff.helper import CannotCompare


def by_id(x, y, level=None):
    if not isinstance(x, dict) or not isinstance(y, dict):
        raise CannotCompare
    return x['id'] == y['id']


@pytest.mark.parametrize('ignore_order', [False, True])
@pytest.mark.parametrize('report_repetition', [False, True])
def test_nested_rejected_pairs_remain_added_and_removed(ignore_order, report_repetition):
    t1 = [{'id': '1010', 'g': [{'id': '2020'}]},
          {'id': '73', 'g': [{'id': '101'}, {'id': '6790'}]}]
    t2 = [{'id': '73', 'g': [{'id': '202'}, {'id': '15294'}]},
          {'id': '1012', 'g': [{'id': '2020'}]}]
    calls = []

    def compare(x, y, level=None):
        calls.append((x['id'], y['id']))
        return by_id(x, y, level)

    kwargs = dict(iterable_compare_func=compare, ignore_order=ignore_order,
                  report_repetition=report_repetition, cutoff_intersection_for_pairs=1)
    # Keep the existing path convention under a moved parent in each mode.
    parent = 1 if ignore_order else 0
    expected = {
        'iterable_item_added': {
            f"root[{parent}]['g'][0]": {'id': '202'},
            f"root[{parent}]['g'][1]": {'id': '15294'},
            'root[1]': t2[1],
        },
        'iterable_item_removed': {
            'root[0]': t1[0],
            f"root[{parent}]['g'][0]": {'id': '101'},
            f"root[{parent}]['g'][1]": {'id': '6790'},
        },
    }
    assert DeepDiff(t1, t2, **kwargs) == expected
    assert len(calls) == (8 if ignore_order else 7)  # No callback calls while building the result.
    tree = DeepDiff(t1, t2, view='tree', **kwargs)
    assert not tree.get('values_changed')
    for report, items in expected.items():
        assert {level.path(): level.t2 if report.endswith('added') else level.t1
                for level in tree[report]} == items


@pytest.mark.parametrize('ignore_order', [False, True])
def test_cannot_compare_keeps_normal_merge(ignore_order):
    kwargs = dict(ignore_order=ignore_order, cutoff_intersection_for_pairs=1)
    t1, t2 = ['a', 'b'], ['x', 'y']
    assert DeepDiff(t1, t2, iterable_compare_func=by_id, **kwargs) == DeepDiff(t1, t2, **kwargs)


def test_cannot_compare_discards_partial_ordered_rejections():
    t1, t2 = [{'id': 1}, 'a'], [{'id': 2}, 'b']
    assert DeepDiff(t1, t2, iterable_compare_func=by_id) == DeepDiff(t1, t2)


@pytest.mark.parametrize('cache_size', [0, 100])
def test_ignore_order_rejections_are_specific_to_the_merged_pair(cache_size):
    t1 = {'a': [{'id': 1}, 'a'], 'b': ['a', {'id': 1}]}
    t2 = {'a': [{'id': 2}, 'b'], 'b': [{'id': 2}, 'b']}
    # Both lists use the same hash sets, so b reuses a's cached pairing. The
    # callback rejects dict/dict only; the same-index mixed pairs use fallback.
    diff = DeepDiff(t1, t2, iterable_compare_func=by_id, ignore_order=True,
                    cutoff_intersection_for_pairs=1, cache_size=cache_size)
    assert diff == {
        'iterable_item_added': {"root['a'][0]": {'id': 2}},
        'iterable_item_removed': {"root['a'][0]": {'id': 1}},
        'values_changed': {
            "root['a'][1]": {'old_value': 'a', 'new_value': 'b'},
            "root['b'][0]": {'old_value': 'a', 'new_value': {'id': 2}},
            "root['b'][1]": {'old_value': {'id': 1}, 'new_value': 'b'},
        },
    }


@pytest.mark.parametrize('ignore_order', [False, True])
def test_rejected_pairs_and_accepted_changes_delta(ignore_order, caplog):
    t1 = {'items': [{'id': 1, 'v': 'old'}, {'id': 2}]}
    t2 = {'items': [{'id': 1, 'v': 'new'}, {'id': 3}]}
    diff = DeepDiff(t1, t2, iterable_compare_func=by_id, ignore_order=ignore_order,
                    report_repetition=ignore_order, cutoff_intersection_for_pairs=1)
    assert diff == {
        'values_changed': {"root['items'][0]['v']": {'old_value': 'old', 'new_value': 'new'}},
        'iterable_item_added': {"root['items'][1]": {'id': 3}},
        'iterable_item_removed': {"root['items'][1]": {'id': 2}},
    }
    with caplog.at_level(logging.ERROR, logger='deepdiff.delta'):
        delta = Delta(diff, bidirectional=True, raise_errors=True)
        assert t1 + delta == t2
        assert t2 - delta == t1
    assert not caplog.records


def test_rejected_nested_pairs_delta_keeps_unmoved_siblings(caplog):
    t1 = {'items': [{'id': i, 'g': [{'id': 'old'}]} for i in range(11)],
          'outside': [{'id': 'old'}]}
    t2 = {'items': [{'id': i, 'g': [{'id': 'new' if i in (1, 10) else 'old'}]}
                    for i in [1, 0, *range(2, 11)]],
          'outside': [{'id': 'new'}]}
    diff = DeepDiff(t1, t2, iterable_compare_func=by_id)
    with caplog.at_level(logging.ERROR, logger='deepdiff.delta'):
        assert t1 + Delta(diff, raise_errors=True) == t2
    assert not caplog.records


@pytest.mark.parametrize('bidirectional', [False, True])
def test_rejected_nested_pairs_delta_under_moved_parent(bidirectional, caplog):
    t1 = [{'id': '1010', 'g': [{'id': '2020'}]},
          {'id': '73', 'g': [{'id': '101'}, {'id': '6790'}]}]
    t2 = [{'id': '73', 'g': [{'id': '202'}, {'id': '15294'}]},
          {'id': '1012', 'g': [{'id': '2020'}]}]
    diff = DeepDiff(t1, t2, iterable_compare_func=by_id)
    with caplog.at_level(logging.ERROR, logger='deepdiff.delta'):
        assert t1 + Delta(diff, bidirectional=bidirectional, raise_errors=True) == t2
    assert not caplog.records
