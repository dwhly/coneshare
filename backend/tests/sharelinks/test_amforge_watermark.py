"""AmForge watermark footer / copy-id tests (image + vector PDF + flattened PDF)."""
import shutil
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory
from PIL import Image

from documents.models import Document, DocumentVersion
from sharelinks import amforge
from sharelinks.models import IssuedCopy, ShareLink, ViewerOrganisation
from sharelinks.views import (_apply_watermark_to_image, _generate_flattened_watermarked_pdf,
                              _generate_watermarked_pdf, _render_watermark_text)


def _identity(**overrides):
    ident = amforge.anonymous_identity(None, 'jane@acme.test')
    ident.update({'name': 'Jane Doe', 'organisation': 'Acme Corp', 'copy_id': 'K7Q2-9XMD', 'kind': 'download'})
    ident.update(overrides)
    return ident


def _sample_pdf_bytes(pages=2):
    from reportlab.pdfgen import canvas
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    for i in range(pages):
        c.drawString(72, 760, f"Confidential model page {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def test_footer_text_format():
    text = amforge.footer_text(_identity(timestamp='2026-11-03 20:00 UTC'))
    assert text == 'Issued to Jane Doe · Acme Corp · jane@acme.test · 2026-11-03 20:00 UTC · Copy K7Q2-9XMD'


def test_template_variables_render():
    rf = RequestFactory().get('/')
    out = _render_watermark_text('{{name}} | {{organisation}} | {{email}} | {{copy_id}} | {{date}}', rf,
                                 identity=_identity(date='2026-11-03'))
    assert out == 'Jane Doe | Acme Corp | jane@acme.test | K7Q2-9XMD | 2026-11-03'


def test_image_watermark_draws_footer_band_and_margin_line():
    img = Image.new('RGBA', (1200, 1600), (255, 255, 255, 255))
    plain = _apply_watermark_to_image(img.copy(), 'CONFIDENTIAL')
    marked = _apply_watermark_to_image(img.copy(), 'CONFIDENTIAL', identity=_identity())
    footer_plain = plain.crop((0, 1560, 1200, 1600)).convert('L')
    footer_marked = marked.crop((0, 1560, 1200, 1600)).convert('L')
    assert min(footer_marked.getdata()) < 100, 'footer text should be dark'
    assert list(footer_plain.getdata()) != list(footer_marked.getdata())
    margin_x = int(1200 * 0.022)
    column = [marked.getpixel((margin_x, y))[0] for y in range(100, 1400, 50)]
    assert all(v < 200 for v in column), 'vertical margin line should be drawn'


@pytest.mark.django_db
def test_vector_pdf_has_footer_and_metadata(django_user_model):
    from core.models import Organization
    org = Organization.objects.first() or Organization.objects.create(name='Org')
    user = django_user_model.objects.create(username='wm@example.com', email='wm@example.com', organization=org)
    doc = Document.objects.create(name='Model.pdf', organization=org, created_by=user, status='ready', type='pdf')
    version = DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True,
                                             original_storage_key='k/model.pdf', file_size=1000)
    request = RequestFactory().get('/')
    fake = MagicMock(content=_sample_pdf_bytes(), raise_for_status=lambda: None)
    with patch('sharelinks.views.fileserver_client') as fs, patch('sharelinks.views.requests.get', return_value=fake):
        fs.generate_download_url.return_value = 'http://fs/k'
        out = _generate_watermarked_pdf(doc, version, 'CONFIDENTIAL {{name}}', request, 'jane@acme.test',
                                        identity=_identity())
    from pypdf import PdfReader
    reader = PdfReader(out)
    assert len(reader.pages) == 2
    for page in reader.pages:
        text = page.extract_text()
        assert 'Issued to Jane Doe' in text
        assert 'Copy K7Q2-9XMD' in text
        assert 'Acme Corp' in text
    meta = reader.metadata
    assert meta['/AmForge-Copy-ID'] == 'K7Q2-9XMD'
    assert 'Jane Doe' in meta['/AmForge-Issued-To']
    xmp = reader.trailer['/Root']['/Metadata'].get_object().get_data().decode()
    assert '<amforge:CopyID>K7Q2-9XMD</amforge:CopyID>' in xmp


@pytest.mark.django_db
@pytest.mark.skipif(not shutil.which('pdftoppm'), reason='poppler not installed')
def test_flattened_pdf_keeps_metadata(django_user_model, settings):
    from core.models import Organization
    org = Organization.objects.first() or Organization.objects.create(name='Org')
    user = django_user_model.objects.create(username='wm2@example.com', email='wm2@example.com', organization=org)
    doc = Document.objects.create(name='Model.pdf', organization=org, created_by=user, status='ready', type='pdf',
                                  num_pages=1)
    version = DocumentVersion.objects.create(document=doc, version_number=1, is_primary=True,
                                             original_storage_key='k/model.pdf', file_size=1000)
    request = RequestFactory().get('/')
    fake = MagicMock(content=_sample_pdf_bytes(1), raise_for_status=lambda: None)
    with patch('sharelinks.views.fileserver_client') as fs, patch('sharelinks.views.requests.get', return_value=fake):
        fs.generate_download_url.return_value = 'http://fs/k'
        out = _generate_flattened_watermarked_pdf(doc, version, 'CONFIDENTIAL', request, 'jane@acme.test',
                                                  identity=_identity())
    from pypdf import PdfReader
    reader = PdfReader(out)
    assert reader.metadata['/AmForge-Copy-ID'] == 'K7Q2-9XMD'
    assert (reader.pages[0].extract_text() or '').strip() == '', 'flattened copy has no selectable text'


@pytest.mark.django_db
def test_issue_copy_reuses_view_copy_and_mints_new_downloads(django_user_model):
    from core.models import Organization
    from django.contrib.sessions.backends.db import SessionStore
    org = Organization.objects.first() or Organization.objects.create(name='Org')
    user = django_user_model.objects.create(username='wm3@example.com', email='wm3@example.com', organization=org)
    doc = Document.objects.create(name='Model.pdf', organization=org, created_by=user, status='ready', type='pdf')
    link = ShareLink.objects.create(document=doc, created_by=user, requires_email=True)
    ViewerOrganisation.objects.create(organization=org, name='Acme Corp', email_domains=['acme.test'])
    request = RequestFactory().get('/')
    request.session = SessionStore()
    request.session['authorized_share_links'] = {str(link.id): {
        'email_verified': True, 'viewer_email': 'jane@acme.test', 'viewer_name': 'Jane Doe',
    }}
    v1 = amforge.issue_copy(link, request, doc, IssuedCopy.KIND_VIEW)
    v2 = amforge.issue_copy(link, request, doc, IssuedCopy.KIND_VIEW)
    d1 = amforge.issue_copy(link, request, doc, IssuedCopy.KIND_DOWNLOAD)
    d2 = amforge.issue_copy(link, request, doc, IssuedCopy.KIND_DOWNLOAD)
    assert v1['copy_id'] == v2['copy_id']
    assert len({v1['copy_id'], d1['copy_id'], d2['copy_id']}) == 3
    assert v1['organisation'] == 'Acme Corp'
    assert IssuedCopy.objects.filter(share_link=link).count() == 3


def test_download_policy():
    link = MagicMock(allow_original_download=False)
    assert amforge.download_requires_watermark(link, False) is True
    link.allow_original_download = True
    assert amforge.download_requires_watermark(link, False) is False
    assert amforge.download_requires_watermark(link, True) is True
