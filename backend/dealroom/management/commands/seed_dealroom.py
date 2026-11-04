import os
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from reportlab.pdfgen.canvas import Canvas
from core.models import Organization, User, APIKey, AppConfiguration
from core.authentication import generate_raw_api_key
from datarooms.models import Dataroom, DataroomFolder
from sharelinks.models import ViewerOrganisation, Viewer, ShareLink, ShareLinkAccessGrant, ShareLinkDataroomSetting
from dealroom.models import RoomPolicy, DomainConfirmation
from dealroom.uploads import upload


class Command(BaseCommand):
    help = 'Idempotent fresh phase-one Atlas demonstration seed (no existing stack touched).'
    def handle(self, *args, **options):
        tenant, _ = Organization.objects.get_or_create(name='AmForge')
        user, _ = User.objects.get_or_create(email='admin@amforge.test', defaults={'username':'admin@amforge.test', 'organization':tenant, 'is_staff':True, 'is_superuser':True, 'role':'admin'})
        user.set_password(os.environ['SEED_STAFF_PASSWORD'])
        user.save()
        room, _ = Dataroom.objects.get_or_create(organization=tenant, name='Project Atlas', defaults={'created_by':user,'enable_qna':False})
        link, _ = ShareLink.objects.get_or_create(dataroom=room, name='Room entry', defaults={'created_by':user, 'slug':'project-atlas','restrict_to_grants':True,'requires_email':True,'requires_email_verification':True,'enable_watermark':True,'enable_qna':False})
        RoomPolicy.objects.get_or_create(room=room, defaults={'entry_link':link})
        org, _ = ViewerOrganisation.objects.get_or_create(organization=tenant, name='Acme', defaults={'email_domains':['acme.test'],'created_by':user})
        DomainConfirmation.objects.get_or_create(domain='acme.test', defaults={'unicode_domain':'acme.test','organization':org,'confirmed_by':user})
        Viewer.objects.get_or_create(organization=tenant, email='jane@acme.test', defaults={'name':'Jane','recipient_org':org})
        ShareLinkAccessGrant.objects.get_or_create(share_link=link, viewer_organisation=org, defaults={'created_by':user})
        for title in ('Financials','Legal','Product'):
            folder, _ = DataroomFolder.objects.get_or_create(dataroom=room, name=title, defaults={'created_by':user})
            if not room.documents.filter(folder=folder).exists():
                data = BytesIO(); canvas = Canvas(data, pagesize=(612,792))
                canvas.setFillColorRGB(.1,.15,.25); canvas.setFont('Helvetica-Bold',26); canvas.drawString(60,710,'Project Atlas')
                canvas.setFont('Helvetica',16); canvas.drawString(60,675,title+' / Confidential overview')
                canvas.setFont('Helvetica',11)
                for n, line in enumerate(['Prepared for the Acme diligence team.', 'This demonstration document contains fictional information.', '', 'Revenue outlook: steady growth across three product lines.', 'Review status: initial diligence.', 'Distribution: authorized recipients only.']):
                    canvas.drawString(60,610-n*24,line)
                canvas.setStrokeColorRGB(.2,.4,.9); canvas.line(60,650,552,650); canvas.save()
                upload(room,user,SimpleUploadedFile(f'Atlas {title}.pdf',data.getvalue(),content_type='application/pdf'),str(folder.pk))
        ShareLinkDataroomSetting.objects.filter(share_link=link).update(enable_watermark=True, allow_download=False)
        from documents.tasks import generate_pdf_pages_task
        for item in room.documents.all():
            version = item.document.versions.get(is_primary=True)
            if not version.has_pages:
                generate_pdf_pages_task.delay(str(version.pk))
        self.stdout.write(f'room={room.pk} recipient=/view/{link.slug}')
