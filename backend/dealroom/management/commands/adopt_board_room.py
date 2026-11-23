"""Explicit operator assignment; never exposed through an HTTP operation."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from datarooms.models import Dataroom
from sharelinks.models import ShareLinkAccessGrant, ViewSession
from dealroom_sign.models import BoardStaffBinding
from dealroom.activity import record
from dealroom.models import Activity, BoardRoom


class Command(BaseCommand):
    help = 'Assign an existing room to a board, or remove only that assignment with --undo.'

    def add_arguments(self, parser):
        parser.add_argument('--board', required=True)
        parser.add_argument('--room', required=True)
        parser.add_argument('--undo', action='store_true')
        parser.add_argument('--force', action='store_true', help='Allow a board without a staff binding.')

    @transaction.atomic
    def handle(self, *args, **options):
        board_id = options['board']
        if not board_id.strip() or len(board_id) > 100:
            raise CommandError('Board ID must be nonempty and at most 100 characters.')
        room = Dataroom.objects.select_for_update().filter(pk=options['room']).first()
        if room is None:
            raise CommandError('Room not found.')
        assignment = BoardRoom.objects.filter(room=room).first()
        if assignment and assignment.board_id != board_id:
            raise CommandError('Room is assigned to another board; undo that assignment explicitly first.')
        if options['undo']:
            if assignment:
                assignment.delete()
                record('board.room.unadopted', organization=room.organization, actor='management-command',
                       actor_kind='operator', room_id=room.pk, data={'board_id': board_id})
            self.stdout.write('Board room assignment removed; room content and access retained.')
            return
        if assignment:
            self.stdout.write('Room already assigned to this board.')
            return
        if not options['force'] and not BoardStaffBinding.objects.filter(board_id=board_id).exists():
            raise CommandError('No staff binding exists for this board; use --force to adopt intentionally.')
        # No invitation table exists in S1a. Historical invitation facts are Activity rows.
        # Keep revoked grants and old sessions: either proves previous recipient exposure.
        candidates = [
            ShareLinkAccessGrant.objects.filter(share_link__dataroom=room)
                .order_by('created_at').values_list('created_at', flat=True).first(),
            Activity.objects.filter(organization=room.organization, room_id=str(room.pk))
                .exclude(event_type__in=['board.room.adopted', 'board.room.unadopted'])
                .order_by('created_at').values_list('created_at', flat=True).first(),
            ViewSession.objects.filter(share_link__dataroom=room)
                .order_by('viewed_at').values_list('viewed_at', flat=True).first(),
        ]
        BoardRoom.objects.create(board_id=board_id, room=room, build_state='ready',
                                 ever_invited_at=min((at for at in candidates if at), default=None))
        record('board.room.adopted', organization=room.organization, actor='management-command',
               actor_kind='operator', room_id=room.pk, data={'board_id': board_id})
        self.stdout.write('Room adopted with ready state.')
