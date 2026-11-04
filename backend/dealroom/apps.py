from django.apps import AppConfig


class DealroomConfig(AppConfig):
    name = 'dealroom'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from .hooks import install
        install()
