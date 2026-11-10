from copy import deepcopy

import json
import pytest

from deepdiff import DeepDiff
from deepdiff.json_diff import (
    CollectionStrategy,
    CollectionStrategyError,
    DeepJSONDiff,
    DuplicateIdentityError,
    DuplicateIdentityPolicy,
    IdentityExtractionError,
    MissingIdentityPolicy,
)


def test_existing_deepdiff_behavior_is_unchanged():
    result = DeepDiff([{"id": 1}, {"id": 2}], [{"id": 2}, {"id": 1}])
    assert result
    assert "values_changed" in result


def test_identity_matching_ignores_reordering_and_reports_real_changes():
    left = {"users": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]}
    right = {"users": [{"id": 2, "name": "B2"}, {"id": 3, "name": "C"}]}
    result = DeepJSONDiff(
        left,
        right,
        collection_strategies=[CollectionStrategy(path="$.users", match_by=("id",))],
    )
    assert set(result) == {
        "dictionary_item_added",
        "dictionary_item_removed",
        "values_changed",
    }
    # Identity-matched changes must point at the encoded identity labels.
    assert result["values_changed"] == {
        "root['users']['[[\"int\",2]]']['name']": {"new_value": "B2", "old_value": "B"}
    }
    assert set(result["dictionary_item_added"]) == {"root['users']['[[\"int\",3]]']"}
    assert set(result["dictionary_item_removed"]) == {"root['users']['[[\"int\",1]]']"}


def test_nested_wildcards_match_exactly_one_level():
    left = {"accounts": [{"users": [{"id": 1}, {"id": 2}]}]}
    right = {"accounts": [{"users": [{"id": 2}, {"id": 1}]}]}
    assert not DeepJSONDiff(
        left,
        right,
        collection_strategies=[
            CollectionStrategy(path="$.accounts[*].users", match_by=("id",))
        ],
    )

    deeper_left = {"accounts": [{"nested": [{"users": [{"id": 1}, {"id": 2}]}]}]}
    deeper_right = {"accounts": [{"nested": [{"users": [{"id": 2}, {"id": 1}]}]}]}
    assert DeepJSONDiff(
        deeper_left,
        deeper_right,
        collection_strategies=[
            CollectionStrategy(path="$.accounts[*].users", match_by=("id",))
        ],
    )


def test_wildcards_only_match_their_own_path_level():
    result = DeepJSONDiff(
        {"a": {"x": [1, 2]}, "b": [[1], [2]]},
        {"a": {"x": [2, 1]}, "b": [[2], [1]]},
        collection_strategies=[
            CollectionStrategy(path="$.a[*]", name="array-wild"),
            CollectionStrategy(path="$.b.*", name="key-wild"),
        ],
    )
    assert result
    assert result.get_strategy_stats() == {"left": {}, "right": {}}


def test_quoted_key_selector_is_round_trippable_with_stats_path():
    result = DeepJSONDiff(
        {"a-b": [{"id": 2}, {"id": 1}]},
        {"a-b": [{"id": 1}, {"id": 2}]},
        collection_strategies=[
            CollectionStrategy(path="$['a-b']", match_by=("id",), name="hyphen")
        ],
    )
    assert not result
    assert result.get_strategy_stats()["left"]["$['a-b']"]["strategy"] == "hyphen"


def test_quoted_key_selector_supports_escaped_quotes():
    result = DeepJSONDiff(
        {"it's": [{"id": 2}, {"id": 1}]},
        {"it's": [{"id": 1}, {"id": 2}]},
        collection_strategies=[
            CollectionStrategy(path=r"$['it\'s']", match_by=("id",), name="quoted")
        ],
    )
    assert not result
    assert result.get_strategy_stats()["left"]["$[\"it's\"]"]["strategy"] == "quoted"


def test_root_and_numeric_index_patterns_are_supported():
    assert not DeepJSONDiff(
        [{"id": 2}, {"id": 1}],
        [{"id": 1}, {"id": 2}],
        collection_strategies=[CollectionStrategy(path="$", match_by=("id",))],
    )
    assert not DeepJSONDiff(
        {"groups": [{"items": [{"id": 2}, {"id": 1}]}]},
        {"groups": [{"items": [{"id": 1}, {"id": 2}]}]},
        collection_strategies=[
            CollectionStrategy(path="$.groups[0].items", match_by=("id",))
        ],
    )


def test_composite_nested_identity_is_collision_safe():
    left = {
        "items": [
            {"first": "a|str:b", "second": "", "value": 1},
            {"first": "a", "second": "b", "value": 2},
        ]
    }
    right = {"items": list(reversed(left["items"]))}
    assert not DeepJSONDiff(
        left,
        right,
        collection_strategies=[
            CollectionStrategy(path="$.items", match_by=("first", "second"))
        ],
    )


@pytest.mark.parametrize("identity", [None, False, True, 1, 1.5, "1"])
def test_identity_scalar_types_are_supported(identity):
    result = DeepJSONDiff(
        {"items": [{"id": identity}]},
        {"items": [{"id": identity}]},
        collection_strategies=[CollectionStrategy(path="$.items", match_by=("id",))],
    )
    assert not result


def test_ignore_numeric_type_changes_does_not_merge_type_distinct_identities():
    left = {"items": [{"id": 1, "v": 1}, {"id": 5, "v": 2}, {"id": 9, "v": 3}]}
    right = {"items": [{"id": 1.0, "v": 1}, {"id": 5, "v": 2}, {"id": 9, "v": 3}]}
    result = DeepJSONDiff(
        left,
        right,
        collection_strategies=[CollectionStrategy(path="$.items", match_by=("id",))],
        ignore_numeric_type_changes=True,
    )
    # Identity labels are type-preserving strings; forwarded numeric options
    # cannot merge them, so 1 and 1.0 stay separate records.
    assert set(result["dictionary_item_added"]) == {"root['items']['[[\"float\",1.0]]']"}
    assert set(result["dictionary_item_removed"]) == {"root['items']['[[\"int\",1]]']"}


@pytest.mark.parametrize("identity", [{"nested": 1}, [1], float("nan"), float("inf")])
def test_invalid_identity_values_are_rejected(identity):
    with pytest.raises(IdentityExtractionError):
        DeepJSONDiff(
            {"items": [{"id": identity}]},
            {"items": []},
            collection_strategies=[
                CollectionStrategy(path="$.items", match_by=("id",))
            ],
        )


def test_identity_is_extracted_before_excluded_fields_are_removed():
    left = {"items": [{"id": 1, "value": "same"}]}
    right = {"items": [{"id": 1, "value": "same"}]}
    result = DeepJSONDiff(
        left,
        right,
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                match_by=("id",),
                exclude_fields=("id",),
            )
        ],
    )
    assert not result
    assert "deepdiff_fallback" not in result.canonical_t1["items"]


def test_mutating_filter_and_normalizer_do_not_mutate_inputs():
    left = {"items": [{"id": 1, "active": True, "region": "IN"}]}
    right = {"items": [{"id": 1, "active": True, "region": "in"}]}
    original_left = deepcopy(left)
    original_right = deepcopy(right)

    def filter_func(item):
        item["filter_seen"] = True
        return item["active"]

    def normalize(item):
        item["region"] = item["region"].lower()
        item.pop("filter_seen", None)
        return item

    result = DeepJSONDiff(
        left,
        right,
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                match_by=("id",),
                filter_func=filter_func,
                normalizers=(normalize,),
            )
        ],
    )
    assert not result
    assert left == original_left
    assert right == original_right


def test_filter_drops_items_and_reports_stats():
    result = DeepJSONDiff(
        {"items": [{"id": 1, "active": True}, {"id": 2, "active": False}]},
        {"items": [{"id": 1, "active": True}, {"id": 9, "active": False}]},
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                match_by=("id",),
                filter_func=lambda item: item.get("active", True),
            )
        ],
    )
    assert not result
    stats = result.get_strategy_stats()
    assert stats["left"]["$.items"]["filtered"] == 1
    assert stats["right"]["$.items"]["filtered"] == 1


def test_sort_by_handles_finite_and_non_finite_numbers_without_type_errors():
    values = [
        {"rank": float("inf")},
        {"rank": 1},
        {"rank": float("-inf")},
        {"rank": float("nan")},
        {"rank": 1.5},
    ]
    # JSON round-trips keep each side's nan objects distinct, so DeepDiff
    # cannot short-circuit the nan comparison by object identity.
    left_items = json.loads(json.dumps(values))
    right_items = json.loads(json.dumps(list(reversed(values))))
    result = DeepJSONDiff(
        {"items": left_items},
        {"items": right_items},
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("rank",))],
        ignore_nan_inequality=True,
    )
    assert not result


def test_sort_by_is_type_stable_for_int_and_float():
    result = DeepJSONDiff(
        {"items": [{"rank": 1.0}, {"rank": 1}]},
        {"items": [{"rank": 1}, {"rank": 1.0}]},
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("rank",))],
    )
    assert not result
    assert isinstance(result.canonical_t1["items"][0]["rank"], int)
    assert isinstance(result.canonical_t1["items"][1]["rank"], float)


def test_sort_by_orders_missing_none_bool_and_string_values():
    values = [{"rank": None}, {"rank": True}, {"rank": 5}, {"rank": "z"}, {}]
    result = DeepJSONDiff(
        {"items": values},
        {"items": list(reversed(values))},
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("rank",))],
    )
    assert not result


def test_sort_by_extracts_through_lists_and_treats_bad_paths_as_missing():
    result = DeepJSONDiff(
        {"items": [[1, "a"], [0, "b"]]},
        {"items": [[0, "b"], [1, "a"]]},
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("0",))],
    )
    assert not result

    # Out-of-range indexes and paths through scalars become stable missing keys.
    assert DeepJSONDiff(
        {"items": [[1], [2]]},
        {"items": [[2], [1]]},
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("5",))],
    )
    assert DeepJSONDiff(
        {"items": [{"id": 1}, {"id": 2}]},
        {"items": [{"id": 2}, {"id": 1}]},
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("id.sub",))],
    )


def test_sort_by_supports_json_lists_and_string_keyed_mappings():
    left = {
        "items": [
            {"rank": {"b": 2, "a": 1}},
            {"rank": [2, 1]},
            {"rank": [1, 2]},
        ]
    }
    right = {"items": list(reversed(left["items"]))}
    assert not DeepJSONDiff(
        left,
        right,
        collection_strategies=[CollectionStrategy(path="$.items", sort_by=("rank",))],
    )


@pytest.mark.parametrize("value", [{1: "bad"}, (1, 2), {1, 2}, object()])
def test_sort_by_rejects_non_json_sort_keys(value):
    with pytest.raises(CollectionStrategyError, match="sort key"):
        DeepJSONDiff(
            {"items": [{"rank": value}]},
            {"items": [{"rank": value}]},
            collection_strategies=[
                CollectionStrategy(path="$.items", sort_by=("rank",))
            ],
        )


def test_compare_as_set_is_type_stable_and_preserves_duplicates():
    result = DeepJSONDiff(
        {"items": [1, 1.0, 1]},
        {"items": [1.0, 1, 1]},
        collection_strategies=[
            CollectionStrategy(path="$.items", compare_as_set=True)
        ],
    )
    assert not result


def test_compare_as_set_reports_count_changes():
    result = DeepJSONDiff(
        {"items": [1, 2, 3]},
        {"items": [1, 3]},
        collection_strategies=[
            CollectionStrategy(path="$.items", compare_as_set=True)
        ],
    )
    assert result["iterable_item_removed"] == {"root['items'][1]": 2}


@pytest.mark.parametrize(
    "value",
    [
        {"id": 1},
        [1],
        (1,),
        {1},
        frozenset({1}),
        b"x",
        bytearray(b"x"),
        object(),
        float("nan"),
        float("inf"),
    ],
)
def test_compare_as_set_accepts_only_finite_json_scalars(value):
    with pytest.raises(CollectionStrategyError, match="finite JSON scalar"):
        DeepJSONDiff(
            {"items": [value]},
            {"items": [value]},
            collection_strategies=[
                CollectionStrategy(path="$.items", compare_as_set=True)
            ],
        )


def test_missing_identity_policies_and_side_separated_stats():
    result = DeepJSONDiff(
        {"items": [{"id": 1}, {"name": "left"}]},
        {"items": [{"name": "right"}, {"id": 1}]},
        collection_strategies=[
            CollectionStrategy(path="$.items", match_by=("id",))
        ],
    )
    stats = result.get_strategy_stats()
    assert stats["left"]["$.items"]["missing_identity"] == 1
    assert stats["right"]["$.items"]["missing_identity"] == 1

    with pytest.raises(IdentityExtractionError, match="right input"):
        DeepJSONDiff(
            {"items": []},
            {"items": [{"name": "right"}]},
            collection_strategies=[
                CollectionStrategy(
                    path="$.items",
                    match_by=("id",),
                    missing_identity=MissingIdentityPolicy.ERROR,
                )
            ],
        )

    excluded = DeepJSONDiff(
        {"items": [{"id": 1}, {"name": "left"}]},
        {"items": [{"id": 1}, {"name": "right"}]},
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                match_by=("id",),
                missing_identity="exclude",
            )
        ],
    )
    assert not excluded


def test_fallback_records_are_compared():
    # Regression: the fallback key must not start with "__", because DeepDiff
    # skips such keys by default (ignore_private_variables=True).
    result = DeepJSONDiff(
        {"items": [{"name": "a"}]},
        {"items": [{"name": "b"}]},
        collection_strategies=[CollectionStrategy(path="$.items", match_by=("id",))],
    )
    assert result["values_changed"] == {
        "root['items']['deepdiff_fallback'][0]['name']": {"new_value": "b", "old_value": "a"}
    }


def test_duplicate_identity_policies_and_stats():
    with pytest.raises(DuplicateIdentityError, match="left input"):
        DeepJSONDiff(
            {"items": [{"id": 1}, {"id": 1}]},
            {"items": []},
            collection_strategies=[
                CollectionStrategy(path="$.items", match_by=("id",))
            ],
        )

    result = DeepJSONDiff(
        {"items": [{"id": 1, "v": 2}, {"id": 1, "v": 1}]},
        {"items": [{"id": 1, "v": 1}, {"id": 1, "v": 2}]},
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                match_by=("id",),
                sort_by=("v",),
                duplicates=DuplicateIdentityPolicy.GROUP,
            )
        ],
    )
    assert not result
    assert result.get_strategy_stats()["left"]["$.items"]["duplicate_groups"] == 1


def test_group_policy_reports_count_changes_per_record():
    result = DeepJSONDiff(
        {"items": [{"id": 1, "v": 1}, {"id": 1, "v": 2}]},
        {"items": [{"id": 1, "v": 1}]},
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                match_by=("id",),
                duplicates=DuplicateIdentityPolicy.GROUP,
            )
        ],
    )
    # A duplicate becoming a single record is an item removal, not a
    # list-to-dict type change.
    assert set(result) == {"iterable_item_removed"}
    assert result["iterable_item_removed"] == {
        "root['items']['[[\"int\",1]]'][1]": {"id": 1, "v": 2}
    }


def test_nested_stats_do_not_merge_different_logical_parents_across_sides():
    left = {
        "orders": [
            {"id": "A", "items": [{"sku": 1}, {"sku": 2}]},
            {"id": "B", "items": [{"sku": 3}]},
        ]
    }
    right = {"orders": list(reversed(left["orders"]))}
    result = DeepJSONDiff(
        left,
        right,
        collection_strategies=[
            CollectionStrategy(path="$.orders", match_by=("id",)),
            CollectionStrategy(path="$.orders[*].items", match_by=("sku",)),
        ],
    )
    assert not result
    stats = result.get_strategy_stats()
    assert stats["left"]["$.orders[0].items"]["items"] == 2
    assert stats["right"]["$.orders[0].items"]["items"] == 1


@pytest.mark.parametrize(
    "option",
    [
        "include_paths",
        "exclude_paths",
        "exclude_regex_paths",
        "ignore_order_func",
        "iterable_compare_func",
        "custom_operators",
        "include_obj_callback",
        "include_obj_callback_strict",
    ],
)
def test_path_sensitive_deepdiff_options_are_rejected(option):
    with pytest.raises(CollectionStrategyError, match="path-sensitive"):
        DeepJSONDiff({}, {}, **{option: object()})


def test_unrelated_deepdiff_kwargs_are_forwarded():
    result = DeepJSONDiff({"value": 1}, {"value": 1.0}, ignore_numeric_type_changes=True)
    assert not result

    # ignore_order is forwarded: reordered lists produce no diff.
    tree = DeepJSONDiff(
        {"items": [1, 2]},
        {"items": [2, 1]},
        ignore_order=True,
        view="tree",
    )
    assert not tree


@pytest.mark.parametrize(
    "kwargs",
    [
        {"path": "users"},
        {"path": "$."},
        {"path": "$.users["},
        {"path": "$.users[-1]"},
        {"path": "$.users[abc]"},
        {"path": "$['unterminated]"},
        {"path": "$['a', 'b']"},
        {"path": "$['a' (1) 'b']"},
        {"path": "$[²]"},
        {"path": "$users"},
        {"path": "$.users", "match_by": "id"},
        {"path": "$.users", "sort_by": ("",)},
        {"path": "$.users", "exclude_fields": ("",)},
        {"path": "$.users", "exclude_fields": ("meta.generatedAt",)},
        {"path": "$.users", "normalizers": "normalize"},
        {"path": "$.users", "normalizers": (None,)},
        {"path": "$.users", "filter_func": "filter"},
        {"path": "$.users", "priority": True},
        {"path": "$.users", "name": ""},
        {"path": "$.users", "missing_identity": "unknown"},
        {"path": "$.users", "duplicates": "unknown"},
        {"path": "$.users", "compare_as_set": True, "sort_by": ("id",)},
        {"path": "$.users", "compare_as_set": True, "match_by": ("id",)},
        {"path": "$.users", "compare_as_set": 1},
    ],
)
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(CollectionStrategyError):
        CollectionStrategy(**kwargs)


def test_strategy_resolution_precedence_and_ambiguity():
    result = DeepJSONDiff(
        {"a": {"users": [{"id": 2}, {"id": 1}]}},
        {"a": {"users": [{"id": 1}, {"id": 2}]}},
        collection_strategies=[
            CollectionStrategy(path="$.*.users", sort_by=("id",), priority=1),
            CollectionStrategy(path="$.a.users", priority=0),
        ],
    )
    assert not result

    with pytest.raises(CollectionStrategyError, match="ambiguous collection strategies"):
        DeepJSONDiff(
            {"a": {"users": []}},
            {"a": {"users": []}},
            collection_strategies=[
                CollectionStrategy(path="$.*.users"),
                CollectionStrategy(path="$.a.*"),
            ],
        )


def test_duplicate_strategy_and_non_strategy_entries_are_rejected():
    strategy = CollectionStrategy(path="$.users")
    with pytest.raises(CollectionStrategyError):
        DeepJSONDiff({}, {}, collection_strategies=[strategy, strategy])
    with pytest.raises(CollectionStrategyError):
        DeepJSONDiff({}, {}, collection_strategies=[object()])


def test_mapping_facade_and_serialization_delegation():
    result = DeepJSONDiff({"value": 1}, {"value": 2})
    assert list(result.keys()) == ["values_changed"]
    assert list(result.items())
    assert result.get("values_changed") is not None
    assert len(result) == 1
    assert "values_changed" in repr(result)
    assert result.to_dict() == result.diff.to_dict()
    assert result.to_json() == result.diff.to_json()
