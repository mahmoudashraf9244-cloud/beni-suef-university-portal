from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from .models import Activity, Category, StudentProfile, Trainer, TrainerProfile


class SampleDataCommandTests(TestCase):
    def test_command_creates_complete_repeatable_assignment_dataset(self):
        call_command('seed_sample_data', verbosity=0)
        call_command('seed_sample_data', verbosity=0)

        self.assertGreaterEqual(Category.objects.count(), 4)
        self.assertGreaterEqual(Trainer.objects.count(), 4)
        self.assertEqual(TrainerProfile.objects.count(), Trainer.objects.count())
        self.assertGreaterEqual(Activity.objects.count(), 8)
        self.assertGreaterEqual(StudentProfile.objects.count(), 4)
        self.assertTrue(Activity.objects.filter(availability_status=False).exists())
        self.assertTrue(any(trainer.activities.count() > 1 for trainer in Trainer.objects.all()))

        for username in ('student_ahmed', 'student_omar', 'student_youssef', 'student_mohamed'):
            user = User.objects.get(username=username)
            self.assertTrue(user.check_password('StudentDemo123!'))
            self.assertTrue(hasattr(user, 'student_profile'))
