from backend.settings import *  # noqa

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
SIGN_INTERNAL_URL = 'http://sign.test'
SIGN_WEBHOOK_SECRET = 'unit-test-secret'

DEALROOM_ENABLED = True
