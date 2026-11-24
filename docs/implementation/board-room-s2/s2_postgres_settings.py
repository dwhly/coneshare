import os
import dj_database_url
from backend.settings import *
DATABASES={'default':dj_database_url.parse(os.environ['S2_POSTGRES_TEST_URL'])}
DEALROOM_ENABLED=True
CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
CELERY_BROKER_URL='memory://'
CELERY_RESULT_BACKEND='cache+memory://'
