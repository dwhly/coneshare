from django.apps import AppConfig

from .tenant_brand import get_tenant_brand


class DealroomSignConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dealroom_sign'

    def ready(self):
        get_tenant_brand()
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        from .recipient_logging import RecipientLogFilter
        for name in ('django.request', 'django.security.csrf', 'django.security.DisallowedHost'):
            logging.getLogger(name).addFilter(RecipientLogFilter())
        from django.apps import apps
        if apps.is_installed("dealroom"):
            from .operations import install
            install()
