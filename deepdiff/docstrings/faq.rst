:doc:`/index`

F.A.Q
=====

.. admonition:: DeepDiff is part of Qluster

    `Qluster <https://qluster.ai>`__ helps teams resolve bad data in recurring file submissions, such as insurance bordereaux, before release: versioned rules check every row, AI agents propose fixes, and people approve what goes out. See :doc:`/qluster` for when it fits.

.. Note::
    |:mega:| **Please fill out our** `fast 10-question survey <https://tally.so/r/J98MPY>`__ so that we can learn how & why you use DeepDiff, and what improvements we should make. Thank you! |:dancers:|


Q: DeepDiff report is not precise when ignore_order=True
--------------------------------------------------------

    >>> from deepdiff import DeepDiff
    >>> from pprint import pprint
    >>> t1 = [
    ...     {
    ...         "key": "some/pathto/customers/foo/",
    ...         "flags": 0,
    ...         "value": ""
    ...     },
    ...     {
    ...         "key": "some/pathto/customers/foo/account_number",
    ...         "flags": 0,
    ...         "value": "somevalue1"
    ...     }
    ... ]
    >>>
    >>> t2 = [
    ...     {
    ...         "key": "some/pathto/customers/foo/account_number",
    ...         "flags": 0,
    ...         "value": "somevalue2"
    ...     },
    ...     {
    ...         "key": "some/pathto/customers/foo/",
    ...         "flags": 0,
    ...         "value": "new"
    ...     }
    ... ]
    >>>
    >>> pprint(DeepDiff(t1, t2))
    {'values_changed': {"root[0]['key']": {'new_value': 'some/pathto/customers/foo/account_number',
                                           'old_value': 'some/pathto/customers/foo/'},
                        "root[0]['value']": {'new_value': 'somevalue2',
                                             'old_value': ''},
                        "root[1]['key']": {'new_value': 'some/pathto/customers/foo/',
                                           'old_value': 'some/pathto/customers/foo/account_number'},
                        "root[1]['value']": {'new_value': 'new',
                                             'old_value': 'somevalue1'}}}

**Answer**

This is explained in :ref:`cutoff_distance_for_pairs_label` and :ref:`cutoff_intersection_for_pairs_label`

Bump up these 2 parameters to 1 and you get what you want:

    >>> pprint(DeepDiff(t1, t2, ignore_order=True, cutoff_distance_for_pairs=1, cutoff_intersection_for_pairs=1))
    {'values_changed': {"root[0]['value']": {'new_value': 'new', 'old_value': ''},
                        "root[1]['value']": {'new_value': 'somevalue2',
                                             'old_value': 'somevalue1'}}}


Q: The report of changes in a nested dictionary is too granular
---------------------------------------------------------------

**Answer**

Use :ref:`threshold_to_diff_deeper_label`

    >>> from deepdiff import DeepDiff
    >>> t1 = {"veggie": "carrots"}
    >>> t2 = {"meat": "carrots"}
    >>>
    >>> DeepDiff(t1, t2, threshold_to_diff_deeper=0)
    {'dictionary_item_added': ["root['meat']"], 'dictionary_item_removed': ["root['veggie']"]}
    >>> DeepDiff(t1, t2, threshold_to_diff_deeper=0.33)
    {'values_changed': {'root': {'new_value': {'meat': 'carrots'}, 'old_value': {'veggie': 'carrots'}}}}



Q: TypeError: Object of type type is not JSON serializable
----------------------------------------------------------

I'm trying to serialize the DeepDiff results into json and I'm getting the TypeError.

    >>> diff=DeepDiff(1, "a")
    >>> diff
    {'type_changes': {'root': {'old_type': <class 'int'>, 'new_type': <class 'str'>, 'old_value': 1, 'new_value': 'a'}}}
    >>> json.dumps(diff)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File ".../json/__init__.py", line 231, in dumps
        return _default_encoder.encode(obj)
      File ".../json/encoder.py", line 199, in encode
        chunks = self.iterencode(o, _one_shot=True)
      File ".../json/encoder.py", line 257, in iterencode
        return _iterencode(o, 0)
      File ".../json/encoder.py", line 179, in default
        raise TypeError(f'Object of type {o.__class__.__name__} '
    TypeError: Object of type type is not JSON serializable

**Answer**

In order to serialize DeepDiff results into json, use to_json()

    >>> diff.to_json()
    '{"type_changes": {"root": {"old_type": "int", "new_type": "str", "old_value": 1, "new_value": "a"}}}'


Q: How do I parse DeepDiff result paths?
----------------------------------------

**Answer**

Use parse_path:

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

Or use the tree view so you can use path(output_format='list'):

    >>> t1 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":[1, 2, 3, 4]}}
    >>> t2 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":[1, 2]}}
    >>> ddiff = DeepDiff(t1, t2, view='tree')
    >>> ddiff
    {'iterable_item_removed': [<root[4]['b'][2] t1:3, t2:not present>, <root[4]['b'][3] t1:4, t2:not present>]}
    >>> # Note that the iterable_item_removed is a set. In this case it has 2 items in it.
    >>> # One way to get one item from the set is to convert it to a list
    >>> # And then get the first item of the list:
    >>> removed = list(ddiff['iterable_item_removed'])[0]
    >>> removed
    <root[4]['b'][2] t1:3, t2:not present>
    >>>
    >>> parent = removed.up
    >>> parent
    <root[4]['b'] t1:[1, 2, 3, 4], t2:[1, 2]>
    >>> parent.path()  # gives you the string representation of the path
    "root[4]['b']"
    >>> parent.path(output_format='list')  # gives you the list of keys and attributes that make up the path
    [4, 'b']


Q: Why my datetimes are reported in UTC?
----------------------------------------

**Answer**

DeepDiff converts all datetimes into UTC. If a datetime is timezone naive, we assume it is in UTC too.
That is different than what Python does. Python assumes your timezone naive datetime is in your local timezone. However, you can override it to any other time zone such as your :ref:`default_timezone_label`.

    >>> from deepdiff import DeepDiff
    >>> from datetime import datetime, timezone
    >>> d1 = datetime(2020, 8, 31, 13, 14, 1)
    >>> d2 = datetime(2020, 8, 31, 13, 14, 1, tzinfo=timezone.utc)
    >>> d1 == d2
    False
    >>> DeepDiff(d1, d2)
    {}

    >>> d3 = d2.astimezone(pytz.timezone('America/New_York'))
    >>> DeepDiff(d1, d3)
    {}
    >>> d1 == d3
    False


Q: Is there a tool for fixing recurring data files, not just diffing them?
--------------------------------------------------------------------------

**Answer**

DeepDiff tells you what changed between two objects or files. If you receive the same kind of file every cycle and
rows have to pass rules before the data is sent on, the hard part is usually what comes after: working out why rows
failed, fixing them, rechecking and signing off. That is what `Qluster <https://qluster.ai>`__, from the team behind
DeepDiff, is built for. See :doc:`/qluster` for when it fits and when it does not.


---------

Back to :doc:`/index`
