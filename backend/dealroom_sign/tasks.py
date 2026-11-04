from celery import shared_task

from .models import Workflow
from .workflows import process


@shared_task(ignore_result=True)
def reconcile_envelope(envelope_id):
    workflow = Workflow.objects.filter(envelope_id=envelope_id).first()
    if workflow:
        process(workflow.pk)
    else:
        # A create response may be lost: pending commands discover by externalId.
        from .workflows import sweep
        sweep()
