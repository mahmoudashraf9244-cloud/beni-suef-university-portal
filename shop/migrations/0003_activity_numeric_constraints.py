from django.core.validators import MinValueValidator
from django.db import migrations, models


def validate_existing_numeric_values(apps, schema_editor):
    """Stop before schema changes if existing records violate the new rules."""
    database = schema_editor.connection.alias
    Activity = apps.get_model('shop', 'Activity')
    TrainerProfile = apps.get_model('shop', 'TrainerProfile')
    invalid_activities = Activity.objects.using(database).filter(
        models.Q(duration__lte=0) | models.Q(max_students__lte=0)
    ).count()
    invalid_profiles = TrainerProfile.objects.using(database).filter(
        years_of_experience__lt=0,
    ).count()
    if invalid_activities or invalid_profiles:
        raise RuntimeError(
            'Cannot add numeric constraints: '
            f'{invalid_activities} activities have non-positive duration or capacity, '
            f'and {invalid_profiles} trainer profiles have negative experience. '
            'Review these records before retrying. No records were changed.'
        )


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0002_activity_learning_outcomes_activity_level_and_more'),
    ]

    operations = [
        migrations.RunPython(
            validate_existing_numeric_values,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='activity',
            name='duration',
            field=models.IntegerField(
                help_text='Duration in days (required)',
                validators=[MinValueValidator(1)],
            ),
        ),
        migrations.AlterField(
            model_name='trainerprofile',
            name='years_of_experience',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='Years of professional experience',
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddConstraint(
            model_name='activity',
            constraint=models.CheckConstraint(
                condition=models.Q(duration__gt=0),
                name='activity_duration_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='activity',
            constraint=models.CheckConstraint(
                condition=models.Q(max_students__gt=0),
                name='activity_capacity_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='trainerprofile',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(years_of_experience__gte=0)
                    | models.Q(years_of_experience__isnull=True)
                ),
                name='trainer_experience_nonnegative',
            ),
        ),
    ]
