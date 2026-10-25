"""Project settings."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent


# Security
DEBUG = os.environ.get('DEBUG', 'False').strip().lower() in ('true', '1', 'yes')
SECRET_KEY = os.environ.get('SECRET_KEY', '').strip()
if DEBUG:
    SECRET_KEY = SECRET_KEY or 'django-insecure-local-development-only-change-before-deployment-12345'
elif not SECRET_KEY or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured(
        'Set a private SECRET_KEY environment variable when DEBUG is False. '
        'For local development, explicitly set DEBUG=True.'
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]' if DEBUG else ''
    ).split(',')
    if host.strip()
]

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# Start with one hour; extend this policy when HTTPS deployment is verified.
SECURE_HSTS_SECONDS = 3600 if not DEBUG else 0


# Applications

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shop',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Passwords

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Localization

LANGUAGE_CODE = 'en'
LANGUAGES = [('en', 'English'), ('ar', 'العربية')]

TIME_ZONE = 'Africa/Cairo'

USE_I18N = True

USE_TZ = True


# Static files

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Authentication

LOGIN_URL = 'shop:login'
LOGIN_REDIRECT_URL = 'shop:home'
LOGOUT_REDIRECT_URL = 'shop:home'


# Email

