"""Isolated glue deployment; all domain code still runs inside Send's Django app."""
import os
from backend.settings import *  # noqa: F401,F403

if 'dealroom_sign' not in INSTALLED_APPS:
    INSTALLED_APPS = [*INSTALLED_APPS, 'dealroom_sign']
ROOT_URLCONF = 'dealroom_sign.runtime_urls'
SIGN_INTERNAL_URL = os.environ.get('SIGN_INTERNAL_URL', 'http://amforge-sign-dev-documenso-1:3000')
SIGN_PUBLIC_URL = os.environ.get('SIGN_PUBLIC_URL', 'http://100.110.241.2:8792')
SIGN_DEPLOYMENT_ID = os.environ.get('SIGN_DEPLOYMENT_ID', 'chief-glue-v1')
SIGN_WEBHOOK_SECRET = os.environ['SIGN_WEBHOOK_SECRET']
SECURE_REFERRER_POLICY = 'no-referrer'
