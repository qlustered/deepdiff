import numpy as np
import pytest
import pytz
from datetime import date, datetime, time, timedelta, timezone
from deepdiff import DeepDiff


class TestDiffDatetime:
    def test_datetime_diff(self):
        """Testing for the correct setting and usage of epsilon."""
        d1 = {"a": datetime(2023, 7, 5, 10, 11, 12)}
        d2 = {"a": datetime(2023, 7, 5, 10, 11, 12)}
        res = DeepDiff(d1, d2)
        assert res == {}

        res = DeepDiff(d1, d2, ignore_numeric_type_changes=True)
        assert res == {}

        d1 = {"a": datetime(2023, 7, 5, 10, 11, 12)}
        d2 = {"a": datetime(2023, 7, 5, 11, 11, 12)}
        res = DeepDiff(d1, d2)
        expected = {
            "values_changed": {
                "root['a']": {
                    "new_value": datetime(2023, 7, 5, 11, 11, 12, tzinfo=timezone.utc),
                    "old_value": datetime(2023, 7, 5, 10, 11, 12, tzinfo=timezone.utc),
                }
            }
        }
        assert res == expected


    def test_date_diff(self):
        """Testing for the correct setting and usage of epsilon."""
        d1 = {"a": date(2023, 7, 5)}
        d2 = {"a": date(2023, 7, 5)}
        res = DeepDiff(d1, d2)
        assert res == {}

        # this usage failed in version >=6.0, <=6.3.0
        res = DeepDiff(d1, d2, ignore_numeric_type_changes=True)
        assert res == {}

        d1 = {"a": date(2023, 7, 5)}
        d2 = {"a": date(2023, 7, 6)}
        res = DeepDiff(d1, d2)
        expected = {
            "values_changed": {
                "root['a']": {
                    "new_value": date(2023, 7, 6),
                    "old_value": date(2023, 7, 5),
                }
            }
        }
        assert res == expected

    def test_time_diff(self):
        """Testing for the correct setting and usage of epsilon."""
        d1 = {"a": time(10, 11, 12)}
        d2 = {"a": time(10, 11, 12)}
        res = DeepDiff(d1, d2)
        assert res == {}

        res = DeepDiff(d1, d2, ignore_numeric_type_changes=True)
        assert res == {}

        d1 = {"a": time(10, 11, 12)}
        d2 = {"a": time(11, 11, 12)}
        res = DeepDiff(d1, d2)
        expected = {
            "values_changed": {
                "root['a']": {
                    "new_value": time(11, 11, 12),
                    "old_value": time(10, 11, 12),
                }
            }
        }
        assert res == expected

    def test_diffs_datetimes_different_timezones(self):
        dt_utc = datetime(2025, 2, 3, 12, 0, 0, tzinfo=pytz.utc)  # UTC timezone
        # Convert it to another timezone (e.g., New York)
        dt_ny = dt_utc.astimezone(pytz.timezone('America/New_York'))
        assert dt_utc == dt_ny
        diff = DeepDiff(dt_utc, dt_ny)
        assert not diff

        t1 = [dt_utc, dt_ny]
        t2 = [dt_ny, dt_utc]
        assert not DeepDiff(t1, t2)
        assert not DeepDiff(t1, t2, ignore_order=True)

        t2 = [dt_ny, dt_utc, dt_ny]
        assert not DeepDiff(t1, t2, ignore_order=True)

    def test_diffs_datetimes_in_different_timezones(self):
        dt_utc = datetime(2025, 2, 3, 12, 0, 0, tzinfo=pytz.utc)  # UTC timezone
        dt_utc2 = datetime(2025, 2, 3, 11, 0, 0, tzinfo=pytz.utc)  # UTC timezone
        dt_ny = dt_utc.astimezone(pytz.timezone('America/New_York'))
        dt_ny2 = dt_utc2.astimezone(pytz.timezone('America/New_York'))
        diff = DeepDiff(dt_ny, dt_ny2)
        assert {
            "values_changed": {
                "root": {
                    "new_value": dt_utc2,
                    "old_value": dt_utc,
                }
            }
        } == diff
        diff2 = DeepDiff(dt_ny, dt_ny2, default_timezone=pytz.timezone('America/New_York'))
        assert {
            "values_changed": {
                "root": {
                    "new_value": dt_ny2,
                    "old_value": dt_ny,
                }
            }
        } == diff2

    def test_datetime_within_array_with_timezone_diff(self):
        d1 = [datetime(2020, 8, 31, 13, 14, 1)]
        d2 = [datetime(2020, 8, 31, 13, 14, 1, tzinfo=timezone.utc)]

        assert d1 != d2, "Python doesn't think these are the same datetimes"
        assert not DeepDiff(d1, d2)
        assert not DeepDiff(d1, d2, ignore_order=True)
        assert not DeepDiff(d1, d2, truncate_datetime='second')


class TestTemporalDictionaryKeys:
    def test_ignore_numeric_types_with_datetime_key(self):
        key = datetime(2020, 5, 17, 22, 15)
        assert DeepDiff({key: 10.0}, {key: 10}, ignore_numeric_type_changes=True) == {}

    @pytest.mark.parametrize("key", [
        datetime(2020, 5, 17, 22, 15),
        datetime(2020, 5, 17, 22, 15, tzinfo=timezone.utc),
        date(2020, 5, 17),
        time(22, 15),
        timedelta(days=2, seconds=3),
        np.datetime64("2020-05-17T22:15"),
    ])
    @pytest.mark.parametrize("options", [
        {"ignore_numeric_type_changes": True},
        {"ignore_string_case": True},
        {"ignore_string_type_changes": True},
        {"ignore_string_case": True, "significant_digits": 3},
        {"ignore_string_type_changes": True, "significant_digits": 3},
    ])
    def test_temporal_keys_with_key_cleaning(self, key, options):
        assert DeepDiff({key: "value"}, {key: "value"}, **options) == {}

    @pytest.mark.parametrize("first, second, paths", [
        (datetime(2020, 5, 17, 22, 15), datetime(2020, 5, 17, 22, 16),
         ("number:2020-05-17 22:15:00", "number:2020-05-17 22:16:00")),
        (date(2020, 5, 17), date(2020, 5, 18),
         ("number:2020-05-17", "number:2020-05-18")),
        (time(22, 15), time(22, 16), ("number:22:15:00", "number:22:16:00")),
        (timedelta(seconds=1), timedelta(seconds=2), ("number:0:00:01", "number:0:00:02")),
        (np.datetime64("2020-05-17"), np.datetime64("2020-05-18"),
         ("number:2020-05-17", "number:2020-05-18")),
    ])
    def test_distinct_temporal_keys_keep_their_values(self, first, second, paths):
        diff = DeepDiff(
            {first: "old-first", second: "old-second"},
            {first: "new-first", second: "new-second"},
            ignore_numeric_type_changes=True,
            view="tree",
        )
        assert set(diff) == {"values_changed"}
        changes = diff["values_changed"]
        assert len(changes) == 2
        assert {
            change.path(output_format="list")[0]: (change.t1, change.t2)
            for change in changes
        } == {
            paths[0]: ("old-first", "new-first"),
            paths[1]: ("old-second", "new-second"),
        }
