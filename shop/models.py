from datetime import date, timedelta

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        help_text="Category name (must be unique)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the category"
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        db_table = 'shop_category'

    def __str__(self):
        return self.name


class Trainer(models.Model):
    trainer_id = models.AutoField(primary_key=True)
    full_name = models.CharField(
        max_length=255,
        null=False,
        help_text="Trainer's full name"
    )
    email = models.EmailField(
        unique=True,
        null=False,
        help_text="Trainer email (must be unique)"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Optional contact number"
    )

    class Meta:
        verbose_name = "Trainer"
        verbose_name_plural = "Trainers"
        db_table = 'shop_trainer'

    def __str__(self):
        return self.full_name


class TrainerProfile(models.Model):
    profile_id = models.AutoField(primary_key=True)
    trainer = models.OneToOneField(
        Trainer,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Links to Trainer (1:1 unique relationship)"
    )
    professional_title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Job title or position"
    )
    biography = models.TextField(
        blank=True,
        null=True,
        help_text="Professional background and experience"
    )
    specialization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Area of expertise or specialization"
    )
    years_of_experience = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Years of professional experience"
    )

    class Meta:
        verbose_name = "Trainer Profile"
        verbose_name_plural = "Trainer Profiles"
        db_table = 'shop_trainer_profile'
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(years_of_experience__gte=0)
                    | models.Q(years_of_experience__isnull=True)
                ),
                name='trainer_experience_nonnegative',
            ),
        ]

    def __str__(self):
        return f"Profile of {self.trainer.full_name}"


class Activity(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    activity_id = models.AutoField(primary_key=True)
    title = models.CharField(
        max_length=255,
        unique=True,
        null=False,
        help_text="Activity title (must be unique)"
    )
    short_description = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Brief summary of the activity"
    )
    full_description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the activity"
    )
    learning_outcomes = models.TextField(
        blank=True,
        default='',
        help_text="One learning outcome per line"
    )
    prerequisites = models.TextField(
        blank=True,
        default='No previous experience required.'
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='beginner'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name='activities',
        null=False,
        help_text="Links to Category (M:1 relationship)"
    )
    trainer = models.ForeignKey(
        Trainer,
        on_delete=models.RESTRICT,
        related_name='activities',
        null=False,
        help_text="Links to Trainer (M:1 relationship)"
    )
    start_date = models.DateField(
        blank=True,
        null=True,
        help_text="Activity start date"
    )
    duration = models.IntegerField(
        null=False,
        validators=[MinValueValidator(1)],
        help_text="Duration in days (required)"
    )
    max_students = models.IntegerField(
        null=False,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of students (must be > 0)"
    )
    availability_status = models.BooleanField(
        default=True,
        help_text="True = available, False = unavailable"
    )

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"
        db_table = 'shop_activity'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration__gt=0),
                name='activity_duration_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(max_students__gt=0),
                name='activity_capacity_positive',
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if (
            self._state.adding
            or self.pk is None
            or not isinstance(self.max_students, int)
            or self.max_students < 1
        ):
            return
        if self.max_students < self.enrollments.count():
            raise ValidationError({
                'max_students': (
                    'Maximum students cannot be lower than the number of enrolled students.'
                ),
            })

    @property
    def end_date(self):
        """Count the start date as day one without overflowing Python dates."""
        if self.start_date is None or self.duration is None or self.duration < 1:
            return None
        days_after_start = self.duration - 1
        if days_after_start > (date.max - self.start_date).days:
            return None
        return self.start_date + timedelta(days=days_after_start)

    def get_status(self, today=None):
        today = timezone.localdate() if today is None else today
        if (
            self.start_date is not None
            and self.duration is not None
            and self.duration > 0
            and (today - self.start_date).days >= self.duration
        ):
            return 'Completed', 'is-completed'
        if not self.availability_status:
            return 'Closed', 'is-closed'
        if self.start_date is not None and self.start_date > today:
            return 'Upcoming', 'is-upcoming'
        return 'Available', 'is-available'

    @property
    def status_label(self):
        return self.get_status()[0]

    @property
    def status_class(self):
        return self.get_status()[1]

    def is_joinable_on(self, today=None):
        return self.get_status(today)[0] in ('Available', 'Upcoming')

    @property
    def is_joinable(self):
        return self.is_joinable_on()


class StudentProfile(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        help_text="Links to User (1:1 unique relationship)"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Student contact number"
    )
    university = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the university"
    )
    faculty = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Faculty or college name"
    )
    academic_year = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Academic year (e.g., '2024-2025', 'Year 2')"
    )

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"
        db_table = 'shop_student_profile'

    def __str__(self):
        return f"Profile of {self.user.username}"


class Enrollment(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.PROTECT,
        related_name='enrollments',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        db_table = 'shop_enrollment'
        ordering = ('-enrolled_at', '-id')
        constraints = [
            models.UniqueConstraint(
                fields=('student', 'activity'),
                name='unique_student_activity_enrollment',
            ),
        ]

    def __str__(self):
        return f'{self.student.user.username}: {self.activity.title}'
