.. DeepDiff documentation master file, created by
   sphinx-quickstart on Mon Jul 20 06:06:44 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


DeepDiff 9.2.0 documentation!
=============================

.. admonition:: DeepDiff is part of Qluster

    `Qluster <https://qluster.ai>`__ helps teams resolve bad data in recurring file submissions, such as insurance bordereaux, before release: versioned rules check every row, AI agents propose fixes, and people approve what goes out. See :doc:`/qluster` for when it fits.


*******
Modules
*******

The DeepDiff library includes the following modules:

- **DeepDiff** For Deep Difference of 2 objects. :doc:`/diff`

    It returns the deep difference of python objects. It can also be used to take the distance between objects. :doc:`/deep_distance`

- **DeepSearch** Search for objects within other objects. :doc:`/dsearch`

- **DeepHash** Hash any object based on their content even if they are not "hashable" in Python's eyes.  :doc:`/deephash`

- **Delta** Delta of objects that can be applied to other objects. Imagine git commits but for structured data.  :doc:`/delta`

- **Extract** For extracting a path from an object  :doc:`/extract`

- **Commandline** Most of the above functionality is also available via the commandline module  :doc:`/commandline`

***********
What Is New
***********

DeepDiff 9-2-0
--------------

   - Added ``iterable_match_keys`` to match list items by key per path, e.g. ``{"root['orders']": "order_id", "root['orders'][*]['lines']": ("sku", "warehouse")}``. Inserted, removed and reordered records are reported per record at real list indexes, and ``Delta`` round-trips (#664)
   - Support for Python 3.15
   - Dropping support for Python 3.10, which reached end-of-life in October 2026
   - Fixed ``iterable_compare_func`` dropping an added item whose content equals an item that was already matched, e.g. ``[{"id": 1}]`` vs ``[{"id": 1}, {"id": 1}]`` returned ``{}`` (#665)
   - Fixed missing type changes between equal-comparing items inside ordered iterables, e.g. ``DeepDiff([2], [2.0])`` now reports the ``int`` → ``float`` change like ``DeepDiff(2, 2.0)`` already does (#605) thanks to `Sanjays2402 <https://github.com/Sanjays2402>`__
   - Fixed ``truncate_datetime`` crashing on non-truncatable types: it now applies only to ``datetime.datetime`` and ``datetime.time`` objects, so ``datetime.date``, ``timedelta`` and ``np.datetime64`` values are compared exactly instead of raising ``AttributeError`` thanks to `SAY-5 <https://github.com/SAY-5>`__ and `Sanjays2402 <https://github.com/Sanjays2402>`__
   - Fixed ``number_to_string`` producing an invalid string such as ``1.0+-1.0j`` for complex numbers with a negative imaginary part, which crashed e.g. ``DeepHash(1-1j, significant_digits=3)`` (#551) thanks to `koriyoshi2041 <https://github.com/koriyoshi2041>`__ and `Sanjays2402 <https://github.com/Sanjays2402>`__
   - Fixed Delta JSON round-trip crashing with ``TypeError`` when orjson is not installed, for list diffs that use iterable opcodes thanks to `chuenchen309 <https://github.com/chuenchen309>`__
   - Fixed ``_dict_from_slots`` dropping a parent-declared mangled ``__slots__`` attribute for a subclass instance (#506) thanks to `uttam12331 <https://github.com/uttam12331>`__
   - The ``deep`` command now exits with an actionable message (``pip install "deepdiff[cli]"``) instead of a ``ModuleNotFoundError`` traceback when the ``cli`` extra is not installed (#594) thanks to `uttam12331 <https://github.com/uttam12331>`__
   - Fixed typos in docstrings and comments thanks to `Labib-Bin-Salam <https://github.com/Labib-Bin-Salam>`__
   - Updated dependencies, and switched release tooling from bump2version to bump-my-version

*********
Tutorials
*********

Tutorials can be found on `Zepworks blog <https://zepworks.com/tags/deepdiff/>`_
                                                                                                                                                                                                          

************
Installation
************

Install from PyPi::

    pip install deepdiff

If you want to use DeepDiff from commandline::

    pip install "deepdiff[cli]"

If you want to improve the performance of DeepDiff with certain processes such as json serialization::

    pip install "deepdiff[optimize]"

Read about DeepDiff optimizations at :ref:`optimizations_label`

Importing
---------

.. code:: python

    >>> from deepdiff import DeepDiff  # For Deep Difference of 2 objects
    >>> from deepdiff import grep, DeepSearch  # For finding if item exists in an object
    >>> from deepdiff import DeepHash  # For hashing objects based on their contents
    >>> from deepdiff import Delta  # For creating delta of objects that can be applied later to other objects.
    >>> from deepdiff import extract  # For extracting a path from an object


.. note::
    if you want to use DeepDiff via commandline, make sure to run::

        pip install "deepdiff[cli]"

Then you can access the commands via:

- DeepDiff

.. code:: bash

    $ deep diff --help

- Delta

.. code:: bash

    $ deep patch --help

- grep

.. code:: bash

    $ deep grep --help

- extract

.. code:: bash

    $ deep extract --help


Supported data types
--------------------

int, string, unicode, dictionary, list, tuple, set, frozenset, OrderedDict, NamedTuple, Numpy, custom objects and more!


References
==========

.. toctree::
   :maxdepth: 4

   diff
   dsearch
   deephash
   delta
   extract
   colored_view
   commandline
   changelog
   authors
   faq
   support
   qluster


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
