# Beni-Suef University Courses & Activities Portal

A bilingual Django student portal for discovering university courses and activities. Students can browse and search the catalogue, inspect course details, create an account, enroll safely, and manage a private profile.

## Features

- Responsive Beni-Suef University project identity with light and dark themes
- Complete English and Arabic interface with right-to-left layout
- Activity catalogue with search and category filtering
- Derived activity states: Available, Upcoming, Closed, and Completed
- Three-course guest preview, authenticated pagination, and preserved filters
- Animated course-detail modal with a full-page fallback when JavaScript is unavailable
- Activity detail pages with overview, learning outcomes, prerequisites, level, trainer, start/end dates, and capacity
- Student registration and login/logout
- Student activity enrollment with capacity checks, duplicate protection, and a private My activities list
- Authenticated student profile and profile editing
- Custom 404 page and friendly empty states
- Django admin management for categories, trainers, activities, and profiles

## Technologies

- Python 3.12, 3.13, or 3.14 (verified with Python 3.14)
- Django 6.1.2
- SQLite
- HTML and CSS
- Django templates and the built-in authentication system

No external frontend framework or JavaScript library is required.

## Project Structure

```text
Final_Project/
├── manage.py
├── .env.example
├── requirements.txt
├── .github/workflows/django.yml
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── shop/
    ├── models.py
    ├── forms.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── test_*.py
    ├── locale/
    ├── migrations/
    ├── templates/shop/
    └── static/shop/
```

## Database Relationships

- A `Category` has many `Activity` records.
- A `Trainer` has many `Activity` records.
- A `Trainer` has one `TrainerProfile`.
- A Django `User` has one `StudentProfile`.
- Each `Activity` belongs to one category and one trainer.
- An `Enrollment` links a `StudentProfile` to an `Activity`, with a registration timestamp and a unique student/activity pair.

The existing schema uses Django's built-in `User` model and SQLite. Activity status is derived from the existing availability flag, start date, and duration; no status or end-date column is stored.

The end date is inclusive: `start_date + duration - 1 day`. A one-day activity ends on its start date and becomes **Completed** the following day. Dates are evaluated in the `Africa/Cairo` timezone.

Completed takes precedence over the manual availability flag. Completed activities remain in the catalogue and detail pages, but have no Join action and are excluded from featured/available activity totals. Other manually disabled activities are **Closed**. Enabled future activities are **Upcoming**, and enabled activities still running are **Available**. An activity without a start date remains **Available** when the administrator enables it; its end date is shown as unspecified.

The activity lifecycle and enrollment are enhancements beyond the original ITI requirements. A visitor logs in before submitting the Join form; viewing a page never enrolls anyone. An active account with a StudentProfile can enroll in an eligible activity. Already registered students see a confirmation and their enrollment in My activities, including after an activity completes.

Enrollment accepts POST requests with CSRF protection and takes student identity from the logged-in account. Duplicate requests are idempotent. Full, closed, and completed activities reject new enrollments. Enabled activities without start dates remain eligible, as configured by the administrator. Full activities are excluded from featured/available activity totals. Enrollment history protects its related activity and student profile from deletion.

All portal enrollment writes go through `shop.services.enroll_student()`. Inside a short transaction, an initial no-op activity UPDATE obtains SQLite's write lock before reading the current capacity and creating an enrollment. A database unique constraint also protects each student/activity pair. SQLite serializes writers, while Django's `select_for_update()` has no effect on SQLite; see the [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html) and [Django SQLite notes](https://docs.djangoproject.com/en/6.1/ref/databases/#queryset-select-for-update-not-supported). Lock contention has bounded retries and a retry message when the database remains busy.

Use the portal service for enrollment writes. Django Admin provides read-only enrollment records so it cannot bypass the registration rules. Activity form validation also rejects lowering capacity below the number of existing enrollments. Programmatic activity edits should run model validation; direct ORM bulk updates bypass that validation.

Each activity also stores a course level, prerequisites, and newline-separated learning outcomes. These fields keep the detail page informative while remaining simple to edit through Django Admin.

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the project dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Explicitly enable local development in the current PowerShell terminal:

   ```powershell
   $env:DEBUG = 'True'
   ```

   `DEBUG` defaults to `False`. A development-only fallback key is used only when you explicitly enable debug mode. Set these environment variables again in each new terminal. The project does not load `.env` files automatically.

   Outside local development, configure `DEBUG=False`, a private random `SECRET_KEY`, and a comma-separated `ALLOWED_HOSTS` containing your deployment hostnames. Startup rejects a missing key or one beginning with `django-insecure-`. Generate a private key locally using Django's `get_random_secret_key()` and store it in your deployment environment; do not commit or share it.

   With debug disabled, HTTPS redirects, secure session/CSRF cookies, and a one-hour HSTS policy are enabled. Configure HTTPS and static-file serving on your deployment server before hosting the application. Proxy trust and HSTS coverage of subdomains/preloading require deployment-specific decisions.

4. Apply migrations:

   ```bash
   python manage.py migrate
   ```

   Existing databases have a new numeric-constraints migration. Review it before applying it: activities require positive duration/capacity, and trainer experience must be nonnegative when supplied. The migration checks existing values first and stops on invalid records without changing or deleting them. Fix such records deliberately before retrying.

   Migration `0004_enrollment` creates the enrollment table and its foreign keys/unique constraint. Back up an existing database and review the migration before applying it. Apply it before running the updated enrollment pages; no sample registrations are created automatically and existing application records are preserved.

5. Load the repeatable sample catalogue and student accounts:

   ```bash
   python manage.py seed_sample_data
   ```

   This command is safe to run again. It reuses matching records and updates the sample catalogue without creating duplicates. It creates four local demo students required by the assignment:

   - `student_ahmed`
   - `student_omar`
   - `student_youssef`
   - `student_mohamed`

   Their local demo password is `StudentDemo123!`. These accounts contain fictional sample data only. Change or remove them before using the project with real users.

6. Start the development server:

   ```bash
   python manage.py runserver
   ```

7. Open `http://127.0.0.1:8000/` in a browser.

## Main URLs

- `/` - Home page
- `/activities/` - Activity catalogue, search, filters, and pagination
- `/activities/<id>/` - Activity details
- `/activities/<id>/enroll/` - Authenticated student enrollment (POST only)
- `/register/` - Student registration
- `/login/` - Student login
- `/logout/` - Student logout
- `/profile/` - Student dashboard/profile
- `/profile/edit/` - Edit student profile
- `/admin/` - Django admin

## Interface and language

The interface supports English and Arabic, including right-to-left layout, translated sample course content, status labels, forms, and feedback messages. Sample trainer names appear in Arabic or English according to the selected language. The theme control remembers the student's light or dark preference.

Guests see a three-course preview. Requesting later catalogue pages sends them to login and returns them to the requested filtered page afterwards. Selecting a course card opens a focused animated preview. Logged-in students see full information and enrollment controls; guests see a concise preview and a login action. The normal detail URL remains the no-JavaScript fallback.

Course subject artwork is stored locally under `shop/static/shop/images/courses/`. The technology icons come from Devicon and Bootstrap Icons; their license files are included there. The homepage photograph comes from Pexels: https://www.pexels.com/photo/two-men-looking-at-a-laptop-4974920/

## Admin Usage

Create an administrator with:

```bash
python manage.py createsuperuser
```

Then visit `/admin/` to manage categories, trainers, trainer profiles, activities, and student profiles. Add activities through the admin interface with a category, trainer, duration, capacity, and availability flag. Enrollments can be searched and viewed, while adding, changing, and deleting them through Admin is disabled.

## Testing

Run the system check and test suite with:

```powershell
$env:DEBUG = 'True'
python manage.py check
python manage.py test
```

The tests cover the main pages, activity search and category filtering, pagination, activity details, registration, login, profile authentication, profile editing, and the custom 404 page. Additional regression tests cover malformed/out-of-range filters, environment-dependent security settings, numeric validation, database constraints, and migration data preservation. Lifecycle tests cover inclusive end dates, completion boundaries, Cairo's local date, missing dates, catalogue visibility, Join eligibility, featured activities, and dashboard totals. Enrollment tests cover CSRF, account authorization, forged identities, duplicate requests, full/closed/completed activities, private profile history, read-only Admin access, and separate-connection concurrent attempts for the last seat. Database tests use a separate temporary test database, leaving `db.sqlite3` unchanged.

GitHub Actions runs the Django system check and complete test suite on every push and pull request.

## Live demo deployment

The project is ready for Vercel's native Django runtime. Configure a private
`SECRET_KEY` and a managed PostgreSQL `DATABASE_URL` in the Vercel project before
deploying. The application continues to use SQLite for local development when no
`DATABASE_URL` is present.

After connecting the database, apply migrations and load the fictional catalogue with
`python manage.py migrate` and `python manage.py seed_sample_data`. Never use the demo
student password for real accounts.

## GitHub safety

The repository intentionally excludes the local SQLite database, virtual environments, environment files, backups, logs, generated static output, source archives, recordings, IDE settings, and the original assignment-material folder. Never commit a production `SECRET_KEY`, real student records, passwords, or a local `.env` file.

Before uploading, review the files selected by Git or GitHub Desktop. A clean repository should contain the application source, migrations, templates, static assets, translation catalogues, tests, workflow, documentation, `.gitignore`, `.env.example`, and `requirements.txt`.
