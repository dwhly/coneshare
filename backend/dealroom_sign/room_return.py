"""Where a room NDA's signer goes after verified publication.

The room application that started the NDA records its own origin (deployment configuration, never request data)
as a ``room.return`` fact on the workflow. The shared signer gateway reads it back here.
"""
from urllib.parse import urlsplit

from django.conf import settings

from .models import ObservedSignEvent


def bind(workflow):
    if workflow.purpose != 'nda':
        return
    origin = urlsplit(settings.SITE_DOMAIN)
    if origin.scheme not in {'http', 'https'} or not origin.netloc or origin.username or origin.password:
        raise ValueError('A configured room site origin is required.')
    ObservedSignEvent.objects.get_or_create(workflow=workflow, kind='room.return', source_id='room.return',
        defaults={'payload': {'room_id': str(workflow.room_id), 'origin': f'{origin.scheme}://{origin.netloc}'}})


def confirmation_url(workflow):
    """The bound room's confirmation page, or None (callers keep their legacy destination)."""
    from dealroom.models import RoomPolicy
    if workflow.purpose != 'nda':
        return None
    binding = ObservedSignEvent.objects.filter(workflow=workflow, kind='room.return', source_id='room.return').first()
    if not binding or binding.payload.get('room_id') != str(workflow.room_id):
        return None
    origin = urlsplit(str(binding.payload.get('origin', '')))
    if origin.scheme not in {'http', 'https'} or not origin.netloc or origin.username or origin.password:
        return None
    policy = RoomPolicy.objects.select_related('entry_link').filter(room_id=workflow.room_id).first()
    if not policy:
        return None
    return f'{origin.scheme}://{origin.netloc}/view/{policy.entry_link.slug}?nda=complete'
