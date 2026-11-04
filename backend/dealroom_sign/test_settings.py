from backend.settings import *  # noqa
INSTALLED_APPS = [*INSTALLED_APPS, 'dealroom_sign']
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
SIGN_INTERNAL_URL = 'http://sign.test'
SIGN_WEBHOOK_SECRET = 'unit-test-secret'
