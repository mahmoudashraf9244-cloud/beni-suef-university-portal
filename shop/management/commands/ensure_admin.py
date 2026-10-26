import os

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction


class Command(BaseCommand):
    help = 'Create or update a superuser from temporary ADMIN_* environment variables.'

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME', '').strip()
        email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
        password = os.environ.get('ADMIN_PASSWORD', '')

        if not any((username, email, password)):
            self.stdout.write('Admin bootstrap skipped: ADMIN_* variables are not configured.')
            return
        if not all((username, email, password)):
            raise CommandError('ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD must all be set.')

        try:
            validate_email(email)
        except ValidationError as error:
            raise CommandError('ADMIN_EMAIL must be a valid email address.') from error

        email_owner = User.objects.filter(email__iexact=email).exclude(username=username).first()
        if email_owner:
            raise CommandError('ADMIN_EMAIL already belongs to another account.')

        user, created = User.objects.get_or_create(username=username)
        user.email = email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True

        try:
            validate_password(password, user=user)
        except ValidationError as error:
            raise CommandError('ADMIN_PASSWORD does not meet Django password requirements.') from error

        user.set_password(password)
        user.save(update_fields=('email', 'is_active', 'is_staff', 'is_superuser', 'password'))
        action = 'created' if created else 'updated'
        self.stdout.write(self.style.SUCCESS(f'Administrator {username!r} {action}.'))
