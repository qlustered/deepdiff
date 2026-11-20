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


@pytest.mark.parametrize('key', [
    "a'\"a",
    "a\"'a",
    "a'\"\\",
    "a'\"\\r\\n",
    "a'\"\r\n",
    "a'\"\U0001d1c0",
    "a'][\"b.c",
])
@pytest.mark.parametrize('change', ['added', 'removed', 'changed'])
def test_string_key_with_both_quotes_round_trip(key, change):
    old = {'container': {'unchanged': 0}}
    new = {'container': {'unchanged': 0}}
    if change != 'added':
        old['container'][key] = 1
    if change != 'removed':
        new['container'][key] = 2
    diff = DeepDiff(old, new, threshold_to_diff_deeper=0)
    category = 'values_changed' if change == 'changed' else f'dictionary_item_{change}'
    path = next(iter(diff[category]))

    assert parse_path(path) == ['container', key]
    assert stringify_path([('container', GET), (key, GET)]) == path
    source = old if change == 'removed' else new
    assert extract(source, path) == source['container'][key]
    delta = Delta(diff, bidirectional=True, raise_errors=True)
    assert old + delta == new
    assert new - delta == old
    assert old == {'container': {'unchanged': 0, **({key: 1} if change != 'added' else {})}}
    assert new == {'container': {'unchanged': 0, **({key: 2} if change != 'removed' else {})}}


@pytest.mark.parametrize('key', [
    'plain', "only'quote", 'only"quote', r'back\slash', 'ending\\',
    "marker\U0001d1c0'quote", 'marker\U0001d1c0\U0001d1c0text', '*', '**',
])
def test_existing_string_key_path_round_trip(key):
    path = stringify_path([(key, GET)])
    assert parse_path(path) == [key]
    assert extract({key: 1}, path) == 1


@pytest.mark.parametrize('keys', [
    ['ending\\', "']"],
    ['"\\', ']'],
    ["'\\", '"]'],
    ["marker\U0001d1c0'quote", 'child'],
])
def test_existing_nested_string_key_path_round_trip(keys):
    path = stringify_path([(key, GET) for key in keys])
    assert parse_path(path) == keys
    assert extract({keys[0]: {keys[1]: 1}}, path) == 1


def test_escaped_string_key_followed_by_attribute():
    key = "a'\"a"
    path = stringify_path([(key, GET), ('age', GETATTR)])
    assert parse_path(path, include_actions=True) == [
        {'element': key, 'action': GET}, {'element': 'age', 'action': GETATTR},
    ]


def test_string_subclass_key_with_both_quotes_round_trip():
    class NamedString(str):
        def __repr__(self):
            return f'NamedString({str.__repr__(self)})'

        def __str__(self):
            return 'custom string representation'

    key = NamedString("a'\"a")
    old, new = {key: 1}, {key: 2}
    diff = DeepDiff(old, new)
    path = next(iter(diff['values_changed']))
    assert parse_path(path) == [key]
    assert extract(new, path) == 2
    delta = Delta(diff, bidirectional=True, raise_errors=True)
    assert old + delta == new
    assert new - delta == old


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
