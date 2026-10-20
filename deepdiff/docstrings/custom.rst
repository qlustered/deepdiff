:doc:`/index`

Customized Diff
===============

.. _iterable_compare_func_label:

Iterable Compare Func
---------------------

New in DeepDiff 5.5.0

There are times that we want to guide DeepDiff as to what items to compare with other items. In such cases we can pass a `iterable_compare_func` that takes a function pointer to compare two items. The function takes three parameters (x, y, level) and should return `True` if it is a match, `False` if it is not a match or raise `CannotCompare` if it is unable to compare the two.


For example take the following objects:


Now let's define a compare_func that takes 3 parameters: x, y and level.

    >>> from deepdiff import DeepDiff
    >>> from deepdiff.helper import CannotCompare
    >>>
    >>> t1 = [
    ...     {
    ...         'id': 1,
    ...         'value': [1]
    ...     },
    ...     {
    ...         'id': 2,
    ...         'value': [7, 8, 1]
    ...     },
    ...     {
    ...         'id': 3,
    ...         'value': [7, 8],
    ...     },
    ... ]
    >>>
    >>> t2 = [
    ...     {
    ...         'id': 2,
    ...         'value': [7, 8]
    ...     },
    ...     {
    ...         'id': 3,
    ...         'value': [7, 8, 1],
    ...     },
    ...     {
    ...         'id': 1,
    ...         'value': [1]
    ...     },
    ... ]
    >>>
    >>> DeepDiff(t1, t2)
    {'values_changed': {"root[0]['id']": {'new_value': 2, 'old_value': 1}, "root[0]['value'][0]": {'new_value': 7, 'old_value': 1}, "root[1]['id']": {'new_value': 3, 'old_value': 2}, "root[2]['id']": {'new_value': 1, 'old_value': 3}, "root[2]['value'][0]": {'new_value': 1, 'old_value': 7}}, 'iterable_item_added': {"root[0]['value'][1]": 8}, 'iterable_item_removed': {"root[2]['value'][1]": 8}}

As you can see the results are different. Now items with the same ids are compared with each other.

    >>> def compare_func(x, y, level=None):
    ...     try:
    ...         return x['id'] == y['id']
    ...     except Exception:
    ...         raise CannotCompare() from None
    ...
    >>> DeepDiff(t1, t2, iterable_compare_func=compare_func)
    {'iterable_item_added': {"root[2]['value'][2]": 1}, 'iterable_item_removed': {"root[1]['value'][2]": 1}}

If we set the verbose_level=2, we can see more details.

    >>> DeepDiff(t1, t2, iterable_compare_func=compare_func, verbose_level=2)
    {'iterable_item_added': {"root[2]['value'][2]": 1}, 'iterable_item_removed': {"root[1]['value'][2]": 1}, 'iterable_item_moved': {'root[0]': {'new_path': 'root[2]', 'value': {'id': 1, 'value': [1]}}, 'root[1]': {'new_path': 'root[0]', 'value': {'id': 2, 'value': [7, 8]}}, 'root[2]': {'new_path': 'root[1]', 'value': {'id': 3, 'value': [7, 8, 1]}}}}


We can also use the level parameter. Levels are explained in the :ref:`tree_view_label`.

For example you could use the level object to further determine if the 2 objects should be matches or not.


    >>> t1 = {
    ...     'path1': [],
    ...     'path2': [
    ...         {
    ...             'id': 1,
    ...             'value': [1]
    ...         },
    ...         {
    ...             'id': 2,
    ...             'value': [7, 8, 1]
    ...         },
    ...     ]
    ... }
    >>>
    >>> t2 = {
    ...     'path1': [{'pizza'}],
    ...     'path2': [
    ...         {
    ...             'id': 2,
    ...             'value': [7, 8, 1]
    ...         },
    ...         {
    ...             'id': 1,
    ...             'value': [1, 2]
    ...         },
    ...     ]
    ... }
    >>>
    >>>
    >>> def compare_func2(x, y, level):
    ...     if (not isinstance(x, dict) or not isinstance(y, dict)):
    ...         raise CannotCompare
    ...     if(level.path() == "root['path2']"):
    ...         if (x["id"] == y["id"]):
    ...             return True
    ...         return False
    ...
    >>>
    >>> DeepDiff(t1, t2, iterable_compare_func=compare_func2)
    {'iterable_item_added': {"root['path1'][0]": {'pizza'}, "root['path2'][0]['value'][1]": 2}}


.. note::

    The level parameter of the iterable_compare_func is only used when ignore_order=False which is the default value for ignore_order.


.. _custom_operators_label:

Custom Operators
----------------

Whether two objects are different or not largely depends on the context. For example, apples and bananas are the same
if you are considering whether they are fruits or not.

In that case, you can pass a *custom_operators* for the job.

Custom operators give you a lot of power. In the following examples, we explore various use cases such as:

- Making DeepDiff report the L2 Distance of items
- Only include specific paths in diffing
- Making DeepDiff stop diffing once we find the first diff.

You can use one of the predefined custom operators that come with DeepDiff. Or you can define one yourself.


Built-In Custom Operators

.. _prefix_or_suffix_operator_label:

PrefixOrSuffixOperator
......................


This operator will skip strings that are suffix or prefix of each other.

For example when this operator is used, the two strings of "joe" and "joe's car" will not be reported as different.

    >>> from deepdiff import DeepDiff
    >>> from deepdiff.operator import PrefixOrSuffixOperator
    >>> t1 = {
    ...     "key1": ["foo", "bar's food", "jack", "joe"]
    ... }
    >>> t2 = {
    ...     "key1": ["foo", "bar", "jill", "joe'car"]
    ... }
    >>>
    >>> DeepDiff(t1, t2)
    {'values_changed': {"root['key1'][1]": {'new_value': 'bar', 'old_value': "bar's food"}, "root['key1'][2]": {'new_value': 'jill', 'old_value': 'jack'}, "root['key1'][3]": {'new_value': "joe'car", 'old_value': 'joe'}}}
    >>> DeepDiff(t1, t2, custom_operators=[
    ...     PrefixOrSuffixOperator()
    ... ])
    >>>
    {'values_changed': {"root['key1'][2]": {'new_value': 'jill', 'old_value': 'jack'}}}




Define A Custom Operator
------------------------


To define a custom operator, you just need to inherit *BaseOperator* or *BaseOperatorPlus*.

    - *BaseOperatorPlus* is our new base operator that can be subclassed and provides the structure to build any custom operator.
    - *BaseOperator* is our older base class for creating custom operators. It was designed mainly for simple string based regex comparison.


Base Operator Plus
..................

*BaseOperatorPlus* is our new base operator that can be subclassed and provides the structure to build any custom operator.

.. code-block:: python

    class BaseOperatorPlus(metaclass=ABCMeta):

        @abstractmethod
        def match(self, level) -> bool:
            """
            Given a level which includes t1 and t2 in the tree view, is this operator a good match to compare t1 and t2?
            If yes, we will run the give_up_diffing to compare t1 and t2 for this level.
            """
            pass

        @abstractmethod
        def give_up_diffing(self, level, diff_instance: "DeepDiff") -> bool:
            """
            Given a level which includes t1 and t2 in the tree view, and the "distance" between l1 and l2.
            do we consider t1 and t2 to be equal or not. The distance is a number between zero to one and is calculated by DeepDiff to measure how similar objects are.
            """

        @abstractmethod
        def normalize_value_for_hashing(self, parent: Any, obj: Any) -> Any:
            """
            Normalize an individual value before hashing, for example with ignore_order=True.

            Unlike give_up_diffing, this method is not gated by match: hashing has no
            pair of values to compare. Check obj's type or parent path here and return
            obj unchanged when no normalization applies.

            For case-insensitive strings, return obj.lower() if isinstance(obj, str) else obj.
            """
            pass


``match`` selects an operator for comparing a pair of values. It does **not**
select which values are passed to ``normalize_value_for_hashing``. Hashing
processes individual values before DeepDiff can pair them for comparison, and
calls each registered operator's normalization method in order. Each method
receives the preceding method's result.

A normalizer must therefore check the type of ``obj`` (or its ``parent`` path)
itself, and return ``obj`` unchanged for values it does not handle. This includes
containers as well as their contents. An empty implementation using ``pass``
returns ``None``; doing that for unrelated values can give them the same hash
and hide differences when ``ignore_order=True``.

**Example 1: We don't care about the exact GUID values. As long as pairs of strings match GUID regex, we want them to be considered as equals**

    >>> import re
    >>> from typing import Any
    >>> from deepdiff import DeepDiff
    >>> from deepdiff.operator import BaseOperatorPlus

    >>> d1 = {
    ...     "Name": "SUB_OBJECT_FILES",
    ...     "Values": {
    ...         "Value": [
    ...             "{f254498b-b752-4f35-bef5-6f1844b61eb7}",
    ...             "{7fb2a550-1849-45c0-b273-9aa5e4eb9f2b}",
    ...             "{a9cbecc0-21dc-49ce-8b2c-d36352dae139}"
    ...         ]
    ...     }
    ... }

    >>> d2 = {
    ...     "Name": "SUB_OBJECT_FILES",
    ...     "Values": {
    ...         "Value": [
    ...             "{e5d18917-1a2c-4abe-b601-8ec002629953}",
    ...             "{ea71ba1f-1339-4fae-bc28-a9ce9b8a8c67}",
    ...             "{66bb6192-9cd2-4074-8be1-f2ac52877c70}",
    ...         ]
    ...     }
    ... }

    >>> class RemoveGUIDsOperator(BaseOperatorPlus):
    ...     _pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    ...     _substitute = "guid"
    ...
    ...     def match(self, level) -> bool:
    ...         return isinstance(level.t1, str) and isinstance(level.t2, str)
    ...
    ...     @classmethod
    ...     def _remove_pattern(cls, t: str):
    ...         return re.sub(cls._pattern, cls._substitute, t)
    ...
    ...     def give_up_diffing(self, level, diff_instance):
    ...         t1 = self._remove_pattern(level.t1)
    ...         t2 = self._remove_pattern(level.t2)
    ...         return t1 == t2
    ...
    ...     def normalize_value_for_hashing(self, parent: Any, obj: Any) -> Any:
    ...         """
    ...         Used for ignore_order=True
    ...         """
    ...         if isinstance(obj, str):
    ...             return self._remove_pattern(obj)
    ...         return obj

    >>> operator = RemoveGUIDsOperator()

    >>> diff1 = DeepDiff(d1, d2, custom_operators=[operator], log_stacktrace=True)
    >>> diff1
    {}
    >>> diff2 = DeepDiff(d1, d2, ignore_order=True, custom_operators=[operator], log_stacktrace=True)
    >>> diff2
    {}

The normalizer above returns non-string values unchanged, so registering the
string operator does not hide differences between numbers:

    >>> bool(DeepDiff([1, 2], [2, 3], ignore_order=True, custom_operators=[operator]))
    True
    >>> DeepDiff([1, 2], [2, 1], ignore_order=True, custom_operators=[operator])
    {}



Base Operator
.............

*BaseOperator* is our older base class for creating custom operators. It was designed mainly for simple string based regex comparison.


.. code-block:: python

    class BaseOperator:

        def __init__(self, regex_paths:Optional[List[str]]=None, types:Optional[List[type]]=None):
            if regex_paths:
                self.regex_paths = convert_item_or_items_into_compiled_regexes_else_none(regex_paths)
            else:
                self.regex_paths = None
            self.types = types

        def match(self, level) -> bool:
            if self.regex_paths:
                for pattern in self.regex_paths:
                    matched = re.search(pattern, level.path()) is not None
                    if matched:
                        return True
            if self.types:
                for type_ in self.types:
                    if isinstance(level.t1, type_) and isinstance(level.t2, type_):
                        return True
            return False

        def give_up_diffing(self, level, diff_instance) -> bool:
            raise NotImplementedError('Please implement the diff function.')



**Example 2: An operator that mapping L2:distance as diff criteria and reports the distance**

    >>> import math
    >>>
    >>> from typing import List
    >>> from deepdiff import DeepDiff
    >>> from deepdiff.operator import BaseOperator
    >>>
    >>>
    >>> class L2DistanceDifferWithPreventDefault(BaseOperator):
    ...     def __init__(self, regex_paths: List[str], distance_threshold: float):
    ...         super().__init__(regex_paths)
    ...         self.distance_threshold = distance_threshold
    ...     def _l2_distance(self, c1, c2):
    ...         return math.sqrt(
    ...             (c1["x"] - c2["x"]) ** 2 + (c1["y"] - c2["y"]) ** 2
    ...         )
    ...     def give_up_diffing(self, level, diff_instance):
    ...         l2_distance = self._l2_distance(level.t1, level.t2)
    ...         if l2_distance > self.distance_threshold:
    ...             diff_instance.custom_report_result('distance_too_far', level, {
    ...                 "l2_distance": l2_distance
    ...             })
    ...         return True
    ...
    >>>
    >>> t1 = {
    ...     "coordinates": [
    ...         {"x": 5, "y": 5},
    ...         {"x": 8, "y": 8}
    ...     ]
    ... }
    >>>
    >>> t2 = {
    ...     "coordinates": [
    ...         {"x": 6, "y": 6},
    ...         {"x": 88, "y": 88}
    ...     ]
    ... }
    >>> DeepDiff(t1, t2, custom_operators=[L2DistanceDifferWithPreventDefault(
    ...     ["^root\\['coordinates'\\]\\[\\d+\\]$"],
    ...     1
    ... )])
    {'distance_too_far': {"root['coordinates'][0]": {'l2_distance': 1.4142135623730951}, "root['coordinates'][1]": {'l2_distance': 113.13708498984761}}}


**Example 3: If the objects are subclasses of a certain type, only compare them if their list attributes are not equal sets**

    >>> class CustomClass:
    ...     def __init__(self, d: dict, l: list):
    ...         self.dict = d
    ...         self.dict['list'] = l
    ...
    >>>
    >>> custom1 = CustomClass(d=dict(a=1, b=2), l=[1, 2, 3])
    >>> custom2 = CustomClass(d=dict(c=3, d=4), l=[1, 2, 3, 2])
    >>> custom3 = CustomClass(d=dict(a=1, b=2), l=[1, 2, 3, 4])
    >>>
    >>>
    >>> class ListMatchOperator(BaseOperator):
    ...     def give_up_diffing(self, level, diff_instance):
    ...         if set(level.t1.dict['list']) == set(level.t2.dict['list']):
    ...             return True
    ...
    >>>
    >>> DeepDiff(custom1, custom2, custom_operators=[
    ...     ListMatchOperator(types=[CustomClass])
    ... ])
    {}
    >>>
    >>>
    >>> DeepDiff(custom2, custom3, custom_operators=[
    ...     ListMatchOperator(types=[CustomClass])
    ... ])
    {'dictionary_item_added': [root.dict['a'], root.dict['b']], 'dictionary_item_removed': [root.dict['c'], root.dict['d']], 'values_changed': {"root.dict['list'][3]": {'new_value': 4, 'old_value': 2}}}
    >>>

**Example 4: Only diff certain paths**

    >>> from deepdiff import DeepDiff
    >>> class MyOperator:
    ...     def __init__(self, include_paths):
    ...         self.include_paths = include_paths
    ...     def match(self, level) -> bool:
    ...         return True
    ...     def give_up_diffing(self, level, diff_instance) -> bool:
    ...         return level.path() not in self.include_paths
    ...
    >>>
    >>> t1 = {'a': [10, 11], 'b': [20, 21], 'c': [30, 31]}
    >>> t2 = {'a': [10, 22], 'b': [20, 33], 'c': [30, 44]}
    >>>
    >>> DeepDiff(t1, t2, custom_operators=[
    ...     MyOperator(include_paths="root['a'][1]")
    ... ])
    {'values_changed': {"root['a'][1]": {'new_value': 22, 'old_value': 11}}}

**Example 5: Give up further diffing once the first diff is found**

Sometimes all you care about is that there is a difference between 2 objects and not all the details of what exactly is different.
In that case you may want to stop diffing as soon as the first diff is found.

    >>> from deepdiff import DeepDiff
    >>> class MyOperator:
    ...     def match(self, level) -> bool:
    ...         return True
    ...     def give_up_diffing(self, level, diff_instance) -> bool:
    ...         return any(diff_instance.tree.values())
    ...
    >>> t1 = [[1, 2], [3, 4], [5, 6]]
    >>> t2 = [[1, 3], [3, 5], [5, 7]]
    >>>
    >>> DeepDiff(t1, t2, custom_operators=[
    ...     MyOperator()
    ... ])
    {'values_changed': {'root[0][1]': {'new_value': 3, 'old_value': 2}}}


Back to :doc:`/index`
