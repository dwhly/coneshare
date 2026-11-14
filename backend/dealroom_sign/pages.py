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
    # Visitor pages carry the Fleet lockup only (docs/design/dealroom-shell.md §0, §4). This response is anonymous: it
    # never carries room metadata (name, files). The context bar's room name and the visitor are filled in by room.html
    # from the AUTHORISED recipient API (/api/v1/dealroom/recipient/<slug>/room/), which withholds them before
    # verification, for inactive/expired links and for revoked access.
    from dealroom.models import RoomPolicy
    if room_id:
        policy = get_object_or_404(RoomPolicy.objects.select_related('entry_link'), room_id=room_id)
        link = policy.entry_link
    else:
        link = get_object_or_404(ShareLink, slug=slug, dataroom__isnull=False)
    response = render(request, 'dealroom_sign/room.html', {'slug': link.slug, 'room_id': str(link.dataroom_id)})
    response['Cache-Control'] = 'private, no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response


@require_GET
def staff(request):
    return render(request, 'dealroom_sign/staff.html', {'sign_url': _sign_url()})
