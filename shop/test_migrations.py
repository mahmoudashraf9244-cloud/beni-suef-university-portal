from datetime import date
from unittest import skipUnless

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


@skipUnless(connection.vendor == 'sqlite', 'SQLite migration regression tests')
class NumericConstraintMigrationTests(TransactionTestCase):
    migrate_from = [('shop', '0002_activity_learning_outcomes_activity_level_and_more')]
    migrate_to = [('shop', '0003_activity_numeric_constraints')]
    model_names = (
        ('shop', 'Category'),
        ('shop', 'Trainer'),
        ('shop', 'TrainerProfile'),
        ('shop', 'Activity'),
        ('auth', 'User'),
        ('shop', 'StudentProfile'),
    )

    def setUp(self):
        super().setUp()
        self.assertEqual(
            connection.settings_dict['NAME'],
            connection.creation._get_test_db_name(),
            'Migration regression tests must run on the Django test database.',
        )
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        self.schema_restored = False
        self.old_apps = None
        self.addCleanup(self.restore_latest_schema)
        self.old_apps = self.migrate(self.migrate_from)
        self.create_historical_fixtures()

    def tearDown(self):
        try:
            self.restore_latest_schema()
        finally:
            super().tearDown()

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def restore_latest_schema(self):
        if self.schema_restored:
            return
        # Restore only this test's fixture values if an assertion interrupted
        # one of the invalid-data scenarios before its finally block finished.
        if self.old_apps is not None:
            self.old_apps.get_model('shop', 'Activity').objects.filter(
                pk=104,
            ).update(duration=3, max_students=25)
            self.old_apps.get_model('shop', 'TrainerProfile').objects.filter(
                pk=103,
            ).update(years_of_experience=4)
        self.migrate(self.latest_targets)
        self.schema_restored = True

    def create_historical_fixtures(self):
        Category = self.old_apps.get_model('shop', 'Category')
        Trainer = self.old_apps.get_model('shop', 'Trainer')
        TrainerProfile = self.old_apps.get_model('shop', 'TrainerProfile')
        Activity = self.old_apps.get_model('shop', 'Activity')
        User = self.old_apps.get_model('auth', 'User')
        StudentProfile = self.old_apps.get_model('shop', 'StudentProfile')

        category = Category.objects.create(
            category_id=101,
            name='Migration workshops',
            description='Preserve category descriptions.',
        )
        trainer = Trainer.objects.create(
            trainer_id=102,
            full_name='Migration Trainer',
            email='migration-trainer@example.com',
            phone_number='01000000000',
        )
        TrainerProfile.objects.create(
            profile_id=103,
            trainer=trainer,
            professional_title='Software Engineer',
            biography='A trainer biography that must survive the migration.',
            specialization='Python',
            years_of_experience=4,
        )
        Activity.objects.create(
            activity_id=104,
            title='Preserve activity records',
            short_description='A short description.',
            full_description='A full description.',
            learning_outcomes='Read migrations.\nProtect existing records.',
            prerequisites='Basic Django knowledge.',
            level='intermediate',
            category=category,
            trainer=trainer,
            start_date=date(2026, 10, 1),
            duration=3,
            max_students=25,
            availability_status=False,
        )
        user = User.objects.create(
            id=105,
            username='migrationstudent',
            first_name='Migration',
            last_name='Student',
            email='migration-student@example.com',
            password='!migration-test-account',
        )
        StudentProfile.objects.create(
            student_id=106,
            user=user,
            phone_number='01100000000',
            university='Beni-Suef University',
            faculty='Computer Science',
            academic_year='Year 2',
        )
        optional_trainer = Trainer.objects.create(
            trainer_id=107,
            full_name='Trainer Without Experience Details',
            email='optional-experience@example.com',
        )
        TrainerProfile.objects.create(
            profile_id=108,
            trainer=optional_trainer,
            years_of_experience=None,
        )

    def row_snapshot(self, apps):
        snapshot = {}
        for app_label, model_name in self.model_names:
            model = apps.get_model(app_label, model_name)
            snapshot[model._meta.label_lower] = list(
                model.objects.order_by(model._meta.pk.name).values()
            )
        return snapshot

    def schema_snapshot(self):
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT type, name, tbl_name, sql FROM sqlite_master '
                'WHERE tbl_name IN (%s, %s) ORDER BY type, name',
                ['shop_activity', 'shop_trainer_profile'],
            )
            return cursor.fetchall()

    def test_migration_preserves_existing_fields_ids_and_relationships(self):
        before = self.row_snapshot(self.old_apps)
        new_apps = self.migrate(self.migrate_to)
        self.assertEqual(self.row_snapshot(new_apps), before)
        self.assertIn(
            self.migrate_to[0], MigrationRecorder(connection).applied_migrations()
        )
        with connection.cursor() as cursor:
            activity_constraints = connection.introspection.get_constraints(
                cursor, 'shop_activity'
            )
            profile_constraints = connection.introspection.get_constraints(
                cursor, 'shop_trainer_profile'
            )
            cursor.execute('PRAGMA foreign_key_check')
            self.assertEqual(cursor.fetchall(), [])
        for name in ('activity_duration_positive', 'activity_capacity_positive'):
            self.assertTrue(activity_constraints[name]['check'])
        self.assertTrue(profile_constraints['trainer_experience_nonnegative']['check'])

    def test_invalid_existing_values_stop_migration_without_changes(self):
        scenarios = (
            ('Activity', 104, 'duration', 0, 3),
            ('Activity', 104, 'max_students', 0, 25),
            ('TrainerProfile', 103, 'years_of_experience', -1, 4),
        )
        for model_name, pk, field, invalid_value, valid_value in scenarios:
            with self.subTest(model=model_name, field=field):
                model = self.old_apps.get_model('shop', model_name)
                model.objects.filter(pk=pk).update(**{field: invalid_value})
                try:
                    before_rows = self.row_snapshot(self.old_apps)
                    before_schema = self.schema_snapshot()
                    before_migrations = set(
                        MigrationRecorder(connection).applied_migrations()
                    )
                    with self.assertRaisesMessage(
                        RuntimeError, 'Cannot add numeric constraints:'
                    ):
                        self.migrate(self.migrate_to)
                    self.assertEqual(self.row_snapshot(self.old_apps), before_rows)
                    self.assertEqual(self.schema_snapshot(), before_schema)
                    after_migrations = set(
                        MigrationRecorder(connection).applied_migrations()
                    )
                    self.assertEqual(after_migrations, before_migrations)
                    self.assertNotIn(self.migrate_to[0], after_migrations)
                finally:
                    model.objects.filter(pk=pk).update(**{field: valid_value})
