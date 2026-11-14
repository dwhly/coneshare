"""Fleet recipient download headers and copy evidence."""
import hashlib
from io import BytesIO
from unittest.mock import patch

import pytest

from datarooms.models import DataroomDocument
from dealroom.models import CopyEvidence
from documents.models import Document, DocumentVersion
from sharelinks.models import IssuedCopy, ShareLink, ShareLinkDataroomSetting
from tests.dealroom.test_foundation import owner, setup_recipient, staff
from tests.dealroom.test_review_r2 import verify


@pytest.fixture(autouse=True)
def fleet_download_environment(settings):
    settings.DEALROOM_ENABLED = True
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    with patch(
        'requests.sessions.Session.request',
        side_effect=AssertionError('HTTP must be mocked in download tests.'),
    ):
        yield


@pytest.mark.django_db
@pytest.mark.parametrize(
    'document_type,flatten,source_extension,extension,content_type,renderer',
    [
        ('pdf', False, '.pdf', '.pdf', 'application/pdf', '_generate_watermarked_pdf'),
        ('pdf', True, '.pdf', '.pdf', 'application/pdf', '_generate_flattened_watermarked_pdf'),
        ('image', False, '.png', '.jpg', 'image/jpeg', '_generate_watermarked_image'),
    ],
    ids=['pdf', 'flattened-pdf', 'image'],
)
@pytest.mark.parametrize(
    'name,ascii_base,encoded_base',
    [
        ('Résumé "Q1"\r\n/東京{ext}', 'Rsum_Q1', 'R%C3%A9sum%C3%A9_Q1%E6%9D%B1%E4%BA%AC'),
        ('東京{ext}', None, '%E6%9D%B1%E4%BA%AC'),
        ('???', None, None),
    ],
    ids=['cleaned-name', 'ascii-fallback', 'empty-cleaned-name'],
)
def test_watermarked_download_headers(
    staff, owner, settings, django_capture_on_commit_callbacks,
    document_type, flatten, source_extension, extension, content_type, renderer,
    name, ascii_base, encoded_base,
):
    settings.FLATTEN_WATERMARKED_DOWNLOADS = flatten
    room_id, slug = setup_recipient(staff)
    link = ShareLink.objects.get(slug=slug)
    link.access_grants.update(download_ceiling='watermarked')
    document = Document.objects.create(
        organization=owner.organization,
        created_by=owner,
        name=name.format(ext=source_extension),
        type=document_type,
        content_type='image/png' if document_type == 'image' else 'application/pdf',
    )
    version = DocumentVersion.objects.create(
        document=document,
        version_number=1,
        is_primary=True,
        original_storage_key=f'fleet/source{source_extension}',
        storage_key=f'fleet/source{source_extension}',
        type=document_type,
        file_size=100,
    )
    item = DataroomDocument.objects.create(dataroom_id=room_id, document=document)
    ShareLinkDataroomSetting.objects.filter(share_link=link, dataroom_document=item).update(
        enable_watermark=True, allow_download=True, download_ceiling='watermarked',
    )
    recipient, confirmed = verify(staff, slug, django_capture_on_commit_callbacks)
    assert confirmed.data['status'] == 'verified', confirmed.data

    rendered_bytes = b'rendered watermarked copy'
    buffer = BytesIO(rendered_bytes)
    rendered = (buffer, content_type) if document_type == 'image' else buffer
    with (
        patch(f'sharelinks.views.{renderer}', return_value=rendered) as render,
        patch('sharelinks.views.fileserver_client') as storage,
    ):
        response = recipient.get(
            f'/api/v1/links/{slug}/download-file/',
            {'dataroom_document_id': str(item.pk)},
        )
    assert response.status_code == 200, getattr(response, 'data', None)
    render.assert_called_once()
    assert not storage.mock_calls
    assert response.content == rendered_bytes
    assert response['Content-Type'] == content_type

    fallback = 'image' if document_type == 'image' else 'document'
    expected_ascii = f'{ascii_base or fallback}{extension}'
    expected_utf8 = f'{encoded_base or fallback}{extension}'
    assert response['Content-Disposition'] == (
        f'attachment; filename="{expected_ascii}"; filename*=UTF-8\'\'{expected_utf8}'
    )
    copy_id = response['X-AmForge-Copy-ID']
    assert copy_id
    assert response['X-Dealroom-Copy-ID'] == copy_id
    assert render.call_args.kwargs['identity']['copy_id'] == copy_id
    copy = IssuedCopy.objects.get(copy_id=copy_id)
    assert copy.document == document
    assert copy.viewer_email == 'jane@acme.test'
    assert copy.kind == IssuedCopy.KIND_DOWNLOAD
    evidence = CopyEvidence.objects.get(copy=copy)
    assert evidence.version == version
    assert evidence.artifact_sha256 == hashlib.sha256(rendered_bytes).hexdigest()
