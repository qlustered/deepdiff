#!/usr/bin/env python
import pytest
from deepdiff import DeepDiff
from deepdiff.helper import pypy3, notpresent
from deepdiff.model import DictRelationship, NonSubscriptableIterableRelationship

import logging
logging.disable(logging.CRITICAL)


class TestDeepDiffTree:
    """DeepDiff Tests."""

    def test_same_objects(self):
        t1 = {1: 1, 2: 2, 3: 3}
        t2 = t1
        ddiff = DeepDiff(t1, t2)
        res = ddiff.tree
        assert res == {}

    def test_significant_digits_signed_zero(self):
        t1 = 0.00001
        t2 = -0.0001
        ddiff = DeepDiff(t1, t2, significant_digits=2)
        res = ddiff.tree
        assert res == {}
        t1 = 1 * 10**-12
        t2 = -1 * 10**-12
        ddiff = DeepDiff(t1, t2, significant_digits=10)
        res = ddiff.tree
        assert res == {}

    def test_item_added_extensive(self):
        t1 = {'one': 1, 'two': 2, 'three': 3, 'four': 4}
        t2 = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'new': 1337}
        ddiff = DeepDiff(t1, t2)
        res = ddiff.tree
        (key, ) = res.keys()
        assert key == 'dictionary_item_added'
        assert len(res['dictionary_item_added']) == 1

        (added1, ) = res['dictionary_item_added']

        # assert added1 DiffLevel chain is valid at all
        assert added1.up.down == added1
        assert added1.down is None
        assert added1.up.up is None
        assert added1.all_up == added1.up
        assert added1.up.all_down == added1
        assert added1.report_type == 'dictionary_item_added'

        # assert DiffLevel chain points to the objects we entered
        assert added1.up.t1 == t1
        assert added1.up.t2 == t2

        assert added1.t1 is notpresent
        assert added1.t2 == 1337

        # assert DiffLevel child relationships are correct
        assert added1.up.t1_child_rel is None
        assert isinstance(added1.up.t2_child_rel, DictRelationship)
        assert added1.up.t2_child_rel.parent == added1.up.t2
        assert added1.up.t2_child_rel.child == added1.t2
        assert added1.up.t2_child_rel.param == 'new'

        assert added1.up.path() == "root"
        assert added1.path() == "root['new']"

    def test_item_added_and_removed(self):
        t1 = {'one': 1, 'two': 2, 'three': 3, 'four': 4}
        t2 = {'one': 1, 'two': 4, 'three': 3, 'five': 5, 'six': 6}
        ddiff = DeepDiff(t1, t2, view='tree')
        assert set(ddiff.keys()) == {
            'dictionary_item_added', 'dictionary_item_removed',
            'values_changed'
        }
        assert len(ddiff['dictionary_item_added']) == 2
        assert len(ddiff['dictionary_item_removed']) == 1

    def test_item_added_and_removed2(self):
        t1 = {2: 2, 4: 4}
        t2 = {2: "b", 5: 5}
        ddiff = DeepDiff(t1, t2, view='tree')
        assert set(ddiff.keys()), {
            'dictionary_item_added', 'dictionary_item_removed',
            'type_changes'
        }
        assert len(ddiff['dictionary_item_added']) == 1
        assert len(ddiff['dictionary_item_removed']) == 1

    def test_non_subscriptable_iterable(self):
        t1 = (i for i in [42, 1337, 31337])
        t2 = (i for i in [
            42,
            1337,
        ])
        ddiff = DeepDiff(t1, t2, view='tree')
        (change, ) = ddiff['iterable_item_removed']

        assert set(ddiff.keys()) == {'iterable_item_removed'}
        assert len(ddiff['iterable_item_removed']) == 1

        assert change.up.t1 == t1
        assert change.up.t2 == t2
        assert change.report_type == 'iterable_item_removed'
        assert change.t1 == 31337
        assert change.t2 is notpresent

        assert isinstance(change.up.t1_child_rel,
                          NonSubscriptableIterableRelationship)
        assert change.up.t2_child_rel is None

    def test_non_subscriptable_iterable_path(self):
        t1 = (i for i in [42, 1337, 31337])
        t2 = (i for i in [42, 1337, ])
        ddiff = DeepDiff(t1, t2, view='tree')
        (change, ) = ddiff['iterable_item_removed']

        # testing path
        assert change.path() is None
        assert change.path(force='yes') == 'root(unrepresentable)'
        assert change.path(force='fake') == 'root[2]'

    def test_unrepresentable_dict_key_path(self):
        class Id:
            def __repr__(self):
                return '<id>'

            def __hash__(self):
                return 1

            def __eq__(self, other):
                return isinstance(other, Id)

        key = Id()
        t1 = {key: 10}
        t2 = {key: 20}
        ddiff = DeepDiff(t1, t2, view='tree')
        (change, ) = ddiff['values_changed']

        # repr does not round-trip, so there is no parsable path
        assert change.path() is None
        assert change.path(force='yes') == 'root[(unrepresentable)]'

    def test_report_type_in_iterable(self):
        a = {"temp": ["a"]}
        b = {"temp": ["b"]}

        ddiff = DeepDiff(a, b, ignore_order=True, view="tree")
        report_type = ddiff['values_changed'][0].report_type
        assert 'values_changed' == report_type

    def test_significant_digits(self):
        ddiff = DeepDiff(
            [0.012, 0.98],
            [0.013, 0.99],
            significant_digits=1,
            view='tree')
        assert ddiff == {}

    def test_significant_digits_with_sets(self):
        ddiff = DeepDiff(
            {0.012, 0.98},
            {0.013, 0.99},
            significant_digits=1,
            view='tree')
        assert ddiff == {}

    def test_significant_digits_with_ignore_order(self):
        ddiff = DeepDiff(
            [0.012, 0.98], [0.013, 0.99],
            significant_digits=1,
            ignore_order=True,
            view='tree')
        assert ddiff == {}

    def test_repr(self):
        t1 = {1, 2, 8}
        t2 = {1, 2, 3, 5}
        ddiff = DeepDiff(t1, t2, view='tree')
        str(ddiff)


class TestDeepDiffTreeWithNumpy:
    """DeepDiff Tests with Numpy."""

    @pytest.mark.skipif(pypy3, reason="Numpy is not compatible with pypy3")
    def test_diff_with_numpy(self):
        import numpy as np
        a1 = np.array([1.23, 1.66, 1.98])
        a2 = np.array([1.23, 1.66, 1.98])
        d1 = {'np': a1}
        d2 = {'np': a2}
        ddiff = DeepDiff(d1, d2)
        res = ddiff.tree
        assert res == {}

    @pytest.mark.skipif(pypy3, reason="Numpy is not compatible with pypy3")
    def test_diff_with_empty_seq(self):
        a1 = {"empty": []}
        a2 = {"empty": []}
        ddiff = DeepDiff(a1, a2)
        assert ddiff == {}


class TestDeepAdditions:
    """Tests for Additions and Subtractions."""

    @pytest.mark.skip(reason="Not currently implemented")
    def test_adding_list_diff(self):
        t1 = [1, 2]
        t2 = [1, 2, 3, 5]
        ddiff = DeepDiff(t1, t2, view='tree')
        addition = ddiff + t1
        assert addition == t2
