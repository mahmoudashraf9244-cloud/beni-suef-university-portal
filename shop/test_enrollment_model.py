from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import Activity, Category, Enrollment, StudentProfile, Trainer


class EnrollmentTestData:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        category = Category.objects.create(name='Enrollment workshops')
        trainer = Trainer.objects.create(
            full_name='Enrollment Trainer', email='enrollment-trainer@example.com'
        )
        cls.activity = Activity.objects.create(
            title='Enrollment workshop',
            category=category,
            trainer=trainer,
            start_date=timezone.localdate() + timedelta(days=7),
            duration=2,
            max_students=20,
        )
        cls.other_activity = Activity.objects.create(
            title='Another enrollment workshop',
            category=category,
            trainer=trainer,
            duration=1,
            max_students=20,
        )
        cls.user = User.objects.create_user(username='enrollment-student')
        cls.student = StudentProfile.objects.create(user=cls.user)
        other_user = User.objects.create_user(username='another-enrollment-student')
        cls.other_student = StudentProfile.objects.create(user=other_user)


class EnrollmentModelTests(EnrollmentTestData, TestCase):
    def test_enrollment_records_relationships_and_creation_time(self):
        enrollment = Enrollment.objects.create(
            student=self.student, activity=self.activity
        )
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.activity, self.activity)
        self.assertTrue(timezone.is_aware(enrollment.enrolled_at))
        self.assertEqual(list(self.student.enrollments.all()), [enrollment])
        self.assertEqual(list(self.activity.enrollments.all()), [enrollment])

    def test_duplicate_student_activity_pair_is_rejected_by_database(self):
        Enrollment.objects.create(student=self.student, activity=self.activity)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(student=self.student, activity=self.activity)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_duplicate_student_activity_pair_fails_model_validation(self):
        Enrollment.objects.create(student=self.student, activity=self.activity)
        duplicate = Enrollment(student=self.student, activity=self.activity)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_students_can_join_different_activities_and_share_an_activity(self):
        for student, activity in (
            (self.student, self.activity),
            (self.student, self.other_activity),
            (self.other_student, self.activity),
        ):
            Enrollment.objects.create(student=student, activity=activity)
        self.assertEqual(Enrollment.objects.count(), 3)

    def test_enrollment_relationships_are_required(self):
        for values in ({'student': self.student}, {'activity': self.activity}):
            with self.subTest(values=tuple(values)):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Enrollment.objects.create(**values)

    def test_enrollment_foreign_keys_reject_missing_records(self):
        for values in (
            {'student_id': 999999, 'activity': self.activity},
            {'student': self.student, 'activity_id': 999999},
        ):
            with self.subTest(values=tuple(values)):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Enrollment.objects.create(**values)
                    # SQLite defers FK errors until commit; check inside the
                    # savepoint so this TestCase can roll back the invalid row.
                    connection.check_constraints(table_names=['shop_enrollment'])

    def test_activity_student_and_user_deletion_cannot_remove_enrollment_history(self):
        enrollment = Enrollment.objects.create(
            student=self.student, activity=self.activity
        )
        for record in (self.activity, self.student, self.user):
            with self.subTest(model=record._meta.label):
                with self.assertRaises(ProtectedError):
                    record.delete()
                self.assertTrue(Enrollment.objects.filter(pk=enrollment.pk).exists())
        self.assertTrue(Activity.objects.filter(pk=self.activity.pk).exists())
        self.assertTrue(StudentProfile.objects.filter(pk=self.student.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_capacity_cannot_be_reduced_below_existing_enrollment_count(self):
        for student in (self.student, self.other_student):
            Enrollment.objects.create(student=student, activity=self.activity)
        self.activity.max_students = 1
        with self.assertRaises(ValidationError) as error:
            self.activity.full_clean()
        self.assertIn('max_students', error.exception.message_dict)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.max_students, 20)
        self.assertEqual(self.activity.enrollments.count(), 2)

    def test_capacity_can_equal_or_exceed_existing_enrollment_count(self):
        for student in (self.student, self.other_student):
            Enrollment.objects.create(student=student, activity=self.activity)
        for capacity in (2, 3):
            with self.subTest(capacity=capacity):
                self.activity.max_students = capacity
                self.activity.full_clean()
                self.activity.save()
                self.activity.refresh_from_db()
                self.assertEqual(self.activity.max_students, capacity)
                self.assertEqual(self.activity.enrollments.count(), 2)

    def test_invalid_capacity_keeps_field_errors_without_enrollment_queries(self):
        for capacity in ('not-a-number', None, 0, -1):
            with self.subTest(capacity=capacity):
                self.activity.max_students = capacity
                with CaptureQueriesContext(connection) as queries:
                    with self.assertRaises(ValidationError) as error:
                        self.activity.full_clean()
                self.assertIn('max_students', error.exception.message_dict)
                self.assertFalse(any(
                    'shop_enrollment' in query['sql'] for query in queries
                ))

    def test_unsaved_activity_capacity_validation_does_not_query_enrollments(self):
        activity = Activity(activity_id=999999, max_students=1)
        with self.assertNumQueries(0):
            activity.clean()


class EnrollmentAdminReadOnlyTests(EnrollmentTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.administrator = User.objects.create_superuser(
            username='enrollment-admin',
            email='enrollment-admin@example.com',
            password=None,
        )
        cls.enrollment = Enrollment.objects.create(
            student=cls.student, activity=cls.activity
        )

    def setUp(self):
        self.client.force_login(self.administrator)

    def test_admin_allows_viewing_and_searching_enrollments(self):
        response = self.client.get(
            reverse('admin:shop_enrollment_changelist'),
            {'q': self.user.username},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.activity.title)
        self.assertContains(response, self.user.username)
        detail = self.client.get(
            reverse('admin:shop_enrollment_change', args=[self.enrollment.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, 'name="_save"')
        self.assertNotContains(detail, 'name="_addanother"')

    def test_even_superuser_has_no_admin_write_permissions_or_actions(self):
        request = RequestFactory().get('/admin/shop/enrollment/')
        request.user = self.administrator
        model_admin = admin.site._registry[Enrollment]
        self.assertTrue(model_admin.has_view_permission(request, self.enrollment))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, self.enrollment))
        self.assertFalse(model_admin.has_delete_permission(request, self.enrollment))
        self.assertEqual(model_admin.get_actions(request), {})

    def test_admin_rejects_direct_add_requests(self):
        url = reverse('admin:shop_enrollment_add')
        self.assertEqual(self.client.get(url).status_code, 403)
        response = self.client.post(
            url, {'student': self.other_student.pk, 'activity': self.activity.pk}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_admin_rejects_direct_change_requests(self):
        response = self.client.post(
            reverse('admin:shop_enrollment_change', args=[self.enrollment.pk]),
            {'student': self.other_student.pk, 'activity': self.other_activity.pk},
        )
        self.assertEqual(response.status_code, 403)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.student_id, self.student.pk)
        self.assertEqual(self.enrollment.activity_id, self.activity.pk)

    def test_admin_rejects_direct_delete_requests(self):
        url = reverse('admin:shop_enrollment_delete', args=[self.enrollment.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 403)
        self.assertTrue(Enrollment.objects.filter(pk=self.enrollment.pk).exists())

    def test_forged_bulk_delete_action_cannot_remove_enrollments(self):
        self.client.post(
            reverse('admin:shop_enrollment_changelist'),
            {
                'action': 'delete_selected',
                '_selected_action': [self.enrollment.pk],
                'post': 'yes',
            },
        )
        self.assertTrue(Enrollment.objects.filter(pk=self.enrollment.pk).exists())

    def test_activity_admin_cannot_reduce_capacity_below_enrollment_count(self):
        Enrollment.objects.create(student=self.other_student, activity=self.activity)
        response = self.client.post(
            reverse('admin:shop_activity_change', args=[self.activity.pk]),
            {
                'title': self.activity.title,
                'category': self.activity.category_id,
                'trainer': self.activity.trainer_id,
                'start_date': self.activity.start_date.isoformat(),
                'duration': self.activity.duration,
                'max_students': 1,
                'level': self.activity.level,
                'availability_status': 'on',
                'prerequisites': self.activity.prerequisites,
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Maximum students cannot be lower than the number of enrolled students.',
        )
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.max_students, 20)
        self.assertEqual(self.activity.enrollments.count(), 2)
