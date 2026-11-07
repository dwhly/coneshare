from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from sharelinks.models import ShareLink


def _sign_url():
    from django.conf import settings
    return (getattr(settings, 'SIGN_PUBLIC_URL', '') or '').rstrip('/')


@require_GET
@ensure_csrf_cookie
def room(request, slug=None, room_id=None):
    # Visitor pages carry the Fleet lockup only (docs/design/dealroom-shell.md §0, §4); the context bar shows the
    # room's name (anyone holding the link already knows which room it is) and, once verified, the visitor.
    from dealroom.models import RoomPolicy
    if room_id:
        policy = get_object_or_404(RoomPolicy.objects.select_related('entry_link', 'entry_link__dataroom'), room_id=room_id)
        link = policy.entry_link
    else:
        link = get_object_or_404(ShareLink.objects.select_related('dataroom'), slug=slug, dataroom__isnull=False)
    response = render(request, 'dealroom_sign/room.html', {'slug': link.slug, 'room_id': str(link.dataroom_id),
                                                          'room_name': link.dataroom.name})
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response


@require_GET
def staff(request):
    return render(request, 'dealroom_sign/staff.html', {'sign_url': _sign_url()})
