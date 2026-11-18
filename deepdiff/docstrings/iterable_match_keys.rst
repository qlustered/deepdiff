:doc:`/index`

.. _iterable_match_keys_label:

Iterable Match Keys
===================

Lists in JSON payloads are often collections of records with a business key such as ``id``, ``sku`` or
``(order_id, line_no)``, not positional sequences. When records are inserted, removed or reordered, comparing
such lists by position produces a cascade of ``values_changed``.

``iterable_match_keys`` tells DeepDiff how records are identified in specific lists. Items are then paired by key,
and you get per-record additions, removals and field changes. The lists stay lists: results are reported at real
list indexes and a :ref:`delta_label` made from the diff can be applied to the original object.

iterable_match_keys: Dictionary, default = None
    Maps a path to a key spec. Only the lists at the given paths are matched by key.

Example: a REST payload
-----------------------

    >>> from deepdiff import DeepDiff
    >>> from pprint import pprint
    >>> t1 = {
    ...     "orders": [
    ...         {"order_id": 1001, "status": "paid", "updatedAt": "2026-11-01T10:00:00Z",
    ...          "lines": [{"sku": "A-1", "warehouse": "east", "qty": 1},
    ...                    {"sku": "B-2", "warehouse": "east", "qty": 2}]},
    ...         {"order_id": 1002, "status": "pending", "updatedAt": "2026-11-01T10:00:00Z",
    ...          "lines": [{"sku": "C-3", "warehouse": "west", "qty": 1}]},
    ...     ]
    ... }
    >>> t2 = {
    ...     "orders": [
    ...         {"order_id": 1003, "status": "pending", "updatedAt": "2026-11-02T09:00:00Z",
    ...          "lines": [{"sku": "A-1", "warehouse": "west", "qty": 4}]},
    ...         {"order_id": 1001, "status": "shipped", "updatedAt": "2026-11-02T09:00:00Z",
    ...          "lines": [{"sku": "B-2", "warehouse": "east", "qty": 2},
    ...                    {"sku": "A-1", "warehouse": "east", "qty": 3}]},
    ...         {"order_id": 1002, "status": "pending", "updatedAt": "2026-11-02T09:00:00Z",
    ...          "lines": [{"sku": "C-3", "warehouse": "west", "qty": 1}]},
    ...     ]
    ... }

A new order was inserted at the top, order 1001 was shipped, and its lines were reordered with one quantity
changed. Compared by position, every order is compared with the wrong one:

    >>> diff = DeepDiff(t1, t2, exclude_paths=["root['orders'][*]['updatedAt']"])
    >>> len(diff['values_changed'])
    9

With ``iterable_match_keys``, orders are matched by ``order_id`` and order lines by ``(sku, warehouse)``:

    >>> pprint(DeepDiff(
    ...     t1, t2,
    ...     iterable_match_keys={
    ...         "root['orders']": "order_id",
    ...         "root['orders'][*]['lines']": ("sku", "warehouse"),
    ...     },
    ...     exclude_paths=["root['orders'][*]['updatedAt']"],
    ... ))
    {'iterable_item_added': {"root['orders'][0]": {'lines': [{'qty': 4,
                                                              'sku': 'A-1',
                                                              'warehouse': 'west'}],
                                                   'order_id': 1003,
                                                   'status': 'pending',
                                                   'updatedAt': '2026-11-02T09:00:00Z'}},
     'values_changed': {"root['orders'][1]['lines'][1]['qty']": {'new_value': 3,
                                                                 'old_value': 1},
                        "root['orders'][1]['status']": {'new_value': 'shipped',
                                                        'old_value': 'paid'}}}

Changes inside a record that changed position are reported at its index in t2, the same as with
:ref:`iterable_compare_func_label`. Reordering alone produces no output in the default view. With
``verbose_level=2``, it is reported as ``iterable_item_moved``.

Paths
-----

Paths use the same syntax as :ref:`exclude_paths_label`, including globs: ``[*]`` matches exactly one path segment and
``[**]`` matches any number of segments. For example ``"root[**]['lines']"`` selects every ``lines`` list at any
depth. A path given without ``root``, for example ``"orders"``, is treated as a key of the root.

- An exact path takes precedence over globs.
- If more than one glob matches the same list and there is no exact path for it, DeepDiff raises ``ValueError``
  instead of guessing.
- Lists that no path selects are compared as usual.

Key specs
---------

The key spec says how to get the key of an item:

- A ``str``: the key is ``item[key]``.
- A ``tuple`` of ``str``: a composite key, ``(item[key1], item[key2], ...)``.
- A callable that takes the item and returns a hashable key. Use it for nested or computed keys:

    >>> t1 = [{"product": {"id": 1}, "ts": 10, "qty": 1}, {"product": {"id": 2}, "ts": 10, "qty": 1}]
    >>> t2 = [{"product": {"id": 2}, "ts": 10, "qty": 5}, {"product": {"id": 1}, "ts": 10, "qty": 1}]
    >>> DeepDiff(t1, t2, iterable_match_keys={"root": lambda item: (item["product"]["id"], item["ts"])})
    {'values_changed': {"root[0]['qty']": {'new_value': 5, 'old_value': 1}}}

Matching rules
--------------

Duplicate keys
    The first item with a given key in t1 is paired with the first item with that key in t2, the second with
    the second, and so on. Extra items are reported as ``iterable_item_added`` or ``iterable_item_removed``.

Items without a key
    An item has no key when getting the key raises ``KeyError``, ``IndexError`` or ``TypeError``, when a callable
    key spec raises ``CannotCompare``, or when the key isn't hashable. Items without a key are paired in order
    among themselves, which is how a list is compared without ``iterable_match_keys``.

Key types
    Numeric keys match across ``int`` and ``float``, so ``1`` and ``1.0`` are the same key: an id that one
    serializer writes as ``1`` and another as ``1.0`` identifies the same record. The type change is still reported
    on the field itself, unless you pass ``ignore_numeric_type_changes=True``. Booleans never match numbers and
    strings never match numbers, so ``True`` and ``1``, or ``"1"`` and ``1``, are different keys. These rules apply to
    each part of a composite key and to keys returned by a callable.

    >>> DeepDiff([{"id": 1, "name": "a"}], [{"id": 1.0, "name": "b"}], iterable_match_keys={"root": "id"},
    ...          ignore_numeric_type_changes=True)
    {'values_changed': {"root[0]['name']": {'new_value': 'b', 'old_value': 'a'}}}
    >>> DeepDiff([{"id": 1}], [{"id": 2}], iterable_match_keys={"root": "id"})
    {'iterable_item_added': {'root[0]': {'id': 2}}, 'iterable_item_removed': {'root[0]': {'id': 1}}}

Records with different keys are always reported as removed and added, even when they are at the same index.

Using it with other parameters
------------------------------

- :ref:`exclude_paths_label` and :ref:`include_paths_label`, including globs, for example to exclude a volatile
  field from every record: ``exclude_paths=["root['orders'][*]['updatedAt']"]``.
- :ref:`ignore_order_label` and ``ignore_order_func``: lists selected by ``iterable_match_keys`` are always matched
  by key. Other lists, for example lists of tags, follow ``ignore_order``. When order is ignored, records matched by
  key at a different index are not reported as moved.
- :ref:`iterable_compare_func_label`: for the lists selected by ``iterable_match_keys``, the key takes precedence.
  The compare function still applies to every other list.
- ``custom_operators`` and ``exclude_obj_callback`` work as usual on the matched records.
- :ref:`delta_label`: ``t1 + Delta(diff) == t2`` for added, removed, changed and reordered records. Create the diff
  with ``verbose_level=2`` so moves are included.

    >>> from deepdiff import Delta
    >>> t1 = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    >>> t2 = [{"id": 3, "name": "c"}, {"id": 2, "name": "b"}, {"id": 1, "name": "A"}]
    >>> diff = DeepDiff(t1, t2, iterable_match_keys={"root": "id"}, verbose_level=2)
    >>> t1 + Delta(diff) == t2
    True

- ``multiprocessing=True``: works, but paired subtrees are diffed in the main process because workers don't
  see the full path. Key specs that can't be pickled, such as lambdas, also keep distance calculations in the main
  process.

Lists inside a record that moved are compared item by item, as with :ref:`iterable_compare_func_label`, unless
``iterable_match_keys`` or ``ignore_order`` selects them too.

Back to :doc:`/index`
