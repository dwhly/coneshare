import logging
import tempfile
import httpx
from datetime import timezone as dt_timezone
from io import BytesIO
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone
from google.auth.exceptions import RefreshError
from core.services import get_dynamic_setting
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from .base import BaseCloudProvider, CloudProviderError

logger = logging.getLogger(__name__)

GOOGLE_EXPORTS = {
    'application/vnd.google-apps.document': ('application/pdf', '.pdf'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx'),
}


class GoogleDriveProvider(BaseCloudProvider):
    """Google Drive integration."""
    PROVIDER_NAME = 'google_drive'
    SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file',
    ]

    def __init__(self, connection=None):
        super().__init__(connection)
        self.client_id = get_dynamic_setting('GOOGLE_DRIVE_CLIENT_ID')
        self.client_secret = get_dynamic_setting('GOOGLE_DRIVE_CLIENT_SECRET')
        if not self.client_id or not self.client_secret:
            raise CloudProviderError("Google Drive API credentials are not configured in settings.py.")

    def _get_redirect_uri(self):
        return urljoin(settings.SITE_DOMAIN, "auth/google_drive/callback")

    def _get_flow(self):
        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._get_redirect_uri()],
            }
        }
        return Flow.from_client_config(
            client_config,
            scopes=self.SCOPES,
            redirect_uri=self._get_redirect_uri()
        )

    def get_authorization_url(self):
        flow = self._get_flow()
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return authorization_url, state

    def handle_callback(self, code):
        try:
            flow = self._get_flow()
            flow.fetch_token(code=code)
            creds = flow.credentials
            return {
                'access_token': creds.token,
                'refresh_token': creds.refresh_token,
                'expires_at': creds.expiry,
            }
        except Exception as e:
            logger.error(f"Google Drive token exchange failed: {e}")
            raise CloudProviderError("Failed to get token from Google Drive.")

    def _get_client(self):
        if not self.connection:
            raise CloudProviderError("No connection provided for Google Drive client.")

        naive_expiry = None
        if self.connection.expires_at:
            if timezone.is_aware(self.connection.expires_at):
                naive_expiry = self.connection.expires_at.astimezone(dt_timezone.utc).replace(tzinfo=None)
            else:
                naive_expiry = self.connection.expires_at

        creds = Credentials(
            token=self.connection.access_token,
            refresh_token=self.connection.refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            expiry=naive_expiry,
        )

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist the refreshed credentials
                self.connection.access_token = creds.token
                if creds.expiry:
                    self.connection.expires_at = (
                        timezone.make_aware(creds.expiry, dt_timezone.utc)
                        if timezone.is_naive(creds.expiry)
                        else creds.expiry
                    )
                else:
                    self.connection.expires_at = None
                update_fields = ['access_token', 'expires_at']

                # A new refresh token is only issued on the initial authorization
                # code exchange if `access_type=offline` and `prompt=consent` are used.
                if creds.refresh_token and creds.refresh_token != self.connection.refresh_token:
                    self.connection.refresh_token = creds.refresh_token
                    update_fields.append('refresh_token')

                self.connection.save(update_fields=update_fields)
                logger.info(f"Refreshed Google Drive token for connection {self.connection.id}")
            except RefreshError as e:
                logger.error(f"Google Drive token refresh failed for connection {self.connection.id}: {e}")
                self._handle_provider_error(e, "token refresh")

        return build('drive', 'v3', credentials=creds)

    def _handle_provider_error(self, e, action_name):
        if isinstance(e, RefreshError) or "invalid_grant" in str(e):
            raise CloudProviderError("Failed to access Google Drive. Your authorization token may have expired or been revoked. Please reconnect your account.")
        raise CloudProviderError(f"Google Drive {action_name} failed: {e}")

    def get_user_info(self):
        creds = Credentials(token=self.connection.access_token)
        service = build('oauth2', 'v2', credentials=creds)
        try:
            user_info = service.userinfo().get().execute()
            return {'email': user_info.get('email')}
        except (HttpError, RefreshError) as e:
            self._handle_provider_error(e, "get_user_info")

    def list_files(self, path='/'):
        try:
            service = self._get_client()
            folder_id = 'root' if path == '/' else path
            items, page_token = [], None
            while True:
                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    pageSize=100, pageToken=page_token,
                    fields="nextPageToken, files(id, name, mimeType, size, parents, modifiedTime, webViewLink)"
                ).execute()
                for file in results.get('files', []):
                    is_folder = file.get('mimeType') == 'application/vnd.google-apps.folder'
                    items.append({**file, 'type': 'folder' if is_folder else 'file',
                                  'path': file['id'], 'size': int(file.get('size', 0))})
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            return items
        except (HttpError, RefreshError) as e:
            self._handle_provider_error(e, "list_files")

    def download_file(self, file_id):
        try:
            service = self._get_client()
            file_metadata = service.files().get(fileId=file_id, fields='name, size, md5Checksum, version, mimeType, modifiedTime, webViewLink').execute()
            mime_type = file_metadata.get('mimeType', '')
            name = file_metadata.get('name', 'Untitled')
            etag_or_rev = file_metadata.get('md5Checksum') or str(file_metadata.get('version', ''))

            # Handle Google Docs / Sheets / Slides editor files
            is_google_apps_file = mime_type.startswith('application/vnd.google-apps.') and mime_type != 'application/vnd.google-apps.folder'

            if is_google_apps_file:
                export_mime, extension = GOOGLE_EXPORTS.get(mime_type, ('application/pdf', '.pdf'))
                if not name.lower().endswith(extension):
                    name += extension

                request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                request = service.files().get_media(fileId=file_id)

            # Use a spooled temporary file to avoid loading large files into memory.
            # It spills to disk if the file is larger than 5MB.
            fh = tempfile.SpooledTemporaryFile(max_size=5 * 1024 * 1024)
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            # Seek to end to find actual size of the downloaded/exported stream
            fh.seek(0, 2)
            actual_size = fh.tell()
            fh.seek(0)

            return {
                'name': name,
                'size': actual_size,
                'content': fh,
                'etag_or_rev': etag_or_rev,
                'content_type': export_mime if is_google_apps_file else mime_type,
                'modifiedTime': file_metadata.get('modifiedTime', ''),
                'webViewLink': file_metadata.get('webViewLink', ''),
            }
        except (HttpError, RefreshError) as e:
            self._handle_provider_error(e, "download")

    def revoke_token(self):
        if not self.connection:
            return
        token = self.connection.refresh_token or self.connection.access_token
        if not token:
            return
        try:
            response = httpx.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=5.0
            )
            response.raise_for_status()
            logger.info(f"Successfully revoked Google Drive token for connection {self.connection.id}")
        except Exception as e:
            logger.warning(f"Failed to revoke Google Drive token: {e}")

    def upload_file(self, file_obj, file_name, folder_id) -> str:
        try:
            service = self._get_client()
            parents = []
            if folder_id and folder_id.strip().lower() != 'root':
                parents = [folder_id.strip()]

            file_metadata = {
                'name': file_name,
            }
            if parents:
                file_metadata['parents'] = parents

            file_obj.seek(0)
            media = MediaIoBaseUpload(file_obj, mimetype='application/octet-stream', resumable=True)
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            return uploaded_file.get('id')
        except (HttpError, RefreshError) as e:
            self._handle_provider_error(e, "upload")
