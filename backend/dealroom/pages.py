"""Existing Sign return links land on the same React room as personal invitations."""
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

from sharelinks.models import ShareLink
from .models import RoomPolicy


def visitor_room(request, slug=None, room_id=None):
    if room_id:
        slug = get_object_or_404(RoomPolicy.objects.select_related('entry_link'), room_id=room_id).entry_link.slug
    else:
        get_object_or_404(ShareLink, slug=slug, dataroom__isnull=False)
    response = HttpResponseRedirect(f'/view/{slug}')
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'same-origin'
    return response
