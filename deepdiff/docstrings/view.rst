:doc:`/index`

.. _view_label:

View
====

You have the options of text view and tree view.
The main difference is that the tree view has the capabilities to traverse the objects to see what objects were compared to what other objects.

While the view options decide the format of the output that is mostly machine readable, regardless of the view you choose, you can get a more human readable output by using the pretty() method.
DeepDiff also offers other specialized views such as the :doc:`colored_view` (which includes a compact variant) and :doc:`delta` view for specific use cases.

.. _text_view_label:

Text View
---------

Text view is the default view of DeepDiff. It is simpler than tree view.

Example of using the text view.
    >>> from decimal import Decimal
    >>> from deepdiff import DeepDiff
    >>> t1 = {1:1, 3:3, 4:4}
    >>> t2 = {1:1, 3:3, 5:5, 6:6}
    >>> ddiff = DeepDiff(t1, t2)
    >>> print(ddiff)
    {'dictionary_item_added': [root[5], root[6]], 'dictionary_item_removed': [root[4]]}

So for example ddiff['dictionary_item_added'] is a set of string results. That's why this view is called the text view.
You can get this view by default or by passing `view='text'`.

.. _tree_view_label:

Tree View
---------

The tree view provides you with tree objects that you can traverse through to find
the parents of the objects that are diffed and the actual objects that are being diffed.
This view is very useful when dealing with nested objects.
Note that tree view always returns results in the form of Python sets.

You can traverse through the tree elements!

.. note::
    The Tree view is just a different representation of the diffed data.
    Behind the scene, DeepDiff creates the tree view first and then converts it to textual
    representation for the text view.

**Tree View Interface**

.. code:: text

    +---------------------------------------------------------------+
    |                                                               |
    |    parent(t1)              parent node            parent(t2)  |----level
    |      +                          ^                     +       |
    +------|--------------------------|---------------------|-------+
           |                      |   | up                  |
           | Child                |   |                     | ChildRelationship
           | Relationship         |   |                     |
           |                 down |   |                     |
    +------|----------------------|-------------------------|-------+
    |      v                      v                         v       |
    |    child(t1)              child node               child(t2)  |----level
    |                                                               |
    +---------------------------------------------------------------+


:up: Move up to the parent node aka parent level
:down: Move down to the child node aka child level
:path(): Get the path to the current node in string representation, path(output_format='list') gives you the path in list representation. path(use_t2=True) gives you the path to t2.
:t1: The first item in the current node that is being diffed
:t2: The second item in the current node that is being diffed
:additional: Additional information about the node i.e. repetition
:repetition: Shortcut to get the repetition report


The tree view allows you to have more than mere textual representation of the diffed objects.
It gives you the actual objects (t1, t2) throughout the tree of parents and children.

**Examples for Tree View**

.. note::
    Set view='tree' in order to get the results in tree view.

Value of an item has changed (Tree View)
    >>> from deepdiff import DeepDiff
    >>> from pprint import pprint
    >>> t1 = {1:1, 2:2, 3:3}
    >>> t2 = {1:1, 2:4, 3:3}
    >>> ddiff_verbose0 = DeepDiff(t1, t2, verbose_level=0, view='tree')
    >>> ddiff_verbose0
    {'values_changed': [<root[2]>]}
    >>>
    >>> ddiff_verbose1 = DeepDiff(t1, t2, verbose_level=1, view='tree')
    >>> ddiff_verbose1
    {'values_changed': [<root[2] t1:2, t2:4>]}
    >>> set_of_values_changed = ddiff_verbose1['values_changed']
    >>> # since set_of_values_changed includes only one item in a set
    >>> # in order to get that one item we can:
    >>> (changed,) = set_of_values_changed
    >>> changed  # Another way to get this is to do: changed=list(set_of_values_changed)[0]
    <root[2] t1:2, t2:4>
    >>> changed.t1
    2
    >>> changed.t2
    4
    >>> # You can traverse through the tree, get to the parents!
    >>> changed.up
    <root t1:{1: 1, 2: 2,...}, t2:{1: 1, 2: 4,...}>

List difference (Tree View)
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
    >>> parent.t1
    [1, 2, 3, 4]
    >>> parent.t2
    [1, 2]
    >>> parent.up
    <root[4] t1:{'a': 'hello...}, t2:{'a': 'hello...}>
    >>> parent.up.up
    <root t1:{1: 1, 2: 2,...}, t2:{1: 1, 2: 2,...}>
    >>> parent.up.up.t1
    {1: 1, 2: 2, 3: 3, 4: {'a': 'hello', 'b': [1, 2, 3, 4]}}
    >>> parent.up.up.t1 == t1  # It is holding the original t1 that we passed to DeepDiff
    True

List difference 2  (Tree View)
    >>> t1 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":[1, 2, 3]}}
    >>> t2 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":[1, 3, 2, 3]}}
    >>> ddiff = DeepDiff(t1, t2, view='tree')
    >>> pprint(ddiff, indent = 2)
    { 'iterable_item_added': [<root[4]['b'][3] t1:not present, t2:3>],
      'values_changed': [<root[4]['b'][1] t1:2, t2:3>, <root[4]['b'][2] t1:3, t2:2>]}
    >>>
    >>> # Note that iterable_item_added is a set with one item.
    >>> # So in order to get that one item from it, we can do:
    >>>
    >>> (added,) = ddiff['iterable_item_added']
    >>> added
    <root[4]['b'][3] t1:not present, t2:3>
    >>> added.up.up
    <root[4] t1:{'a': 'hello...}, t2:{'a': 'hello...}>
    >>> added.up.up.path()
    'root[4]'
    >>> added.up.up.path(output_format='list')  # gives you the list of keys and attributes that make up the path
    [4]
    >>> added.up.up.down
    <root[4]['b'] t1:[1, 2, 3], t2:[1, 3, 2, 3]>
    >>>
    >>> # going up twice and then down twice gives you the same node in the tree:
    >>> added.up.up.down.down == added
    True

List difference ignoring order but reporting repetitions (Tree View)
    >>> t1 = [1, 3, 1, 4]
    >>> t2 = [4, 4, 1]
    >>> ddiff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True, view='tree')
    >>> pprint(ddiff, indent=2)
    { 'iterable_item_removed': [<root[1] t1:3, t2:not present>],
      'repetition_change': [<root[3] {'repetition': {'old_repeat': 1,...}>, <root[0] {'repetition': {'old_repeat': 2,...}>]}
    >>>
    >>> # repetition_change is a set with 2 items.
    >>> # in order to get those 2 items, we can do the following.
    >>> # or we can convert the set to list and get the list items.
    >>> # or we can iterate through the set items
    >>>
    >>> (repeat1, repeat2) = ddiff['repetition_change']
    >>> repeat1  # the default verbosity is set to 1.
    <root[3] {'repetition': {'old_repeat': 1,...}>
    >>> # The actual data regarding the repetitions can be found in the repetition attribute:
    >>> repeat1.repetition
    {'old_repeat': 1, 'new_repeat': 2, 'old_indexes': [3], 'new_indexes': [0, 1]}
    >>>
    >>> # If you change the verbosity, you will see less:
    >>> ddiff = DeepDiff(t1, t2, ignore_order=True, report_repetition=True, view='tree', verbose_level=0)
    >>> ddiff
    {'repetition_change': [<root[3]>, <root[0]>], 'iterable_item_removed': [<root[1]>]}
    >>> (repeat1, repeat2) = ddiff['repetition_change']
    >>> repeat1
    <root[0]>
    >>>
    >>> # But the verbosity level does not change the actual report object.
    >>> # It only changes the textual representation of the object. We get the actual object here:
    >>> repeat1.repetition
    {'old_repeat': 1, 'new_repeat': 2, 'old_indexes': [3], 'new_indexes': [0, 1]}
    >>> repeat1.t1
    4
    >>> repeat1.t2
    4
    >>> repeat1.up
    <root>

List that contains dictionary (Tree View)
    >>> t1 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":[1, 2, {1:1, 2:2}]}}
    >>> t2 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":[1, 2, {1:3}]}}
    >>> ddiff = DeepDiff(t1, t2, view='tree')
    >>> pprint (ddiff, indent = 2)
    { 'dictionary_item_removed': [<root[4]['b'][2][2] t1:2, t2:not present>],
      'values_changed': [<root[4]['b'][2][1] t1:1, t2:3>]}

Sets (Tree View):
    >>> t1 = {1, 2, 8}
    >>> t2 = {1, 2, 3, 5}
    >>> ddiff = DeepDiff(t1, t2, view='tree')
    >>> print(ddiff)
    {'set_item_removed': [<root: t1:8, t2:not present>], 'set_item_added': [<root: t1:not present, t2:3>, <root: t1:not present, t2:5>]}
    >>> # grabbing one item from set_item_removed set which has one item only
    >>> (item,) = ddiff['set_item_removed']
    >>> item.up
    <root t1:{8, 1, 2}, t2:{1, 2, 3, 5}>
    >>> item.up.t1 == t1
    True

Named Tuples (Tree View):
    >>> from collections import namedtuple
    >>> Point = namedtuple('Point', ['x', 'y'])
    >>> t1 = Point(x=11, y=22)
    >>> t2 = Point(x=11, y=23)
    >>> print(DeepDiff(t1, t2, view='tree'))
    {'values_changed': [<root.y t1:22, t2:23>]}

Custom objects (Tree View):
    >>> class ClassA(object):
    ...     a = 1
    ...     def __init__(self, b):
    ...         self.b = b
    ...
    >>> t1 = ClassA(1)
    >>> t2 = ClassA(2)
    >>>
    >>> print(DeepDiff(t1, t2, view='tree'))
    {'values_changed': [<root.b t1:1, t2:2>]}

Object attribute added (Tree View):
    >>> t2.c = "new attribute"
    >>> pprint(DeepDiff(t1, t2, view='tree'))
    {'attribute_added': [<root.c t1:not present, t2:'new attribute'>],
     'values_changed': [<root.b t1:1, t2:2>]}

Approximate decimals comparison (Significant digits after the point) (Tree View):
    >>> t1 = Decimal('1.52')
    >>> t2 = Decimal('1.57')
    >>> DeepDiff(t1, t2, significant_digits=0, view='tree')
    {}
    >>> ddiff = DeepDiff(t1, t2, significant_digits=1, view='tree')
    >>> ddiff
    {'values_changed': [<root t1:Decimal('1.52'), t2:Decimal('1.57')>]}
    >>> (change1,) = ddiff['values_changed']
    >>> change1
    <root t1:Decimal('1.52'), t2:Decimal('1.57')>
    >>> change1.t1
    Decimal('1.52')
    >>> change1.t2
    Decimal('1.57')
    >>> change1.path()
    'root'

Approximate float comparison (Significant digits after the point) (Tree View):
    >>> t1 = [ 1.1129, 1.3359 ]
    >>> t2 = [ 1.113, 1.3362 ]
    >>> ddiff = DeepDiff(t1, t2, significant_digits=3, view='tree')
    >>> ddiff
    {}
    >>> ddiff = DeepDiff(t1, t2, view='tree')
    >>> pprint(ddiff, indent=2)
    { 'values_changed': [<root[0] t1:1.1129, t2:1.113>, <root[1] t1:1.3359, t2:1.3362>]}
    >>> ddiff = DeepDiff(1.23*10**20, 1.24*10**20, significant_digits=1, view='tree')
    >>> ddiff
    {'values_changed': [<root t1:1.23e+20, t2:1.24e+20>]}


pretty() method
---------------

Use the pretty method for human readable output. This is regardless of what view you have used to generate the results.
    >>> from deepdiff import DeepDiff
    >>> t1={1,2,4}
    >>> t2={2,3}
    >>> print(DeepDiff(t1, t2).pretty())
    Item root[3] added to set.
    Item root[4] removed from set.
    Item root[1] removed from set.

The pretty method has an optional parameter ``prefix`` that allows a prefix string before every output line (*e.g.* for logging):
    >>> from deepdiff import DeepDiff
    >>> t1={1,2,4}
    >>> t2={2,3}
    >>> print(DeepDiff(t1, t2).pretty(prefix='Diff: '))
    Diff: Item root[3] added to set.
    Diff: Item root[4] removed from set.
    Diff: Item root[1] removed from set.

The ``prefix`` may also be a callable function. This function must accept ``**kwargs``; as of this version, the only parameter is ``diff`` but the signature allows for future expansion.
The ``diff`` given will be the ``DeepDiff`` that ``pretty`` was called on; this allows interesting capabilities such as:

.. code:: python

    >>> from deepdiff import DeepDiff
    >>> t1={1,2,4}
    >>> t2={2,3}
    >>> def callback(**kwargs):
    ...     """Helper function using a hidden variable on the diff that tracks which count prints next"""
    ...     kwargs['diff']._diff_count = 1 + getattr(kwargs['diff'], '_diff_count', 0)
    ...     return f"Diff #{kwargs['diff']._diff_count}: "
    ...
    >>> print(DeepDiff(t1, t2).pretty(prefix=callback))
    Diff #1: Item root[3] added to set.
    Diff #2: Item root[4] removed from set.
    Diff #3: Item root[1] removed from set.


Text view vs. Tree view vs. pretty() method
-----------------------------------------------

Views are just different format of results. Each comes with its own set of features. At the end of the day the user can choose the right format based on the use case.

- The text view is the default format of the results. It is the format that is the most suitable if you don't need to know the traversal history of the objects being compared.
- The tree view allows you to traverse back and forth through the tree and see what objects were compared to what other objects.
- The pretty() method is not a view. All the views are dictionaries. The pretty() method spits out a string output of what has changed and is designed to be human readable.

For example
    >>> from deepdiff import DeepDiff
    >>> t1={1,2,4}
    >>> t2={2,3}

Text view (default)
    >>> DeepDiff(t1, t2)  # same as view='text'
    {'set_item_removed': [root[4], root[1]], 'set_item_added': [root[3]]}

Tree view
    >>> tree = DeepDiff(t1, t2, view='tree')
    >>> tree
    {'set_item_removed': [<root: t1:4, t2:not present>, <root: t1:1, t2:not present>], 'set_item_added': [<root: t1:not present, t2:3>]}
    >>> tree['set_item_added'][0]
    <root: t1:not present, t2:3>
    >>> tree['set_item_added'][0].t2
    3

Pretty method. Regardless of what view was used, you can use the "pretty()" method to get a human readable output.
    >>> print(DeepDiff(t1, t2).pretty())
    Item root[3] added to set.
    Item root[4] removed from set.
    Item root[1] removed from set.


Back to :doc:`/index`
