"""Fleet Design System v0.9 review r1 [1]: the anonymous visitor page never discloses the confidential room name.

/signing/room/<slug> and /signing/nda/<room_id> are served to anyone holding the link, before any verification. The room
name (and everything else about the room) comes only from the authorised recipient API, which withholds it before
verification, for inactive or expired links, and once access is revoked."""
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from tests.dealroom.test_foundation import owner, staff, agent, setup_recipient  # noqa: F401 (fixtures)
from tests.dealroom.test_review_r2 import verify

SECRET_NAME = 'Project Kestrel (confidential)'


@pytest.mark.django_db
@pytest.mark.parametrize('case', ['anonymous', 'inactive_link', 'expired_link', 'revoked_access', 'verified'])
def test_visitor_page_never_renders_the_room_name(case, staff, owner, django_capture_on_commit_callbacks):
    from datarooms.models import Dataroom
    from sharelinks.models import ShareLink, ShareLinkAccessGrant
    room_id, slug = setup_recipient(staff)
    Dataroom.objects.filter(pk=room_id).update(name=SECRET_NAME)
    link = ShareLink.objects.get(slug=slug)
    client = Client()
    api = f'/api/v1/dealroom/recipient/{slug}/room/'
    if case == 'inactive_link':
        link.is_active = False
        link.save()
    elif case == 'expired_link':
        link.expires_at = timezone.now() - timedelta(days=1)
        link.save()
    elif case in ('revoked_access', 'verified'):
        client, result = verify(staff, slug, django_capture_on_commit_callbacks)
        assert result.data['status'] == 'verified', result.data
        if case == 'revoked_access':
            ShareLinkAccessGrant.objects.filter(share_link=link).update(revoked_at=timezone.now())
    # The only source of the name is the authorised API: it answers for a granted, verified visitor and nobody else.
    room = client.get(api)
    if case == 'verified':
        assert room.status_code == 200 and room.data['name'] == SECRET_NAME
    else:
        assert room.status_code in (401, 403, 404), (case, room.status_code)
        assert SECRET_NAME not in room.content.decode()
    for path in (f'/signing/room/{slug}', f'/signing/nda/{room_id}'):
        page = client.get(path)
        assert page.status_code == 200, (path, page.status_code)
        html = page.content.decode()
        assert SECRET_NAME not in html and 'Kestrel' not in html, (case, path)
        assert 'id="context-room"></span>' in html
        assert page['Cache-Control'] == 'private, no-store'
