from deepdiff import DeepDiff
from deepdiff.helper import COLORED_VIEW, COLORED_COMPACT_VIEW
from deepdiff.colored_view import RED, GREEN, RESET


def test_colored_view_basic():
    t1 = {
        "name": "John",
        "age": 30,
        "gender": "male",
        "scores": [1, 2, 3],
        "address": {
            "city": "New York",
            "zip": "10001",
        },
    }

    t2 = {
        "name": "John",
        "age": 31,  # Changed
        "scores": [1, 2, 4],  # Changed
        "address": {
            "city": "Boston",  # Changed
            "zip": "10001",
        },
        "team": "abc",  # Added
    }

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''{{
  "name": "John",
  "age": {RED}30{RESET} -> {GREEN}31{RESET},
  "scores": [
    1,
    2,
    {RED}3{RESET} -> {GREEN}4{RESET}
  ],
  "address": {{
    "city": {RED}"New York"{RESET} -> {GREEN}"Boston"{RESET},
    "zip": "10001"
  }},
  {GREEN}"team": {GREEN}"abc"{RESET}{RESET},
  {RED}"gender": {RED}"male"{RESET}{RESET}
}}'''
    assert result == expected


def test_colored_view_nested_changes():
    t1 = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": True
                }
            }
        }
    }

    t2 = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": False
                }
            }
        }
    }

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''{{
  "level1": {{
    "level2": {{
      "level3": {{
        "level4": {RED}true{RESET} -> {GREEN}false{RESET}
      }}
    }}
  }}
}}'''
    assert result == expected


def test_colored_view_list_changes():
    t1 = [1, 2, 3, 4]
    t2 = [1, 5, 3, 6]

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''[
  1,
  {RED}2{RESET} -> {GREEN}5{RESET},
  3,
  {RED}4{RESET} -> {GREEN}6{RESET}
]'''
    assert result == expected


def test_colored_view_list_deletions():
    t1 = [1, 2, 3, 4, 5, 6]
    t2 = [2, 4]

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''[
  {RED}1{RESET},
  2,
  {RED}3{RESET},
  4,
  {RED}5{RESET},
  {RED}6{RESET}
]'''
    assert result == expected


def test_colored_view_list_all_removed():
    """Test that removing all items from a list shows them in colored view."""
    t1 = [1, 2, 3]
    t2 = []

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''[
  {RED}1{RESET},
  {RED}2{RESET},
  {RED}3{RESET}
]'''
    assert result == expected


def test_colored_view_list_additions():
    t1 = [2, 4]
    t2 = [1, 2, 3, 4, 5]

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''[
  {GREEN}1{RESET},
  2,
  {GREEN}3{RESET},
  4,
  {GREEN}5{RESET}
]'''
    assert result == expected


def test_colored_view_list_changes_deletions():
    t1 = [1, 5, 7, 3, 6]
    t2 = [1, 2, 3, 4]

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''[
  1,
  {RED}5{RESET} -> {GREEN}2{RESET},
  {RED}7{RESET},
  3,
  {RED}6{RESET} -> {GREEN}4{RESET}
]'''
    assert result == expected


def test_colored_view_list_changes_additions():
    t1 = [1, 2, 3, 4]
    t2 = [1, 5, 7, 3, 6]

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = f'''[
  1,
  {RED}2{RESET} -> {GREEN}5{RESET},
  {GREEN}7{RESET},
  3,
  {RED}4{RESET} -> {GREEN}6{RESET}
]'''
    assert result == expected


def test_colored_view_list_no_changes_with_ignore_order():
    t1 = [1, 2, 3]
    t2 = [3, 2, 1]

    diff = DeepDiff(t1, t2, view=COLORED_VIEW, ignore_order=True)
    result = str(diff)

    expected = '''[
  3,
  2,
  1
]'''
    assert result == expected


def test_colored_view_list_with_ignore_order():
    t1 = {
        "hobbies": [
            "reading",
            "hiking"
        ]
    }

    t2 = {
        "hobbies": [
            "hiking",
            "painting",
            "coding"
        ]
    }

    diff = DeepDiff(t1, t2, view=COLORED_VIEW, ignore_order=True)
    result = str(diff)

    expected = f'''{{
  "hobbies": [
    {RED}"reading"{RESET},
    "hiking",
    {GREEN}"painting"{RESET},
    {GREEN}"coding"{RESET}
  ]
}}'''
    assert result == expected


def test_colored_view_no_changes():
    t1 = {"a": 1, "b": 2}
    t2 = {"a": 1, "b": 2}

    diff = DeepDiff(t1, t2, view=COLORED_VIEW)
    result = str(diff)

    expected = '''{
  "a": 1,
  "b": 2
}'''
    assert result == expected


def test_compact_view_basic():
    t1 = {
        "name": "John",
        "age": 30,
        "gender": "male",
        "scores": [1, 2, 3],
        "address": {
            "city": "New York",
            "zip": "10001",
            "details": {
                "type": "apartment",
                "floor": 5
            }
        },
        "hobbies": ["reading", {"sport": "tennis", "level": "advanced"}]
    }

    t2 = {
        "name": "John",
        "age": 31,  # Changed
        "scores": [1, 2, 4],  # Changed
        "address": {
            "city": "Boston",  # Changed
            "zip": "10001",
            "details": {
                "type": "apartment",
                "floor": 5
            }
        },
        "team": "abc",  # Added
        "hobbies": ["reading", {"sport": "tennis", "level": "advanced"}]
    }

    diff = DeepDiff(t1, t2, view=COLORED_COMPACT_VIEW)
    result = str(diff)

    expected = f'''{{
  "name": "John",
  "age": {RED}30{RESET} -> {GREEN}31{RESET},
  "scores": [
    1,
    2,
    {RED}3{RESET} -> {GREEN}4{RESET}
  ],
  "address": {{
    "city": {RED}"New York"{RESET} -> {GREEN}"Boston"{RESET},
    "zip": "10001",
    "details": {{...}}
  }},
  {GREEN}"team": {GREEN}"abc"{RESET}{RESET},
  "hobbies": [...],
  {RED}"gender": {RED}"male"{RESET}{RESET}
}}'''
    assert result == expected


def test_compact_view_nested_changes():
    t1 = {
        "level1": {
            "unchanged1": {
                "deep1": True,
                "deep2": [1, 2, 3]
            },
            "level2": {
                "a": 1,
                "b": "test",
                "c": [1, 2, 3],
                "d": {"x": 1, "y": 2}
            },
            "unchanged2": [1, 2, {"a": 1}]
        }
    }

    t2 = {
        "level1": {
            "unchanged1": {
                "deep1": True,
                "deep2": [1, 2, 3]
            },
            "level2": {
                "a": 2,  # Changed
                "b": "test",
                "c": [1, 2, 4],  # Changed
                "d": {"x": 1, "y": 3}  # Changed
            },
            "unchanged2": [1, 2, {"a": 1}]
        }
    }

    diff = DeepDiff(t1, t2, view=COLORED_COMPACT_VIEW)
    result = str(diff)

    expected = f'''{{
  "level1": {{
    "unchanged1": {{...}},
    "level2": {{
      "a": {RED}1{RESET} -> {GREEN}2{RESET},
      "b": "test",
      "c": [
        1,
        2,
        {RED}3{RESET} -> {GREEN}4{RESET}
      ],
      "d": {{
        "x": 1,
        "y": {RED}2{RESET} -> {GREEN}3{RESET}
      }}
    }},
    "unchanged2": [...]
  }}
}}'''
    assert result == expected


def test_compact_view_no_changes():
    # Test with dict
    t1 = {"a": 1, "b": [1, 2], "c": {"x": True}}
    t2 = {"a": 1, "b": [1, 2], "c": {"x": True}}
    diff = DeepDiff(t1, t2, view=COLORED_COMPACT_VIEW)
    assert str(diff) == "{...}"

    # Test with list
    t1 = [1, {"a": 1}, [1, 2]]
    t2 = [1, {"a": 1}, [1, 2]]
    diff = DeepDiff(t1, t2, view=COLORED_COMPACT_VIEW)
    assert str(diff) == "[...]"


def test_compact_view_list_changes():
    t1 = [1, {"a": 1, "b": {"x": 1, "y": 2}}, [1, 2, {"z": 3}]]
    t2 = [1, {"a": 2, "b": {"x": 1, "y": 2}}, [1, 2, {"z": 3}]]

    diff = DeepDiff(t1, t2, view=COLORED_COMPACT_VIEW)
    result = str(diff)

    expected = f'''[
  1,
  {{
    "a": {RED}1{RESET} -> {GREEN}2{RESET},
    "b": {{...}}
  }},
  [...]
]'''
    assert result == expected


def test_compact_view_primitive_siblings():
    t1 = {
        "changed": 1,
        "str_sibling": "hello",
        "int_sibling": 42,
        "bool_sibling": True,
        "nested_sibling": {"a": 1, "b": 2}
    }

    t2 = {
        "changed": 2,
        "str_sibling": "hello",
        "int_sibling": 42,
        "bool_sibling": True,
        "nested_sibling": {"a": 1, "b": 2}
    }

    diff = DeepDiff(t1, t2, view=COLORED_COMPACT_VIEW)
    result = str(diff)

    expected = f'''{{
  "changed": {RED}1{RESET} -> {GREEN}2{RESET},
  "str_sibling": "hello",
  "int_sibling": 42,
  "bool_sibling": true,
  "nested_sibling": {{...}}
}}'''
    assert result == expected


def test_colored_view_bool_evaluation():
    # Test COLORED_VIEW
    # Scenario 1: No differences
    t1_no_diff = {"a": 1, "b": 2}
    t2_no_diff = {"a": 1, "b": 2}
    diff_no_diff_colored = DeepDiff(t1_no_diff, t2_no_diff, view=COLORED_VIEW)
    assert not bool(diff_no_diff_colored), "bool(diff) should be False when no diffs (colored view)"

    # Scenario 2: With differences
    t1_with_diff = {"a": 1, "b": 2}
    t2_with_diff = {"a": 1, "b": 3}
    diff_with_diff_colored = DeepDiff(t1_with_diff, t2_with_diff, view=COLORED_VIEW)
    assert bool(diff_with_diff_colored), "bool(diff) should be True when diffs exist (colored view)"

    # Test COLORED_COMPACT_VIEW
    # Scenario 1: No differences
    diff_no_diff_compact = DeepDiff(t1_no_diff, t2_no_diff, view=COLORED_COMPACT_VIEW)
    assert not bool(diff_no_diff_compact), "bool(diff) should be False when no diffs (compact view)"

    # Scenario 2: With differences
    diff_with_diff_compact = DeepDiff(t1_with_diff, t2_with_diff, view=COLORED_COMPACT_VIEW)
    assert bool(diff_with_diff_compact), "bool(diff) should be True when diffs exist (compact view)"
