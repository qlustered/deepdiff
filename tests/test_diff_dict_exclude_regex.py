import re
from types import SimpleNamespace

import pytest

from deepdiff import DeepDiff


class TestDictionaryRegexExclusion:
    @pytest.mark.parametrize("exclude_regex_paths", [
        r"\['foo.'\]", [r"\['foo.'\]"], re.compile(r"\['foo.'\]"),
    ])
    @pytest.mark.parametrize("threshold_to_diff_deeper", [0, 0.33, 1])
    def test_dictionary_threshold_excludes_regex_paths(self, exclude_regex_paths, threshold_to_diff_deeper):
        t1 = {'a': [1, 2, [3, {'foo1': 'bar'}]]}
        t2 = {'a': [1, 2, [3, {'foo2': 'bar'}]]}

        diff = DeepDiff(t1, t2, exclude_regex_paths=exclude_regex_paths,
                        threshold_to_diff_deeper=threshold_to_diff_deeper)

        assert diff == {}

    def test_dictionary_threshold_regex_keeps_unexcluded_change(self):
        t1 = {'a': 1, 'foo1': 0, 'foo2': 0, 'foo3': 0}
        t2 = {'a': 2, 'foo4': 0, 'foo5': 0, 'foo6': 0}

        diff = DeepDiff(t1, t2, exclude_regex_paths=r"\['foo.'\]")

        assert diff == {'values_changed': {"root['a']": {'old_value': 1, 'new_value': 2}}}

    @pytest.mark.parametrize("options", [{}, {'exclude_regex_paths': r"\['absent'\]"}])
    def test_dictionary_threshold_without_matching_regex(self, options):
        t1 = {'a': 1}
        t2 = {'b': 2}

        diff = DeepDiff(t1, t2, **options)

        assert diff == {'values_changed': {'root': {'old_value': t1, 'new_value': t2}}}

    @pytest.mark.parametrize("include_paths", [["root"], "root[**]"])
    def test_dictionary_threshold_regex_preserves_include_precedence(self, include_paths):
        t1 = {'a': 1, 'foo1': 0}
        t2 = {'a': 2, 'foo2': 0}

        diff = DeepDiff(t1, t2, include_paths=include_paths, exclude_regex_paths=r"\['foo\d'\]",
                        threshold_to_diff_deeper=1)

        assert diff == {'values_changed': {'root': {'old_value': t1, 'new_value': t2}}}

    @pytest.mark.parametrize("t1,t2,pattern", [
        ({1: 'a'}, {2: 'b'}, r"\[\d\]"),
        ({"foo'1": 'a'}, {"foo'2": 'b'}, r"\[\"foo'\d\"\]"),
    ])
    def test_dictionary_threshold_regex_uses_reported_key_paths(self, t1, t2, pattern):
        assert DeepDiff(t1, t2, exclude_regex_paths=pattern) == {}

    def test_dictionary_threshold_regex_uses_attribute_paths(self):
        t1 = SimpleNamespace(a=1, foo1=0)
        t2 = SimpleNamespace(a=1, foo2=0)

        diff = DeepDiff(t1, t2, exclude_regex_paths=r"\.foo\d$", threshold_to_diff_deeper=1)

        assert diff == {}

    def test_dictionary_threshold_regex_does_not_evaluate_child_callbacks(self):
        paths = []

        def exclude_obj_callback(obj, path):
            paths.append(path)
            return False

        t1 = {'a': 1}
        t2 = {'b': 2}
        diff = DeepDiff(t1, t2, exclude_regex_paths=r"\['absent'\]",
                        exclude_obj_callback=exclude_obj_callback)

        assert diff == {'values_changed': {'root': {'old_value': t1, 'new_value': t2}}}
        assert set(paths) == {'root'}

    def test_dictionary_threshold_regex_preserves_private_variable_filter(self):
        t1 = {'a': 1, '__private1': 0}
        t2 = {'a': 2, '__private2': 0}

        diff = DeepDiff(t1, t2, exclude_regex_paths=r"\['absent'\]")

        assert diff == {'values_changed': {"root['a']": {'old_value': 1, 'new_value': 2}}}

    def test_dictionary_threshold_regex_uses_original_changed_keys_when_ignoring_case(self):
        t1 = {'FOO1': 0}
        t2 = {'FOO2': 0}

        assert DeepDiff(t1, t2, ignore_string_case=True, exclude_regex_paths=r"\['FOO\d'\]") == {}

    def test_dictionary_threshold_regex_keeps_dissimilar_unexcluded_keys(self):
        t1 = {'a': 1, 'foo1': 0}
        t2 = {'b': 2, 'foo2': 0}

        diff = DeepDiff(t1, t2, exclude_regex_paths=r"\['foo\d'\]")

        assert diff == {'values_changed': {'root': {'old_value': t1, 'new_value': t2}}}

    @pytest.mark.parametrize("exclude_paths", [
        ["root['other1']", "root['other2']"], ["root[**]['other1']", "root[**]['other2']"],
    ])
    def test_dictionary_threshold_regex_combines_with_other_path_exclusions(self, exclude_paths):
        t1 = {'foo1': 0, 'other1': 0}
        t2 = {'foo2': 0, 'other2': 0}

        diff = DeepDiff(t1, t2, exclude_regex_paths=r"\['foo\d'\]", exclude_paths=exclude_paths)

        assert diff == {}
