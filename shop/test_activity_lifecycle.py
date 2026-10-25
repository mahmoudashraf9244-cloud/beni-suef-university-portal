from datetime import date, datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from .models import Activity


class ActivityLifecycleTests(SimpleTestCase):
    def make_activity(self, start_date=None, duration=3, available=True):
        return Activity(
            title='Lifecycle workshop',
            start_date=start_date,
            duration=duration,
            max_students=20,
            availability_status=available,
        )

    def test_one_day_activity_includes_its_start_date(self):
        activity = self.make_activity(start_date=date(2026, 10, 24), duration=1)
        self.assertEqual(activity.end_date, date(2026, 10, 24))
        for today, expected, joinable in (
            (date(2026, 10, 23), ('Upcoming', 'is-upcoming'), True),
            (date(2026, 10, 24), ('Available', 'is-available'), True),
            (date(2026, 10, 25), ('Completed', 'is-completed'), False),
        ):
            with self.subTest(today=today):
                self.assertEqual(activity.get_status(today), expected)
                self.assertEqual(activity.is_joinable_on(today), joinable)

    def test_multiday_activity_remains_available_through_its_end_date(self):
        activity = self.make_activity(start_date=date(2026, 10, 24), duration=3)
        self.assertEqual(activity.end_date, date(2026, 10, 26))
        for day in (24, 25, 26):
            with self.subTest(day=day):
                today = date(2026, 10, day)
                self.assertEqual(activity.get_status(today), ('Available', 'is-available'))
                self.assertTrue(activity.is_joinable_on(today))
        self.assertEqual(
            activity.get_status(date(2026, 10, 27)), ('Completed', 'is-completed')
        )
        self.assertFalse(activity.is_joinable_on(date(2026, 10, 27)))

    def test_future_activity_is_upcoming_and_joinable(self):
        activity = self.make_activity(start_date=date(2026, 11, 1))
        self.assertEqual(
            activity.get_status(date(2026, 10, 24)), ('Upcoming', 'is-upcoming')
        )
        self.assertTrue(activity.is_joinable_on(date(2026, 10, 24)))

    def test_missing_start_date_remains_available_when_enabled(self):
        activity = self.make_activity()
        self.assertIsNone(activity.end_date)
        self.assertEqual(
            activity.get_status(date(2026, 10, 24)), ('Available', 'is-available')
        )
        self.assertTrue(activity.is_joinable_on(date(2026, 10, 24)))

    def test_missing_start_date_is_closed_when_disabled(self):
        activity = self.make_activity(available=False)
        self.assertIsNone(activity.end_date)
        self.assertEqual(
            activity.get_status(date(2026, 10, 24)), ('Closed', 'is-closed')
        )
        self.assertFalse(activity.is_joinable_on(date(2026, 10, 24)))

    def test_manual_closure_overrides_upcoming_and_active_status(self):
        for start in (date(2026, 10, 24), date(2026, 11, 1)):
            with self.subTest(start=start):
                activity = self.make_activity(start_date=start, available=False)
                self.assertEqual(
                    activity.get_status(date(2026, 10, 24)), ('Closed', 'is-closed')
                )
                self.assertFalse(activity.is_joinable_on(date(2026, 10, 24)))

    def test_completed_status_overrides_manual_closure(self):
        activity = self.make_activity(
            start_date=date(2026, 10, 20), duration=2, available=False
        )
        self.assertEqual(
            activity.get_status(date(2026, 10, 24)), ('Completed', 'is-completed')
        )
        self.assertFalse(activity.is_joinable_on(date(2026, 10, 24)))

    def test_end_date_handles_leap_days_and_year_boundaries(self):
        for start, expected in (
            (date(2028, 2, 28), date(2028, 2, 29)),
            (date(2026, 12, 31), date(2027, 1, 1)),
        ):
            with self.subTest(start=start):
                self.assertEqual(
                    self.make_activity(start_date=start, duration=2).end_date,
                    expected,
                )

    def test_lifecycle_properties_use_cairo_local_date(self):
        activity = self.make_activity(start_date=date(2026, 10, 24), duration=1)
        # It is already October 25 in Cairo while the UTC date is October 24.
        instant = datetime(2026, 10, 24, 22, 30, tzinfo=datetime_timezone.utc)
        with timezone.override('Africa/Cairo'), patch(
            'django.utils.timezone.now', return_value=instant
        ):
            self.assertEqual(activity.get_status(), ('Completed', 'is-completed'))
            self.assertEqual(activity.status_label, 'Completed')
            self.assertEqual(activity.status_class, 'is-completed')
            self.assertFalse(activity.is_joinable)

    def test_explicit_today_does_not_depend_on_the_system_clock(self):
        activity = self.make_activity(start_date=date(2026, 10, 24), duration=1)
        with patch('shop.models.timezone.localdate', side_effect=AssertionError):
            self.assertEqual(
                activity.get_status(date(2026, 10, 24)), ('Available', 'is-available')
            )
            self.assertTrue(activity.is_joinable_on(date(2026, 10, 24)))

    def test_huge_positive_duration_does_not_overflow_status_or_end_date(self):
        activity = self.make_activity(start_date=date.min, duration=2_147_483_647)
        self.assertIsNone(activity.end_date)
        self.assertEqual(activity.get_status(date.max), ('Available', 'is-available'))
        self.assertTrue(activity.is_joinable_on(date.max))

    def test_last_supported_date_can_be_an_inclusive_end_date(self):
        activity = self.make_activity(
            start_date=date.max - timedelta(days=2), duration=3
        )
        self.assertEqual(activity.end_date, date.max)
        self.assertEqual(activity.get_status(date.max), ('Available', 'is-available'))

    def test_end_date_beyond_supported_calendar_is_unrepresentable(self):
        activity = self.make_activity(start_date=date.max, duration=2)
        self.assertIsNone(activity.end_date)
        self.assertEqual(activity.get_status(date.max), ('Available', 'is-available'))
        self.assertTrue(activity.is_joinable_on(date.max))
