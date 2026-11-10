"""Path-scoped JSON comparison strategies built on top of :class:`DeepDiff`.

The API is opt-in. ``DeepJSONDiff`` creates canonical, caller-isolated views of
JSON-like inputs and delegates the final recursive comparison to ``DeepDiff``.
"""
from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping as MappingABC
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .diff import DeepDiff


_MISSING = object()
_ARRAY_WILDCARD = object()
_KEY_WILDCARD = object()

JSONScalar = Optional[bool | int | float | str]
FilterFunc = Callable[[Any], bool]
Normalizer = Callable[[Any], Any]
PathToken = str | int | object
SortKey = Tuple[Any, ...]

_UNSAFE_DEEPDIFF_KWARGS = {
    "include_paths",
    "exclude_paths",
    "exclude_regex_paths",
    "ignore_order_func",
    "iterable_compare_func",
    "custom_operators",
    "exclude_obj_callback",
    "exclude_obj_callback_strict",
    "include_obj_callback",
    "include_obj_callback_strict",
}


class MissingIdentityPolicy(str, Enum):
    """Behaviour when an item does not contain all configured identity fields."""

    ERROR = "error"
    FALLBACK = "fallback"
    EXCLUDE = "exclude"


class DuplicateIdentityPolicy(str, Enum):
    """Behaviour when multiple items produce the same identity."""

    ERROR = "error"
    GROUP = "group"


class CollectionStrategyError(ValueError):
    """Base error for invalid collection strategy configuration or execution."""


class IdentityExtractionError(CollectionStrategyError):
    """Raised when a required identity field cannot be extracted."""


class DuplicateIdentityError(CollectionStrategyError):
    """Raised when an identity expected to be unique is duplicated."""


def _as_non_empty_string_tuple(value: Any, field_name: str) -> Tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise CollectionStrategyError(f"{field_name} must be a sequence of non-empty strings")
    result = tuple(value)
    if any(not isinstance(item, str) or not item for item in result):
        raise CollectionStrategyError(f"{field_name} must contain only non-empty strings")
    return result


def _parse_quoted_key(token: str, pattern: str) -> str:
    try:
        value = ast.literal_eval(token)
    except (SyntaxError, ValueError, TypeError) as exc:
        raise CollectionStrategyError(f"invalid quoted key selector in {pattern!r}") from exc
    if not isinstance(value, str):
        raise CollectionStrategyError(f"quoted key selector in {pattern!r} must contain a string")
    return value


def _parse_pattern(pattern: str) -> Tuple[PathToken, ...]:
    """Parse the supported JSONPath-like collection selector into path tokens."""
    if not isinstance(pattern, str) or not pattern.startswith("$"):
        raise CollectionStrategyError("strategy path must be a string starting with '$'")
    if pattern == "$":
        return ()

    tokens: List[PathToken] = []
    index = 1
    while index < len(pattern):
        if pattern[index] == ".":
            index += 1
            start = index
            while index < len(pattern) and pattern[index] not in ".[":
                index += 1
            token = pattern[start:index]
            if not token:
                raise CollectionStrategyError(f"invalid strategy path {pattern!r}")
            tokens.append(_KEY_WILDCARD if token == "*" else token)
            continue

        if pattern[index] == "[":
            close = index + 1
            quote: Optional[str] = None
            escaped = False
            while close < len(pattern):
                char = pattern[close]
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif quote is not None:
                    if char == quote:
                        quote = None
                elif char in ("'", '"'):
                    quote = char
                elif char == "]":
                    break
                close += 1
            if close >= len(pattern) or pattern[close] != "]" or quote is not None:
                raise CollectionStrategyError(f"invalid strategy path {pattern!r}")

            token = pattern[index + 1 : close]
            if token == "*":
                tokens.append(_ARRAY_WILDCARD)
            elif token.isdigit():
                try:
                    tokens.append(int(token))
                except ValueError as exc:
                    raise CollectionStrategyError(f"invalid strategy path {pattern!r}") from exc
            elif len(token) >= 2 and token[0] in ("'", '"') and token[-1] == token[0]:
                tokens.append(_parse_quoted_key(token, pattern))
            else:
                raise CollectionStrategyError(
                    "bracket selectors must contain an integer index, '*', or a quoted key"
                )
            index = close + 1
            continue

        raise CollectionStrategyError(f"invalid strategy path {pattern!r}")

    return tuple(tokens)


@dataclass(frozen=True)
class CollectionStrategy:
    """Rules applied to a JSON array selected by ``path``."""

    path: str
    match_by: Tuple[str, ...] = ()
    sort_by: Tuple[str, ...] = ()
    filter_func: Optional[FilterFunc] = None
    normalizers: Tuple[Normalizer, ...] = ()
    exclude_fields: Tuple[str, ...] = ()
    compare_as_set: bool = False
    missing_identity: MissingIdentityPolicy = MissingIdentityPolicy.FALLBACK
    duplicates: DuplicateIdentityPolicy = DuplicateIdentityPolicy.ERROR
    priority: int = 0
    name: Optional[str] = None
    _pattern_tokens: Tuple[PathToken, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        pattern_tokens = _parse_pattern(self.path)
        match_by = _as_non_empty_string_tuple(self.match_by, "match_by")
        sort_by = _as_non_empty_string_tuple(self.sort_by, "sort_by")
        exclude_fields = _as_non_empty_string_tuple(self.exclude_fields, "exclude_fields")
        if any("." in field_name for field_name in exclude_fields):
            raise CollectionStrategyError("exclude_fields supports top-level keys only")

        if isinstance(self.normalizers, (str, bytes)) or not isinstance(
            self.normalizers, Sequence
        ):
            raise CollectionStrategyError("normalizers must be a sequence of callables")
        normalizers = tuple(self.normalizers)
        if any(not callable(item) for item in normalizers):
            raise CollectionStrategyError("all normalizers must be callable")
        if self.filter_func is not None and not callable(self.filter_func):
            raise CollectionStrategyError("filter_func must be callable")
        if not isinstance(self.compare_as_set, bool):
            raise CollectionStrategyError("compare_as_set must be a boolean")
        if self.compare_as_set and match_by:
            raise CollectionStrategyError("compare_as_set and match_by are mutually exclusive")
        if self.compare_as_set and sort_by:
            raise CollectionStrategyError("compare_as_set and sort_by are mutually exclusive")
        if not isinstance(self.priority, int) or isinstance(self.priority, bool):
            raise CollectionStrategyError("priority must be an integer")
        if self.name is not None and (not isinstance(self.name, str) or not self.name):
            raise CollectionStrategyError("name must be a non-empty string or None")

        try:
            missing_identity = MissingIdentityPolicy(self.missing_identity)
        except (TypeError, ValueError) as exc:
            raise CollectionStrategyError(
                f"invalid missing_identity policy {self.missing_identity!r}"
            ) from exc
        try:
            duplicates = DuplicateIdentityPolicy(self.duplicates)
        except (TypeError, ValueError) as exc:
            raise CollectionStrategyError(
                f"invalid duplicates policy {self.duplicates!r}"
            ) from exc

        object.__setattr__(self, "match_by", match_by)
        object.__setattr__(self, "sort_by", sort_by)
        object.__setattr__(self, "exclude_fields", exclude_fields)
        object.__setattr__(self, "normalizers", normalizers)
        object.__setattr__(self, "missing_identity", missing_identity)
        object.__setattr__(self, "duplicates", duplicates)
        object.__setattr__(self, "_pattern_tokens", pattern_tokens)


@dataclass
class StrategyStats:
    """Execution diagnostics for one concrete collection path on one input side."""

    strategy: str
    items: int = 0
    filtered: int = 0
    missing_identity: int = 0
    duplicate_groups: int = 0


@dataclass
class _Context:
    side: str
    stats: Dict[str, StrategyStats] = field(default_factory=dict)


@dataclass
class _PreparedItem:
    original_index: int
    value: Any
    identity: Optional[Tuple[Any, ...]] = None
    sort_key: Optional[Tuple[SortKey, ...]] = None


def _path_to_string(path: Tuple[Any, ...]) -> str:
    result = "$"
    for part in path:
        if isinstance(part, int):
            result += f"[{part}]"
        elif isinstance(part, str) and part.isidentifier():
            result += f".{part}"
        else:
            result += f"[{part!r}]"
    return result


def _pattern_matches(pattern: Tuple[PathToken, ...], path: Tuple[Any, ...]) -> bool:
    if len(pattern) != len(path):
        return False
    for expected, actual in zip(pattern, path):
        if expected is _ARRAY_WILDCARD:
            if not isinstance(actual, int):
                return False
        elif expected is _KEY_WILDCARD:
            if not isinstance(actual, str):
                return False
        elif expected != actual:
            return False
    return True


def _extract(value: Any, relative_path: str, default: Any = _MISSING) -> Any:
    """Extract a dotted relative path from mappings and integer-indexed lists."""
    current = value
    for token in relative_path.split("."):
        if isinstance(current, Mapping):
            if token not in current:
                return default
            current = current[token]
        elif isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return current


def _scalar_component(
    value: Any,
    *,
    field_name: Optional[str] = None,
    location: Optional[str] = None,
) -> Tuple[str, Any]:
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            detail = f"identity field {field_name!r} at {location}" if field_name else "value"
            raise IdentityExtractionError(f"{detail} must be finite")
        return ("float", value)
    if isinstance(value, str):
        return ("str", value)
    detail = f"identity field {field_name!r} at {location}" if field_name else "value"
    raise IdentityExtractionError(
        f"{detail} must resolve to a JSON scalar; got {type(value).__name__}"
    )


def _identity_label(
    identity: Tuple[Any, ...],
    fields: Tuple[str, ...],
    location: str,
) -> str:
    encoded = [
        _scalar_component(value, field_name=field_name, location=location)
        for field_name, value in zip(fields, identity)
    ]
    return json.dumps(encoded, ensure_ascii=False, separators=(",", ":"))


def _stable_value(value: Any, *, location: str) -> SortKey:
    """Return a total deterministic ordering key for JSON-compatible values."""
    if value is _MISSING:
        return (0,)
    if value is None:
        return (1,)
    if isinstance(value, bool):
        return (2, value)
    if isinstance(value, int):
        return (3, 0, value)
    if isinstance(value, float):
        if value == float("-inf"):
            return (3, 1, 0)
        if math.isfinite(value):
            return (3, 1, 1, value)
        if value == float("inf"):
            return (3, 1, 2)
        return (3, 1, 3)  # NaN
    if isinstance(value, str):
        return (4, value)
    if isinstance(value, list):
        return (5, tuple(_stable_value(item, location=location) for item in value))
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CollectionStrategyError(
                f"sort key at {location} contains a mapping with non-string keys"
            )
        return (
            6,
            tuple(
                (key, _stable_value(value[key], location=location))
                for key in sorted(value)
            ),
        )
    raise CollectionStrategyError(
        f"sort key at {location} must be JSON-compatible; got {type(value).__name__}"
    )


class DeepJSONDiff(MappingABC[str, Any]):
    """Compare JSON-like values with path-scoped collection semantics.

    Path-sensitive DeepDiff options are rejected because matching strategies
    change selected list paths into canonical identity-keyed mappings.
    """

    def __init__(
        self,
        t1: Any,
        t2: Any,
        *,
        collection_strategies: Iterable[CollectionStrategy] = (),
        **deepdiff_kwargs: Any,
    ) -> None:
        unsafe = sorted(_UNSAFE_DEEPDIFF_KWARGS.intersection(deepdiff_kwargs))
        if unsafe:
            raise CollectionStrategyError(
                "path-sensitive DeepDiff options are not supported by DeepJSONDiff: "
                + ", ".join(unsafe)
            )

        self.collection_strategies = tuple(collection_strategies)
        self._validate_strategies()
        self.stats: Dict[str, Dict[str, StrategyStats]] = {"left": {}, "right": {}}

        left_context = _Context(side="left", stats=self.stats["left"])
        right_context = _Context(side="right", stats=self.stats["right"])
        self.canonical_t1 = self._canonicalize(t1, (), left_context)
        self.canonical_t2 = self._canonicalize(t2, (), right_context)
        self.diff = DeepDiff(self.canonical_t1, self.canonical_t2, **deepdiff_kwargs)

    def _validate_strategies(self) -> None:
        seen: Dict[Tuple[str, int], CollectionStrategy] = {}
        for strategy in self.collection_strategies:
            if not isinstance(strategy, CollectionStrategy):
                raise CollectionStrategyError(
                    "collection_strategies must contain CollectionStrategy instances"
                )
            key = (strategy.path, strategy.priority)
            if key in seen:
                raise CollectionStrategyError(
                    f"ambiguous strategies for path {strategy.path!r} "
                    f"at priority {strategy.priority}"
                )
            seen[key] = strategy

    @staticmethod
    def _specificity(strategy: CollectionStrategy) -> int:
        return sum(
            token is not _ARRAY_WILDCARD and token is not _KEY_WILDCARD
            for token in strategy._pattern_tokens
        )

    def _resolve_strategy(self, path: Tuple[Any, ...]) -> Optional[CollectionStrategy]:
        matches = [
            strategy
            for strategy in self.collection_strategies
            if _pattern_matches(strategy._pattern_tokens, path)
        ]
        if not matches:
            return None
        matches.sort(
            key=lambda item: (item.priority, self._specificity(item)),
            reverse=True,
        )
        if len(matches) > 1:
            first, second = matches[0], matches[1]
            if (
                first.priority == second.priority
                and self._specificity(first) == self._specificity(second)
            ):
                raise CollectionStrategyError(
                    "ambiguous collection strategies matched concrete path "
                    f"{_path_to_string(path)!r}"
                )
        return matches[0]

    def _canonicalize(self, value: Any, path: Tuple[Any, ...], context: _Context) -> Any:
        strategy = self._resolve_strategy(path) if isinstance(value, list) else None
        if isinstance(value, Mapping):
            return {
                key: self._canonicalize(item, path + (key,), context)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return self._canonicalize_list(value, path, strategy, context)
        return value

    def _prepare_item(
        self,
        original: Any,
        index: int,
        path: Tuple[Any, ...],
        strategy: CollectionStrategy,
        context: _Context,
        stat: StrategyStats,
    ) -> Optional[_PreparedItem]:
        item = deepcopy(original) if strategy.filter_func or strategy.normalizers else original
        if strategy.filter_func is not None and not strategy.filter_func(item):
            stat.filtered += 1
            return None

        for normalizer in strategy.normalizers:
            item = normalizer(item)

        identity: Optional[Tuple[Any, ...]] = None
        if strategy.match_by:
            identity = tuple(_extract(item, field) for field in strategy.match_by)

        rendered = _path_to_string(path)
        sort_key: Optional[Tuple[SortKey, ...]] = None
        if strategy.sort_by:
            sort_key = tuple(
                _stable_value(
                    _extract(item, field),
                    location=f"{rendered} sort_by {field!r}",
                )
                for field in strategy.sort_by
            )

        if isinstance(item, Mapping) and strategy.exclude_fields:
            item = dict(item)
            for field_name in strategy.exclude_fields:
                item.pop(field_name, None)

        item = self._canonicalize(item, path + (index,), context)
        return _PreparedItem(index, item, identity, sort_key)

    def _canonicalize_list(
        self,
        values: List[Any],
        path: Tuple[Any, ...],
        strategy: Optional[CollectionStrategy],
        context: _Context,
    ) -> Any:
        if strategy is None:
            return [
                self._canonicalize(item, path + (index,), context)
                for index, item in enumerate(values)
            ]

        rendered = _path_to_string(path)
        stat = StrategyStats(strategy=strategy.name or strategy.path, items=len(values))
        context.stats[rendered] = stat

        prepared = [
            item
            for index, original in enumerate(values)
            if (item := self._prepare_item(original, index, path, strategy, context, stat))
            is not None
        ]

        if strategy.match_by:
            return self._index_by_identity(prepared, path, strategy, context, stat)

        if strategy.sort_by:
            prepared = sorted(prepared, key=lambda item: item.sort_key or ())
        elif strategy.compare_as_set:
            for item in prepared:
                try:
                    _scalar_component(item.value)
                except IdentityExtractionError as exc:
                    raise CollectionStrategyError(
                        f"compare_as_set at {rendered} supports finite JSON scalar items only"
                    ) from exc
            prepared = sorted(
                prepared,
                key=lambda item: _stable_value(item.value, location=rendered),
            )
        return [item.value for item in prepared]

    def _index_by_identity(
        self,
        prepared: List[_PreparedItem],
        path: Tuple[Any, ...],
        strategy: CollectionStrategy,
        context: _Context,
        stat: StrategyStats,
    ) -> Dict[str, Any]:
        rendered = _path_to_string(path)
        grouped: Dict[str, List[_PreparedItem]] = {}
        fallback: List[Any] = []

        for prepared_item in prepared:
            item_location = f"{rendered}[{prepared_item.original_index}]"
            identity = prepared_item.identity
            assert identity is not None

            if any(value is _MISSING for value in identity):
                stat.missing_identity += 1
                if strategy.missing_identity is MissingIdentityPolicy.ERROR:
                    missing = [
                        field
                        for field, value in zip(strategy.match_by, identity)
                        if value is _MISSING
                    ]
                    raise IdentityExtractionError(
                        f"missing identity field(s) {missing!r} on {context.side} input "
                        f"at {item_location} while applying strategy {strategy.path!r}"
                    )
                if strategy.missing_identity is MissingIdentityPolicy.EXCLUDE:
                    continue
                fallback.append(prepared_item.value)
                continue

            label = _identity_label(identity, strategy.match_by, item_location)
            grouped.setdefault(label, []).append(prepared_item)

        result: Dict[str, Any] = {}
        for label, group in grouped.items():
            if len(group) > 1:
                stat.duplicate_groups += 1
                if strategy.duplicates is DuplicateIdentityPolicy.ERROR:
                    raise DuplicateIdentityError(
                        f"duplicate identity {label!r} on {context.side} input at "
                        f"{rendered} while applying strategy {strategy.path!r}"
                    )
            if strategy.sort_by:
                group = sorted(group, key=lambda item: item.sort_key or ())
            if strategy.duplicates is DuplicateIdentityPolicy.GROUP:
                # Always a list so a count change diffs record-by-record
                # instead of as a list-to-dict type change.
                result[label] = [item.value for item in group]
            else:
                result[label] = group[0].value

        if fallback:
            # The key must not start with "__": DeepDiff skips such keys by
            # default (ignore_private_variables=True), which would silently
            # drop fallback records from the comparison.
            result["deepdiff_fallback"] = fallback
        return result

    def get_strategy_stats(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Return strategy diagnostics separated by input side.

        Distinct from ``DeepDiff.get_stats()``, which reports run statistics.
        """
        return {
            side: {
                path: {
                    "strategy": stat.strategy,
                    "items": stat.items,
                    "filtered": stat.filtered,
                    "missing_identity": stat.missing_identity,
                    "duplicate_groups": stat.duplicate_groups,
                }
                for path, stat in side_stats.items()
            }
            for side, side_stats in self.stats.items()
        }

    def __bool__(self) -> bool:
        return bool(self.diff)

    def __getitem__(self, key: str) -> Any:
        return self.diff[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.diff)

    def __len__(self) -> int:
        return len(self.diff)

    def __repr__(self) -> str:
        return repr(self.diff)

    def to_dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return self.diff.to_dict(*args, **kwargs)

    def to_json(self, *args: Any, **kwargs: Any) -> str:
        return self.diff.to_json(*args, **kwargs)
