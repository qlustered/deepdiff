:orphan:

.. |qluster_link| raw:: html

   <a href="/qluster"><strong>Qluster</strong></a>

.. admonition:: DeepDiff is now part of |qluster_link|.

    *If you're building workflows around data validation and correction,* `Qluster </qluster>`__ *gives your team a structured way to manage rules, review failures, approve fixes, and reuse decisions—without building the entire system from scratch.*

DeepDiff Module
===============

Deep Difference of dictionaries, iterables, strings and almost any other object.
It will recursively look for all the changes.

**Parameters**

t1 : A dictionary, list, string or any python object that has __dict__ or __slots__
    This is the first item to be compared to the second item

t2 : dictionary, list, string or almost any python object that has __dict__ or __slots__
    The second item is to be compared to the first one

cutoff_distance_for_pairs : 1 >= float >= 0, default=0.3
    :ref:`cutoff_distance_for_pairs_label` What is the threshold to consider 2 items as pairs.
    Note that it is only used when ignore_order = True.

cutoff_intersection_for_pairs : 1 >= float >= 0, default=0.7
    :ref:`cutoff_intersection_for_pairs_label` What is the threshold to calculate pairs of items between 2 iterables.
    For example 2 iterables that have nothing in common, do not need their pairs to be calculated.
    Note that it is only used when ignore_order = True.

cache_size : int >= 0, default=0
    :ref:`cache_size_label` Cache size to be used to improve the performance. A cache size of zero means it is disabled.
    Using the cache_size can dramatically improve the diff performance especially for the nested objects at the cost of more memory usage.

cache_purge_level: int, 0, 1, or 2. default=1
    :ref:`cache_purge_level` defines what objects in DeepDiff should be deleted to free the memory once the diff object is calculated. If this value is set to zero, most of the functionality of the diff object is removed and the most memory is released. A value of 1 preserves all the functionalities of the diff object. A value of 2 also preserves the cache and hashes that were calculated during the diff calculations. In most cases the user does not need to have those objects remained in the diff unless for investigation purposes.

cache_tuning_sample_size : int >= 0, default = 0
    :ref:`cache_tuning_sample_size_label` This is an experimental feature. It works hands in hands with the :ref:`cache_size_label`. When cache_tuning_sample_size is set to anything above zero, it will sample the cache usage with the passed sample size and decide whether to use the cache or not. And will turn it back on occasionally during the diffing process. This option can be useful if you are not sure if you need any cache or not. However you will gain much better performance with keeping this parameter zero and running your diff with different cache sizes and benchmarking to find the optimal cache size.

custom_operators : BaseOperator subclasses, default = None
    :ref:`custom_operators_label` if you are considering whether they are fruits or not. In that case, you can pass a *custom_operators* for the job.

default_timezone : datetime.timezone subclasses or pytz datetimes, default = datetime.timezone.utc
    :ref:`default_timezone_label` defines the default timezone. If a datetime is timezone naive, which means it doesn't have a timezone, we assume the datetime is in this timezone. Also any datetime that has a timezone will be converted to this timezone so the datetimes can be compared properly all in the same timezone. Note that Python's default behavior assumes the default timezone is your local timezone. DeepDiff's default is UTC, not your local time zone.

encodings: List, default = None
    :ref:`encodings_label` Character encodings to iterate through when we convert bytes into strings. You may want to pass an explicit list of encodings in your objects if you start getting UnicodeDecodeError from DeepHash. Also check out :ref:`ignore_encoding_errors_label` if you can get away with ignoring these errors and don't want to bother with an explicit list of encodings but it will come at the price of slightly less accuracy of the final results. Example: encodings=["utf-8", "latin-1"]

exclude_paths: list, default = None
    :ref:`exclude_paths_label`
    List of paths to exclude from the report. If only one item, you can path it as a string.
    Supports :ref:`wildcard_paths_label`: use ``[*]`` to match one segment or ``[**]`` to match any depth.

exclude_regex_paths: list, default = None
    :ref:`exclude_regex_paths_label`
    List of string regex paths or compiled regex paths objects to exclude from the report. If only one item, you can pass it as a string or regex compiled object.

exclude_types: list, default = None
    :ref:`exclude_types_label`
    List of object types to exclude from the report.

exclude_obj_callback: function, default = None
    :ref:`exclude_obj_callback_label`
    A function that takes the object and its path and returns a Boolean. If True is returned, the object is excluded from the results, otherwise it is included.
    This is to give the user a higher level of control than one can achieve via exclude_paths, exclude_regex_paths or other means.

exclude_obj_callback_strict: function, default = None
    :ref:`exclude_obj_callback_strict_label`
    A function that works the same way as exclude_obj_callback, but excludes elements from the result only if the function returns True for both elements.

include_paths: list, default = None
    :ref:`include_paths_label`
    List of the only paths to include in the report. If only one item is in the list, you can pass it as a string.
    Supports :ref:`wildcard_paths_label`: use ``[*]`` to match one segment or ``[**]`` to match any depth.

include_obj_callback: function, default = None
    :ref:`include_obj_callback_label`
    A function that takes the object and its path and returns a Boolean. If True is returned, the object is included in the results, otherwise it is excluded.
    This is to give the user a higher level of control than one can achieve via include_paths.

include_obj_callback_strict: function, default = None
    :ref:`include_obj_callback_strict_label`
    A function that works the same way as include_obj_callback, but includes elements in the result only if the function returns True for both elements.

get_deep_distance: Boolean, default = False
    :ref:`get_deep_distance_label` will get you the deep distance between objects. The distance is a number between 0 and 1 where zero means there is no diff between the 2 objects and 1 means they are very different. Note that this number should only be used to compare the similarity of 2 objects and nothing more. The algorithm for calculating this number may or may not change in the future releases of DeepDiff.

group_by: String or a list of size 2, default=None
    :ref:`group_by_label` can be used when dealing with the list of dictionaries. It converts them from lists to a single dictionary with the key defined by group_by. The common use case is when reading data from a flat CSV, and the primary key is one of the columns in the CSV. We want to use the primary key instead of the CSV row number to group the rows. The group_by can do 2D group_by by passing a list of 2 keys.

group_by_sort_key: String or a function
    :ref:`group_by_sort_key_label` is used to define how dictionaries are sorted if multiple ones fall under one group. When this parameter is used, group_by converts the lists of dictionaries into a dictionary of keys to lists of dictionaries. Then, :ref:`group_by_sort_key_label` is used to sort between the list.

hasher: default = DeepHash.sha256hex
    Hash function to be used. If you don't want SHA256, you can use your own hash function
    by passing hasher=hash. This is for advanced usage and normally you don't need to modify it.

ignore_order : Boolean, default=False
    :ref:`ignore_order_label` ignores order of elements when comparing iterables (lists)
    Normally ignore_order does not report duplicates and repetition changes.
    In order to report repetitions, set report_repetition=True in addition to ignore_order=True

ignore_order_func : Function, default=None
    :ref:`ignore_order_func_label` Sometimes single *ignore_order* parameter is not enough to do a diff job,
    you can use *ignore_order_func* to determine whether the order of certain paths should be ignored

ignore_string_type_changes: Boolean, default = False
    :ref:`ignore_string_type_changes_label`
    Whether to ignore string type changes or not. For example b"Hello" vs. "Hello" are considered the same if ignore_string_type_changes is set to True.

ignore_numeric_type_changes: Boolean, default = False
    :ref:`ignore_numeric_type_changes_label`
    Whether to ignore numeric type changes or not. For example 10 vs. 10.0 are considered the same if ignore_numeric_type_changes is set to True.

ignore_type_in_groups: Tuple or List of Tuples, default = None
    :ref:`ignore_type_in_groups_label`
    ignores types when t1 and t2 are both within the same type group.

ignore_type_subclasses: Boolean, default = False
    :ref:`ignore_type_subclasses_label`
    ignore type (class) changes when dealing with the subclasses of classes that were marked to be ignored.

.. Note::
    ignore_type_subclasses was incorrectly doing the reverse of its job up until DeepDiff 6.7.1
    Please make sure to flip it in your use cases, when upgrading from older versions to 7.0.0 or above.

ignore_uuid_types: Boolean, default = False
    :ref:`ignore_uuid_types_label`
    Whether to ignore UUID vs string type differences when comparing. When set to True, comparing a UUID object with its string representation will not report as a type change.

ignore_string_case: Boolean, default = False
    :ref:`ignore_string_case_label`
    Whether to be case-sensitive or not when comparing strings. By setting ignore_string_case=True, strings will be compared case-insensitively.

ignore_nan_inequality: Boolean, default = False
    :ref:`ignore_nan_inequality_label`
    Whether to ignore float('nan') inequality in Python.


ignore_private_variables: Boolean, default = True
    :ref:`ignore_private_variables_label`
    Whether to exclude the private variables in the calculations or not. It only affects variables that start with double underscores (__).


ignore_encoding_errors: Boolean, default = False
    :ref:`ignore_encoding_errors_label` If you want to get away with UnicodeDecodeError without passing explicit character encodings, set this option to True. If you want to make sure the encoding is done properly, keep this as False and instead pass an explicit list of character encodings to be considered via the :ref:`encodings_label` parameter.


zip_ordered_iterables: Boolean, default = False
    :ref:`zip_ordered_iterables_label`:
    When comparing ordered iterables such as lists, DeepDiff tries to find the smallest difference between the two iterables to report. That means that items in the two lists are not paired individually in the order of appearance in the iterables. Sometimes, that is not the desired behavior. Set this flag to True to make DeepDiff pair and compare the items in the iterables in the order they appear.

iterable_compare_func:
    :ref:`iterable_compare_func_label`:
    There are times that we want to guide DeepDiff as to what items to compare with other items. In such cases we can pass a iterable_compare_func that takes a function pointer to compare two items. The function takes three parameters (x, y, level) and should return True if it is a match, False if it is not a match or raise CannotCompare if it is unable to compare the two.


log_frequency_in_sec: Integer, default = 0
    :ref:`log_frequency_in_sec_label`
    How often to log the progress. The default of 0 means logging progress is disabled.
    If you set it to 20, it will log every 20 seconds. This is useful only when running DeepDiff
    on massive objects that will take a while to run. If you are only dealing with small objects, keep it at 0 to disable progress logging.

log_scale_similarity_threshold: float, default = 0.1
    :ref:`use_log_scale_label` along with :ref:`log_scale_similarity_threshold_label` can be used to ignore small changes in numbers by comparing their differences in logarithmic space. This is different than ignoring the difference based on significant digits.

log_stacktrace: Boolean, default = False
    If True, we log the stacktrace when logging errors. Otherwise we only log the error message.

max_passes: Integer, default = 10000000
    :ref:`max_passes_label` defined the maximum number of passes to run on objects to pin point what exactly is different. This is only used when ignore_order=True. A new pass is started each time 2 iterables are compared in a way that every single item that is different from the first one is compared to every single item that is different in the second iterable.

max_diffs: Integer, default = None
    :ref:`max_diffs_label` defined the maximum number of diffs to run on objects to pin point what exactly is different. This is only used when ignore_order=True

math_epsilon: Decimal, default = None
    :ref:`math_epsilon_label` uses Python's built in Math.isclose. It defines a tolerance value which is passed to math.isclose(). Any numbers that are within the tolerance will not report as being different. Any numbers outside of that tolerance will show up as different.

math_rel_epsilon: Decimal, default = None
    :ref:`math_rel_epsilon_label` is the relative counterpart of math_epsilon. It is passed to math.isclose() as rel_tol. Any numbers whose difference is within that fraction of the larger of the two magnitudes will not report as being different. It can be combined with math_epsilon.

number_format_notation : string, default="f"
    :ref:`number_format_notation_label` is what defines the meaning of significant digits. The default value of "f" means the digits AFTER the decimal point. "f" stands for fixed point. The other option is "e" which stands for exponent notation or scientific notation.

number_to_string_func : function, default=None
    :ref:`number_to_string_func_label` is an advanced feature to give the user the full control into overriding how numbers are converted to strings for comparison. The default function is defined in https://github.com/seperman/deepdiff/blob/master/deepdiff/helper.py and is called number_to_string. You can define your own function to do that.

progress_logger: log function, default = logger.info
    :ref:`progress_logger_label` defines what logging function to use specifically for progress reporting. This function is only used when progress logging is enabled which happens by setting log_frequency_in_sec to anything above zero.

report_repetition : Boolean, default=False
    :ref:`report_repetition_label` reports repetitions when set True
    It only works when ignore_order is set to True too.

significant_digits : int >= 0, default=None
    :ref:`significant_digits_label` defines the number of digits AFTER the decimal point to be used in the comparison. However you can override that by setting the number_format_notation="e" which will make it mean the digits in scientific notation.

truncate_datetime: string, default = None
    :ref:`truncate_datetime_label` can take value one of 'second', 'minute', 'hour', 'day' and truncate with this value datetime objects before hashing it

threshold_to_diff_deeper: float, default = 0.33
    :ref:`threshold_to_diff_deeper_label` is a number between 0 and 1. When comparing dictionaries that have a small intersection of keys, we will report the dictionary as a new_value instead of reporting individual keys changed. If you set it to zero, you get the same results as DeepDiff 7.0.1 and earlier, which means this feature is disabled. The new default is 0.33 which means if less that one third of keys between dictionaries intersect, report it as a new object.

use_enum_value: Boolean, default=False
    :ref:`use_enum_value_label` makes it so when diffing enum, we use the enum's value. It makes it so comparing an enum to a string or any other value is not reported as a type change.

use_log_scale: Boolean, default=False
    :ref:`use_log_scale_label` along with :ref:`log_scale_similarity_threshold_label` can be used to ignore small changes in numbers by comparing their differences in logarithmic space. This is different than ignoring the difference based on significant digits.

verbose_level: 2 >= int >= 0, default = 1
    Higher verbose level shows you more details.
    For example verbose level 1 shows what dictionary item are added or removed.
    And verbose level 2 shows the value of the items that are added or removed too.

view: string, default = text
    :ref:`view_label`
    Views are different "formats" of results. Each view comes with its own features.
    The choices are text (the default) and tree.
    The text view is the original format of the results.
    The tree view allows you to traverse through the tree of results. So you can traverse through the tree and see what items were compared to what.


**Returns**

    A DeepDiff object that has already calculated the difference of the 2 items. The format of the object is chosen by the view parameter.

**Supported data types**

int, string, unicode, dictionary, list, tuple, set, frozenset, OrderedDict, NamedTuple, Numpy, custom objects and more!

.. Note::
    |:mega:| **Please fill out our** `fast 10-question survey <https://tally.so/r/J98MPY>`__ so that we can learn how & why you use DeepDiff, and what improvements we should make. Thank you! |:dancers:|
