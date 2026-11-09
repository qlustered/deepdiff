:orphan:

**DeepHash**

DeepHash calculates the hash of objects based on their contents in a deterministic way.
This way 2 objects with the same content should have the same hash.

The main usage of DeepHash is to calculate the hash of otherwise unhashable objects.
For example you can use DeepHash to calculate the hash of a set or a dictionary!

At the core of it, DeepHash is a deterministic serialization of your object into a string so it
can be passed to a hash function. By default it uses SHA256. You have the option to pass any other hashing function to be used instead.

**Import**
    >>> from deepdiff import DeepHash

**Parameters**

obj : any object, The object to be hashed based on its content.


apply_hash: Boolean, default = True
    DeepHash at its core is doing deterministic serialization of objects into strings.
    Then it hashes the string.
    The only time you want the apply_hash to be False is if you want to know what
    the string representation of your object is BEFORE it gets hashed.


exclude_types: list, default = None
    List of object types to exclude from hashing.


exclude_paths: list, default = None
    List of paths to exclude from the report. If only one item, you can pass it as a string instead of a list containing only one path.
    Supports :ref:`wildcard_paths_label`: use ``[*]`` to match one segment or ``[**]`` to match any depth.


include_paths: list, default = None
    List of the only paths to include in the report. If only one item, you can pass it as a string.
    Supports :ref:`wildcard_paths_label`: use ``[*]`` to match one segment or ``[**]`` to match any depth.


exclude_regex_paths: list, default = None
    List of string regex paths or compiled regex paths objects to exclude from the report. If only one item, you can pass it as a string instead of a list containing only one regex path.


exclude_obj_callback
    function, default = None
    A function that takes the object and its path and returns a Boolean. If True is returned, the object is excluded from the results, otherwise it is included.
    This is to give the user a higher level of control than one can achieve via exclude_paths, exclude_regex_paths or other means.


encodings: List, default = None
    Character encodings to iterate through when we convert bytes into strings. You may want to pass an explicit list of encodings in your objects if you start getting UnicodeDecodeError from DeepHash. Also check out ignore_encoding_errors if you can get away with ignoring these errors and don't want to bother with an explicit list of encodings but it will come at the price of slightly less accuracy of the final results. Example: encodings=["utf-8", "latin-1"]


hashes: dictionary, default = empty dictionary
    A dictionary of {object or object id: object hash} to start with.
    Any object that is encountered and it is already in the hashes dictionary or its id is in the hashes dictionary,
    will re-use the hash that is provided by this dictionary instead of re-calculating
    its hash. This is typically used when you have a series of objects to be hashed and there might be repeats of the same object.


hasher: function. default = DeepHash.sha256hex
    hasher is the hashing function. The default is DeepHash.sha256hex.
    But you can pass another hash function to it if you want.
    For example a cryptographic hash function or Python's builtin hash function.
    All it needs is a function that takes the input in string format and returns the hash.

    You can use it by passing: hasher=hash for Python's builtin hash.

    The following alternative is already provided:

    - hasher=DeepHash.sha1hex

    Note that prior to DeepDiff 5.2, Murmur3 was the default hash function.
    But Murmur3 is removed from DeepDiff dependencies since then.


ignore_repetition: Boolean, default = True
    If repetitions in an iterable should cause the hash of iterable to be different.
    Note that the deepdiff diffing functionality lets this to be the default at all times.
    But if you are using DeepHash directly, you can set this parameter.


ignore_type_in_groups
    Ignore type changes between members of groups of types. For example if you want to ignore type changes between float and decimals etc. Note that this is a more granular feature. Most of the times the shortcuts provided to you are enough.
    The shortcuts are ignore_string_type_changes which by default is False and ignore_numeric_type_changes which is by default False. You can read more about those shortcuts in this page. ignore_type_in_groups gives you more control compared to the shortcuts.

    For example lets say you have specifically str and byte datatypes to be ignored for type changes. Then you have a couple of options:

    1. Set ignore_string_type_changes=True which is the default.
    2. Set ignore_type_in_groups=[(str, bytes)]. Here you are saying if we detect one type to be str and the other one bytes, do not report them as type change. It is exactly as passing ignore_type_in_groups=[DeepDiff.strings] or ignore_type_in_groups=DeepDiff.strings .

    Now what if you want also typeA and typeB to be ignored when comparing against each other?

    1. ignore_type_in_groups=[DeepDiff.strings, (typeA, typeB)]
    2. or ignore_type_in_groups=[(str, bytes), (typeA, typeB)]

ignore_string_type_changes: Boolean, default = True
    string type conversions should not affect the hash output when this is set to True.
    For example "Hello" and b"Hello" should produce the same hash.

    By setting it to True, both the string and bytes of hello return the same hash.


ignore_numeric_type_changes: Boolean, default = False
    numeric type conversions should not affect the hash output when this is set to True.
    For example 10, 10.0 and Decimal(10) should produce the same hash.
    When ignore_numeric_type_changes is set to True, all numbers are converted
    to strings with the precision of significant_digits parameter and number_format_notation notation.
    If no significant_digits is passed by the user, a default value of 12 is used.


ignore_type_subclasses
    Use ignore_type_subclasses=True so when ignoring type (class), the subclasses of that class are ignored too.


ignore_string_case
    Whether to be case-sensitive or not when comparing strings. By settings ignore_string_case=False, strings will be compared case-insensitively.


ignore_private_variables: Boolean, default = True
    Whether to exclude the private variables in the calculations or not. It only affects variables that start with double underscores (__).


ignore_encoding_errors: Boolean, default = False
    If you want to get away with UnicodeDecodeError without passing explicit character encodings, set this option to True. If you want to make sure the encoding is done properly, keep this as False and instead pass an explicit list of character encodings to be considered via the encodings parameter.

ignore_iterable_order: Boolean, default = True
    If order of items in an iterable should not cause the hash of the iterable to be different.

number_format_notation : string, default="f"
    number_format_notation is what defines the meaning of significant digits. The default value of "f" means the digits AFTER the decimal point. "f" stands for fixed point. The other option is "e" which stands for exponent notation or scientific notation.


significant_digits : int >= 0, default=None
    By default the significant_digits compares only that many digits AFTER the decimal point. However you can set override that by setting the number_format_notation="e" which will make it mean the digits in scientific notation.

    Important: This will affect ANY number comparison when it is set.

    Note: If ignore_numeric_type_changes is set to True and you have left significant_digits to the default of None, it gets automatically set to 12. The reason is that normally when numbers from 2 different types are compared, instead of comparing the values, we only report the type change. However when ignore_numeric_type_changes=True, in order compare numbers from different types to each other, we need to convert them all into strings. The significant_digits will be used to make sure we accurately convert all the numbers into strings in order to report the changes between them.

    Internally it uses "{:.Xf}".format(Your Number) to compare numbers where X=significant_digits when the number_format_notation is left as the default of "f" meaning fixed point.

    Note that "{:.3f}".format(1.1135) = 1.113, but "{:.3f}".format(1.11351) = 1.114

    For Decimals, Python's format rounds 2.5 to 2 and 3.5 to 4 (to the closest even number)

    When you set the number_format_notation="e", we use "{:.Xe}".format(Your Number) where X=significant_digits.

truncate_datetime: string, default = None
    Can take value one of 'second', 'minute', 'hour', 'day' and truncate with this value datetime objects before hashing it



**Returns**
    A dictionary of {item: item hash}.
    If your object is nested, it will build hashes of all the objects it contains too.


.. note::
    DeepHash output is not like conventional hash functions. It is a dictionary of object IDs to their hashes. This happens because DeepHash calculates the hash of the object and any other objects found within the object in a recursive manner. If you only need the hash of the object you are passing, all you need to do is to do:

    >>> from deepdiff import DeepHash
    >>> obj = {1: 2, 'a': 'b'}
    >>> DeepHash(obj)[obj] # doctest: +SKIP


**Examples**

Let's say you have a dictionary object.
    >>> from deepdiff import DeepHash
    >>> obj = {1: 2, 'a': 'b'}

If you try to hash it:
    >>> hash(obj)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: unhashable type: 'dict'

But with DeepHash:

    >>> from deepdiff import DeepHash
    >>> obj = {1: 2, 'a': 'b'}
    >>> DeepHash(obj) # doctest: +SKIP

    So what is exactly the hash of obj in this case?
    DeepHash is calculating the hash of the obj and any other object that obj contains.
    The output of DeepHash is a dictionary of object IDs to their hashes.
    In order to get the hash of obj itself, you need to use the object (or the id of object) to get its hash:

    >>> hashes = DeepHash(obj)
    >>> hashes[obj]
    'bf5478de322aa033da36bf3bcf9f0599e13a520773f50c6eb9f2487377a7929b'

    Which you can write as:

    >>> hashes = DeepHash(obj)[obj]

    At first it might seem weird why DeepHash(obj)[obj] but remember that DeepHash(obj) is a dictionary of hashes of all other objects that obj contains too.

    If you prefer to use another hashing algorithm, you can pass it using the hasher parameter.

    If you do a deep copy of the obj, it should still give you the same hash:

    >>> from copy import deepcopy
    >>> obj2 = deepcopy(obj)
    >>> DeepHash(obj2)[obj2]
    'bf5478de322aa033da36bf3bcf9f0599e13a520773f50c6eb9f2487377a7929b'

    Note that by default DeepHash will include string type differences. So if your strings were bytes:

    >>> obj3 = {1: 2, b'a': b'b'}
    >>> DeepHash(obj3)[obj3]
    '71db3231177d49f78b52a356ca206e6179417b681604d00ed703a077049e3300'

    But if you want the same hash if string types are different, set ignore_string_type_changes to True:

    >>> DeepHash(obj3, ignore_string_type_changes=True)[obj3]
    'e60c2befb84be625037c75e1e26d0bfc85a0ffc1f3cde9500f68f6eac55e5ad6'

    ignore_numeric_type_changes is by default False too.

    >>> from decimal import Decimal
    >>> obj1 = {4:10}
    >>> obj2 = {4.0: Decimal(10.0)}
    >>> DeepHash(obj1)[4] == DeepHash(obj2)[4.0]
    False

    But by setting it to True, we can get the same hash.

    >>> DeepHash(obj1, ignore_numeric_type_changes=True)[4] == DeepHash(obj2, ignore_numeric_type_changes=True)[4.0]
    True

number_format_notation: String, default = "f"
    number_format_notation is what defines the meaning of significant digits. The default value of "f" means the digits AFTER the decimal point. "f" stands for fixed point. The other option is "e" which stands for exponent notation or scientific notation.


ignore_string_type_changes: Boolean, default = True
    By setting it to True, both the string and bytes of hello return the same hash.

    >>> DeepHash(b'hello', ignore_string_type_changes=True)[b'hello']
    '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    >>> DeepHash('hello', ignore_string_type_changes=True)['hello']
    '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'


ignore_numeric_type_changes: Boolean, default = False
    For example if significant_digits=5, 1.1, Decimal(1.1) are both converted to 1.10000

    That way they both produce the same hash.

    >>> t1 = {1: 1, 2: 2.22}
    >>> DeepHash(t1)[1]
    'c1800a30c736483f13615542e7096f7973631fef8ca935ee1ed9f35fb06fd44e'
    >>> DeepHash(t1, ignore_numeric_type_changes=True)[1] == DeepHash(t1, ignore_numeric_type_changes=True)[1.0]
    True

    You can pass a list of tuples or list of lists if you have various type groups. When t1 and t2 both fall under one of these type groups, the type change will be ignored. DeepDiff already comes with 2 groups: DeepDiff.strings and DeepDiff.numbers . If you want to pass both:

    >>> from deepdiff import DeepDiff
    >>> ignore_type_in_groups = [DeepDiff.strings, DeepDiff.numbers]


ignore_type_in_groups example with custom objects:

    >>> class Burrito:
    ...     bread = 'flour'
    ...     def __init__(self):
    ...         self.spicy = True
    ...
    >>>
    >>> class Taco:
    ...     bread = 'flour'
    ...     def __init__(self):
    ...         self.spicy = True
    ...
    >>>
    >>> burrito = Burrito()
    >>> taco = Taco()
    >>>
    >>> burritos = [burrito]
    >>> tacos = [taco]
    >>>
    >>> d1 = DeepHash(burritos, ignore_type_in_groups=[(Taco, Burrito)])
    >>> d2 = DeepHash(tacos, ignore_type_in_groups=[(Taco, Burrito)])
    >>> d1[burrito] == d2[taco]
    True


ignore_type_subclasses
    Use ignore_type_subclasses=True so when ignoring type (class), the subclasses of that class are ignored too.

    >>> from deepdiff import DeepHash
    >>>
    >>> class ClassB:
    ...     def __init__(self, x):
    ...         self.x = x
    ...     def __repr__(self):
    ...         return "obj b"
    ...
    >>>
    >>> class ClassC(ClassB):
    ...     def __repr__(self):
    ...         return "obj c"
    ...
    >>> obj_b = ClassB(1)
    >>> obj_c = ClassC(1)
    >>>
    >>> # By default, subclasses are considered part of the type group.
    ... # ignore_type_in_groups=[(ClassB, )] matches ClassC too since it's a subclass.
    ... hashes_b = DeepHash(obj_b, ignore_type_in_groups=[(ClassB, )])
    >>> hashes_c = DeepHash(obj_c, ignore_type_in_groups=[(ClassB, )])
    >>> hashes_b[obj_b] == hashes_c[obj_c]
    True
    >>>
    >>> # With ignore_type_subclasses=True, only exact type matches count.
    ... # ClassC no longer matches (ClassB, ) group, so hashes differ.
    ... hashes_b = DeepHash(obj_b, ignore_type_in_groups=[(ClassB, )], ignore_type_subclasses=True)
    >>> hashes_c = DeepHash(obj_c, ignore_type_in_groups=[(ClassB, )], ignore_type_subclasses=True)
    >>> hashes_b[obj_b] != hashes_c[obj_c]
    True

ignore_string_case
    Whether to be case-sensitive or not when comparing strings. By settings ignore_string_case=False, strings will be compared case-insensitively.

    >>> from deepdiff import DeepHash
    >>> DeepHash('hello')['hello'] == DeepHash('heLLO')['heLLO']
    False
    >>> DeepHash('hello', ignore_string_case=True)['hello'] == DeepHash('heLLO', ignore_string_case=True)['heLLO']
    True

exclude_obj_callback
    function, default = None
    A function that takes the object and its path and returns a Boolean. If True is returned, the object is excluded from the results, otherwise it is included.
    This is to give the user a higher level of control than one can achieve via exclude_paths, exclude_regex_paths or other means.

    >>> def exclude_obj_callback(obj, path):
    ...     return True if isinstance(obj, str) and obj in ('x', 'y') else False
    ...
    >>> dic1 = {"x": 1, "y": 2, "z": 3}
    >>> t1 = [dic1]
    >>> t1_hash = DeepHash(t1, exclude_obj_callback=exclude_obj_callback)
    >>>
    >>> dic2 = {"z": 3}
    >>> t2 = [dic2]
    >>> t2_hash = DeepHash(t2, exclude_obj_callback=exclude_obj_callback)
    >>>
    >>> t1_hash[t1] == t2_hash[t2]
    True

number_format_notation : string, default="f"
    When numbers are converted to the string, you have the choices between "f" as fixed point and "e" as scientific notation:

    >>> t1=10002
    >>> t2=10004
    >>> t1_hash = DeepHash(t1, significant_digits=3, number_format_notation="f")
    >>> t2_hash = DeepHash(t2, significant_digits=3, number_format_notation="f")
    >>>
    >>> t1_hash[t1] == t2_hash[t2]
    False
    >>>
    >>>
    >>> # Now we use the scientific notation
    ... t1_hash = DeepHash(t1, significant_digits=3, number_format_notation="e")
    >>> t2_hash = DeepHash(t2, significant_digits=3, number_format_notation="e")
    >>>
    >>> t1_hash[t1] == t2_hash[t2]
    True

Defining your own number_to_string_func
    Lets say you want the hash of numbers below 100 to be the same for some reason.

    >>> from deepdiff import DeepHash
    >>> from deepdiff.helper import number_to_string
    >>> def custom_number_to_string(number, *args, **kwargs):
    ...     number = 100 if number < 100 else number
    ...     return number_to_string(number, *args, **kwargs)
    ...
    >>> t1 = [10, 12, 100000]
    >>> t2 = [50, 63, 100021]
    >>> t1_hash = DeepHash(t1, significant_digits=3, number_format_notation="e", number_to_string_func=custom_number_to_string)
    >>> t2_hash = DeepHash(t2, significant_digits=3, number_format_notation="e", number_to_string_func=custom_number_to_string)
    >>> t1_hash[t1] == t2_hash[t2]
    True

    So both lists produced the same hash thanks to the low significant digits for 100000 vs 100021 and also the custom_number_to_string that converted all numbers below 100 to be 100!
