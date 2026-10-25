from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Activity, Category, StudentProfile, Trainer


class PortalTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Technology')
		self.other_category = Category.objects.create(name='Creative Practice')
		self.trainer = Trainer.objects.create(
			full_name='Dr. Sam Taylor',
			email='sam@example.com',
		)
		self.activity = Activity.objects.create(
			title='Digital Foundations',
			short_description='A practical technology workshop.',
			full_description='Learn the foundations of digital work.',
			category=self.category,
			trainer=self.trainer,
			start_date=date.today() + timedelta(days=14),
			duration=5,
			max_students=20,
			availability_status=True,
		)
		self.closed_activity = Activity.objects.create(
			title='Closed Studio',
			category=self.other_category,
			trainer=self.trainer,
			start_date=date.today(),
			duration=2,
			max_students=10,
			availability_status=False,
		)
		self.user_data = {
			'username': 'student1',
			'first_name': 'Taylor',
			'last_name': 'Student',
			'email': 'student@example.com',
			'password': 'StrongPass123!',
		}
		self.user = User.objects.create_user(**self.user_data)
		StudentProfile.objects.create(user=self.user)

	def test_home_page_loads(self):
		response = self.client.get(reverse('shop:home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Learn something that stays with you.')
		self.assertContains(response, self.activity.title)

	def test_activities_page_loads(self):
		response = self.client.get(reverse('shop:activity_list'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.activity.title)
		self.assertContains(response, 'Upcoming')
		self.assertContains(response, 'Closed')

	def test_activity_search_filters_by_title(self):
		response = self.client.get(reverse('shop:activity_list'), {'q': 'Digital'})
		self.assertContains(response, self.activity.title)
		self.assertNotContains(response, self.closed_activity.title)

	def test_category_filter_filters_activities(self):
		response = self.client.get(
			reverse('shop:activity_list'),
			{'category': self.other_category.category_id},
		)
		self.assertContains(response, self.closed_activity.title)
		self.assertNotContains(response, self.activity.title)

	def test_search_and_category_filter_work_together(self):
		response = self.client.get(
			reverse('shop:activity_list'),
			{'q': 'Closed', 'category': self.other_category.category_id},
		)
		self.assertContains(response, self.closed_activity.title)
		self.assertNotContains(response, self.activity.title)

	def test_activity_detail_page_loads(self):
		response = self.client.get(
			reverse('shop:activity_detail', args=[self.activity.activity_id])
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, self.activity.full_description)
		self.assertContains(response, 'Upcoming')

	def test_activity_entry_and_join_action_use_detail_destination(self):
		list_response = self.client.get(reverse('shop:activity_list'))
		detail_path = reverse('shop:activity_detail', args=[self.activity.activity_id])
		self.assertContains(list_response, f'class="activity-card-link" href="{detail_path}"')
		detail_response = self.client.get(detail_path)
		self.assertContains(detail_response, f'next={detail_path}')
		self.assertContains(detail_response, 'Log in to see full details')

	def test_registration_preserves_activity_destination(self):
		detail_path = reverse('shop:activity_detail', args=[self.activity.activity_id])
		response = self.client.post(
			reverse('shop:register'),
			{
				'next': detail_path,
				'username': 'joiningstudent',
				'first_name': 'Joining',
				'last_name': 'Student',
				'email': 'joining@example.com',
				'password1': 'StrongPass123!',
				'password2': 'StrongPass123!',
			},
		)
		self.assertRedirects(response, f'{reverse("shop:login")}?next={detail_path}')

	def test_login_returns_to_activity_after_join(self):
		detail_path = reverse('shop:activity_detail', args=[self.activity.activity_id])
		response = self.client.post(
			reverse('shop:login') + f'?next={detail_path}',
			{'username': self.user_data['username'], 'password': self.user_data['password']},
		)
		self.assertRedirects(response, detail_path)

	def test_activity_course_content_defaults_are_available(self):
		self.assertEqual(self.activity.level, 'beginner')
		self.assertEqual(self.activity.prerequisites, 'No previous experience required.')
		self.assertEqual(self.activity.learning_outcomes, '')

	def test_activity_detail_displays_course_content(self):
		self.activity.learning_outcomes = 'Write clear functions.\nUse simple data structures.'
		self.activity.prerequisites = 'Basic computer literacy.'
		self.activity.save()
		response = self.client.get(
			reverse('shop:activity_detail', args=[self.activity.activity_id])
		)
		self.assertContains(response, 'Course Overview')
		self.assertContains(response, 'What You Will Learn')
		self.assertContains(response, 'Write clear functions.')
		self.assertContains(response, 'Use simple data structures.')
		self.assertContains(response, 'Basic computer literacy.')
		self.assertContains(response, 'Beginner')

	def test_activity_pagination_preserves_results(self):
		self.client.force_login(self.user)
		for number in range(7):
			Activity.objects.create(
				title=f'Extra Activity {number}',
				category=self.category,
				trainer=self.trainer,
				duration=1,
				max_students=10,
			)
		first_page = self.client.get(reverse('shop:activity_list'))
		second_page = self.client.get(reverse('shop:activity_list'), {'page': 2})
		self.assertEqual(first_page.context['page_obj'].paginator.num_pages, 3)
		self.assertTrue(first_page.context['page_obj'].has_next())
		self.assertEqual(second_page.context['page_obj'].number, 2)

	def test_pagination_links_preserve_filters(self):
		for number in range(7):
			Activity.objects.create(
				title=f'Python Extra {number}',
				category=self.category,
				trainer=self.trainer,
				duration=1,
				max_students=10,
			)
		response = self.client.get(
			reverse('shop:activity_list'),
			{'q': 'Python', 'category': self.category.category_id},
		)
		self.assertContains(response, f'q=Python&category={self.category.category_id}&page=2')

	def test_register_creates_user_and_profile(self):
		response = self.client.post(
			reverse('shop:register'),
			{
				'username': 'newstudent',
				'first_name': 'New',
				'last_name': 'Student',
				'email': 'new@example.com',
				'password1': 'StrongPass123!',
				'password2': 'StrongPass123!',
			},
		)
		self.assertRedirects(response, reverse('shop:login'))
		new_user = User.objects.get(username='newstudent')
		self.assertTrue(StudentProfile.objects.filter(user=new_user).exists())

	def test_login_redirects_to_home(self):
		response = self.client.post(
			reverse('shop:login'),
			{'username': self.user_data['username'], 'password': self.user_data['password']},
		)
		self.assertRedirects(response, reverse('shop:home'))

	def test_profile_requires_authentication(self):
		response = self.client.get(reverse('shop:student_profile'))
		self.assertRedirects(
			response,
			f'{reverse("shop:login")}?next={reverse("shop:student_profile")}',
		)

	def test_profile_page_loads_for_authenticated_user(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse('shop:student_profile'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Profile complete')
		self.assertContains(response, 'Available activities')

	def test_profile_edit_updates_student_profile(self):
		self.client.force_login(self.user)
		response = self.client.post(
			reverse('shop:edit_student_profile'),
			{
				'phone_number': '555-0100',
				'university': 'Northbridge University',
				'faculty': 'Computing',
				'academic_year': 'Year 2',
			},
		)
		self.assertRedirects(response, reverse('shop:student_profile'))
		profile = StudentProfile.objects.get(user=self.user)
		self.assertEqual(profile.faculty, 'Computing')

	@override_settings(DEBUG=False)
	def test_custom_404_page(self):
		response = self.client.get('/this-page-does-not-exist/')
		self.assertEqual(response.status_code, 404)
		self.assertContains(response, 'That page has moved on.', status_code=404)

