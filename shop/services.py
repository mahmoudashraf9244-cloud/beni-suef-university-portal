"""Enrollment rules shared by the portal's registration endpoint."""

import sqlite3
from enum import StrEnum
from time import sleep

from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.models import F

from .models import Activity, Enrollment, StudentProfile


class EnrollmentResult(StrEnum):
    CREATED = 'created'
    ALREADY_ENROLLED = 'already_enrolled'
    FULL = 'full'
    CLOSED = 'closed'
    COMPLETED = 'completed'
    INELIGIBLE = 'ineligible'
    BUSY = 'busy'


def _sqlite_lock_error(error):
    if connection.vendor != 'sqlite':
        return False
    code = getattr(error.__cause__, 'sqlite_errorcode', 0)
    return (code & 0xFF) in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)


def enroll_student(*, student_id, activity_id):
    """Reserve one seat, serializing writers before reading SQLite capacity.

    The caller obtains student_id from the authenticated user's own profile.
    Short transactions and bounded retries handle SQLite write contention.
    """
    if not isinstance(activity_id, int) or not 0 < activity_id <= 2**63 - 1:
        raise Activity.DoesNotExist

    for attempt in range(4):
        try:
            with transaction.atomic():
                # This must be the first query inside the transaction. A no-op
                # UPDATE obtains SQLite's write lock; SELECT FOR UPDATE does not.
                if not Activity.objects.filter(pk=activity_id).update(max_students=F('max_students')):
                    raise Activity.DoesNotExist
                activity = Activity.objects.get(pk=activity_id)
                if not StudentProfile.objects.filter(pk=student_id, user__is_active=True).exists():
                    return EnrollmentResult.INELIGIBLE
                existing = Enrollment.objects.filter(student_id=student_id, activity_id=activity_id)
                if existing.exists():
                    return EnrollmentResult.ALREADY_ENROLLED
                status, _ = activity.get_status()
                if status == 'Completed':
                    return EnrollmentResult.COMPLETED
                if status not in ('Available', 'Upcoming'):
                    return EnrollmentResult.CLOSED
                if activity.enrollments.count() >= activity.max_students:
                    return EnrollmentResult.FULL
                Enrollment.objects.create(student_id=student_id, activity_id=activity_id)
                return EnrollmentResult.CREATED
        except IntegrityError:
            # The unique constraint is a final safeguard for duplicate writes.
            if Enrollment.objects.filter(student_id=student_id, activity_id=activity_id).exists():
                return EnrollmentResult.ALREADY_ENROLLED
            raise
        except OperationalError as error:
            if not _sqlite_lock_error(error):
                raise
            if attempt == 3:
                return EnrollmentResult.BUSY
            sleep(0.05 * (attempt + 1))
