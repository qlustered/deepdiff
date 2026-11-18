import pytest
import pytz
from datetime import date, datetime, time, timedelta, timezone
from deepdiff import DeepDiff, DeepHash


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

    def test_truncate_datetime_with_timedelta(self):
        """truncate_datetime must not crash on timedelta (no .replace())."""
        for truncate_datetime in ('second', 'minute', 'hour', 'day'):
            d1 = {"a": timedelta(days=1)}
            d2 = {"a": timedelta(days=1)}
            assert not DeepDiff(d1, d2, truncate_datetime=truncate_datetime)
            d2 = {"a": timedelta(days=2)}
            assert DeepDiff(d1, d2, truncate_datetime=truncate_datetime)

    @pytest.mark.parametrize('truncate_datetime, value1, value2', [
        ('second', '2020-05-17T22:15:30.100', '2020-05-17T22:15:30.900'),
        ('minute', '2020-05-17T22:15:30', '2020-05-17T22:15:59'),
        ('hour', '2020-05-17T22:15', '2020-05-17T22:45'),
        ('day', '2020-05-17T08:15', '2020-05-17T22:45'),
    ])
    def test_truncate_datetime_not_applied_to_np_datetime64_hash(self, truncate_datetime, value1, value2):
        """Intended behaviour: truncate_datetime applies only to datetime and time objects.

        np.datetime64 values are hashed untruncated, so two values that differ only
        below the truncation unit still get different hashes.
        """
        np = pytest.importorskip("numpy")
        t1 = np.datetime64(value1)
        t2 = np.datetime64(value2)
        t1_copy = np.datetime64(value1)

        h1 = DeepHash(t1, truncate_datetime=truncate_datetime)
        h2 = DeepHash(t2, truncate_datetime=truncate_datetime)
        h1_copy = DeepHash(t1_copy, truncate_datetime=truncate_datetime)

        assert h1[t1] != h2[t2]
        assert h1[t1] == h1_copy[t1_copy]

    def test_truncate_datetime_not_applied_to_timedelta(self):
        """Intended behaviour: truncate_datetime applies only to datetime and time objects.

        A sub-second timedelta difference is still reported under truncate_datetime='second'.
        """
        t1 = timedelta(seconds=1, microseconds=1)
        t2 = timedelta(seconds=1)
        diff = DeepDiff({"a": t1}, {"a": t2}, truncate_datetime='second')
        assert {"values_changed": {"root['a']": {"new_value": t2, "old_value": t1}}} == diff

    def test_truncate_datetime_with_ignore_order_only_applies_to_datetime_and_time(self):
        """Intended behaviour: truncate_datetime applies only to datetime and time objects.

        With ignore_order=True, datetimes differing below the truncation unit are equal,
        while np.datetime64 and timedelta values are still compared exactly.
        """
        np = pytest.importorskip("numpy")

        dt1 = datetime(2020, 5, 17, 22, 15, 30)
        dt2 = datetime(2020, 5, 17, 22, 15, 59)
        assert not DeepDiff([dt1], [dt2], truncate_datetime='minute', ignore_order=True)

        np1 = np.datetime64('2020-05-17T22:15:30')
        np2 = np.datetime64('2020-05-17T22:15:59')
        diff = DeepDiff([np1], [np2], truncate_datetime='minute', ignore_order=True)
        assert {"values_changed": {"root[0]": {"new_value": np2, "old_value": np1}}} == diff

        td1 = timedelta(seconds=1, microseconds=1)
        td2 = timedelta(seconds=1)
        diff = DeepDiff([td1], [td2], truncate_datetime='second', ignore_order=True)
        assert {"values_changed": {"root[0]": {"new_value": td2, "old_value": td1}}} == diff
