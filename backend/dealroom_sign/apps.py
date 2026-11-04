from django.apps import AppConfig


class DealroomSignConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dealroom_sign'

    def ready(self):
        from django.apps import apps
        if apps.is_installed("dealroom"):
            from .operations import install
            install()
