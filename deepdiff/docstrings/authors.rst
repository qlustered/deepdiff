:doc:`/index`

Authors
=======

Authors in order of the timeline of their contributions:

-  `Sep Dehpour (Seperman)`_
-  `Victor Hahn Castell`_ for the tree view and major contributions:
-  `nfvs`_ for Travis-CI setup script.
-  `brbsix`_ for initial Py3 porting.
-  `WangFenjin`_ for unicode support.
-  `timoilya`_ for comparing list of sets when ignoring order.
-  `Bernhard10`_ for significant digits comparison.
-  `b-jazz`_ for PEP257 cleanup, Standardize on full names, fixing line
   endings.
-  `finnhughes`_ for fixing **slots**
-  `moloney`_ for Unicode vs. Bytes default
-  `serv-inc`_ for adding help(deepdiff)
-  `movermeyer`_ for updating docs
-  `maxrothman`_ for search in inherited class attributes
-  `maxrothman`_ for search for types/objects
-  `MartyHub`_ for exclude regex paths
-  `sreecodeslayer`_ for DeepSearch match_string
-  Brian Maissy `brianmaissy`_ for weakref fix, enum tests
-  Bartosz Borowik `boba-2`_ for Exclude types fix when ignoring order
-  Brian Maissy `brianmaissy <https://github.com/brianmaissy>`__ for
   fixing classes which inherit from classes with slots didn’t have all
   of their slots compared
-  Juan Soler `Soleronline`_ for adding ignore_type_number
-  `mthaddon`_ for adding timedelta diffing support
-  `Necrophagos`_ for Hashing of the number 1 vs. True
-  `gaal-dev`_ for adding exclude_obj_callback
-  Ivan Piskunov `van-ess0`_ for deprecation warning enhancement.
-  Michał Karaś `MKaras93`_ for the pretty view
-  Christian Kothe `chkothe`_ for the basic support for diffing numpy
   arrays
-  `Timothy`_ for truncate_datetime
-  `d0b3rm4n`_ for bugfix to not apply format to non numbers.
-  `MyrikLD`_ for Bug Fix NoneType in ignore type groups
-  Stian Jensen `stianjensen`_ for improving ignoring of NoneType in
   diff
-  Florian Klien `flowolf`_ for adding math_epsilon
-  Tim Klein `timjklein36`_ for retaining the order of multiple
   dictionary items added via Delta.
-  Wilhelm Schürmann\ `wbsch`_ for fixing the typo with yml files.
-  `lyz-code`_ for adding support for regular expressions in DeepSearch
   and strict_checking feature in DeepSearch.
-  `dtorres-sf`_ for adding the option for custom compare function
-  Tony Wang `Tony-Wang`_ for bugfix: verbose_level==0 should disable
   values_changes.
-  Sun Ao `eggachecat`_ for adding custom operators.
-  Sun Ao `eggachecat`_ for adding ignore_order_func.
-  `SlavaSkvortsov`_ for fixing unprocessed key error.
-  Håvard Thom `havardthom`_ for adding UUID support.
-  Dhanvantari Tilak `Dhanvantari`_ for Bug-Fix:
   ``TypeError in _get_numbers_distance() when ignore_order = True``.
-  Yael Mintz `yaelmi3`_ for detailed pretty print when verbose_level=2.
-  Mikhail Khviyuzov `mskhviyu`_ for Exclude obj callback strict.
-  `dtorres-sf`_ for the fix for diffing using iterable_compare_func with nested objects.
-  `Enric Pou <https://github.com/epou>`__ for bug fix of ValueError
   when using Decimal 0.x
- `Uwe Fladrich <https://github.com/uwefladrich>`__ for fixing bug when diff'ing non-sequence iterables
-  `Michal Ozery-Flato <https://github.com/michalozeryflato>`__ for
   setting equal_nan=ignore_nan_inequality in the call for
   np.array_equal
-  `martin-kokos <https://github.com/martin-kokos>`__ for using Pytest’s
   tmp_path fixture instead of /tmp/
-  Håvard Thom `havardthom <https://github.com/havardthom>`__ for adding
   include_obj_callback and include_obj_callback_strict.
-  `Noam Gottlieb <https://github.com/noamgot>`__ for fixing a corner
   case where numpy’s ``np.float32`` nans are not ignored when using
   ``ignore_nan_equality``.
-  `maggelus <https://github.com/maggelus>`__ for the bugfix deephash
   for paths.
-  `maggelus <https://github.com/maggelus>`__ for the bugfix deephash
   compiled regex.
-  `martin-kokos <https://github.com/martin-kokos>`__ for fixing the
   tests dependent on toml.
-  `kor4ik <https://github.com/kor4ik>`__ for the bugfix for
   ``include_paths`` for nested dictionaries.
-  `martin-kokos <https://github.com/martin-kokos>`__ for using tomli
   and tomli-w for dealing with tomli files.
-  `Alex Sauer-Budge <https://github.com/amsb>`__ for the bugfix for
   ``datetime.date``.
- `William Jamieson <https://github.com/WilliamJamieson>`__ for `NumPy 2.0 compatibility <https://github.com/seperman/deepdiff/pull/422>`__
-  `Leo Sin <https://github.com/leoslf>`__ for Supporting Python 3.12 in
   the build process
-  `sf-tcalhoun <https://github.com/sf-tcalhoun>`__ for fixing
   “Instantiating a Delta with a flat_dict_list unexpectedly mutates the
   flat_dict_list”
-  `dtorres-sf <https://github.com/dtorres-sf>`__ for fixing iterable
   moved items when iterable_compare_func is used.
-  `Florian Finkernagel <https://github.com/TyberiusPrime>`__ for pandas
   and polars support.
- Mathis Chenuet `artemisart <https://github.com/artemisart>`__ for
  fixing slots classes comparison and PR review.
- Sherjeel Shabih `sherjeelshabih <https://github.com/sherjeelshabih>`__
  for fixing the issue where the key deep_distance is not returned when
  both compared items are equal #510
- `Juergen Skrotzky <https://github.com/Jorgen-VikingGod>`__ for adding
  empty ``py.typed``
- `Mate Valko <https://github.com/vmatt>`__ for fixing the issue so we
  lower only if clean_key is instance of str via #504
- `jlaba <https://github.com/jlaba>`__ for fixing #493 include_paths,
  when only certain keys are included via #499
- `Doron Behar <https://github.com/doronbehar>`__ for fixing DeepHash
  for numpy booleans via #496
- `Aaron D. Marasco <https://github.com/AaronDMarasco>`__ for adding
  print() options which allows a user-defined string (or callback
  function) to prefix every output when using the pretty() call.
- `David Hotham <https://github.com/dimbleby>`__ for relaxing
  orderly-set dependency via #486
- `dtorres-sf <https://github.com/dtorres-sf>`__ for the fix for moving
  nested tables when using iterable_compare_func.
- `Jim Cipar <https://github.com/jcipar>`__ for the fix recursion depth
  limit when hashing numpy.datetime64
- `Enji Cooper <https://github.com/ngie-eign>`__ for converting legacy
  setuptools use to pyproject.toml
- `Diogo Correia <https://github.com/diogotcorreia>`__ for reporting security vulnerability in Delta and DeepDiff that could allow remote code execution.
- `am-periphery <https://github.com/am-periphery>`__ for reporting CVE-2026-33155: denial-of-service via crafted pickle payloads triggering massive memory allocation.
- `echan5 <https://github.com/echan5>`__ for adding callable ``group_by`` support.
- `yannrouillard <https://github.com/yannrouillard>`__ for fixing colored view display when all list items are removed.
- `tpvasconcelos <https://github.com/tpvasconcelos>`__ for fixing ``__slots__`` handling for objects with ``__getattr__``.
- `devin13cox <https://github.com/devin13cox>`__ for fixing Delta producing phantom entries when items both move and change values with ``iterable_compare_func``.
- `vitalis89 <https://github.com/vitalis89>`__ for fixing ``ignore_keys`` issue in ``detailed__dict__``.
- `ljames8 <https://github.com/ljames8>`__ for fixing logarithmic similarity type hint.
- `srini047 <https://github.com/srini047>`__ for fixing README typo.
- `Nagato-Yuzuru <https://github.com/Nagato-Yuzuru>`__ for colored view tests.
- `akshat62 <https://github.com/akshat62>`__ for adding Fraction numeric support.
- `akshat62 <https://github.com/akshat62>`__ for adding wildcard/glob pattern support for ``exclude_paths`` and ``include_paths``.
- `mgorny <https://github.com/mgorny>`__ for adding missing files to sdist and removing obsolete ``MANIFEST.in``.
- `Sanjays2402 <https://github.com/Sanjays2402>`__ for fixing missing type changes between equal-comparing list items (e.g. ``[2]`` vs ``[2.0]``).
- `SAY-5 <https://github.com/SAY-5>`__ for skipping time truncation for ``date`` objects in ``truncate_datetime``.
- `koriyoshi2041 <https://github.com/koriyoshi2041>`__ for handling negative imaginary parts in ``number_to_string``.
- `Labib-Bin-Salam <https://github.com/Labib-Bin-Salam>`__ for fixing typos in docstrings and comments.
- `uttam12331 <https://github.com/uttam12331>`__ for fixing mangled ``__slots__`` attributes lost for subclass instances.
- `uttam12331 <https://github.com/uttam12331>`__ for giving an actionable error when ``deep`` runs without the ``cli`` extra.
- `chuenchen309 <https://github.com/chuenchen309>`__ for fixing Delta JSON round-trip crash when orjson is not installed.
- `Sanjays2402 <https://github.com/Sanjays2402>`__ for fixing ``truncate_datetime`` for ``timedelta`` and ``np.datetime64``, and adding negative-imaginary ``number_to_string`` tests.


.. _Sep Dehpour (Seperman): http://www.zepworks.com
.. _Victor Hahn Castell: http://hahncastell.de
.. _nfvs: https://github.com/nfvs
.. _brbsix: https://github.com/brbsix
.. _WangFenjin: https://github.com/WangFenjin
.. _timoilya: https://github.com/timoilya
.. _Bernhard10: https://github.com/Bernhard10
.. _b-jazz: https://github.com/b-jazz
.. _finnhughes: https://github.com/finnhughes
.. _moloney: https://github.com/moloney
.. _serv-inc: https://github.com/serv-inc
.. _movermeyer: https://github.com/movermeyer
.. _maxrothman: https://github.com/maxrothman
.. _MartyHub: https://github.com/MartyHub
.. _sreecodeslayer: https://github.com/sreecodeslayer
.. _brianmaissy: https://github.com/
.. _boba-2: https://github.com/boba-2
.. _Soleronline: https://github.com/Soleronline
.. _mthaddon: https://github.com/mthaddon
.. _Necrophagos: https://github.com/Necrophagos
.. _gaal-dev: https://github.com/gaal-dev
.. _van-ess0: https://github.com/van-ess0
.. _MKaras93: https://github.com/MKaras93
.. _chkothe: https://github.com/chkothe
.. _Timothy: https://github.com/timson
.. _d0b3rm4n: https://github.com/d0b3rm4n
.. _MyrikLD: https://github.com/MyrikLD
.. _stianjensen: https://github.com/stianjensen
.. _flowolf: https://github.com/flowolf
.. _timjklein36: https://github.com/timjklein36
.. _wbsch: https://github.com/wbsch
.. _lyz-code: https://github.com/lyz-code
.. _dtorres-sf: https://github.com/dtorres-sf
.. _Tony-Wang: https://github.com/Tony-Wang
.. _eggachecat: https://github.com/eggachecat
.. _SlavaSkvortsov: https://github.com/SlavaSkvortsov
.. _havardthom: https://github.com/havardthom
.. _Dhanvantari: https://github.com/Dhanvantari
.. _yaelmi3: https://github.com/yaelmi3
.. _mskhviyu: https://github.com/mskhviyu

Thank you for contributing to DeepDiff!

Back to :doc:`/index`
