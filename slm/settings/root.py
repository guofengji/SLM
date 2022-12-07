"""
Django settings for SLM.

Generated by 'django-admin startproject' using Django 3.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
from slm.settings import set_default, is_defined
from split_settings.tools import include
import os

set_default('DEBUG', False)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
set_default('BASE_DIR', Path(__file__).resolve().parent.parent)
set_default('SITE_DIR', BASE_DIR)
set_default('DJANGO_DEBUG_TOOLBAR', False)

# manage.py will set this to true if django has been loaded to run a management command
MANAGEMENT_MODE = os.environ.get('SLM_MANAGEMENT_FLAG', False) == 'ON'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

if is_defined('ALLOWED_HOSTS') and ALLOWED_HOSTS:
    set_default('DEFAULT_FROM_EMAIL', f'noreply@{ALLOWED_HOSTS[0]}')

# Application definition

# django.contrib.___ gives us useful tools for authentication, etc.
INSTALLED_APPS = [
    'slm.map',
    'slm',
    'rest_framework',
    'render_static',
    'django_filters',
    'compressor',
    'widget_tweaks',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder'
)

# this statement was added during creation of custom user model
AUTH_USER_MODEL = 'slm.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'slm.settings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages'
            ],
            'builtins': ['slm.templatetags.slm']
        },
    },
]

WSGI_APPLICATION = 'sites.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# Following two statements added to assist with handling of static files
STATIC_URL = '/static/'

set_default(
    'SITE_NAME',
    ALLOWED_HOSTS[0] if is_defined('ALLOWED_HOSTS') and ALLOWED_HOSTS
    else 'localhost'
)

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

include('secrets.py')
include('logging.py')
include('internationalization.py')
include('static_templates.py')
include('routines.py')
include('auth.py')
include('rest.py')
include('slm.py')
include('debug.py')

set_default('SITE_ID', 1)

MEDIA_URL = '/media/'
set_default('STATIC_ROOT', SITE_DIR / 'static')
set_default('MEDIA_ROOT', SITE_DIR / 'media')

COMPRESS_OFFLINE = True
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL

#Path(STATIC_ROOT).mkdir(parents=True, exist_ok=True)
#Path(MEDIA_ROOT).mkdir(parents=True, exist_ok=True)
