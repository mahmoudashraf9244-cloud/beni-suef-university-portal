from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Activity, Category, Trainer


class ActivityLifecycleViewTests(TestCase):
    today = date(2026, 10, 24)

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Lifecycle workshops')
        cls.trainer = Trainer.objects.create(
            full_name='Lifecycle Trainer', email='lifecycle@example.com',
        )
        cls.student = User.objects.create_user(username='lifecycle-student')

        def activity(title, start_date, duration=1, available=True):
            return Activity.objects.create(
                title=title, category=cls.category, trainer=cls.trainer,
                start_date=start_date, duration=duration, max_students=10,
                availability_status=available,
            )

        cls.completed = [
            activity(f'Completed workshop {number}', cls.today - timedelta(days=20), 3)
            for number in range(4)
        ]
        cls.completed_closed = activity(
            'Completed disabled workshop', cls.today - timedelta(days=5), available=False,
        )
        cls.ending_today = activity('Ending today workshop', cls.today - timedelta(days=1), 2)
        cls.upcoming = activity('Upcoming workshop', cls.today + timedelta(days=1), 2)
        cls.later = activity('Later workshop', cls.today + timedelta(days=2), 2)
        cls.unscheduled = activity('Enabled without date', None)
        cls.closed = activity('Manually closed workshop', cls.today + timedelta(days=3), available=False)
        cls.unscheduled_closed = activity('Disabled without date', None, available=False)

    def setUp(self):
        date_patch = patch('django.utils.timezone.localdate', return_value=self.today)
        date_patch.start()
        self.addCleanup(date_patch.stop)

    def test_completed_activities_stay_in_catalogue_and_search(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('shop:activity_list'), {'q': 'Completed'})
        second = self.client.get(reverse('shop:activity_list'), {'q': 'Completed', 'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 5)
        self.assertContains(response, 'class="availability is-completed"', count=3)
        self.assertContains(second, 'class="availability is-completed"', count=2)
        combined = response.content.decode() + second.content.decode()
        for activity in self.completed + [self.completed_closed]:
            self.assertIn(activity.title, combined)
            self.assertIn(reverse('shop:activity_detail', args=[activity.pk]), combined)

    def test_catalogue_pagination_keeps_all_statuses(self):
        self.client.force_login(self.student)
        first = self.client.get(reverse('shop:activity_list'))
        pages = [first] + [self.client.get(reverse('shop:activity_list'), {'page': number})
                           for number in range(2, first.context['page_obj'].paginator.num_pages + 1)]
        ids = {
            activity.pk
            for response in pages
            for activity in response.context['activities']
        }
        self.assertEqual(first.context['page_obj'].paginator.count, 11)
        self.assertEqual(ids, set(Activity.objects.values_list('pk', flat=True)))

    def test_home_excludes_completed_before_selecting_three_featured_activities(self):
        response = self.client.get(reverse('shop:home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [activity.pk for activity in response.context['activities']],
            [self.unscheduled.pk, self.ending_today.pk, self.upcoming.pk],
        )
        for activity in self.completed + [self.completed_closed, self.closed]:
            self.assertNotContains(response, activity.title)

    def test_dashboard_available_count_uses_same_eligibility_as_home(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('shop:student_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['dashboard_stats']['available_activities'], 4)

    def test_completed_detail_disables_join_for_guests_and_authenticated_students(self):
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(self.student)
            for activity in (self.completed[0], self.completed_closed):
                with self.subTest(authenticated=authenticated, activity=activity.title):
                    response = self.client.get(reverse('shop:activity_detail', args=[activity.pk]))
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'Activity completed')
                    self.assertContains(response, 'This activity has ended')
                    self.assertNotContains(response, 'Join Activity')
                    self.assertNotContains(response, 'class="btn btn-primary join-button"')
                    self.assertEqual(response.context['activity'].status_label, 'Completed')

    def test_activity_ending_today_still_allows_join_and_shows_end_date(self):
        response = self.client.get(reverse('shop:activity_detail', args=[self.ending_today.pk]))
        self.assertContains(response, 'Log in to see full details')
        self.assertContains(response, 'End date')
        self.assertEqual(response.context['activity'].end_date, self.today)
        self.assertEqual(response.context['activity'].status_label, 'Available')

    def test_missing_date_obeys_administrator_availability_choice(self):
        for activity, status, join_allowed in (
            (self.unscheduled, 'Available', True),
            (self.unscheduled_closed, 'Closed', False),
        ):
            with self.subTest(status=status):
                response = self.client.get(reverse('shop:activity_detail', args=[activity.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['activity'].status_label, status)
                self.assertContains(response, 'Not specified')
                if join_allowed:
                    self.assertContains(response, 'Log in to see full details')
                else:
                    self.assertContains(response, 'Activity closed')
                    self.assertNotContains(response, 'Join Activity')

    def test_detail_completes_the_day_after_its_inclusive_end_date(self):
        with patch('django.utils.timezone.localdate', return_value=self.today + timedelta(days=1)):
            response = self.client.get(reverse('shop:activity_detail', args=[self.ending_today.pk]))
        self.assertContains(response, 'Activity completed')
        self.assertNotContains(response, 'Join Activity')

    def test_get_requests_do_not_change_stored_availability(self):
        before = list(Activity.objects.order_by('pk').values())
        self.client.get(reverse('shop:home'))
        self.client.get(reverse('shop:activity_list'))
        self.client.get(reverse('shop:activity_detail', args=[self.completed[0].pk]))
        self.assertEqual(list(Activity.objects.order_by('pk').values()), before)
