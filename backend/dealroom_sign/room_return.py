"""Persist the room application's origin before handing an NDA to a shared signer."""
from urllib.parse import urlsplit

from django.conf import settings

from dealroom.models import RoomPolicy
from .models import ObservedSignEvent


def bind(workflow):
    if workflow.purpose != 'nda':
        return
    # Only deployment configuration supplies this value. Never accept request data,
    # Host, Referer or callback query parameters as a return destination.
    origin = urlsplit(settings.SITE_DOMAIN)
    if origin.scheme not in {'http', 'https'} or not origin.netloc or origin.username or origin.password:
        raise ValueError('A configured room site origin is required.')
    ObservedSignEvent.objects.get_or_create(workflow=workflow, kind='room.return', source_id='room.return',
        defaults={'payload': {'room_id': str(workflow.room_id), 'origin': f'{origin.scheme}://{origin.netloc}'}})


def confirmation_url(workflow):
    if workflow.purpose != 'nda':
        return None
    policy = RoomPolicy.objects.select_related('entry_link').filter(room_id=workflow.room_id).first()
    if not policy:
        return None
    binding = ObservedSignEvent.objects.filter(workflow=workflow, kind='room.return', source_id='room.return').first()
    if binding:
        if binding.payload.get('room_id') != str(workflow.room_id):
            return None
        origin = binding.payload['origin']
    else:
        # Legacy workflows on a single deployment retain their configured destination.
        # Starting/continuing one through the room binds it before the next handoff.
        origin = settings.SITE_DOMAIN.rstrip('/')
    return f'{origin}/view/{policy.entry_link.slug}?nda=complete'
