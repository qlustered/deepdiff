import pytest
from deepdiff import DeepDiff, Delta
from deepdiff.path import _path_to_elements, GET, GETATTR, extract, parse_path, stringify_path, _add_to_elements


@pytest.mark.parametrize('test_num, path, expected', [
    (1, "root[4]['b'][3]", [(4, GET), ('b', GET), (3, GET)]),
    (2, "root[4].b[3]", [(4, GET), ('b', GETATTR), (3, GET)]),
    (3, "root[4].b['a3']", [(4, GET), ('b', GETATTR), ('a3', GET)]),
    (4, "root[4.3].b['a3']", [(4.3, GET), ('b', GETATTR), ('a3', GET)]),
    (5, "root.a.b", [('a', GETATTR), ('b', GETATTR)]),
    (6, "root.hello", [('hello', GETATTR)]),
    (7, "root['h']", [('h', GET)]),
    (8, "root['a\rb']", [('a\rb', GET)]),
    (9, "root['a\\rb']", [('a\\rb', GET)]),
    (10, "root", []),
    (11, ((4, GET), ('b', GET)), ((4, GET), ('b', GET))),
])
def test_path_to_elements(test_num, path, expected):
    result = _path_to_elements(path, root_element=None)
    assert tuple(expected) == result, f"test_path_to_elements #{test_num} failed"
    if isinstance(path, str):
        path_again = stringify_path(path=result)
        assert path == path_again, f"test_path_to_elements #{test_num} failed"


@pytest.mark.parametrize('obj, path, expected', [
    ({1: [2, 3], 2: [4, 5]},
     "root[2][1]",
     5),
    ({1: [{'2': 'b'}, 3], 2: {4, 5}},
     "root[1][0]['2']",
     'b'
     ),
    ({'test [a]': 'b'},
     "root['test [a]']",
     'b'
     ),
    ({"a']['b']['c": 1},
     """root["a']['b']['c"]""",
     1
     ),
])
def test_get_item(obj, path, expected):
    result = extract(obj, path)
    assert expected == result


def test_parse_path():
    result = parse_path("root[1][2]['age']")
    assert [1, 2, 'age'] == result
    result2 = parse_path("root[1][2]['age']", include_actions=True)
    assert [{'element': 1, 'action': 'GET'}, {'element': 2, 'action': 'GET'}, {'element': 'age', 'action': 'GET'}] == result2
    result3 = parse_path("root['joe'].age")
    assert ['joe', 'age'] == result3
    result4 = parse_path("root['joe'].age", include_actions=True)
    assert [{'element': 'joe', 'action': 'GET'}, {'element': 'age', 'action': 'GETATTR'}] == result4


@pytest.mark.parametrize('test_num, elem, inside, expected', [
    (
        1,
        "'hello'",
        None,
        [('hello', GET)],
    ),
    (
        2,
        "'a\rb'",
        None,
        [('a\rb', GET)],
    ),
])
def test__add_to_elements(test_num, elem, inside, expected):
    elements = []
    _add_to_elements(elements, elem, inside)
    assert expected == elements


@pytest.mark.parametrize('key', [
    b'',
    b'foo',
    b"has'quote",
    b'has"quote',
    b"has'both\"quotes",
    b'back\\slash',
    b'ending\\',
    b'ending\\\\',
    b"slash\\'and\"quotes",
    b'\xff\x00',
    b'bracket]dot.',
])
@pytest.mark.parametrize('change', ['added', 'removed', 'changed'])
def test_bytes_key_paths(key, change):
    old_items = {'same': 0}
    new_items = {'same': 0}
    if change != 'added':
        old_items[key] = 1
    if change != 'removed':
        new_items[key] = 2
    before = {'items': [old_items]}
    after = {'items': [new_items]}
    path = f"root['items'][0][{key!r}]"

    diff = DeepDiff(before, after)
    report_type = 'values_changed' if change == 'changed' else f'dictionary_item_{change}'
    assert list(diff) == [report_type]
    assert list(diff[report_type]) == [path]
    assert parse_path(path) == ['items', 0, key]
    assert stringify_path(_path_to_elements(path, root_element=None)) == path
    assert extract(before if change == 'removed' else after, path) == (1 if change == 'removed' else 2)

    delta = Delta(diff, bidirectional=True, raise_errors=True)
    assert before + delta == after
    assert after - delta == before


@pytest.mark.parametrize('key', [
    "b'foo'",
    'b"foo"',
    r"b'back\slash'",
    r'back\slash',
    '*',
    '**',
])
def test_string_key_path_round_trip(key):
    before = {key: 1}
    after = {key: 2}
    diff = DeepDiff(before, after)
    path, = diff['values_changed']
    assert parse_path(path) == [key]
    assert extract(after, path) == 2
    assert before + Delta(diff, raise_errors=True) == after
