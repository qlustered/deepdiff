from decimal import Decimal
from unittest import mock
from deepdiff import DeepDiff


class TestDiffMath:
    def test_math_diff(self):
        """Testing for the correct setting and usage of epsilon."""
        d1 = {"a": Decimal("3.5")}
        d2 = {"a": Decimal("4")}
        ep = 0.5
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("2.5")}
        d2 = {"a": Decimal("3")}
        ep = 0.5
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("2.5")}
        d2 = {"a": Decimal("2")}
        ep = 0.5
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("7.175")}
        d2 = {"a": Decimal("7.174")}
        ep = 0.1
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("7.175")}
        d2 = {"a": Decimal("7.174")}
        ep = 0.01
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("7.175")}
        d2 = {"a": Decimal("7.174")}
        ep = 0.001
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("7.175")}
        d2 = {"a": Decimal("7.174")}
        ep = 0.0001
        expected = {
            "values_changed": {
                "root['a']": {
                    "new_value": Decimal("7.174"),
                    "old_value": Decimal("7.175"),
                }
            }
        }
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == expected

    def test_math_diff_special_case(self):
        """Testing epsilon on a special Decimal case.
        
        Even though the Decimal looks different, math will evaluate it for us."""
        d1 = {"a": Decimal("9.709999618320632")}
        d2 = {"a": Decimal("9.710000038146973")}
        ep = 0.001
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("9.709999618320632")}
        d2 = {"a": Decimal("9.710000038146973")}
        ep = 0.0001
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("9.709999618320632")}
        d2 = {"a": Decimal("9.710000038146973")}
        ep = 0.00001
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("9.709999618320632")}
        d2 = {"a": Decimal("9.710000038146973")}
        ep = 0.000001
        res = DeepDiff(d1, d2, math_epsilon=ep)
        assert res == {}
        d1 = {"a": Decimal("9.709999618320632")}
        d2 = {"a": Decimal("9.710000038146973")}
        ep = 0.0000001
        res = DeepDiff(d1, d2, math_epsilon=ep)
        expected = {
            "values_changed": {
                "root['a']": {
                    "new_value": Decimal("9.710000038146973"),
                    "old_value": Decimal("9.709999618320632"),
                }
            }
        }
        assert res == expected

    def test_math_diff_ignore_order(self):
        """math_close will not work with ignore_order=true.
        
        Items are hashed if order is ignored, that will not work."""
        d1 = {"a": [Decimal("9.709999618320632"), Decimal("9.709999618320632")]}
        d2 = {"a": [Decimal("9.710000038146973"), Decimal("9.709999618320632")]}
        ep = 0.0001
        res = DeepDiff(d1, d2, ignore_order=False, math_epsilon=ep)
        assert res == {}

    def test_math_diff_ignore_order_warning(self, caplog):
        """math_close will not work with ignore_order=true.
        
        Items are hashed if order is ignored, that will not work."""
        d1 = {"a": [Decimal("9.709999618320632"), Decimal("9.709999618320632")]}
        d2 = {"a": [Decimal("9.710000038146973"), Decimal("9.709999618320632")]}
        ep = 0.0001
        res = DeepDiff(d1, d2, ignore_order=True, math_epsilon=ep)
        expected = {
            "iterable_item_added": {"root['a'][0]": Decimal("9.710000038146973")}
        }
        assert res == expected
        # assert "math_epsilon will be ignored." in caplog.text

    def test_ignore_numeric_type_changes_with_numeric_keys_and_no_significant_digits(self):
        """Test that ignore_numeric_type_changes works with numeric keys when significant_digits is None.
        
        This test covers the bug fix in _get_clean_to_keys_mapping where significant_digits=None
        caused a crash when number_to_string was called without the required parameter.
        """
        # Test case with numeric keys and ignore_numeric_type_changes=True, significant_digits=None
        d1 = {1: "value1", 2.5: "value2"}  
        d2 = {1.0: "value1", 2.5: "value2"}  # int vs float keys
        
        # This should not crash and should treat 1 and 1.0 as the same key
        result = DeepDiff(d1, d2, ignore_numeric_type_changes=True, significant_digits=None)
        assert result == {}

    def test_math_rel_diff(self):
        """math_rel_epsilon scales the tolerance with the magnitude of the numbers."""
        d1 = {"small": 0.001, "big": 1000000}
        d2 = {"small": 0.00101, "big": 1010000}
        res = DeepDiff(d1, d2, math_rel_epsilon=0.02)
        assert res == {}
        # The same absolute tolerance can't cover both values.
        res = DeepDiff(d1, d2, math_epsilon=0.02)
        assert res == {"values_changed": {"root['big']": {"new_value": 1010000, "old_value": 1000000}}}
        res = DeepDiff(d1, d2, math_rel_epsilon=0.001)
        expected = {
            "values_changed": {
                "root['small']": {"new_value": 0.00101, "old_value": 0.001},
                "root['big']": {"new_value": 1010000, "old_value": 1000000},
            }
        }
        assert res == expected

    def test_math_rel_diff_decimal(self):
        d1 = {"a": Decimal("7.175")}
        d2 = {"a": Decimal("7.174")}
        res = DeepDiff(d1, d2, math_rel_epsilon=0.001)
        assert res == {}
        res = DeepDiff(d1, d2, math_rel_epsilon=0.0001)
        expected = {
            "values_changed": {
                "root['a']": {
                    "new_value": Decimal("7.174"),
                    "old_value": Decimal("7.175"),
                }
            }
        }
        assert res == expected

    def test_math_rel_diff_near_zero(self):
        """A relative tolerance alone never considers a non-zero number close to zero."""
        res = DeepDiff(0.0, 1e-12, math_rel_epsilon=0.01)
        assert res == {"values_changed": {"root": {"new_value": 1e-12, "old_value": 0.0}}}
        res = DeepDiff(0.0, 1e-12, math_rel_epsilon=0.01, math_epsilon=1e-9)
        assert res == {}

    def test_math_rel_and_abs_diff(self):
        """Numbers are the same if they are within either tolerance, like math.isclose."""
        d1 = [0.001, 1000]
        d2 = [0.002, 1001]
        res = DeepDiff(d1, d2, math_epsilon=0.01, math_rel_epsilon=0.01)
        assert res == {}
        res = DeepDiff(d1, d2, math_epsilon=0.01)
        assert res == {"values_changed": {"root[1]": {"new_value": 1001, "old_value": 1000}}}
        res = DeepDiff(d1, d2, math_rel_epsilon=0.01)
        assert res == {"values_changed": {"root[0]": {"new_value": 0.002, "old_value": 0.001}}}

    @mock.patch('deepdiff.diff.logger')
    def test_math_rel_diff_ignore_order_warning(self, mock_logger):
        d1 = {"a": [Decimal("9.709999618320632"), Decimal("9.709999618320632")]}
        d2 = {"a": [Decimal("9.710000038146973"), Decimal("9.709999618320632")]}
        res = DeepDiff(d1, d2, ignore_order=True, math_rel_epsilon=0.0001)
        expected = {
            "iterable_item_added": {"root['a'][0]": Decimal("9.710000038146973")}
        }
        assert res == expected
        assert "math_rel_epsilon will not have an effect when comparing nested objects" in mock_logger.warning.call_args[0][0]
