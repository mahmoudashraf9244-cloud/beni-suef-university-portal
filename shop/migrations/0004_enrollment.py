import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0003_activity_numeric_constraints'),
    ]

    operations = [
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                (
                    'activity',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='enrollments',
                        to='shop.activity',
                    ),
                ),
                (
                    'student',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='enrollments',
                        to='shop.studentprofile',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Enrollment',
                'verbose_name_plural': 'Enrollments',
                'db_table': 'shop_enrollment',
                'ordering': ('-enrolled_at', '-id'),
                'constraints': [
                    models.UniqueConstraint(
                        fields=('student', 'activity'),
                        name='unique_student_activity_enrollment',
                    ),
                ],
            },
        ),
    ]
