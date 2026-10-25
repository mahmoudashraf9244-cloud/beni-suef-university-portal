from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.translation import override

from .models import Activity, Category, StudentProfile, Trainer
from .templatetags.portal import course_image, localize


class FrontendFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Python Programming')
        cls.trainer = Trainer.objects.create(full_name='محمد خالد', email='demo@example.com')
        cls.user = User.objects.create_user('preview-test', password='Test-only-pass-5638')
        StudentProfile.objects.create(user=cls.user)
        cls.course = Activity.objects.create(
            title='Python Bootcamp', category=cls.category, trainer=cls.trainer,
            short_description='Build confidence with Python through practical programming challenges.',
            full_description='This hands-on bootcamp introduces Python syntax, problem-solving, and common data structures through a series of short exercises that build toward a small command-line project.',
            prerequisites='No previous programming experience required.',
            duration=3, max_students=20, availability_status=True,
        )
        for i in range(4):
            Activity.objects.create(title=f'Python practice {i}', category=cls.category,
                                    trainer=cls.trainer, duration=2, max_students=10)

    def language(self, code, next_url='/'):
        return self.client.post(reverse('set_language'), {'language': code, 'next': next_url})

    def test_language_switch_translates_home_and_course_content_and_back(self):
        self.language('ar')
        home = self.client.get('/')
        self.assertContains(home, 'lang="ar" dir="rtl"')
        self.assertContains(home, 'اتعلّم مهارة تكمّل معاك.')
        self.assertNotContains(home, 'Learn something that stays with you.')
        detail = self.client.get(reverse('shop:activity_detail', args=[self.course.pk]))
        for text in ('معسكر بايثون', 'محمد خالد', 'طوّر مهاراتك', 'معسكر عملي', 'سجّل دخولك لعرض التفاصيل كاملة', 'المدة'):
            self.assertContains(detail, text)
        self.assertNotContains(detail, self.course.full_description)
        self.language('en')
        detail = self.client.get(reverse('shop:activity_detail', args=[self.course.pk]))
        self.assertContains(detail, 'lang="en" dir="ltr"')
        self.assertContains(detail, self.course.full_description)
        self.assertContains(detail, 'Mohamed Khaled')
        self.assertNotContains(detail, 'محمد خالد')

    def test_arabic_search_matches_translated_title_and_category(self):
        self.language('ar')
        response = self.client.get('/activities/', {'q': 'معسكر', 'category': self.category.pk})
        self.assertContains(response, 'معسكر بايثون')
        self.assertEqual(list(response.context['activities']), [self.course])

    def test_guest_preview_is_three_and_next_requires_login_with_filters(self):
        response = self.client.get('/activities/')
        self.assertEqual(len(response.context['activities']), 3)
        response = self.client.get('/activities/', {'q': 'Python', 'category': self.category.pk, 'page': 2})
        self.assertEqual(response.status_code, 302)
        next_url = parse_qs(urlsplit(response.url).query)['next'][0]
        self.assertEqual(parse_qs(urlsplit(next_url).query), {'q': ['Python'], 'category': [str(self.category.pk)], 'page': ['2']})
        login = self.client.post(response.url, {'username': 'preview-test', 'password': 'Test-only-pass-5638'}, follow=True)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.context['page_obj'].number, 2)
        self.assertEqual(len(login.context['activities']), 2)

    def test_out_of_range_page_cannot_bypass_guest_gate(self):
        for page in ('2', '999999', '-1'):
            with self.subTest(page=page):
                response = self.client.get('/activities/', {'page': page}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertEqual(response.status_code, 302)

    def test_language_change_preserves_destination_and_rejects_external_redirect(self):
        destination = '/activities/?q=Python&category=1&page=1'
        self.assertEqual(self.language('ar', destination).url, destination)
        self.assertEqual(self.language('en', 'https://example.net/').url, '/')

    def test_language_form_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('set_language'), {'language': 'ar'}).status_code, 403)

    def test_forms_use_translated_labels_and_real_password_rules(self):
        self.language('ar')
        response = self.client.get('/register/')
        self.assertContains(response, 'الاسم الأول')
        self.assertContains(response, 'إظهار كلمة المرور')
        self.assertContains(response, 'id_password1_helptext')
        self.assertNotContains(response, 'One uppercase letter')
        invalid = self.client.post('/register/', {})
        self.assertContains(invalid, 'هذا الحقل مطلوب')

    def test_translated_enrollment_feedback_and_profile(self):
        self.client.force_login(self.user)
        self.language('ar')
        response = self.client.post(reverse('shop:enroll_activity', args=[self.course.pk]), follow=True)
        self.assertContains(response, 'تم تسجيلك في الكورس بنجاح.')
        self.assertContains(response, 'أنت مسجّل في الكورس')
        profile = self.client.get('/profile/')
        self.assertContains(profile, 'كورساتي')
        self.assertContains(profile, 'معسكر بايثون')

    def test_nullable_and_untranslated_content_remains_safe(self):
        with override('ar'):
            self.assertEqual(localize(None), '')
            self.assertEqual(localize('An administrator-defined course'), 'An administrator-defined course')
        self.course.title = '<script>alert(1)</script>'
        self.course.save()
        self.assertNotContains(self.client.get('/activities/'), '<script>alert(1)</script>')

    def test_course_art_has_local_asset_and_unknown_category_fallback(self):
        for category in ('Python Programming', 'Web Development', 'Artificial Intelligence', 'Data Science', 'Database', 'React Development', 'UI/UX Design', 'Cybersecurity', 'Custom category'):
            self.course.category.name = category
            asset = course_image(self.course)
            self.assertTrue((Path(settings.BASE_DIR) / 'shop/static' / asset).is_file(), asset)

    def test_home_navigation_has_no_active_marker_and_guest_modal_configuration(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'href="/" class="is-active"')
        self.assertContains(response, 'data-authenticated="false"')
        self.assertContains(response, 'Create account')

    def test_authenticated_page_marks_modal_as_full_detail(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/activities/'), 'data-authenticated="true"')
