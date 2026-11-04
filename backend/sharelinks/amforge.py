"""
AmForge Deal Suite extensions for share links.

Kept in one module so the upstream Coneshare views stay close to their original
shape (easier rebases). Covers:

* organisation / email access grants (``ShareLink.restrict_to_grants``),
* viewer identity (name + resolved counterparty organisation),
* per-copy ids (``IssuedCopy``) and the structured watermark footer that is
  drawn on server-rendered page images and on downloaded PDFs,
* PDF metadata (Info dictionary + XMP) carrying the copy id.
"""
import logging
import os
from datetime import datetime, timezone as dt_timezone
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.conf import settings
from django.utils import timezone

from backend.utils import get_client_ip

from .models import IssuedCopy, ShareLinkAccessGrant, ViewerOrganisation, ViewSession

logger = logging.getLogger(__name__)

FOOTER_SEPARATOR = " \u00b7 "  # middle dot
FOOTER_FONT_CANDIDATES = (
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
)


# ---------------------------------------------------------------------------
# Organisation grants
# ---------------------------------------------------------------------------

def email_domain(email: str) -> str:
    return ViewerOrganisation.normalize_domain(email or '')


def resolve_viewer_organisation(tenant_organization, email: str, share_link=None):
    """
    Resolve the counterparty organisation for a verified email. Organisations
    granted on ``share_link`` win over other organisations of the same tenant.
    """
    domain = email_domain(email)
    if not domain or tenant_organization is None:
        return None
    candidates = list(
        ViewerOrganisation.objects.filter(organization=tenant_organization).order_by('name')
    )
    matching = [org for org in candidates if domain in (org.email_domains or [])]
    if not matching:
        return None
    if share_link is not None:
        granted_ids = set(
            share_link.access_grants.filter(viewer_organisation__isnull=False)
            .values_list('viewer_organisation_id', flat=True)
        )
        for org in matching:
            if org.id in granted_ids:
                return org
    return matching[0]


def is_email_granted(share_link, email: str) -> bool:
    """True if ``email`` may pass a link with ``restrict_to_grants`` enabled."""
    email = (email or '').strip().lower()
    if not email:
        return False
    grants = list(share_link.access_grants.select_related('viewer_organisation'))
    for grant in grants:
        if grant.email and grant.email == email:
            return True
        if grant.viewer_organisation and grant.viewer_organisation.matches_email(email):
            return True
    return False


def grants_bypassed(auth_status: dict) -> bool:
    """Owners / org members previewing their own link are never grant-checked."""
    return (auth_status or {}).get('email_method') in ('owner', 'account')


# ---------------------------------------------------------------------------
# Viewer identity + issued copies
# ---------------------------------------------------------------------------

def _session_key(request) -> str:
    session = getattr(request, 'session', None)
    if session is None:
        return ''
    if not session.session_key:
        try:
            session.save()
        except Exception:  # pragma: no cover - defensive
            return ''
    return session.session_key or ''


def _auth_status(request, share_link) -> dict:
    session = getattr(request, 'session', None)
    if session is None:
        return {}
    return session.get('authorized_share_links', {}).get(str(share_link.id), {}) or {}


def _identity_from_session(request, share_link, auth_status=None) -> dict:
    auth_status = auth_status if auth_status is not None else _auth_status(request, share_link)
    email = (auth_status.get('viewer_email') or '').strip().lower()
    name = (auth_status.get('viewer_name') or '').strip()
    organisation = (auth_status.get('viewer_organisation_name') or '').strip()
    view_session = None
    view_session_id = auth_status.get('view_session_id')
    if view_session_id:
        view_session = ViewSession.objects.filter(id=view_session_id, share_link=share_link).first()
    if view_session is not None:
        email = email or view_session.viewer_email
        name = name or view_session.viewer_name
        organisation = organisation or view_session.viewer_organisation_name
    if email and not organisation:
        org = resolve_viewer_organisation(share_link.organization, email, share_link)
        organisation = org.name if org else ''
    return {
        'email': email,
        'name': name,
        'organisation': organisation,
        'view_session': view_session,
    }


def _identity_dict(copy: IssuedCopy, ip_address: str) -> dict:
    issued_at = copy.created_at.astimezone(dt_timezone.utc)
    return {
        'name': copy.viewer_name,
        'organisation': copy.viewer_organisation_name,
        'email': copy.viewer_email,
        'ip_address': ip_address or '',
        'copy_id': copy.copy_id,
        'kind': copy.kind,
        'issued_at': issued_at,
        'timestamp': issued_at.strftime('%Y-%m-%d %H:%M UTC'),
        'date': issued_at.strftime('%Y-%m-%d'),
    }


def issue_copy(share_link, request, document, kind, dataroom_document=None, auth_status=None, version_override=None) -> dict:
    """
    Return the watermark identity for one copy of ``document``.

    ``kind='view'`` reuses one IssuedCopy per (link, document, browser session)
    so every page of a viewing session carries the same copy id (and the page
    images stay cacheable). Downloads always mint a new copy.
    """
    ident = _identity_from_session(request, share_link, auth_status)
    ip_address = get_client_ip(request) or ''
    session_key = _session_key(request)
    copy = None
    version = version_override or document.versions.filter(is_primary=True).first()
    if kind == IssuedCopy.KIND_VIEW:
        lookup = IssuedCopy.objects.filter(
            share_link=share_link, kind=kind, document=document, session_key=session_key,
            viewer_email=ident['email'],
        )
        if dataroom_document is not None:
            lookup = lookup.filter(dataroom_document=dataroom_document)
        if getattr(settings, 'DEALROOM_ENABLED', False):
            from dealroom.brand import load_brand
            lookup = lookup.filter(evidence__version=version, evidence__brand_revision=load_brand()['revision'])
        copy = lookup.order_by('-created_at').first() if session_key else None
    if copy is None:
        copy = IssuedCopy.objects.create(
            kind=kind,
            share_link=share_link,
            view_session=ident['view_session'],
            session_key=session_key,
            document=document,
            dataroom_document=dataroom_document,
            viewer_email=ident['email'],
            viewer_name=ident['name'],
            viewer_organisation_name=ident['organisation'],
            ip_address=ip_address or None,
        )
        if getattr(settings, 'DEALROOM_ENABLED', False):
            from dealroom.activity import record
            from dealroom.models import CopyEvidence
            from dealroom.brand import load_brand
            if version:
                decision = getattr(request, 'dealroom_decision', None)
                CopyEvidence.objects.create(copy=copy, version=version, brand_revision=load_brand()['revision'], source_sha256=version.metadata.get('source_sha256', ''), grant_id=decision.grant_id if decision else None, policy_revision=decision.policy_revision if decision else 1)
            record('copy.issued', organization=share_link.organization, actor=ident['view_session'].viewer if ident['view_session'] else ident['email'], room_id=share_link.dataroom_id, target_id=copy.copy_id, data={'kind': kind})
        if kind == IssuedCopy.KIND_ORIGINAL:
            logger.warning(
                "AUDIT original-file download link=%s document=%s copy=%s email=%s ip=%s",
                share_link.id, getattr(document, 'id', None), copy.copy_id, copy.viewer_email, ip_address,
            )
        else:
            logger.info(
                "Issued %s copy %s link=%s document=%s email=%s",
                kind, copy.copy_id, share_link.id, getattr(document, 'id', None), copy.viewer_email,
            )
    return _identity_dict(copy, ip_address)


def anonymous_identity(request, viewer_email: str = '') -> dict:
    now = timezone.now().astimezone(dt_timezone.utc)
    return {
        'name': '', 'organisation': '', 'email': (viewer_email or '').strip().lower(),
        'ip_address': (get_client_ip(request) or '') if request is not None else '',
        'copy_id': '', 'kind': '', 'issued_at': now,
        'timestamp': now.strftime('%Y-%m-%d %H:%M UTC'), 'date': now.strftime('%Y-%m-%d'),
    }


def render_watermark_template(template_string: str, identity: dict) -> str:
    """Resolve {{email}}, {{ip-address}}, {{name}}, {{organisation}}, {{copy_id}}, {{date}}."""
    replacements = {
        '{{ip-address}}': identity.get('ip_address') or 'N/A',
        '{{email}}': identity.get('email') or 'N/A',
        '{{name}}': identity.get('name') or identity.get('email') or 'N/A',
        '{{organisation}}': identity.get('organisation') or 'N/A',
        '{{organization}}': identity.get('organisation') or 'N/A',
        '{{copy_id}}': identity.get('copy_id') or 'N/A',
        '{{date}}': identity.get('date') or '',
    }
    rendered = template_string or ''
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered


def footer_text(identity: dict) -> str:
    """'Issued to {name} · {organisation} · {email} · {UTC timestamp} · Copy {copy_id}'."""
    name = identity.get('name') or identity.get('email') or 'Unidentified viewer'
    from dealroom.brand import load_brand
    if getattr(settings, 'DEALROOM_ENABLED', False):
        return render_watermark_template(load_brand()['watermark'], identity)
    parts = [f"Issued to {name}"]
    if identity.get('organisation'):
        parts.append(identity['organisation'])
    if identity.get('email'):
        parts.append(identity['email'])
    parts.append(identity.get('timestamp') or '')
    if identity.get('copy_id'):
        parts.append(f"Copy {identity['copy_id']}")
    return FOOTER_SEPARATOR.join(p for p in parts if p)


def margin_text(identity: dict) -> str:
    from dealroom.brand import load_brand
    bits = [load_brand()['name']]
    if identity.get('copy_id'):
        bits.append(f"Copy {identity['copy_id']}")
    if identity.get('email'):
        bits.append(identity['email'])
    return FOOTER_SEPARATOR.join(bits)


# ---------------------------------------------------------------------------
# Drawing: Pillow (page images / image downloads)
# ---------------------------------------------------------------------------

def _load_pil_font(size: int):
    from PIL import ImageFont
    candidates = list(FOOTER_FONT_CANDIDATES) + [getattr(settings, 'WATERMARK_FONT_PATH', '')]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:  # pragma: no cover - font edge cases
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def draw_footer_on_image(image, identity: dict):
    """Draw the structured footer band + thin vertical margin line on an RGBA image."""
    from PIL import Image, ImageDraw

    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    width, height = image.size
    text = footer_text(identity)
    font_size = max(12, int(width / 64))
    font = _load_pil_font(font_size)
    layer = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)

    # Shrink the font until the footer fits within 94% of the page width.
    while font_size > 9:
        bbox = draw.textbbox((0, 0), text, font=font)
        if (bbox[2] - bbox[0]) <= width * 0.94:
            break
        font_size -= 1
        font = _load_pil_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = max(4, int(font_size * 0.5))
    band_h = text_h + pad * 2
    band_top = height - band_h
    draw.rectangle([0, band_top, width, height], fill=(255, 255, 255, 225))
    draw.line([(0, band_top), (width, band_top)], fill=(120, 120, 120, 200), width=1)
    text_x = max(pad, int((width - text_w) / 2))
    draw.text((text_x - bbox[0], band_top + pad - bbox[1]), text, font=font, fill=(40, 40, 40, 255))

    # Thin vertical margin line near the left edge with the copy id running along it.
    margin_x = max(6, int(width * 0.022))
    line_w = max(1, int(width / 900))
    draw.line([(margin_x, 0), (margin_x, band_top)], fill=(110, 110, 110, 170), width=line_w)
    m_text = margin_text(identity)
    m_font_size = max(9, int(font_size * 0.75))
    m_font = _load_pil_font(m_font_size)
    m_bbox = draw.textbbox((0, 0), m_text, font=m_font)
    m_w, m_h = m_bbox[2] - m_bbox[0], m_bbox[3] - m_bbox[1]
    if m_w < band_top:
        tile = Image.new('RGBA', (m_w + 2, m_h + 2), (255, 255, 255, 0))
        ImageDraw.Draw(tile).text((-m_bbox[0], -m_bbox[1]), m_text, font=m_font, fill=(90, 90, 90, 190))
        tile = tile.rotate(90, expand=True)
        y = max(0, int((band_top - tile.height) / 2))
        x = margin_x + line_w + 2
        if x + tile.width < width:
            layer.alpha_composite(tile, (x, y))
    return Image.alpha_composite(image, layer)


def jpeg_exif_for(identity: dict):
    """EXIF block (ImageDescription/Artist/Copyright) carrying the copy id."""
    try:
        from PIL import Image
        exif = Image.Exif()
        exif[0x010E] = f"AmForge-Copy-ID: {identity.get('copy_id', '')}; {footer_text(identity)}"
        exif[0x013B] = identity.get('email') or ''
        return exif.tobytes()
    except Exception:  # pragma: no cover
        return b''


# ---------------------------------------------------------------------------
# Drawing: ReportLab (vector PDF overlay)
# ---------------------------------------------------------------------------

def draw_footer_on_canvas(pdf_canvas, page_width: float, page_height: float, identity: dict):
    """Draw footer band + margin line on a ReportLab canvas (Helvetica covers U+00B7)."""
    from reportlab.lib import colors

    text = footer_text(identity)
    font_name = 'Helvetica'
    font_size = max(5.5, min(9.0, page_width / 66.0))
    while font_size > 5 and pdf_canvas.stringWidth(text, font_name, font_size) > page_width * 0.94:
        font_size -= 0.25
    pad = font_size * 0.55
    band_h = font_size + pad * 2

    pdf_canvas.saveState()
    pdf_canvas.setFillColor(colors.white, alpha=0.88)
    pdf_canvas.rect(0, 0, page_width, band_h, stroke=0, fill=1)
    pdf_canvas.setStrokeColor(colors.Color(0.47, 0.47, 0.47), alpha=0.8)
    pdf_canvas.setLineWidth(0.4)
    pdf_canvas.line(0, band_h, page_width, band_h)
    pdf_canvas.setFillColor(colors.Color(0.16, 0.16, 0.16), alpha=1)
    pdf_canvas.setFont(font_name, font_size)
    pdf_canvas.drawCentredString(page_width / 2.0, pad + font_size * 0.18, text)

    margin_x = max(8.0, page_width * 0.022)
    pdf_canvas.setStrokeColor(colors.Color(0.43, 0.43, 0.43), alpha=0.7)
    pdf_canvas.setLineWidth(0.5)
    pdf_canvas.line(margin_x, band_h, margin_x, page_height)
    m_text = margin_text(identity)
    m_size = max(5.0, font_size * 0.8)
    m_w = pdf_canvas.stringWidth(m_text, font_name, m_size)
    span = page_height - band_h
    if m_w < span:
        pdf_canvas.setFillColor(colors.Color(0.35, 0.35, 0.35), alpha=0.8)
        pdf_canvas.setFont(font_name, m_size)
        pdf_canvas.translate(margin_x + m_size + 1.5, band_h + (span - m_w) / 2.0)
        pdf_canvas.rotate(90)
        pdf_canvas.drawString(0, 0, m_text)
    pdf_canvas.restoreState()


# ---------------------------------------------------------------------------
# PDF metadata
# ---------------------------------------------------------------------------

def _xmp_packet(identity: dict) -> bytes:
    issued_to = issued_to_string(identity)
    issued_at = identity.get('issued_at') or datetime.now(dt_timezone.utc)
    return (
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
        '  <rdf:Description rdf:about=""\n'
        '    xmlns:amforge="https://amforge.com/ns/issued-copy/1.0/"\n'
        '    xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'   <amforge:CopyID>{xml_escape(identity.get("copy_id") or "")}</amforge:CopyID>\n'
        f'   <amforge:IssuedTo>{xml_escape(issued_to)}</amforge:IssuedTo>\n'
        f'   <amforge:IssuedAt>{xml_escape(issued_at.isoformat())}</amforge:IssuedAt>\n'
        f'   <amforge:Kind>{xml_escape(identity.get("kind") or "")}</amforge:Kind>\n'
        f'   <dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{xml_escape(footer_text(identity))}</rdf:li></rdf:Alt></dc:rights>\n'
        '  </rdf:Description>\n'
        ' </rdf:RDF>\n'
        '</x:xmpmeta>\n'
        '<?xpacket end="w"?>'
    ).encode('utf-8')


def issued_to_string(identity: dict) -> str:
    bits = [identity.get('name') or identity.get('email') or 'Unidentified viewer']
    if identity.get('email') and identity.get('name'):
        bits[0] = f"{identity['name']} <{identity['email']}>"
    if identity.get('organisation'):
        bits.append(f"({identity['organisation']})")
    return ' '.join(bits)


def apply_pdf_metadata(writer, identity: dict):
    """Stamp a pypdf PdfWriter with Info keys and an XMP packet carrying the copy id."""
    from pypdf.generic import NameObject, StreamObject

    issued_at = identity.get('issued_at') or datetime.now(dt_timezone.utc)
    writer.add_metadata({
        '/AmForge-Copy-ID': identity.get('copy_id') or '',
        '/AmForge-Issued-To': issued_to_string(identity),
        '/AmForge-Issued-At': issued_at.isoformat(),
        '/Subject': footer_text(identity),
        '/Producer': __import__('dealroom.brand', fromlist=['load_brand']).load_brand()['name'] + ' Send',
    })
    try:
        stream = StreamObject()
        stream.set_data(_xmp_packet(identity))
        stream.update({
            NameObject('/Type'): NameObject('/Metadata'),
            NameObject('/Subtype'): NameObject('/XML'),
        })
        root = getattr(writer, 'root_object', None) or writer._root_object
        root[NameObject('/Metadata')] = writer._add_object(stream)
    except Exception as exc:  # pragma: no cover - metadata must never block a download
        logger.warning("Could not embed XMP metadata: %s", exc)
    return writer


def stamp_pdf_bytes(pdf_bytes: bytes, identity: dict) -> BytesIO:
    """Re-write an existing PDF (e.g. a Pillow-flattened one) with AmForge metadata."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter(clone_from=reader)
    apply_pdf_metadata(writer, identity)
    out = BytesIO()
    writer.write(out)
    out.seek(0)
    return out


# ---------------------------------------------------------------------------
# Download policy
# ---------------------------------------------------------------------------

def download_requires_watermark(share_link, item_watermark_enabled: bool) -> bool:
    """
    Every download is a watermarked copy unless the admin explicitly allowed
    original-file downloads on the link AND the item itself is not watermarked.
    """
    if getattr(settings, 'DEALROOM_ENABLED', False) or item_watermark_enabled:
        return True
    return not bool(getattr(share_link, 'allow_original_download', False))


def access_grant_queryset_for_link(share_link):
    return ShareLinkAccessGrant.objects.filter(share_link=share_link).select_related('viewer_organisation')


def viewer_organisations_for_tenant(tenant_organization):
    return ViewerOrganisation.objects.filter(organization=tenant_organization)


def find_view_session_organisation(view_session) -> str:
    if view_session is None:
        return ''
    return view_session.viewer_organisation_name or ''


__all__ = [
    'apply_pdf_metadata', 'anonymous_identity', 'download_requires_watermark',
    'draw_footer_on_canvas', 'draw_footer_on_image', 'footer_text', 'grants_bypassed',
    'is_email_granted', 'issue_copy', 'jpeg_exif_for', 'render_watermark_template',
    'resolve_viewer_organisation', 'stamp_pdf_bytes',
]
