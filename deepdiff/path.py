import re
import logging
from ast import literal_eval
from functools import lru_cache

logger = logging.getLogger(__name__)

GETATTR = 'GETATTR'
GET = 'GET'


class _WildcardToken:
    """Sentinel object for wildcard path tokens.

    Using a dedicated class (instead of plain strings) ensures that a literal
    dict key ``'*'`` (parsed from ``root['*']``) is never confused with the
    wildcard ``*`` (parsed from ``root[*]``).
    """
    def __init__(self, symbol):
        self._symbol = symbol

    def __repr__(self):
        return self._symbol

    def __eq__(self, other):
        return isinstance(other, _WildcardToken) and self._symbol == other._symbol

    def __hash__(self):
        return hash(('_WildcardToken', self._symbol))


SINGLE_WILDCARD = _WildcardToken('*')
MULTI_WILDCARD = _WildcardToken('**')


class PathExtractionError(ValueError):
    pass


class RootCanNotBeModified(ValueError):
    pass


def _add_to_elements(elements, elem, inside):
    # Ignore private items
    if not elem:
        return
    if not elem.startswith('__'):
        # Handle wildcard tokens (* and **) as-is.
        # Unquoted root[*] arrives as bare '*' which matches the string check.
        # Quoted root['*'] arrives as "'*'" which does NOT match, so it falls
        # through to literal_eval and becomes the plain string '*' — which is
        # distinct from the _WildcardToken sentinel and thus treated as a
        # literal dict key.
        if elem in ('*', '**'):
            action = GETATTR if inside == '.' else GET
            elements.append((SINGLE_WILDCARD if elem == '*' else MULTI_WILDCARD, action))
            return
        remove_quotes = False
        # Bytes literals need their backslash escapes decoded by literal_eval.
        if ('𝆺𝅥𝅯' in elem or '\\' in elem) and not elem.startswith(("b'", 'b"')):
            remove_quotes = True
        else:
            try:
                elem = literal_eval(elem)
                remove_quotes = False
            except (ValueError, SyntaxError):
                remove_quotes = True
        if remove_quotes and elem[0] == elem[-1] and elem[0] in {'"', "'"}:
            elem = elem[1: -1]
        action = GETATTR if inside == '.' else GET
        elements.append((elem, action))


DEFAULT_FIRST_ELEMENT = ('root', GETATTR)


@lru_cache(maxsize=1024 * 128)
def _path_to_elements(path, root_element=DEFAULT_FIRST_ELEMENT):
    """
    Given a path, it extracts the elements that form the path and their relevant most likely retrieval action.

        >>> from deepdiff import _path_to_elements
        >>> path = "root[4.3].b['a3']"
        >>> _path_to_elements(path, root_element=None)
        [(4.3, 'GET'), ('b', 'GETATTR'), ('a3', 'GET')]
    """
    if isinstance(path, (tuple, list)):
        return path
    elements = []
    if root_element:
        elements.append(root_element)
    elem = ''
    inside = False
    prev_char = None
    path = path[4:]  # removing "root from the beginning"
    brackets = []
    inside_quotes = False
    inside_bytes = False
    escaped = False
    quote_used = ''
    for char in path:
        if inside_bytes and escaped:
            elem += char
            escaped = False
        elif inside_bytes and char == '\\':
            elem += char
            escaped = True
        elif prev_char == '𝆺𝅥𝅯':
            elem += char
        elif char in {'"', "'"}:
            elem += char
            # If we are inside and the quote is not what we expected, the quote is not closing
            if not(inside_quotes and quote_used != char):
                inside_quotes = not inside_quotes
                if inside_quotes:
                    quote_used = char
                    inside_bytes = elem.startswith(("b'", 'b"'))
                else:
                    inside_bytes = False
                    _add_to_elements(elements, elem, inside)
                    elem = ''
                    quote_used = ''
        elif inside_quotes:
            elem += char
        elif char == '[':
            if inside == '.':
                _add_to_elements(elements, elem, inside)
                inside = '['
                elem = ''
            # we are already inside. The bracket is a part of the word.
            elif inside == '[':
                elem += char
            else:
                inside = '['
                brackets.append('[')
                elem = ''
        elif char == '.':
            if inside == '[':
                elem += char
            elif inside == '.':
                _add_to_elements(elements, elem, inside)
                elem = ''
            else:
                inside = '.'
                elem = ''
        elif char == ']':
            if brackets and brackets[-1] == '[':
                brackets.pop()
            if brackets:
                elem += char
            else:
                _add_to_elements(elements, elem, inside)
                elem = ''
                inside = False
        else:
            elem += char
        prev_char = char
    if elem:
        _add_to_elements(elements, elem, inside)
    return tuple(elements)


def _get_nested_obj(obj, elements, next_element=None):
    for (elem, action) in elements:
        check_elem(elem)
        if action == GET:
            obj = obj[elem]
        elif action == GETATTR:
            obj = getattr(obj, elem)
    return obj


def _guess_type(elements, elem, index, next_element):
    # If we are not at the last elements
    if index < len(elements) - 1:
        # We assume it is a nested dictionary not a nested list
        return {}
    if isinstance(next_element, int):
        return []
    return {}


def check_elem(elem):
    if isinstance(elem, str) and elem.startswith("__") and elem.endswith("__"):
        raise ValueError("traversing dunder attributes is not allowed")


def _get_nested_obj_and_force(obj, elements, next_element=None):
    prev_elem = None
    prev_action = None
    prev_obj = obj
    for index, (elem, action) in enumerate(elements):
        check_elem(elem)
        _prev_obj = obj
        if action == GET:
            try:
                obj = obj[elem]
                prev_obj = _prev_obj
            except KeyError:
                obj[elem] = _guess_type(elements, elem, index, next_element)
                obj = obj[elem]
                prev_obj = _prev_obj
            except IndexError:
                if isinstance(obj, list) and isinstance(elem, int) and elem >= len(obj):
                    obj.extend([None] * (elem - len(obj)))
                    obj.append(_guess_type(elements, elem, index, next_element))
                    obj = obj[-1]
                    prev_obj = _prev_obj
                elif isinstance(obj, list) and len(obj) == 0 and prev_elem:
                    # We ran into an empty list that should have been a dictionary
                    # We need to change it from an empty list to a dictionary
                    obj = {elem: _guess_type(elements, elem, index, next_element)}
                    if prev_action == GET:
                        prev_obj[prev_elem] = obj
                    else:
                        setattr(prev_obj, str(prev_elem), obj)
                    obj = obj[elem]
        elif action == GETATTR:
            obj = getattr(obj, elem)
            prev_obj = _prev_obj
        prev_elem = elem
        prev_action = action
    return obj


def extract(obj, path):
    """
    Get the item from obj based on path.

    Example:

        >>> from deepdiff import extract
        >>> obj = {1: [{'2': 'b'}, 3], 2: [4, 5]}
        >>> path = "root[1][0]['2']"
        >>> extract(obj, path)
        'b'

    Note that you can use extract in conjunction with DeepDiff results
    or even with the search and :ref:`deepsearch_label` modules. For example:

        >>> from deepdiff import grep
        >>> obj = {1: [{'2': 'b'}, 3], 2: [4, 5]}
        >>> result = obj | grep(5)
        >>> result
        {'matched_values': ['root[2][1]']}
        >>> result['matched_values'][0]
        'root[2][1]'
        >>> path = result['matched_values'][0]
        >>> extract(obj, path)
        5


    .. note::
        Note that even if DeepDiff tried gives you a path to an item in a set,
        there is no such thing in Python and hence you will get an error trying
        to extract that item from a set.
        If you want to be able to get items from sets, use the SetOrdered module
        to generate the sets.
        In fact Deepdiff uses SetOrdered as a dependency.

        >>> from deepdiff import grep, extract
        >>> obj = {"a", "b"}
        >>> obj | grep("b")
        Set item detected in the path.'set' objects do NOT support indexing. But DeepSearch will still report a path.
        {'matched_values': SetOrdered(['root[0]'])}
        >>> extract(obj, 'root[0]')
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
          File "deepdiff/deepdiff/path.py", line 126, in extract
            return _get_nested_obj(obj, elements)
          File "deepdiff/deepdiff/path.py", line 84, in _get_nested_obj
            obj = obj[elem]
        TypeError: 'set' object is not subscriptable
        >>> from orderly_set import SetOrdered
        >>> obj = SetOrdered(["a", "b"])
        >>> extract(obj, 'root[0]')
        'a'

    """
    elements = _path_to_elements(path, root_element=None)
    return _get_nested_obj(obj, elements)


def parse_path(path, root_element=DEFAULT_FIRST_ELEMENT, include_actions=False):
    """
    Parse a path to a format that is machine readable

    **Parameters**

    path : A string
    The path string such as "root[1][2]['age']"

    root_element: string, default='root'
        What the root is called in the path.

    include_actions: boolean, default=False
        If True, we return the action required to retrieve the item at each element of the path.  

    **Examples**

        >>> from deepdiff import parse_path
        >>> parse_path("root[1][2]['age']")
        [1, 2, 'age']
        >>> parse_path("root[1][2]['age']", include_actions=True)
        [{'element': 1, 'action': 'GET'}, {'element': 2, 'action': 'GET'}, {'element': 'age', 'action': 'GET'}]
        >>>
        >>> parse_path("root['joe'].age")
        ['joe', 'age']
        >>> parse_path("root['joe'].age", include_actions=True)
        [{'element': 'joe', 'action': 'GET'}, {'element': 'age', 'action': 'GETATTR'}]

    """

    result = _path_to_elements(path, root_element=root_element)
    result = iter(result)
    if root_element:
        next(result)  # We don't want the root item
    if include_actions is False:
        return [i[0] for i in result]
    return [{'element': i[0], 'action': i[1]} for i in result]


def stringify_element(param, quote_str=None):
    if isinstance(param, bytes):
        return repr(param)
    has_quote = "'" in param
    has_double_quote = '"' in param
    if has_quote and has_double_quote and not quote_str:
        new_param = []
        for char in param:
            if char in {'"', "'"}:
                new_param.append('𝆺𝅥𝅯')
            new_param.append(char)
        result = '"' + ''.join(new_param) + '"'
    elif has_quote:
        result = f'"{param}"'
    elif has_double_quote:
        result = f"'{param}'"
    else:
        result = param if quote_str is None else quote_str.format(param)
    return result


def stringify_path(path, root_element=DEFAULT_FIRST_ELEMENT, quote_str="'{}'"):
    """
    Gets the path as an string.

    For example [1, 2, 'age'] should become
    root[1][2]['age']
    """
    if not path:
        return root_element[0]
    result = [root_element[0]]
    has_actions = False
    try:
        if path[0][1] in {GET, GETATTR}:
            has_actions = True
    except (KeyError, IndexError, TypeError):
        pass
    if not has_actions:
        path = [(i, GET) for i in path]
        path[0] = (path[0][0], root_element[1])  # The action for the first element might be a GET or GETATTR. We update the action based on the root_element.
    for element, action in path:
        if isinstance(element, str) and action == GET:
            element = stringify_element(element, quote_str)
        if action == GET:
            result.append(f"[{element}]")
        else:
            result.append(f".{element}")
    return ''.join(result)


# Regex to detect wildcard segments in a raw path string.
# Matches [*], [**], .*, .** that are NOT inside quotes.
_WILDCARD_RE = re.compile(
    r'\[\*\*?\]'        # [*] or [**]
    r'|\.\*\*?(?=[.\[]|$)'  # .* or .** followed by . or [ or end of string
)


def path_has_wildcard(path):
    """Check if a path string contains wildcard segments (* or **)."""
    return bool(_WILDCARD_RE.search(path))


class GlobPathMatcher:
    """Pre-compiled matcher for a single glob pattern path.

    Parses a pattern like ``root['users'][*]['password']`` into segments
    and matches concrete path strings against it.

    ``*`` matches exactly one path segment (any key, index, or attribute).
    ``**`` matches zero or more path segments.
    """

    def __init__(self, pattern_path):
        self.original_pattern = pattern_path
        elements = _path_to_elements(pattern_path, root_element=('root', GETATTR))
        # Skip the root element for matching
        self._pattern = elements[1:]

    def match(self, path_string):
        """Return True if *path_string* matches this pattern exactly."""
        target = _path_to_elements(path_string, root_element=('root', GETATTR))[1:]
        return self._match_segments(target, 0, 0, {}, allow_extra_target=False)

    def match_or_is_ancestor(self, path_string):
        """Return True if *path_string* matches OR is an ancestor of a potential match.

        This is needed for ``include_paths``: we must not prune a path that
        could lead to a matching descendant.
        """
        target = _path_to_elements(path_string, root_element=('root', GETATTR))[1:]
        memo = {}
        return (self._match_segments(target, 0, 0, memo, allow_extra_target=False)
                or self._could_match_descendant(target, 0, 0, {}))

    def match_or_is_descendant(self, path_string):
        """Return True if *path_string* matches OR is a descendant of a matching path.

        Equivalent to: the pattern matches some prefix of *path_string*.
        """
        target = _path_to_elements(path_string, root_element=('root', GETATTR))[1:]
        return self._match_segments(target, 0, 0, {}, allow_extra_target=True)

    def _match_segments(self, target, pi, ti, memo, allow_extra_target):
        """Recursive segment matcher with backtracking for ``**``.

        ``memo`` is a per-top-level-call dict keyed by ``(pi, ti)`` so each
        state is computed at most once — turns the worst case from
        exponential to ``O(len(pattern) * len(target))``.
        """
        key = (pi, ti)
        if key in memo:
            return memo[key]
        pattern = self._pattern
        target_len = len(target)
        pattern_len = len(pattern)

        while pi < pattern_len and ti < target_len:
            pat_elem = pattern[pi][0]
            if pat_elem is MULTI_WILDCARD:
                # ** matches zero or more segments — try every suffix
                for k in range(ti, target_len + 1):
                    if self._match_segments(target, pi + 1, k, memo, allow_extra_target):
                        memo[key] = True
                        return True
                memo[key] = False
                return False
            elif pat_elem is SINGLE_WILDCARD:
                pi += 1
                ti += 1
            else:
                if pat_elem != target[ti][0]:
                    memo[key] = False
                    return False
                pi += 1
                ti += 1

        # Consume any trailing ** (they can match zero segments)
        while pi < pattern_len and pattern[pi][0] is MULTI_WILDCARD:
            pi += 1

        if allow_extra_target:
            result = pi == pattern_len
        else:
            result = pi == pattern_len and ti == target_len
        memo[key] = result
        return result

    def _could_match_descendant(self, target, pi, ti, memo):
        """Check if *target* is a prefix that could lead to a match deeper down."""
        key = (pi, ti)
        if key in memo:
            return memo[key]
        pattern = self._pattern
        if ti == len(target):
            result = pi < len(pattern)
            memo[key] = result
            return result
        if pi >= len(pattern):
            memo[key] = False
            return False

        pat_elem = pattern[pi][0]
        if pat_elem is MULTI_WILDCARD:
            result = (self._could_match_descendant(target, pi + 1, ti, memo)
                      or self._could_match_descendant(target, pi, ti + 1, memo))
        elif pat_elem is SINGLE_WILDCARD:
            result = self._could_match_descendant(target, pi + 1, ti + 1, memo)
        else:
            if pat_elem != target[ti][0]:
                memo[key] = False
                return False
            result = self._could_match_descendant(target, pi + 1, ti + 1, memo)
        memo[key] = result
        return result


def compile_glob_paths(paths):
    """Compile a list of glob pattern strings into GlobPathMatcher objects.

    Returns a list of ``GlobPathMatcher`` or ``None`` if *paths* is empty/None.
    """
    if not paths:
        return None
    return [GlobPathMatcher(p) for p in paths]
