"""Tests for ``DeepDiff(iterable_match_keys=...)`` (#664) and the
``iterable_compare_func`` duplicate-item fix it builds on (#665)."""
import pickle
from typing import Any, Dict

import pytest

from deepdiff import DeepDiff, Delta
from deepdiff.helper import CannotCompare, TREE_VIEW
from deepdiff.match_keys import BOOL_TAG, NO_KEY, CompiledMatchKeys, get_item_key


def assert_delta_round_trip(t1, t2, **kwargs):
    diff = DeepDiff(t1, t2, verbose_level=2, **kwargs)
    assert t1 + Delta(diff) == t2
    return diff


def by_id(x, y, level=None):
    try:
        return x["id"] == y["id"]
    except Exception:
        raise CannotCompare() from None


class TestIterableCompareFuncDuplicates:
    """#665: an unmatched t2 item with the same content as a matched one was dropped."""

    @pytest.mark.parametrize("t1, t2, expected", [
        ([{"id": 1}], [{"id": 1}, {"id": 1}], {"iterable_item_added": {"root[1]": {"id": 1}}}),
        ({"a": [{"id": 1}]}, {"a": [{"id": 1}, {"id": 1}]},
         {"iterable_item_added": {"root['a'][1]": {"id": 1}}}),
        ([{"id": 1, "v": 1}], [{"id": 1, "v": 1}, {"id": 1, "v": 1}, {"id": 2}],
         {"iterable_item_added": {"root[1]": {"id": 1, "v": 1}, "root[2]": {"id": 2}}}),
        ([{"id": 1, "v": 1}], [{"id": 1, "v": 1}, {"id": 1, "v": 2}],
         {"iterable_item_added": {"root[1]": {"id": 1, "v": 2}}}),
        ([{"id": 1}, {"id": 1}], [{"id": 1}], {"iterable_item_removed": {"root[1]": {"id": 1}}}),
    ])
    def test_duplicates(self, t1, t2, expected):
        assert DeepDiff(t1, t2, iterable_compare_func=by_id) == expected
        tree = DeepDiff(t1, t2, iterable_compare_func=by_id, view=TREE_VIEW)
        for report_type, paths in expected.items():
            assert {level.path() for level in tree[report_type]} == set(paths)
        assert_delta_round_trip(t1, t2, iterable_compare_func=by_id)

    @pytest.mark.parametrize("t1, t2", [
        ([{"id": 1}], [{"id": 1}, {"id": 1}]),
        ([{"id": 1, "v": 1}], [{"id": 1, "v": 1}, {"id": 1, "v": 1}, {"id": 2}]),
    ])
    def test_duplicates_with_ignore_order(self, t1, t2):
        diff = DeepDiff(t1, t2, iterable_compare_func=by_id, ignore_order=True)
        assert diff == DeepDiff(t1, t2, ignore_order=True)


class TestMatchByKey:

    def test_reorder_only_has_no_diff(self):
        t1 = {"users": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}, {"id": 3, "name": "c"}]}
        t2 = {"users": [{"id": 3, "name": "c"}, {"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
        assert DeepDiff(t1, t2, iterable_match_keys={"root['users']": "id"}) == {}
        diff = assert_delta_round_trip(t1, t2, iterable_match_keys={"root['users']": "id"})
        assert set(diff["iterable_item_moved"]) == {"root['users'][0]", "root['users'][1]", "root['users'][2]"}
        assert diff["iterable_item_moved"]["root['users'][0]"]["new_path"] == "root['users'][1]"

    def test_reorder_with_field_change(self):
        t1 = {"users": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
        t2 = {"users": [{"id": 2, "name": "b"}, {"id": 1, "name": "A"}]}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['users']": "id"})
        # Paths inside moved items are reported at the t2 index, as with iterable_compare_func.
        assert diff == {"values_changed": {"root['users'][1]['name']": {"new_value": "A", "old_value": "a"}}}
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root['users']": "id"})

    def test_insert_does_not_cascade(self):
        t1 = [{"id": i, "v": i} for i in range(5)]
        t2 = [{"id": 99, "v": 99}] + [{"id": i, "v": i} for i in range(5)]
        assert DeepDiff(t1, t2) != {"iterable_item_added": {"root[0]": {"id": 99, "v": 99}}}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root": "id"})
        assert diff == {"iterable_item_added": {"root[0]": {"id": 99, "v": 99}}}
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root": "id"})

    @pytest.mark.parametrize("t1, t2, expected", [
        ([{"id": 1}], [{"id": 2}],
         {"iterable_item_added": {"root[0]": {"id": 2}}, "iterable_item_removed": {"root[0]": {"id": 1}}}),
        ([{"id": 1}, {"id": 2}, {"id": 3}], [{"id": 1}, {"id": 4}, {"id": 5}],
         {"iterable_item_added": {"root[1]": {"id": 4}, "root[2]": {"id": 5}},
          "iterable_item_removed": {"root[1]": {"id": 2}, "root[2]": {"id": 3}}}),
    ])
    def test_few_shared_keys_are_not_collapsed(self, t1, t2, expected):
        assert DeepDiff(t1, t2, iterable_match_keys={"root": "id"}) == expected
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root": "id"})

    def test_adds_removes_changes_and_reorders_round_trip(self):
        t1 = {"users": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}, {"id": 3, "name": "c"}]}
        t2 = {"users": [{"id": 3, "name": "c"}, {"id": 0, "name": "z"}, {"id": 1, "name": "A"}]}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['users']": "id"})
        assert diff == {
            "iterable_item_added": {"root['users'][1]": {"id": 0, "name": "z"}},
            "iterable_item_removed": {"root['users'][1]": {"id": 2, "name": "b"}},
            "values_changed": {"root['users'][2]['name']": {"new_value": "A", "old_value": "a"}},
        }
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root['users']": "id"})

    def test_tree_view(self):
        t1 = {"users": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}
        t2 = {"users": [{"id": 2, "name": "b"}, {"id": 3, "name": "c"}]}
        tree = DeepDiff(t1, t2, iterable_match_keys={"users": "id"}, view=TREE_VIEW)
        assert [level.path() for level in tree["iterable_item_added"]] == ["root['users'][1]"]
        assert [level.path() for level in tree["iterable_item_removed"]] == ["root['users'][0]"]
        assert not tree["values_changed"]


class TestKeySpecs:

    def test_composite_key(self):
        t1 = [{"sku": "a", "wh": 1, "q": 1}, {"sku": "a", "wh": 2, "q": 2}]
        t2 = [{"sku": "a", "wh": 2, "q": 3}, {"sku": "a", "wh": 1, "q": 1}]
        diff = DeepDiff(t1, t2, iterable_match_keys={"root": ("sku", "wh")})
        assert diff == {"values_changed": {"root[0]['q']": {"new_value": 3, "old_value": 2}}}
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root": ("sku", "wh")})

    def test_callable_key(self):
        t1 = [{"product": {"id": 1}, "ts": 10, "n": 1}, {"product": {"id": 2}, "ts": 10, "n": 1}]
        t2 = [{"product": {"id": 2}, "ts": 10, "n": 2}, {"product": {"id": 1}, "ts": 10, "n": 1}]
        keys = {"root": lambda item: (item["product"]["id"], item["ts"])}
        assert DeepDiff(t1, t2, iterable_match_keys=keys) == {
            "values_changed": {"root[0]['n']": {"new_value": 2, "old_value": 1}}}
        assert_delta_round_trip(t1, t2, iterable_match_keys=keys)

    def test_callable_raising_cannot_compare_means_no_key(self):
        def key(item):
            if "id" not in item:
                raise CannotCompare()
            return item["id"]
        t1 = [{"v": 1}, {"id": 1}]
        t2 = [{"id": 1}, {"v": 2}]
        assert DeepDiff(t1, t2, iterable_match_keys={"root": key}) == {
            "values_changed": {"root[1]['v']": {"new_value": 2, "old_value": 1}}}

    def test_int_and_float_ids_match(self):
        t1 = [{"id": 1, "n": "a"}]
        t2 = [{"id": 1.0, "n": "b"}]
        diff = DeepDiff(t1, t2, iterable_match_keys={"root": "id"})
        assert set(diff) == {"type_changes", "values_changed"}
        assert set(diff["type_changes"]) == {"root[0]['id']"}
        assert DeepDiff(t1, t2, iterable_match_keys={"root": "id"}, ignore_numeric_type_changes=True) == {
            "values_changed": {"root[0]['n']": {"new_value": "b", "old_value": "a"}}}

    @pytest.mark.parametrize("old_id, new_id", [(True, 1), (1, True), ("1", 1), (False, 0)])
    def test_bools_and_strings_never_match_numbers(self, old_id, new_id):
        diff = DeepDiff([{"id": old_id}], [{"id": new_id}], iterable_match_keys={"root": "id"})
        assert diff == {
            "iterable_item_added": {"root[0]": {"id": new_id}},
            "iterable_item_removed": {"root[0]": {"id": old_id}},
        }

    def test_key_typing_applies_per_component_and_to_callables(self):
        t1 = [{"a": 1, "b": True}]
        assert DeepDiff(t1, [{"a": 1.0, "b": True}], iterable_match_keys={"root": ("a", "b")},
                        ignore_numeric_type_changes=True) == {}
        assert "iterable_item_added" in DeepDiff(
            t1, [{"a": 1, "b": 1}], iterable_match_keys={"root": ("a", "b")})
        assert "iterable_item_added" in DeepDiff(
            t1, [{"a": 1, "b": 1}], iterable_match_keys={"root": lambda x: (x["a"], x["b"])})
        assert get_item_key({"a": 1, "b": True}, ("a", "b")) == (1, (BOOL_TAG, True))

    @pytest.mark.parametrize("item", [{"x": 1}, [1, 2], 5, "id", None, {"id": [1, 2]}])
    def test_items_without_a_usable_key(self, item):
        assert get_item_key(item, "id") is NO_KEY

    def test_missing_keys_are_paired_in_order(self):
        t1 = [{"v": "a"}, {"id": 1, "v": 1}, "scalar", {"v": "b"}]
        t2 = [{"id": 1, "v": 1}, {"v": "A"}, "scalar"]
        diff = DeepDiff(t1, t2, iterable_match_keys={"root": "id"})
        assert diff == {
            "values_changed": {"root[1]['v']": {"new_value": "A", "old_value": "a"}},
            "iterable_item_removed": {"root[3]": {"v": "b"}},
        }
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root": "id"})

    def test_duplicate_keys_pair_by_occurrence(self):
        t1 = [{"id": 1, "v": 1}, {"id": 1, "v": 2}, {"id": 2}]
        t2 = [{"id": 1, "v": 1}, {"id": 1, "v": 3}, {"id": 1, "v": 4}]
        diff = DeepDiff(t1, t2, iterable_match_keys={"root": "id"})
        assert diff == {
            "values_changed": {"root[1]['v']": {"new_value": 3, "old_value": 2}},
            "iterable_item_added": {"root[2]": {"id": 1, "v": 4}},
            "iterable_item_removed": {"root[2]": {"id": 2}},
        }
        assert_delta_round_trip(t1, t2, iterable_match_keys={"root": "id"})

    def test_identical_duplicates(self):
        assert DeepDiff([{"id": 1}], [{"id": 1}, {"id": 1}], iterable_match_keys={"root": "id"}) == {
            "iterable_item_added": {"root[1]": {"id": 1}}}
        assert_delta_round_trip([{"id": 1}], [{"id": 1}, {"id": 1}], iterable_match_keys={"root": "id"})

    def test_tuples(self):
        t1 = ({"id": 1, "v": 1}, {"id": 2})
        t2 = ({"id": 2}, {"id": 1, "v": 2})
        assert DeepDiff(t1, t2, iterable_match_keys={"root": "id"}) == {
            "values_changed": {"root[1]['v']": {"new_value": 2, "old_value": 1}}}

    def test_bool_tag_survives_pickling(self):
        assert pickle.loads(pickle.dumps(BOOL_TAG)) is BOOL_TAG


class TestPaths:
    T1 = {"orders": [
        {"id": 1, "items": [{"sku": "a", "q": 1}, {"sku": "b", "q": 2}]},
        {"id": 2, "items": [{"sku": "x", "q": 1}]},
        {"id": 3, "items": []},
    ]}
    T2 = {"orders": [
        {"id": 2, "items": [{"sku": "y", "q": 1}, {"sku": "x", "q": 5}]},
        {"id": 1, "items": [{"sku": "b", "q": 2}, {"sku": "a", "q": 9}]},
        {"id": 4, "items": [{"sku": "z", "q": 1}]},
    ]}
    EXPECTED = {
        "iterable_item_added": {
            "root['orders'][0]['items'][0]": {"sku": "y", "q": 1},
            "root['orders'][2]": {"id": 4, "items": [{"sku": "z", "q": 1}]},
        },
        "iterable_item_removed": {"root['orders'][2]": {"id": 3, "items": []}},
        "values_changed": {
            "root['orders'][0]['items'][1]['q']": {"new_value": 5, "old_value": 1},
            "root['orders'][1]['items'][1]['q']": {"new_value": 9, "old_value": 1},
        },
    }

    @pytest.mark.parametrize("keys", [
        {"root['orders']": "id", "root['orders'][*]['items']": "sku"},
        {"root['orders']": "id", "root[**]['items']": "sku"},
        {"orders": "id", "root.orders[*].items": "sku"},
        {'root["orders"]': "id", "root['orders'][*]['items']": lambda item: item["sku"]},
    ])
    def test_nested_keyed_lists(self, keys):
        assert DeepDiff(self.T1, self.T2, iterable_match_keys=keys) == self.EXPECTED
        assert_delta_round_trip(self.T1, self.T2, iterable_match_keys=keys)

    def test_unselected_lists_are_compared_by_position(self):
        diff = DeepDiff(self.T1, self.T2, iterable_match_keys={"root['orders']": "id"})
        assert "root['orders'][0]['items'][0]['sku']" in diff["values_changed"]

    def test_exact_path_takes_precedence_over_globs(self):
        t1 = {"a": [{"id": 1, "k": 1}, {"id": 2, "k": 2}]}
        t2 = {"a": [{"id": 2, "k": 1}, {"id": 1, "k": 2}]}
        keys = {"root[*]": "id", "root[**]": "id", "root['a']": "k"}
        assert DeepDiff(t1, t2, iterable_match_keys=keys) == {
            "values_changed": {"root['a'][0]['id']": {"new_value": 2, "old_value": 1},
                               "root['a'][1]['id']": {"new_value": 1, "old_value": 2}}}

    def test_two_matching_globs_raise(self):
        with pytest.raises(ValueError, match="More than one iterable_match_keys glob"):
            DeepDiff({"a": [1]}, {"a": [2]}, iterable_match_keys={"root[*]": "id", "root[**]": "id"})

    def test_globs_that_never_match_together_are_fine(self):
        keys = {"root['a']": "id", "root[*][*]['b']": "id"}
        assert DeepDiff({"a": [{"id": 1}]}, {"a": [{"id": 1}]}, iterable_match_keys=keys) == {}

    @pytest.mark.parametrize("keys, message", [
        (["root"], "must be a mapping"),
        ({1: "id"}, "paths must be strings"),
        ({"root": 1}, "must be a key name"),
        ({"root": ()}, "must be a key name"),
        ({"root": ("a", 1)}, "must be a key name"),
        ({"[*]": "id"}, "must start with 'root'"),
        ({"users": "id", "root['users']": "name"}, "more than one key spec"),
    ])
    def test_invalid_arguments(self, keys, message):
        with pytest.raises(ValueError, match=message):
            DeepDiff([], [], iterable_match_keys=keys)

    def test_paths_that_are_not_lists_are_ignored(self):
        assert CompiledMatchKeys({"root": "id"}).get_spec(None) is None
        assert DeepDiff({"a": {"id": 1}}, {"a": {"id": 2}}, iterable_match_keys={"root['a']": "id"}) == {
            "values_changed": {"root['a']['id']": {"new_value": 2, "old_value": 1}}}


class TestComposition:

    def test_exclude_paths_glob(self):
        t1 = {"orders": [{"id": 1, "generatedAt": 1, "x": 1}, {"id": 2, "generatedAt": 1, "x": 1}]}
        t2 = {"orders": [{"id": 2, "generatedAt": 2, "x": 1}, {"id": 1, "generatedAt": 2, "x": 2}]}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['orders']": "id"},
                        exclude_paths=["root['orders'][*]['generatedAt']"])
        assert diff == {"values_changed": {"root['orders'][1]['x']": {"new_value": 2, "old_value": 1}}}

    def test_include_paths(self):
        t1 = {"orders": [{"id": 1, "a": 1, "x": 1}, {"id": 2, "a": 1, "x": 1}], "other": 1}
        t2 = {"orders": [{"id": 2, "a": 2, "x": 1}, {"id": 1, "a": 2, "x": 2}], "other": 2}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['orders']": "id"},
                        include_paths=["root['orders'][*]['x']"])
        assert diff == {"values_changed": {"root['orders'][1]['x']": {"new_value": 2, "old_value": 1}}}

    def test_ignore_order_for_other_lists(self):
        t1 = {"users": [{"id": 1, "tags": [3, 1, 2]}, {"id": 2, "tags": [1]}], "ids": [1, 2, 2]}
        t2 = {"users": [{"id": 2, "tags": [1, 1]}, {"id": 1, "tags": [1, 2, 3]}], "ids": [2, 1]}
        keys = {"root['users']": "id"}
        diff = DeepDiff(t1, t2, iterable_match_keys=keys, ignore_order=True, report_repetition=True)
        assert set(diff) == {"repetition_change"}
        # Under ignore_order, paths are t1 paths like for any other ignore_order list.
        assert set(diff["repetition_change"]) == {"root['ids'][1]", "root['users'][1]['tags'][0]"}
        delta_diff = DeepDiff(t1, t2, iterable_match_keys=keys, ignore_order=True,
                              report_repetition=True, verbose_level=2)
        # Records paired by key at a different index are not reported as moved when order is ignored.
        assert "iterable_item_moved" not in delta_diff
        # Delta doesn't replay order under ignore_order, so compare ignoring order.
        assert DeepDiff(t1 + Delta(delta_diff), t2, ignore_order=True, report_repetition=True) == {}

    def test_ignore_order_delta_with_changes_in_reindexed_records(self):
        t1 = {"u": [{"id": 1, "n": 1}, {"id": 2, "n": 5}, {"id": 3}]}
        t2 = {"u": [{"id": 4}, {"id": 2, "n": 6}, {"id": 1, "n": 2}]}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['u']": "id"}, ignore_order=True,
                        report_repetition=True, verbose_level=2)
        assert diff["values_changed"]["root['u'][0]['n']"]["new_path"] == "root['u'][2]['n']"
        assert DeepDiff(t1 + Delta(diff), t2, ignore_order=True) == {}

    def test_keyed_list_under_ignore_order(self):
        # The #307 scenario: a list of records identified by uuid, with ignore_order=True.
        t1 = {"fields": [{"uuid": "a", "name": "f1", "size": 1}, {"uuid": "b", "name": "f2", "size": 2}],
              "version": "0.0.0"}
        t2 = {"fields": [{"uuid": "a", "name": "f1", "size": 1}, {"uuid": "c", "name": "f3", "size": 3}],
              "version": "0.0.1"}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['fields']": "uuid"}, ignore_order=True)
        assert diff == {
            "values_changed": {"root['version']": {"new_value": "0.0.1", "old_value": "0.0.0"}},
            "iterable_item_added": {"root['fields'][1]": {"uuid": "c", "name": "f3", "size": 3}},
            "iterable_item_removed": {"root['fields'][1]": {"uuid": "b", "name": "f2", "size": 2}},
        }

    def test_ignore_order_func_selects_other_lists(self):
        t1 = {"users": [{"id": 1}, {"id": 2}], "tags": [1, 2]}
        t2 = {"users": [{"id": 2}, {"id": 3}], "tags": [2, 1]}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['users']": "id"},
                        ignore_order_func=lambda level: True)
        assert diff == {
            "iterable_item_added": {"root['users'][1]": {"id": 3}},
            "iterable_item_removed": {"root['users'][0]": {"id": 1}},
        }

    def test_takes_precedence_over_iterable_compare_func(self):
        def by_name(x, y, level=None):
            try:
                return x["name"] == y["name"]
            except Exception:
                raise CannotCompare() from None
        t1 = {"users": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
              "groups": [{"name": "g1", "n": 1}, {"name": "g2", "n": 1}]}
        t2 = {"users": [{"id": 2, "name": "a"}, {"id": 1, "name": "b"}],
              "groups": [{"name": "g2", "n": 1}, {"name": "g1", "n": 2}]}
        diff = DeepDiff(t1, t2, iterable_match_keys={"root['users']": "id"}, iterable_compare_func=by_name)
        assert diff == {"values_changed": {
            "root['users'][1]['name']": {"new_value": "b", "old_value": "a"},
            "root['users'][0]['name']": {"new_value": "a", "old_value": "b"},
            "root['groups'][1]['n']": {"new_value": 2, "old_value": 1},
        }}

    def test_scalar_lists_elsewhere_keep_their_diff_and_round_trip(self):
        t1 = {"tags": [1, 2, 3, 4, 5], "users": [{"id": 1, "n": 1, "t": [1, 2, 3]}, {"id": 2, "t": [5]}]}
        t2 = {"tags": [0, 1, 9, 8, 3, 5, 6],
              "users": [{"id": 2, "t": [4, 5, 6]}, {"id": 1, "n": 2, "t": [0, 1, 2, 7, 3, 4]}]}
        keys = {"root['users']": "id"}
        diff = DeepDiff(t1, t2, iterable_match_keys=keys)
        assert diff["iterable_item_added"]["root['tags'][0]"] == 0
        assert_delta_round_trip(t1, t2, iterable_match_keys=keys)

    def test_scalar_list_inside_unmoved_record(self):
        t1 = {"users": [{"id": 1, "t": [1, 2, 3]}]}
        t2 = {"users": [{"id": 1, "t": [0, 1, 2, 3]}]}
        keys = {"root['users']": "id"}
        assert DeepDiff(t1, t2, iterable_match_keys=keys) == {
            "iterable_item_added": {"root['users'][0]['t'][0]": 0}}
        assert_delta_round_trip(t1, t2, iterable_match_keys=keys)

    def test_custom_operators(self):
        from deepdiff.operator import BaseOperator

        class CaseInsensitive(BaseOperator):
            def give_up_diffing(self, level, diff_instance):
                if isinstance(level.t1, str) and isinstance(level.t2, str):
                    return level.t1.lower() == level.t2.lower()
                return False

        t1 = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        t2 = [{"id": 2, "name": "BOB"}, {"id": 1, "name": "alice"}]
        diff = DeepDiff(t1, t2, iterable_match_keys={"root": "id"},
                        custom_operators=[CaseInsensitive(types=[str])])
        assert diff == {}

    def test_subtree_multiprocessing_is_disabled(self):
        diff = DeepDiff([], [], iterable_match_keys={"root": "id"})
        assert diff._subtree_parallel_safe() is False

    @pytest.mark.slow
    def test_multiprocessing_matches_serial(self):
        t1 = [{"g": i, "items": [{"sku": s, "q": i} for s in "abcd"]} for i in range(12)]
        t2 = [{"g": i, "items": [{"sku": s, "q": i + (s == "c")} for s in "dcba"]} for i in range(12)]
        kwargs: Dict[str, Any] = dict(iterable_match_keys={"root[*]['items']": "sku"}, ignore_order=True,
                                      cutoff_intersection_for_pairs=1)
        serial = DeepDiff(t1, t2, **kwargs)
        assert len(serial["values_changed"]) == 12
        parallel = DeepDiff(t1, t2, multiprocessing=True, multiprocessing_workers=4,
                            multiprocessing_threshold=0, **kwargs)
        assert parallel == serial
