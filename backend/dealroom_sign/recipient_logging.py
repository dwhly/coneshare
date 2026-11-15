"""Keep recipient capabilities and cookies out of Django diagnostic destinations."""
import logging


class RecipientLogFilter(logging.Filter):
    def filter(self, record):
        request = getattr(record, 'request', None)
        if request and (request.META.get('HTTP_X_FLEET_RECIPIENT_LISTENER') == '1' or
                        request.path.startswith(('/s/', '/sign/', '/api/files/token/'))):
            record.msg = 'Recipient request failed (request details withheld)'
            record.args = ()
            record.exc_info = record.exc_text = None
            del record.request
        return True
