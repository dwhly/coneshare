import pytest


@pytest.fixture(autouse=True)
def fictional_capability_key(settings):
    settings.SIGN_CAPABILITY_KEY = 'fictional-capability-key-for-signing-tests'


@pytest.fixture(autouse=True)
def fictional_sign_integration(settings):
    settings.SIGN_INTERNAL_URL = 'http://sign.test'
