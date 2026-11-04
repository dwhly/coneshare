from django.apps import AppConfig


class DealroomSignConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dealroom_sign'

    def ready(self):
        from . import operations  # noqa: F401
