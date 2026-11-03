"""
AmForge: duplicate a data room.

Copies the folder tree, document references (the same ``documents.Document``
rows, so no stored file or version blob is duplicated), item ordering, room
settings/branding and, optionally, the room's share links as *inactive*
templates (settings, per-item permissions and organisation/email grants only;
never visitor data, sessions, NDA acceptances, Q&A or analytics).
"""
import logging

from django.db import transaction

from sharelinks.models import ShareLink, ShareLinkAccessGrant, ShareLinkDataroomSetting

from .models import (
    Dataroom,
    DataroomBannerImage,
    DataroomDocument,
    DataroomFolder,
    DataroomItemOrder,
)

logger = logging.getLogger(__name__)

ROOM_FIELDS_TO_COPY = (
    'show_file_index', 'enable_qna', 'banner_mode', 'logo_mode',
    'brand_primary_color', 'brand_secondary_color', 'brand_accent_color',
    'storage_quota_mb', 'storage_version',
)

LINK_FIELDS_TO_COPY = (
    'expires_at', 'password', 'requires_email', 'requires_email_verification',
    'allow_download', 'allow_original_download', 'restrict_to_grants', 'enable_qna',
    'enable_watermark', 'watermark_text', 'receive_email_notification',
    'require_nda', 'nda_text',
)


def _unique_room_name(organization, base_name: str) -> str:
    existing = set(
        Dataroom.objects.filter(organization=organization, name__startswith=base_name)
        .values_list('name', flat=True)
    )
    candidate = f"{base_name} (copy)"
    n = 2
    while candidate in existing:
        candidate = f"{base_name} (copy {n})"
        n += 1
    return candidate


def _ordered_folders(source: Dataroom):
    """Folders parents-first so every parent is cloned before its children."""
    folders = list(DataroomFolder.objects.filter(dataroom=source).order_by('created_at', 'id'))
    by_id = {f.id: f for f in folders}
    ordered, placed = [], set()

    def place(folder, chain=()):
        if folder.id in placed or folder.id in chain:
            return
        if folder.parent_id and folder.parent_id in by_id:
            place(by_id[folder.parent_id], chain + (folder.id,))
        placed.add(folder.id)
        ordered.append(folder)

    for f in folders:
        place(f)
    return ordered


@transaction.atomic
def clone_dataroom(source: Dataroom, user, name: str | None = None, include_share_links: bool = True) -> dict:
    new_room = Dataroom(
        organization=source.organization,
        created_by=user,
        name=(name or '').strip() or _unique_room_name(source.organization, source.name),
    )
    for field in ROOM_FIELDS_TO_COPY:
        setattr(new_room, field, getattr(source, field))
    # Reuse stored branding files by reference (no blob copy).
    if source.branding_banner:
        new_room.branding_banner = source.branding_banner.name
    if source.brand_logo_override:
        new_room.brand_logo_override = source.brand_logo_override.name
    new_room.save()

    for banner in DataroomBannerImage.objects.filter(dataroom=source).order_by('position', 'created_at'):
        DataroomBannerImage.objects.create(
            dataroom=new_room, image=banner.image.name, caption=banner.caption, position=banner.position,
        )

    folder_map = {}
    for folder in _ordered_folders(source):
        folder_map[folder.id] = DataroomFolder.objects.create(
            dataroom=new_room,
            parent=folder_map.get(folder.parent_id),
            name=folder.name,
            created_by=user,
            is_starred=folder.is_starred,
        )

    doc_map = {}
    source_docs = DataroomDocument.objects.filter(
        dataroom=source, document__deleted_at__isnull=True,
    ).select_related('document').order_by('created_at', 'id')
    for ddoc in source_docs:
        doc_map[ddoc.id] = DataroomDocument.objects.create(
            dataroom=new_room,
            document=ddoc.document,  # same Document -> same stored versions/blobs
            folder=folder_map.get(ddoc.folder_id),
            name=ddoc.name,
            is_starred=ddoc.is_starred,
            is_direct_upload=False,  # a reference; deleting the copy never deletes the file
        )

    orders = []
    for row in DataroomItemOrder.objects.filter(dataroom=source).order_by('position'):
        parent = folder_map.get(row.parent_folder_id) if row.parent_folder_id else None
        if row.parent_folder_id and parent is None:
            continue
        if row.item_type == DataroomItemOrder.ITEM_TYPE_FOLDER:
            target = folder_map.get(row.folder_id)
            if target is None:
                continue
            orders.append(DataroomItemOrder(
                dataroom=new_room, parent_folder=parent, item_type=row.item_type,
                folder=target, position=row.position,
            ))
        else:
            target = doc_map.get(row.dataroom_document_id)
            if target is None:
                continue
            orders.append(DataroomItemOrder(
                dataroom=new_room, parent_folder=parent, item_type=row.item_type,
                dataroom_document=target, position=row.position,
            ))
    DataroomItemOrder.objects.bulk_create(orders)

    cloned_links = []
    if include_share_links:
        for link in ShareLink.objects.filter(dataroom=source).order_by('created_at'):
            new_link = ShareLink(dataroom=new_room, created_by=user, name=link.name, is_active=False)
            for field in LINK_FIELDS_TO_COPY:
                setattr(new_link, field, getattr(link, field))
            new_link.save()  # post_save signal seeds default per-item settings
            # Mirror per-item permissions onto the cloned items.
            new_settings = {
                (s.dataroom_folder_id or s.dataroom_document_id): s
                for s in ShareLinkDataroomSetting.objects.filter(share_link=new_link)
            }
            for s in ShareLinkDataroomSetting.objects.filter(share_link=link):
                if s.dataroom_folder_id:
                    mapped = folder_map.get(s.dataroom_folder_id)
                else:
                    mapped = doc_map.get(s.dataroom_document_id)
                if mapped is None:
                    continue
                target = new_settings.get(mapped.id)
                if target is None:
                    continue
                target.is_visible = s.is_visible
                target.allow_download = s.allow_download
                target.enable_watermark = s.enable_watermark
                target.save(update_fields=['is_visible', 'allow_download', 'enable_watermark', 'updated_at'])
            for grant in ShareLinkAccessGrant.objects.filter(share_link=link):
                ShareLinkAccessGrant.objects.create(
                    share_link=new_link, viewer_organisation=grant.viewer_organisation,
                    email=grant.email, created_by=user,
                )
            cloned_links.append(new_link)

    logger.info(
        "Cloned dataroom %s -> %s (%d folders, %d documents, %d links) by user %s",
        source.id, new_room.id, len(folder_map), len(doc_map), len(cloned_links), getattr(user, 'id', None),
    )
    return {
        'dataroom': new_room,
        'folder_count': len(folder_map),
        'document_count': len(doc_map),
        'share_links': cloned_links,
    }
