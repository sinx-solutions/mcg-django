"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 5.1.8.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import sys

# Load environment variables from .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Supabase JWT Secret for token verification
SUPABASE_JWT_SECRET = os.getenv('JWT_SECRET') # Load from .env

if not SUPABASE_JWT_SECRET:
    print("WARNING: Missing JWT_SECRET environment variable for Supabase token verification.", file=sys.stderr)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', "django-insecure-ikfbztg&cxbh8qn-)13om7gqp2oygeqh-r50wcxdpiozp!#n!%")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
DEBUG = True # Temporarily set to True to see traceback

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'mcg-be.sinxsolutions.ai']


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
    "drf_spectacular",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Remove custom logging middleware reference
    # "api.middleware.RequestResponseLoggingMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Use SQLite for local development
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# For production with Supabase, uncomment and configure:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': os.getenv('DB_HOST', 'tpiipfpvepfvwlqdvcqq.supabase.co'),
        'NAME': os.getenv('DB_NAME', 'postgres'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'PORT': os.getenv('DB_PORT'),
        'OPTIONS': {
            'sslmode': 'require'
        },
    }
}



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://mcg-be.sinxsolutions.ai',
]
CORS_ALLOW_ALL_ORIGINS = False

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Remove SessionAuthentication from defaults to avoid CSRF conflicts with JWT auth
        # 'rest_framework.authentication.SessionAuthentication',
        'authentication.SupabaseAuthentication', # Rely solely on Supabase JWT by default
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny', # Allows requests even if not authenticated
    ],
    # Add throttling configuration
    'DEFAULT_THROTTLE_RATES': {
        'enhance_work_experience': '10/hour',    # 10 requests per hour for enhance_work_experience
        'enhance_project': '10/hour',            # 10 requests per hour for enhance_project
        'enhance_certification': '10/hour',      # 10 requests per hour for enhance_certification
        'enhance_custom_section_item': '10/hour', # 10 requests per hour for enhance_custom_section_item
        'suggest_skills': '10/hour',             # 10 requests per hour for suggest_skills
    },
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'MCG API',
    'DESCRIPTION': 'API for the My Career Gateway project',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # OTHER SETTINGS
    # Restrict schema/UI access to admin users (is_staff=True)
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
}

# Add the origins users will access the site from
CSRF_TRUSTED_ORIGINS = [
    'https://mcg-be.sinxsolutions.ai',
    # Add others if necessary, e.g., for local testing:
    # 'http://localhost:8000',
    # 'http://127.0.0.1:8000',
]

# --- Important Security Settings for Production ---
# Make sure these are TRUE if your site is served over HTTPS
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
# --------------------------------------------------