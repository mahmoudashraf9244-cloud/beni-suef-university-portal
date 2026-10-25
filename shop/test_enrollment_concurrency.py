from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase

from .models import Activity, Category, Enrollment, StudentProfile, Trainer
from .services import EnrollmentResult, enroll_student


@skipUnless(connection.vendor == 'sqlite', 'SQLite enrollment concurrency regression tests')
class EnrollmentConcurrencyTests(TransactionTestCase):
    today = date(2026, 10, 24)

    def setUp(self):
        super().setUp()
        self.assertEqual(
            connection.settings_dict['NAME'],
            connection.creation._get_test_db_name(),
            'Concurrency tests must run on the Django test database.',
        )
        category = Category.objects.create(name='Concurrent enrollment workshops')
        trainer = Trainer.objects.create(
            full_name='Concurrency Trainer', email='concurrency-trainer@example.com',
        )
        self.activity = Activity.objects.create(
            title='Only one remaining seat', category=category, trainer=trainer,
            start_date=self.today + timedelta(days=1), duration=2,
            max_students=1, availability_status=True,
        )
        self.students = [
            StudentProfile.objects.create(
                user=User.objects.create_user(username=f'concurrent-student-{number}'),
            )
            for number in range(2)
        ]
        date_patch = patch('django.utils.timezone.localdate', return_value=self.today)
        date_patch.start()
        self.addCleanup(date_patch.stop)

    def simultaneous_enrollments(self, student_ids):
        # Each thread gets its own Django connection. Synchronize BEFORE the
        # service transaction, so a lock holder never waits for its competitor.
        start = Barrier(len(student_ids) + 1, timeout=10)
        activity_id = self.activity.pk

        def enroll_from_independent_connection(student_id):
            close_old_connections()
            try:
                start.wait()
                return enroll_student(student_id=student_id, activity_id=activity_id)
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=len(student_ids)) as executor:
            futures = [executor.submit(enroll_from_independent_connection, pk) for pk in student_ids]
            start.wait()
            return [future.result(timeout=30) for future in futures]

    def test_two_students_competing_for_the_last_seat_cannot_overbook(self):
        student_ids = [student.pk for student in self.students]
        results = self.simultaneous_enrollments(student_ids)
        self.assertCountEqual(results, [EnrollmentResult.CREATED, EnrollmentResult.FULL])
        self.assertEqual(Enrollment.objects.filter(activity=self.activity).count(), 1)
        winner = student_ids[results.index(EnrollmentResult.CREATED)]
        self.assertEqual(Enrollment.objects.get().student_id, winner)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.max_students, 1)

    def test_simultaneous_duplicate_requests_create_exactly_one_enrollment(self):
        student_id = self.students[0].pk
        results = self.simultaneous_enrollments([student_id, student_id])
        self.assertCountEqual(
            results, [EnrollmentResult.CREATED, EnrollmentResult.ALREADY_ENROLLED],
        )
        self.assertEqual(Enrollment.objects.count(), 1)
        enrollment = Enrollment.objects.get()
        self.assertEqual(enrollment.student_id, student_id)
        self.assertEqual(enrollment.activity_id, self.activity.pk)
