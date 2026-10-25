import sqlite3
from datetime import date, timedelta
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import OperationalError, connection
from django.db.models.query import QuerySet
from django.test import TestCase

from .models import Activity, Category, Enrollment, StudentProfile, Trainer
from .services import EnrollmentResult, enroll_student


class EnrollmentServiceTests(TestCase):
    today = date(2026, 10, 24)

    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='Enrollment workshops')
        trainer = Trainer.objects.create(
            full_name='Enrollment Trainer', email='enrollment-trainer@example.com',
        )
        cls.activity = Activity.objects.create(
            title='Enrollment service workshop', category=category, trainer=trainer,
            start_date=cls.today + timedelta(days=1), duration=2,
            max_students=2, availability_status=True,
        )
        cls.student = StudentProfile.objects.create(
            user=User.objects.create_user(username='enrollment-student'),
        )
        cls.other_student = StudentProfile.objects.create(
            user=User.objects.create_user(username='other-enrollment-student'),
        )
        cls.inactive_student = StudentProfile.objects.create(
            user=User.objects.create_user(username='inactive-enrollment-student', is_active=False),
        )

    def setUp(self):
        date_patch = patch('django.utils.timezone.localdate', return_value=self.today)
        date_patch.start()
        self.addCleanup(date_patch.stop)

    def enroll(self, student=None, activity=None):
        return enroll_student(
            student_id=(student or self.student).pk,
            activity_id=(activity or self.activity).pk,
        )

    def test_creates_enrollment_for_the_requested_student_and_activity(self):
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        enrollment = Enrollment.objects.get()
        self.assertEqual(enrollment.student_id, self.student.pk)
        self.assertEqual(enrollment.activity_id, self.activity.pk)
        self.assertIsNotNone(enrollment.enrolled_at)

    def test_repeat_request_does_not_create_another_enrollment(self):
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        original = Enrollment.objects.get()
        self.assertEqual(self.enroll(), EnrollmentResult.ALREADY_ENROLLED)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.get().pk, original.pk)
        self.assertEqual(Enrollment.objects.get().enrolled_at, original.enrolled_at)

    def test_existing_enrollment_remains_idempotent_after_closure_or_completion(self):
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        for changes in (
            {'availability_status': False},
            {'availability_status': True, 'start_date': self.today - timedelta(days=5)},
        ):
            with self.subTest(changes=changes):
                Activity.objects.filter(pk=self.activity.pk).update(**changes)
                self.assertEqual(self.enroll(), EnrollmentResult.ALREADY_ENROLLED)
                self.assertEqual(Enrollment.objects.count(), 1)

    def test_capacity_rejects_another_student_after_the_last_seat(self):
        Activity.objects.filter(pk=self.activity.pk).update(max_students=1)
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        self.assertEqual(self.enroll(student=self.other_student), EnrollmentResult.FULL)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertFalse(Enrollment.objects.filter(student=self.other_student).exists())

    def test_duplicate_request_is_idempotent_even_when_activity_is_full(self):
        Activity.objects.filter(pk=self.activity.pk).update(max_students=1)
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        self.assertEqual(self.enroll(), EnrollmentResult.ALREADY_ENROLLED)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_manually_closed_activity_rejects_enrollment(self):
        Activity.objects.filter(pk=self.activity.pk).update(availability_status=False)
        self.assertEqual(self.enroll(), EnrollmentResult.CLOSED)
        self.assertFalse(Enrollment.objects.exists())

    def test_completed_activity_rejects_enrollment_regardless_of_manual_flag(self):
        for available in (True, False):
            with self.subTest(available=available):
                Activity.objects.filter(pk=self.activity.pk).update(
                    start_date=self.today - timedelta(days=5), availability_status=available,
                )
                self.assertEqual(self.enroll(), EnrollmentResult.COMPLETED)
                self.assertFalse(Enrollment.objects.exists())

    def test_end_date_is_inclusive_but_the_following_day_rejects_enrollment(self):
        Activity.objects.filter(pk=self.activity.pk).update(
            start_date=self.today - timedelta(days=1), duration=2,
        )
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        with patch('django.utils.timezone.localdate', return_value=self.today + timedelta(days=1)):
            self.assertEqual(self.enroll(student=self.other_student), EnrollmentResult.COMPLETED)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_enabled_activity_without_a_start_date_accepts_enrollment(self):
        Activity.objects.filter(pk=self.activity.pk).update(start_date=None)
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_disabled_activity_without_a_start_date_rejects_enrollment(self):
        Activity.objects.filter(pk=self.activity.pk).update(
            start_date=None, availability_status=False,
        )
        self.assertEqual(self.enroll(), EnrollmentResult.CLOSED)
        self.assertFalse(Enrollment.objects.exists())

    def test_inactive_student_cannot_enroll(self):
        self.assertEqual(self.enroll(student=self.inactive_student), EnrollmentResult.INELIGIBLE)
        self.assertFalse(Enrollment.objects.exists())

    def test_missing_student_cannot_enroll_or_create_a_profile(self):
        profile_count = StudentProfile.objects.count()
        self.assertEqual(
            enroll_student(student_id=999999, activity_id=self.activity.pk),
            EnrollmentResult.INELIGIBLE,
        )
        self.assertEqual(StudentProfile.objects.count(), profile_count)
        self.assertFalse(Enrollment.objects.exists())

    def test_unknown_or_out_of_range_activity_is_not_found(self):
        for activity_id in (0, -1, 999999, 2**63):
            with self.subTest(activity_id=activity_id):
                with self.assertRaises(Activity.DoesNotExist):
                    enroll_student(student_id=self.student.pk, activity_id=activity_id)
        self.assertFalse(Enrollment.objects.exists())

    def test_enrollment_does_not_change_stored_activity_fields(self):
        before = Activity.objects.values().get(pk=self.activity.pk)
        self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        self.assertEqual(Activity.objects.values().get(pk=self.activity.pk), before)

    @staticmethod
    def sqlite_operation_error(code):
        driver_error = sqlite3.OperationalError('Simulated SQLite operation failure')
        driver_error.sqlite_errorcode = code
        error = OperationalError('Simulated SQLite operation failure')
        error.__cause__ = driver_error
        return error

    @skipUnless(connection.vendor == 'sqlite', 'SQLite contention retry contract')
    def test_persistent_busy_or_locked_errors_stop_after_bounded_retries(self):
        for code in (
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
            sqlite3.SQLITE_LOCKED | (1 << 8),
        ):
            with self.subTest(code=code):
                error = self.sqlite_operation_error(code)
                with patch.object(QuerySet, 'update', side_effect=error) as update, patch(
                    'shop.services.sleep'
                ) as pause:
                    self.assertEqual(self.enroll(), EnrollmentResult.BUSY)
                self.assertEqual(update.call_count, 4)
                self.assertEqual(pause.call_count, 3)
                self.assertFalse(Enrollment.objects.exists())

    @skipUnless(connection.vendor == 'sqlite', 'SQLite contention retry contract')
    def test_transient_lock_is_retried_in_a_fresh_transaction(self):
        real_update = QuerySet.update
        attempts = 0

        def fail_once_then_update(queryset, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise self.sqlite_operation_error(sqlite3.SQLITE_BUSY)
            return real_update(queryset, **kwargs)

        with patch.object(QuerySet, 'update', autospec=True, side_effect=fail_once_then_update), patch(
            'shop.services.sleep'
        ) as pause:
            self.assertEqual(self.enroll(), EnrollmentResult.CREATED)
        self.assertEqual(attempts, 2)
        pause.assert_called_once()
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_unrelated_database_error_is_not_hidden_as_contention(self):
        error = self.sqlite_operation_error(sqlite3.SQLITE_IOERR)
        with patch.object(QuerySet, 'update', side_effect=error) as update, patch(
            'shop.services.sleep'
        ) as pause:
            with self.assertRaises(OperationalError) as raised:
                self.enroll()
        self.assertIs(raised.exception, error)
        update.assert_called_once()
        pause.assert_not_called()
        self.assertFalse(Enrollment.objects.exists())
