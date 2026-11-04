from .models import Activity


def record(event_type, *, organization, actor, room_id='', target_id='', data=None):
    """Append a local fact inside the caller's transaction. No secrets in data."""
    from core.models import APIKey
    return Activity.objects.create(
        event_type=event_type, organization=organization,
        actor_kind='agent' if isinstance(actor, APIKey) else 'staff',
        actor_id=str(getattr(actor, 'pk', actor)), room_id=str(room_id or ''),
        target_id=str(target_id or ''), data=data or {},
    )
