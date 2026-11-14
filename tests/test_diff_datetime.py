import pytz
import pytest
from datetime import date, datetime, time, timedelta, timezone
from deepdiff import DeepDiff


class TestDiffDatetime:
    @pytest.mark.parametrize('old_offset,new_offset', [
        (timedelta(), timedelta(hours=1)),
        (timedelta(hours=1), timedelta(hours=2)),
        (timedelta(hours=-5), timedelta(hours=5, minutes=30)),
        (timedelta(microseconds=1), timedelta(microseconds=2)),
    ])
    @pytest.mark.parametrize('truncate_datetime', [None, 'day'])
    def test_timezone_diff(self, old_offset, new_offset, truncate_datetime):
        old = timezone(old_offset)
        new = timezone(new_offset)

        assert DeepDiff(old, new, truncate_datetime=truncate_datetime) == {
            'values_changed': {'root': {'old_value': old, 'new_value': new}}
        }

    def test_timezone_diff_in_dictionary(self):
        old = timezone(timedelta(hours=1))
        new = timezone(timedelta(hours=2))

        assert DeepDiff({'timezone': old}, {'timezone': new}) == {
            'values_changed': {"root['timezone']": {'old_value': old, 'new_value': new}}
        }

    @pytest.mark.parametrize('ignore_order', [False, True])
    def test_timezone_diff_in_list(self, ignore_order):
        old = timezone(timedelta(hours=1))
        new = timezone(timedelta(hours=2))

        assert DeepDiff([old], [new], ignore_order=ignore_order) == {
            'values_changed': {'root[0]': {'old_value': old, 'new_value': new}}
        }

    def test_timezone_diff_in_set(self):
        old = timezone(timedelta(hours=1))
        new = timezone(timedelta(hours=2))

        assert DeepDiff({old}, {new}) == {
            'set_item_removed': {f'root[{old}]'},
            'set_item_added': {f'root[{new}]'},
        }

    @pytest.mark.parametrize('offset', [timedelta(), timedelta(hours=1), timedelta(hours=-5)])
    def test_timezone_equal_offsets_different_names(self, offset):
        old = timezone(offset)
        new = timezone(offset, 'custom name')

        assert DeepDiff(old, new) == {}
        assert DeepDiff([old], [new], ignore_order=True) == {}
        assert DeepDiff({old}, {new}) == {}

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
