"""Board configuration parsing shared by Send and the signing deployment."""
import json

from django.core.exceptions import ImproperlyConfigured


def parse_board_sign_boards(raw):
    """Require an explicit list for each board's owner, room, and team scope."""
    try:
        boards = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ImproperlyConfigured('BOARD_SIGN_BOARDS must be valid JSON.') from exc

    if not isinstance(boards, dict):
        raise ImproperlyConfigured('BOARD_SIGN_BOARDS must be a JSON object.')

    for board, config in boards.items():
        if not isinstance(config, dict):
            raise ImproperlyConfigured(
                f'BOARD_SIGN_BOARDS[{board!r}] must be an object.'
            )
        for field in ('owner_ids', 'room_ids', 'team_ids'):
            if not isinstance(config.get(field), list):
                raise ImproperlyConfigured(
                    f'BOARD_SIGN_BOARDS[{board!r}].{field} must be a list.'
                )
    return boards
