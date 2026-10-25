from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Activity, Category, Trainer, TrainerProfile


class NumericValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Validation workshops')
        cls.trainer = Trainer.objects.create(
            full_name='Validation Trainer',
            email='validation@example.com',
        )

    def activity_values(self, **overrides):
        values = {
            'title': 'Numeric validation activity',
            'category': self.category,
            'trainer': self.trainer,
            'duration': 1,
            'max_students': 1,
        }
        values.update(overrides)
        return values

    def test_activity_full_clean_rejects_nonpositive_numbers(self):
        for field in ('duration', 'max_students'):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    activity = Activity(**self.activity_values(**{field: value}))
                    with self.assertRaises(ValidationError) as error:
                        activity.full_clean()
                    self.assertIn(field, error.exception.message_dict)

    def test_activity_accepts_minimum_duration_and_capacity(self):
        activity = Activity(**self.activity_values())
        activity.full_clean()
        activity.save()
        activity.refresh_from_db()
        self.assertEqual(activity.duration, 1)
        self.assertEqual(activity.max_students, 1)

    def test_activity_database_rejects_nonpositive_numbers_on_create(self):
        for field in ('duration', 'max_students'):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        Activity.objects.create(
                            **self.activity_values(**{field: value})
                        )

    def test_activity_database_rejects_nonpositive_numbers_on_update(self):
        activity = Activity.objects.create(**self.activity_values())
        for field in ('duration', 'max_students'):
            for value in (0, -1):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        Activity.objects.filter(pk=activity.pk).update(
                            **{field: value}
                        )
        activity.refresh_from_db()
        self.assertEqual(activity.duration, 1)
        self.assertEqual(activity.max_students, 1)

    def test_experience_full_clean_rejects_negative_numbers(self):
        profile = TrainerProfile(trainer=self.trainer, years_of_experience=-1)
        with self.assertRaises(ValidationError) as error:
            profile.full_clean()
        self.assertIn('years_of_experience', error.exception.message_dict)

    def test_experience_accepts_zero_and_unspecified_value(self):
        profile = TrainerProfile(trainer=self.trainer, years_of_experience=0)
        profile.full_clean()
        profile.save()
        profile.years_of_experience = None
        profile.full_clean()
        profile.save()
        profile.refresh_from_db()
        self.assertIsNone(profile.years_of_experience)

    def test_experience_database_accepts_unspecified_value_on_create(self):
        profile = TrainerProfile.objects.create(trainer=self.trainer)
        self.assertIsNone(profile.years_of_experience)

    def test_experience_database_rejects_negative_numbers_on_create(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TrainerProfile.objects.create(
                trainer=self.trainer,
                years_of_experience=-1,
            )

    def test_experience_database_rejects_negative_numbers_on_update(self):
        profile = TrainerProfile.objects.create(
            trainer=self.trainer,
            years_of_experience=0,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            TrainerProfile.objects.filter(pk=profile.pk).update(
                years_of_experience=-1,
            )
        profile.refresh_from_db()
        self.assertEqual(profile.years_of_experience, 0)
