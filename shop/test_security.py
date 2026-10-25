import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .models import StudentProfile


class SecuritySettingsTests(SimpleTestCase):
    settings_path = Path(__file__).resolve().parent.parent / 'config' / 'settings.py'
    test_secret = 'test-only-settings-secret-' + ('x' * 64)

    def load_settings(self, **environment):
        # Exercise startup decisions independently of the test runner's settings.
        with patch.dict(os.environ, environment, clear=True):
            return runpy.run_path(str(self.settings_path))

    def test_production_requires_an_explicit_secret(self):
        for secret in (None, '', '   ', 'django-insecure-example-key'):
            with self.subTest(secret_kind='missing' if secret is None else 'invalid'):
                environment = {} if secret is None else {'SECRET_KEY': secret}
                with self.assertRaises(ImproperlyConfigured):
                    self.load_settings(**environment)

    def test_production_is_the_default_with_secure_transport_settings(self):
        configuration = self.load_settings(SECRET_KEY=self.test_secret)
        self.assertFalse(configuration['DEBUG'])
        self.assertEqual(configuration['SECRET_KEY'], self.test_secret)
        self.assertEqual(configuration['ALLOWED_HOSTS'], [])
        self.assertTrue(configuration['SECURE_SSL_REDIRECT'])
        self.assertTrue(configuration['SESSION_COOKIE_SECURE'])
        self.assertTrue(configuration['CSRF_COOKIE_SECURE'])
        self.assertEqual(configuration['SECURE_HSTS_SECONDS'], 3600)
        self.assertNotIn('SECURE_PROXY_SSL_HEADER', configuration)

    def test_only_explicit_truthy_debug_values_allow_the_development_key(self):
        for value in ('true', 'True', '1', 'yes', ' YES '):
            with self.subTest(value=value):
                configuration = self.load_settings(DEBUG=value)
                self.assertTrue(configuration['DEBUG'])
                self.assertTrue(configuration['SECRET_KEY'].startswith('django-insecure-'))

    def test_false_debug_values_keep_production_settings(self):
        for value in ('false', 'False', '0', 'no', ''):
            with self.subTest(value=value):
                configuration = self.load_settings(DEBUG=value, SECRET_KEY=self.test_secret)
                self.assertFalse(configuration['DEBUG'])
                self.assertTrue(configuration['SECURE_SSL_REDIRECT'])

    def test_debug_preserves_an_explicit_secret(self):
        configuration = self.load_settings(DEBUG='true', SECRET_KEY=self.test_secret)
        self.assertEqual(configuration['SECRET_KEY'], self.test_secret)

    def test_development_uses_local_hosts_and_http(self):
        configuration = self.load_settings(DEBUG='true')
        self.assertEqual(configuration['ALLOWED_HOSTS'], ['localhost', '127.0.0.1', '[::1]'])
        self.assertFalse(configuration['SECURE_SSL_REDIRECT'])
        self.assertFalse(configuration['SESSION_COOKIE_SECURE'])
        self.assertFalse(configuration['CSRF_COOKIE_SECURE'])
        self.assertEqual(configuration['SECURE_HSTS_SECONDS'], 0)

    def test_allowed_hosts_are_read_from_the_environment(self):
        for debug in ('true', 'false'):
            with self.subTest(debug=debug):
                configuration = self.load_settings(
                    DEBUG=debug,
                    SECRET_KEY=self.test_secret,
                    ALLOWED_HOSTS=' portal.example.com, localhost, ,127.0.0.1, ',
                )
                self.assertEqual(
                    configuration['ALLOWED_HOSTS'],
                    ['portal.example.com', 'localhost', '127.0.0.1'],
                )

    def test_explicit_empty_hosts_do_not_restore_development_defaults(self):
        configuration = self.load_settings(DEBUG='true', ALLOWED_HOSTS=' , ')
        self.assertEqual(configuration['ALLOWED_HOSTS'], [])


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class AuthenticationSecurityTests(TestCase):
    password = 'Orbit!Canyon5842'

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username='security-student',
            password=cls.password,
        )
        cls.other_student = User.objects.create_user(
            username='other-security-student',
            password=cls.password,
        )
        cls.profile = StudentProfile.objects.create(user=cls.student, faculty='Original faculty')
        cls.other_profile = StudentProfile.objects.create(
            user=cls.other_student,
            faculty='Other student faculty',
        )

    def test_account_post_endpoints_require_csrf_tokens(self):
        endpoints = (
            ('shop:login', False),
            ('shop:register', False),
            ('shop:edit_student_profile', True),
            ('shop:logout', True),
        )
        for endpoint, authenticated in endpoints:
            with self.subTest(endpoint=endpoint):
                client = Client(enforce_csrf_checks=True)
                if authenticated:
                    client.force_login(self.student)
                response = client.post(reverse(endpoint), {'faculty': 'Untrusted change'})
                self.assertEqual(response.status_code, 403)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.faculty, 'Original faculty')
        self.assertEqual(User.objects.count(), 2)

    def test_registration_accepts_a_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('shop:register'))
        response = client.post(
            reverse('shop:register'),
            {
                'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
                'username': 'new-security-student',
                'first_name': 'New',
                'last_name': 'Student',
                'email': 'new-security-student@example.com',
                'password1': self.password,
                'password2': self.password,
            },
        )
        self.assertRedirects(response, reverse('shop:login'))
        self.assertTrue(StudentProfile.objects.filter(user__username='new-security-student').exists())

    def test_login_accepts_a_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('shop:login'))
        response = client.post(
            reverse('shop:login'),
            {
                'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
                'username': self.student.username,
                'password': self.password,
            },
        )
        self.assertRedirects(response, reverse('shop:home'))
        self.assertEqual(client.session['_auth_user_id'], str(self.student.pk))

    def test_profile_edit_accepts_a_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        client.get(reverse('shop:edit_student_profile'))
        response = client.post(
            reverse('shop:edit_student_profile'),
            {
                'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
                'faculty': 'Updated faculty',
            },
        )
        self.assertRedirects(response, reverse('shop:student_profile'))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.faculty, 'Updated faculty')

    def test_logout_requires_post_and_accepts_a_valid_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        response = client.get(reverse('shop:logout'))
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', client.session)

        client.get(reverse('shop:student_profile'))
        response = client.post(
            reverse('shop:logout'),
            {'csrfmiddlewaretoken': client.cookies['csrftoken'].value},
        )
        self.assertRedirects(response, reverse('shop:home'))
        self.assertNotIn('_auth_user_id', client.session)

    def test_profile_edit_cannot_target_another_student(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('shop:edit_student_profile'),
            {
                'user': self.other_student.pk,
                'student_id': self.other_profile.pk,
                'faculty': 'My updated faculty',
            },
        )
        self.assertRedirects(response, reverse('shop:student_profile'))
        self.profile.refresh_from_db()
        self.other_profile.refresh_from_db()
        self.assertEqual(self.profile.faculty, 'My updated faculty')
        self.assertEqual(self.profile.user_id, self.student.pk)
        self.assertEqual(self.other_profile.faculty, 'Other student faculty')
        self.assertEqual(self.other_profile.user_id, self.other_student.pk)

    def test_guest_cannot_read_or_update_student_profiles(self):
        requests = (
            ('get', 'shop:student_profile'),
            ('get', 'shop:edit_student_profile'),
            ('post', 'shop:edit_student_profile'),
        )
        for method, endpoint in requests:
            with self.subTest(method=method, endpoint=endpoint):
                path = reverse(endpoint)
                response = (
                    self.client.post(path, {'faculty': 'Guest change'})
                    if method == 'post'
                    else self.client.get(path)
                )
                self.assertRedirects(
                    response,
                    f'{reverse("shop:login")}?next={path}',
                )
        self.profile.refresh_from_db()
        self.other_profile.refresh_from_db()
        self.assertEqual(self.profile.faculty, 'Original faculty')
        self.assertEqual(self.other_profile.faculty, 'Other student faculty')
