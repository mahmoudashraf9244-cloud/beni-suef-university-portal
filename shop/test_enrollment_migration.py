from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class EnrollmentMigrationTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(
            connection.settings_dict['NAME'], connection.creation._get_test_db_name(),
            'Schema tests must use the Django test database.',
        )
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        self.addCleanup(self.restore_latest_schema)
        self.old_apps = self.migrate([('shop', '0003_activity_numeric_constraints')])

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def restore_latest_schema(self):
        self.migrate(self.latest_targets)

    def test_new_enrollment_table_preserves_existing_records(self):
        category = self.old_apps.get_model('shop', 'Category').objects.create(
            name='Preserved enrollment category', description='Existing description',
        )
        trainer = self.old_apps.get_model('shop', 'Trainer').objects.create(
            full_name='Preserved Trainer', email='preserved@example.com',
        )
        self.old_apps.get_model('shop', 'TrainerProfile').objects.create(
            trainer_id=trainer.pk, biography='Existing trainer biography', years_of_experience=0,
        )
        self.old_apps.get_model('shop', 'Activity').objects.create(
            title='Preserved activity', category_id=category.pk, trainer_id=trainer.pk,
            duration=2, max_students=10,
        )
        user = self.old_apps.get_model('auth', 'User').objects.create(
            username='preserved-enrollment-student', password='!unusable-test-password',
        )
        self.old_apps.get_model('shop', 'StudentProfile').objects.create(
            user_id=user.pk, university='Beni-Suef University', faculty='Computing',
        )
        model_names = (
            ('shop', 'Category'), ('shop', 'Trainer'), ('shop', 'TrainerProfile'),
            ('shop', 'Activity'), ('auth', 'User'), ('shop', 'StudentProfile'),
        )

        def snapshot(apps):
            return {
                name: list(apps.get_model(app, name).objects.order_by('pk').values())
                for app, name in model_names
            }

        before = snapshot(self.old_apps)
        new_apps = self.migrate([('shop', '0004_enrollment')])
        self.assertEqual(snapshot(new_apps), before)
        Enrollment = new_apps.get_model('shop', 'Enrollment')
        self.assertFalse(Enrollment.objects.exists())
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, 'shop_enrollment')
            self.assertTrue(constraints['unique_student_activity_enrollment']['unique'])
            if connection.vendor == 'sqlite':
                cursor.execute('PRAGMA foreign_key_check')
                self.assertEqual(cursor.fetchall(), [])
