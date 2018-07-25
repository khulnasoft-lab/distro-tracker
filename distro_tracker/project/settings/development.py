"""
Appropriate settings to run during development.

When running in development mode, selected.py should point to this file.
"""

from . import defaults
from .db_sqlite import DATABASES  # noqa

__all__ = [
    'ADMINS',
    'CACHES',
    'DATABASES',
    'DEBUG',
    'EMAIL_BACKEND',
    'INSTALLED_APPS',
    'INTERNAL_IPS',
    'MIDDLEWARE',
    'SITE_URL',
    'TEMPLATES',
    'XHR_SIMULATED_DELAY',
]

DEBUG = True

ADMINS = ()

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SITE_URL = 'http://127.0.0.1:8000'

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

TEMPLATES = defaults.TEMPLATES.copy()
TEMPLATES[0] = TEMPLATES[0].copy()
TEMPLATES[0]['OPTIONS'] = TEMPLATES[0]['OPTIONS'].copy()
TEMPLATES[0]['OPTIONS']['loaders'] = TEMPLATES[0]['OPTIONS']['loaders'].copy()
TEMPLATES[0]['OPTIONS']['loaders'] = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

XHR_SIMULATED_DELAY = 0.5

INSTALLED_APPS = defaults.INSTALLED_APPS.copy()
INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE = defaults.MIDDLEWARE.copy()
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

INTERNAL_IPS = [
    '127.0.0.1',
]
