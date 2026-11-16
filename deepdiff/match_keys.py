"""Key-based matching of list items for ``DeepDiff(iterable_match_keys=...)``.

``iterable_match_keys`` maps paths (exact or glob) to a key spec. For the
lists selected by a path, items in t1 and t2 are paired by their key instead
of by position, so inserts, removals and reorders don't cascade into
``values_changed`` reports.
"""
from collections import deque
from collections.abc import Mapping
from typing import Any, Callable, Dict, Hashable, List, Optional, Tuple, Union

from deepdiff.helper import (
    CannotCompare, ListItemRemovedOrAdded, add_root_to_paths, booleans,
)
from deepdiff.path import GlobPathMatcher, _path_to_elements, path_has_wildcard

KeySpec = Union[str, Tuple[str, ...], Callable[[Any], Hashable]]

_ROOT_ELEMENT = ('root', 'GETATTR')


class _NoKey:
    """The item has no key: it is paired in order with other key-less items."""

    def __repr__(self):  # pragma: no cover
        return 'NO_KEY'


class _BoolTag:
    """Tags boolean key components so that ``True`` never matches ``1``."""

    def __repr__(self):  # pragma: no cover
        return 'BOOL'

    def __reduce__(self):
        # Keep the module-level singleton identity across pickling (multiprocessing).
        return 'BOOL_TAG'


NO_KEY = _NoKey()
BOOL_TAG = _BoolTag()

# Exceptions that mean "this item has no key" rather than a programming error.
_NO_KEY_EXCEPTIONS = (KeyError, IndexError, TypeError, CannotCompare)


def _validate_key_spec(path: str, spec: Any) -> KeySpec:
    if isinstance(spec, str) or callable(spec):
        return spec
    if isinstance(spec, tuple) and spec and all(isinstance(i, str) for i in spec):
        return spec
    raise ValueError(
        "iterable_match_keys[{!r}] must be a key name (str), a non-empty tuple of key names, "
        "or a callable that takes an item and returns a hashable key. Got: {!r}".format(path, spec))


def _path_to_segments(path: str) -> Tuple[Any, ...]:
    """The path's segments without the root and without the access action.

    ``root['a']`` and ``root.a`` give the same segments, the same way
    ``GlobPathMatcher`` compares paths.
    """
    return tuple(elem for elem, _ in _path_to_elements(path, root_element=_ROOT_ELEMENT)[1:])


class CompiledMatchKeys:
    """``iterable_match_keys`` compiled for fast lookup by list path."""

    def __init__(self, iterable_match_keys: Any) -> None:
        if not isinstance(iterable_match_keys, Mapping):
            raise ValueError(
                "iterable_match_keys must be a mapping of path to key spec. Got: {!r}".format(iterable_match_keys))
        self.exact: Dict[Tuple[Any, ...], KeySpec] = {}
        self.globs: List[Tuple[GlobPathMatcher, KeySpec]] = []
        for path, spec in iterable_match_keys.items():
            if not isinstance(path, str):
                raise ValueError("iterable_match_keys paths must be strings. Got: {!r}".format(path))
            spec = _validate_key_spec(path, spec)
            if path_has_wildcard(path):
                if not path.startswith('root'):
                    raise ValueError("Wildcard paths must start with 'root'. Got: {}".format(path))
                self.globs.append((GlobPathMatcher(path), spec))
                continue
            for variant in add_root_to_paths([path]):  # type: ignore
                segments = _path_to_segments(variant)
                existing = self.exact.get(segments, NO_KEY)
                if existing is not NO_KEY and existing != spec:
                    raise ValueError(
                        "iterable_match_keys has more than one key spec for the path {!r}.".format(path))
                self.exact[segments] = spec

    def get_spec(self, path: Optional[str]) -> Optional[KeySpec]:
        """Return the key spec for the list at ``path``, or None if no entry selects it.

        An exact path takes precedence over globs. If more than one glob matches
        and there is no exact path, raise ValueError rather than guess.
        """
        if not path:
            return None
        if self.exact:
            try:
                segments = _path_to_segments(path)
            except Exception:  # pragma: no cover. Paths DeepDiff builds are parseable.
                segments = None
            if segments is not None and segments in self.exact:
                return self.exact[segments]
        matched = [(matcher, spec) for matcher, spec in self.globs if matcher.match(path)]
        if not matched:
            return None
        if len(matched) > 1:
            raise ValueError(
                "More than one iterable_match_keys glob matches the path {}: {}. "
                "Add an exact path for it or make the globs more specific.".format(
                    path, ', '.join(repr(matcher.original_pattern) for matcher, _ in matched)))
        return matched[0][1]


def _normalize_key(value: Any) -> Any:
    """Normalize a key so that int and float ids match but booleans never match numbers.

    Python already treats ``1 == 1.0`` with equal hashes and ``"1" != 1``.
    Only booleans need special handling since ``True == 1``.
    """
    if isinstance(value, booleans):
        return (BOOL_TAG, bool(value))
    if isinstance(value, tuple):
        return tuple(_normalize_key(i) for i in value)
    return value


def get_item_key(item: Any, spec: KeySpec) -> Any:
    """Return the normalized key of ``item``, or ``NO_KEY`` if it has none."""
    try:
        if isinstance(spec, str):
            key = item[spec]
        elif isinstance(spec, tuple):
            key = tuple(item[i] for i in spec)
        else:
            key = spec(item)
        key = _normalize_key(key)
        hash(key)
    except _NO_KEY_EXCEPTIONS:
        return NO_KEY
    return key


def get_key_matching_pairs(
    t1: Any, t2: Any, spec: KeySpec,
) -> List[Tuple[Tuple[int, int], Tuple[Any, Any]]]:
    """Pair the items of t1 and t2 by key in O(n + m).

    - The k-th occurrence of a key in t1 pairs with the k-th occurrence in t2.
      Extra occurrences are reported as removed or added.
    - Items without a key are paired in order among themselves.

    Returns the same structure as ``DeepDiff._get_matching_pairs``.
    """
    t1_items = list(t1)
    t2_items = list(t2)
    t2_index: Dict[Any, deque] = {}
    t2_no_key: List[int] = []
    for j, y in enumerate(t2_items):
        key = get_item_key(y, spec)
        if key is NO_KEY:
            t2_no_key.append(j)
        else:
            t2_index.setdefault(key, deque()).append(j)

    matches: List[Tuple[Tuple[int, int], Tuple[Any, Any]]] = []
    t2_matched = set()
    no_key_position = 0
    for i, x in enumerate(t1_items):
        key = get_item_key(x, spec)
        j = None
        if key is NO_KEY:
            if no_key_position < len(t2_no_key):
                j = t2_no_key[no_key_position]
                no_key_position += 1
        else:
            candidates = t2_index.get(key)
            if candidates:
                j = candidates.popleft()
        if j is None:
            matches.append(((i, -1), (x, ListItemRemovedOrAdded)))
        else:
            t2_matched.add(j)
            matches.append(((i, j), (x, t2_items[j])))
    for j, y in enumerate(t2_items):
        if j not in t2_matched:
            matches.append(((-1, j), (ListItemRemovedOrAdded, y)))
    return matches
