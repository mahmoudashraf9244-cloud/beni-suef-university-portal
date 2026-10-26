import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase


class EnsureAdminCommandTests(TestCase):
    def test_skips_safely_without_environment_variables(self):
        output = StringIO()
        with patch.dict(os.environ, {}, clear=True):
            call_command('ensure_admin', stdout=output)

        self.assertIn('skipped', output.getvalue())
        self.assertFalse(User.objects.exists())

    def test_creates_superuser_from_environment_variables(self):
        variables = {
            'ADMIN_USERNAME': 'deployment_admin',
            'ADMIN_EMAIL': 'admin@example.com',
            'ADMIN_PASSWORD': 'Strong-Admin-Pass-5831!',
        }
        with patch.dict(os.environ, variables, clear=True):
            call_command('ensure_admin')

        user = User.objects.get(username='deployment_admin')
        self.assertEqual(user.email, 'admin@example.com')
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(variables['ADMIN_PASSWORD']))
