from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Activity, Category, Enrollment, StudentProfile, Trainer
from .services import EnrollmentResult


class EnrollmentViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='Enrollment workshops')
        trainer = Trainer.objects.create(full_name='Enrollment Trainer', email='enrollment@example.com')
        cls.activity = Activity.objects.create(
            title='Secure enrollment workshop', category=category, trainer=trainer,
            start_date=timezone.localdate() + timedelta(days=2), duration=2, max_students=1,
        )
        cls.user = User.objects.create_user(username='enrollment-student')
        cls.profile = StudentProfile.objects.create(user=cls.user)
        cls.other_user = User.objects.create_user(username='other-enrollment-student')
        cls.other_profile = StudentProfile.objects.create(user=cls.other_user)

    def setUp(self):
        self.detail_url = reverse('shop:activity_detail', args=[self.activity.pk])
        self.enroll_url = reverse('shop:enroll_activity', args=[self.activity.pk])

    def test_guest_post_requires_login_and_does_not_enroll(self):
        response = self.client.post(self.enroll_url)
        self.assertRedirects(response, f'{reverse("shop:login")}?next={self.enroll_url}')
        self.assertFalse(Enrollment.objects.exists())

    def test_authenticated_get_is_not_allowed_and_does_not_enroll(self):
        self.client.force_login(self.user)
        response = self.client.get(self.enroll_url)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(Enrollment.objects.exists())

    def test_authenticated_student_post_enrolls_and_updates_detail(self):
        self.client.force_login(self.user)
        response = self.client.post(self.enroll_url, follow=True)
        self.assertRedirects(response, self.detail_url)
        enrollment = Enrollment.objects.get()
        self.assertEqual(enrollment.student_id, self.profile.pk)
        self.assertEqual(enrollment.activity_id, self.activity.pk)
        self.assertContains(response, 'You are enrolled')
        self.assertNotContains(response, '>Join Activity<')
        self.assertEqual(response.context['remaining_seats'], 0)

    def test_student_identity_and_redirect_cannot_be_overridden_by_post(self):
        self.client.force_login(self.user)
        response = self.client.post(self.enroll_url, {
            'student': self.other_profile.pk,
            'student_id': self.other_profile.pk,
            'user': self.other_user.pk,
            'next': 'https://attacker.example/',
        })
        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Enrollment.objects.get().student_id, self.profile.pk)

    def test_repeated_post_is_idempotent(self):
        self.client.force_login(self.user)
        self.client.post(self.enroll_url)
        response = self.client.post(self.enroll_url, follow=True)
        self.assertContains(response, 'You are already enrolled')
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_missing_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(self.enroll_url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Enrollment.objects.exists())

    def test_valid_csrf_token_allows_enrollment(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(self.detail_url)
        response = client.post(self.enroll_url, {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        })
        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Enrollment.objects.get().student_id, self.profile.pk)

    def test_authenticated_account_without_student_profile_is_forbidden(self):
        account = User.objects.create_user(username='account-without-student-profile')
        self.client.force_login(account)
        response = self.client.post(self.enroll_url)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Enrollment.objects.exists())
        detail = self.client.get(self.detail_url)
        self.assertContains(detail, 'Student account required')
        self.assertNotContains(detail, '>Join Activity<')

    def test_unknown_activity_returns_404_without_enrollment(self):
        self.client.force_login(self.user)
        for activity_id in (0, 999999, 2**63):
            with self.subTest(activity_id=activity_id):
                response = self.client.post(reverse('shop:enroll_activity', args=[activity_id]))
                self.assertEqual(response.status_code, 404)
        self.assertFalse(Enrollment.objects.exists())

    def test_full_activity_hides_join_and_rejects_post(self):
        Enrollment.objects.create(student=self.other_profile, activity=self.activity)
        for authenticated in (False, True):
            with self.subTest(authenticated=authenticated):
                if authenticated:
                    self.client.force_login(self.user)
                response = self.client.get(self.detail_url)
                self.assertContains(response, 'Activity full')
                self.assertNotContains(response, '>Join Activity<')
                self.assertEqual(response.context['remaining_seats'], 0)
        response = self.client.post(self.enroll_url, follow=True)
        self.assertContains(response, 'There are no remaining seats')
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_completed_and_closed_activities_reject_forged_post(self):
        self.client.force_login(self.user)
        for changes, message in (
            ({'availability_status': False}, 'This activity is closed'),
            ({'availability_status': True, 'start_date': timezone.localdate() - timedelta(days=3)},
             'This activity has completed'),
        ):
            with self.subTest(message=message):
                Activity.objects.filter(pk=self.activity.pk).update(**changes)
                response = self.client.post(self.enroll_url, follow=True)
                self.assertContains(response, message)
                self.assertFalse(Enrollment.objects.exists())

    def test_existing_enrollment_remains_visible_after_completion(self):
        Enrollment.objects.create(student=self.profile, activity=self.activity)
        Activity.objects.filter(pk=self.activity.pk).update(
            start_date=timezone.localdate() - timedelta(days=3), availability_status=False,
        )
        self.client.force_login(self.user)
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'You are enrolled')
        self.assertEqual(response.context['activity'].status_label, 'Completed')
        self.assertNotContains(response, '>Join Activity<')

    def test_full_activity_is_excluded_from_home_and_available_dashboard_count(self):
        Enrollment.objects.create(student=self.profile, activity=self.activity)
        home = self.client.get(reverse('shop:home'))
        self.assertNotContains(home, self.activity.title)
        self.client.force_login(self.user)
        profile = self.client.get(reverse('shop:student_profile'))
        self.assertEqual(profile.context['dashboard_stats']['available_activities'], 0)
        self.assertEqual(profile.context['dashboard_stats']['enrolled_activities'], 1)

    def test_profile_only_shows_own_enrollments_and_preserves_history(self):
        other_activity = Activity.objects.create(
            title='Private other student activity', category=self.activity.category,
            trainer=self.activity.trainer, duration=1, max_students=2,
        )
        Enrollment.objects.create(student=self.profile, activity=self.activity)
        Enrollment.objects.create(student=self.other_profile, activity=other_activity)
        Activity.objects.filter(pk=self.activity.pk).update(
            start_date=timezone.localdate() - timedelta(days=3),
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse('shop:student_profile'))
        self.assertContains(response, 'My activities')
        self.assertContains(response, self.activity.title)
        self.assertContains(response, 'Completed')
        self.assertNotContains(response, other_activity.title)
        self.assertEqual(len(response.context['enrollments']), 1)

    def test_view_handles_ineligible_or_busy_service_results(self):
        self.client.force_login(self.user)
        with patch('shop.views.enroll_student', return_value=EnrollmentResult.INELIGIBLE):
            self.assertEqual(self.client.post(self.enroll_url).status_code, 403)
        with patch('shop.views.enroll_student', return_value=EnrollmentResult.BUSY):
            response = self.client.post(self.enroll_url, follow=True)
        self.assertContains(response, 'Registration is busy')
        self.assertFalse(Enrollment.objects.exists())

    def test_get_detail_and_profile_never_create_an_enrollment(self):
        self.client.force_login(self.user)
        self.client.get(self.detail_url)
        self.client.get(reverse('shop:student_profile'))
        self.assertFalse(Enrollment.objects.exists())
