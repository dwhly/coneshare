"""Explicit isolated-deployment acceptance fixture. Never run against another deployment."""
import io
import json
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from reportlab.pdfgen import canvas
from core.models import Organization, User, APIKey
from core.authentication import generate_raw_api_key
from datarooms.models import Dataroom, DataroomDocument
from documents.models import Document, DocumentVersion
from documents.fileserver import fileserver_client
from sharelinks.models import ShareLink, ShareLinkAccessGrant, ShareLinkDataroomSetting
from dealroom.models import RoomPolicy
from dealroom_sign.models import SignCredential, NdaPolicy
from dealroom_sign.validation import digest


class Command(BaseCommand):
    help = 'Create real isolated signing fixtures; credentials enter only on stdin.'

    def handle(self, *args, **options):
        if settings.SIGN_DEPLOYMENT_ID != 'chief-glue-v1':
            raise CommandError('Fixture restricted to chief-glue-v1.')
        secret = json.load(sys.stdin)
        org, _ = Organization.objects.get_or_create(name='Chief Glue Review')
        owner, _ = User.objects.get_or_create(email='admin@amforge.test', defaults={'username':'glue-admin','organization':org,'is_staff':True,'role':'admin'})
        owner.set_password(secret['password']); owner.is_staff=True; owner.save()
        SignCredential.objects.update_or_create(owner=owner, defaults={'team_id':secret['teamId'],'token':secret['token'],'enabled':True})
        room, _ = Dataroom.objects.get_or_create(organization=org, name='Project Atlas · Glue review', defaults={'created_by':owner,'enable_qna':False})
        link, _ = ShareLink.objects.get_or_create(dataroom=room, name='Verified room entry', defaults={'created_by':owner,'requires_email':True,'requires_email_verification':True,'restrict_to_grants':True,'enable_watermark':True,'enable_qna':False})
        RoomPolicy.objects.get_or_create(room=room, defaults={'entry_link':link})
        for email in ['member@acme.test','other@acme.test']:
            ShareLinkAccessGrant.objects.get_or_create(share_link=link,email=email,defaults={'created_by':owner,'download_ceiling':'none'})
        versions={}
        for name in ['Confidentiality agreement','Investment agreement']:
            data=io.BytesIO();c=canvas.Canvas(data,pagesize=(600,800));c.setFont('Helvetica-Bold',22);c.drawString(60,710,name)
            c.setFont('Helvetica',12)
            for i,line in enumerate(['Chief Dealroom integration acceptance fixture.','This document exercises the real signing and evidence flow.','No production legal terms are represented by this fixture.','Please sign below to complete this test.']):c.drawString(60,650-i*26,line)
            c.rect(60,176,210,64);c.drawString(60,155,'Signature');c.save();pdf=data.getvalue()
            key=f'{org.pk}/glue-fixtures/{digest(pdf)}.pdf';fileserver_client.upload_file(key,pdf,'application/pdf')
            doc, _=Document.objects.get_or_create(organization=org,name=name+'.pdf',defaults={'created_by':owner,'status':'ready','type':'pdf','content_type':'application/pdf','storage_key':key,'original_storage_key':key,'num_pages':1,'file_size':len(pdf)})
            version,_=DocumentVersion.objects.get_or_create(document=doc,version_number=1,defaults={'is_primary':True,'content_type':'application/pdf','type':'pdf','storage_type':'local','storage_key':key,'original_storage_key':key,'num_pages':1,'file_size':len(pdf)})
            item,_=DataroomDocument.objects.get_or_create(dataroom=room,document=doc,defaults={'name':doc.name})
            ShareLinkDataroomSetting.objects.get_or_create(share_link=link,dataroom_document=item,defaults={'is_visible':True,'allow_download':False})
            versions[name]=str(version.pk)
            if name=='Confidentiality agreement':
                NdaPolicy.objects.get_or_create(room=room,defaults={'source_version':version,'source_sha256':digest(pdf),'fields':[{'type':'SIGNATURE','page':1,'positionX':10,'positionY':70,'width':35,'height':8}]})
        raw,prefix,hashed=generate_raw_api_key();APIKey.objects.create(user=owner,name='Glue acceptance agent',prefix=prefix,hashed_key=hashed,tier='read_write')
        self.stdout.write(json.dumps({'room_id':str(room.pk),'slug':link.slug,'versions':versions,'agent_key':raw}))
