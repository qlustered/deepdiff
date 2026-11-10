import pytest

from deepdiff.json_diff import (
    CollectionStrategy,
    CollectionStrategyError,
    DeepJSONDiff,
    DuplicateIdentityPolicy,
)


def test_sort_by_is_extracted_before_excluded_fields_are_removed():
    left = {
        "items": [
            {"id": "late", "rank": 2},
            {"id": "early", "rank": 1},
        ]
    }
    right = {
        "items": [
            {"id": "early", "rank": 1},
            {"id": "late", "rank": 2},
        ]
    }

    result = DeepJSONDiff(
        left,
        right,
        collection_strategies=[
            CollectionStrategy(
                path="$.items",
                sort_by=("rank",),
                exclude_fields=("rank",),
            )
        ],
    )

    assert not result
    assert all("rank" not in item for item in result.canonical_t1["items"])
    assert all("rank" not in item for item in result.canonical_t2["items"])


def test_duplicate_group_sort_key_is_extracted_before_exclusion():
    strategy = CollectionStrategy(
        path="$.items",
        match_by=("id",),
        sort_by=("version",),
        exclude_fields=("version",),
        duplicates=DuplicateIdentityPolicy.GROUP,
    )
    left = {
        "items": [
            {"id": 1, "version": 2, "value": "new"},
            {"id": 1, "version": 1, "value": "old"},
        ]
    }
    right = {"items": list(reversed(left["items"]))}

    result = DeepJSONDiff(left, right, collection_strategies=[strategy])

    assert not result


@pytest.mark.parametrize(
    "option",
    ["exclude_obj_callback", "exclude_obj_callback_strict"],
)
def test_path_sensitive_object_callbacks_are_rejected(option):
    with pytest.raises(CollectionStrategyError, match="path-sensitive"):
        DeepJSONDiff({}, {}, **{option: lambda *_args: False})
