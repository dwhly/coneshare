"""Gate 3 regressions; exercise the deployed policy with real OTP proofs."""
import re
import pytest
from django.core import mail
from rest_framework.test import APIClient
from tests.dealroom.test_foundation import owner, staff, agent, setup_recipient


def verify(staff, slug, capture, email='jane@acme.test'):
    client = APIClient(enforce_csrf_checks=True)
    base = f'/api/v1/dealroom/recipient/{slug}'
    csrf = client.get(base + '/challenge/').data['csrf_token']
    with capture(execute=True):
        issued = client.post(base + '/challenge/', {'email': email, 'name': 'Jane'}, format='json', HTTP_X_CSRFTOKEN=csrf)
    code = re.search(r'code is (\d{6})', mail.outbox[-1].body)[1]
    result = client.post(base + '/confirm/', {'challenge_id': issued.data['challenge_id'], 'code': code}, format='json', HTTP_X_CSRFTOKEN=csrf)
    return client, result


@pytest.mark.django_db
def test_r2_03_recipient_folders_require_visible_permitted_content(staff, owner, django_capture_on_commit_callbacks, monkeypatch):
    from datarooms.models import DataroomFolder, DataroomDocument
    from documents.models import Document, DocumentVersion
    from sharelinks.models import ShareLink, ShareLinkDataroomSetting
    from rest_framework.exceptions import PermissionDenied
    import dealroom.recipient as recipient
    room, slug = setup_recipient(staff)
    link = ShareLink.objects.get(slug=slug)
    folders = {}
    for name in ('Financials', 'Bidder B – LOI', 'Empty', 'Executed', 'NDAs'):
        folders[name] = DataroomFolder.objects.create(dataroom_id=room, name=name, created_by=owner, parent=folders.get('Executed') if name == 'NDAs' else None)
    private_id = None
    for name in ('Financials', 'Bidder B – LOI', 'NDAs'):
        doc = Document.objects.create(organization=owner.organization, created_by=owner, name=name + '.pdf')
        DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True)
        item = DataroomDocument.objects.create(dataroom_id=room, folder=folders[name], document=doc)
        if name == 'NDAs':
            private_id = str(item.pk)
    ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_folder=folders['Bidder B – LOI']).update(is_visible=False)
    original = recipient.evaluate
    def subject_policy(request, link, **kwargs):
        if kwargs.get('document_id') == private_id:
            raise PermissionDenied('Execution artifact belongs to another member.')
        return original(request, link, **kwargs)
    monkeypatch.setattr(recipient, 'evaluate', subject_policy)
    client, result = verify(staff, slug, django_capture_on_commit_callbacks)
    assert result.data['status'] == 'verified'
    result = client.get(f'/api/v1/dealroom/recipient/{slug}/room/')
    assert result.status_code == 200
    assert [f['name'] for f in result.data['folders']] == ['Financials']
    assert [f['name'] for f in result.data['files']] == ['Financials.pdf']
