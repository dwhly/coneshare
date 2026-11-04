import os
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.i18n_utils import resolve_email_language
from core.models import AppConfiguration
from core.tasks import send_signup_verification_email_task
from sharelinks.models import ViewSession
from sharelinks.tasks import send_view_notification_email_task

User = get_user_model()


@pytest.fixture
def user(db, organization):
    return User.objects.create_user(
        username="user@example.com",
        email="user@example.com",
        password="password123",
        organization=organization
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestUserLanguagePreference:
    """Verify user language preference CRUD and API response localization."""

    def test_user_language_default_is_english(self, user):
        assert user.language == 'en'

    def test_update_user_language(self, api_client, user):
        url = reverse('user-detail', kwargs={'pk': user.id})
        resp = api_client.patch(url, {'language': 'zh-hans'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_invalid_language_rejected(self, api_client, user):
        url = reverse('user-detail', kwargs={'pk': user.id})
        resp = api_client.patch(url, {'language': 'invalid_code'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_list_languages_endpoint(self, db):
        client = APIClient()
        url = reverse('languages')
        resp = client.get(url, HTTP_ACCEPT_LANGUAGE='ru')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == [
            {'code': 'en', 'name': 'English'},
            {'code': 'zh-hans', 'name': '简体中文'},
            {'code': 'ru', 'name': 'Русский'},
            {'code': 'de', 'name': 'Deutsch'},
            {'code': 'fr', 'name': 'Français'},
            {'code': 'nl', 'name': 'Nederlands'},
        ]

    def test_api_error_respects_accept_language_header(self, api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = reverse('set_password')
        payload = {
            'old_password': 'wrong_password',
            'new_password1': 'new_pass123',
            'new_password2': 'new_pass123',
        }
        resp = api_client.post(url, payload, HTTP_ACCEPT_LANGUAGE='zh-hans')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_api_error_in_russian(self, api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = reverse('set_password')
        payload = {
            'old_password': 'wrong_password',
            'new_password1': 'new_pass123',
            'new_password2': 'new_pass123',
        }
        resp = api_client.post(url, payload, HTTP_ACCEPT_LANGUAGE='ru')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_api_error_in_german(self, api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = reverse('set_password')
        payload = {
            'old_password': 'wrong_password',
            'new_password1': 'new_pass123',
            'new_password2': 'new_pass123',
        }
        resp = api_client.post(url, payload, HTTP_ACCEPT_LANGUAGE='de')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_api_error_in_french(self, api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = reverse('set_password')
        payload = {
            'old_password': 'wrong_password',
            'new_password1': 'new_pass123',
            'new_password2': 'new_pass123',
        }
        resp = api_client.post(url, payload, HTTP_ACCEPT_LANGUAGE='fr')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    def test_api_error_in_dutch(self, api_client):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        url = reverse('set_password')
        payload = {
            'old_password': 'wrong_password',
            'new_password1': 'new_pass123',
            'new_password2': 'new_pass123',
        }
        resp = api_client.post(url, payload, HTTP_ACCEPT_LANGUAGE='nl')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    @pytest.mark.parametrize("lang, expected_subject, expected_snippet", [
        ("en", "Verify your Coneshare account", "Welcome to Coneshare."),
        ("zh-hans", "验证您的 Coneshare 账号", "欢迎使用 Coneshare。"),
        ("ru", "Подтвердите ваш аккаунт Coneshare", "Добро пожаловать в Coneshare."),
        ("de", "Bestätigen Sie Ihr Coneshare-Konto", "Willkommen bei Coneshare."),
        ("fr", "Vérifiez votre compte Coneshare", "Bienvenue sur Coneshare."),
        ("nl", "Verifieer uw Coneshare-account", "Welkom bij Coneshare."),
    ])
    def test_signup_verification_email_task_language_override(self, mailoutbox, lang, expected_subject, expected_snippet):
        """Verify Celery signup verification email task respects language override for subject and body."""
        mailoutbox.clear()
        send_signup_verification_email_task(
            email='user@example.com',
            verify_url='https://example.com/verify',
            language=lang
        )
        assert len(mailoutbox) == 1
        msg = mailoutbox[0]
        assert msg.to == ['user@example.com']
        assert msg.subject == expected_subject
        assert expected_snippet in msg.body

    def test_signup_request_uses_user_language_when_no_accept_header(self, db, monkeypatch):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        AppConfiguration.objects.update_or_create(
            key='ENABLE_PUBLIC_SIGNUP',
            defaults={'value': 'true', 'description': 'Enable public signup.'}
        )
        cache.clear()
        captured = {}

        def _fake_delay(email, verify_url, language):
            captured['language'] = language

        monkeypatch.setattr('core.views.transaction.on_commit', lambda fn: fn())
        monkeypatch.setattr('core.views.send_signup_verification_email_task.delay', _fake_delay)

        user = User.objects.create_user(
            username="inactive@example.com",
            email="inactive@example.com",
            password="StrongPassword123!",
            language="zh-hans",
            is_active=False
        )
        client = APIClient()
        url = reverse('signup_request')
        resp = client.post(url, {'email': 'inactive@example.com', 'password': 'StrongPassword123!', 'name': 'Inactive User'})
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    @pytest.mark.parametrize("lang, expected_subject, expected_snippet", [
        ("en", "Verify your email to view 'Test Document.pdf'", "Please click the link below to view 'Test Document.pdf'."),
        ("zh-hans", "请验证您的邮箱以查看“Test Document.pdf”", "请点击下方链接查看“Test Document.pdf”："),
        ("ru", "Подтвердите email для просмотра «Test Document.pdf»", "Пожалуйста, перейдите по ссылке ниже для просмотра «Test Document.pdf»."),
        ("de", "Bestätigen Sie Ihre E-Mail-Adresse, um „Test Document.pdf“ anzuzeigen", "Bitte klicken Sie auf den unten stehenden Link, um „Test Document.pdf“ anzuzeigen."),
        ("fr", "Vérifiez votre e-mail pour afficher « Test Document.pdf »", "Veuillez cliquer sur le lien ci-dessous pour afficher « Test Document.pdf »."),
        ("nl", "Verifieer uw e-mailadres om ‘Test Document.pdf’ te bekijken", "Klik op de onderstaande link om ‘Test Document.pdf’ te bekijken."),
    ])
    def test_sharelink_email_verification_language(self, mailoutbox, share_link_requires_email_verification, lang, expected_subject, expected_snippet):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        mailoutbox.clear()
        client = APIClient()
        url = reverse('share-link-request-access', kwargs={'slug': share_link_requires_email_verification.slug})
        resp = client.post(url, {'email': 'viewer@example.com'}, HTTP_ACCEPT_LANGUAGE=lang)
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @pytest.mark.parametrize("lang, expected_subject, expected_snippet", [
        ("en", "Your shared item 'Test Document.pdf' was viewed", "Just letting you know that your shared item, 'Test Document.pdf', was viewed."),
        ("zh-hans", "您分享的“Test Document.pdf”已被查看", "特此通知：您分享的“Test Document.pdf”已被查看。"),
        ("ru", "Ваш общий объект «Test Document.pdf» был просмотрен", "Сообщаем, что ваш общий объект «Test Document.pdf» был просмотрен."),
        ("de", "Ihr geteiltes Element „Test Document.pdf“ wurde aufgerufen", "Ihr geteiltes Element „Test Document.pdf“ wurde soeben aufgerufen."),
        ("fr", "Votre élément partagé « Test Document.pdf » a été consulté", "Votre élément partagé « Test Document.pdf » a été consulté."),
        ("nl", "Uw gedeelde item ‘Test Document.pdf’ is bekeken", "Wij laten u weten dat uw gedeelde item ‘Test Document.pdf’ is bekeken."),
    ])
    def test_sharelink_view_notification_email_owner_language(self, mailoutbox, share_link, lang, expected_subject, expected_snippet):
        """Verify sharelink view notification email respects the link owner's preferred language."""
        share_link.receive_email_notification = True
        share_link.save()

        owner = share_link.created_by
        owner.language = lang
        owner.save()

        session = ViewSession.objects.create(
            share_link=share_link,
            viewer_email='viewer@example.com',
            ip_address='127.0.0.1'
        )

        mailoutbox.clear()
        send_view_notification_email_task(str(session.id))
        assert len(mailoutbox) == 1
        msg = mailoutbox[0]
        assert msg.to == [owner.email]
        assert msg.subject == expected_subject
        assert expected_snippet in msg.body

    def test_signup_request_preserves_user_language_when_accept_header_unsupported(self, db, monkeypatch):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        AppConfiguration.objects.update_or_create(
            key='ENABLE_PUBLIC_SIGNUP',
            defaults={'value': 'true', 'description': 'Enable public signup.'}
        )
        cache.clear()
        captured = {}

        def _fake_delay(email, verify_url, language):
            captured['language'] = language

        monkeypatch.setattr('core.views.transaction.on_commit', lambda fn: fn())
        monkeypatch.setattr('core.views.send_signup_verification_email_task.delay', _fake_delay)

        user = User.objects.create_user(
            username="inactive_ru@example.com",
            email="inactive_ru@example.com",
            password="StrongPassword123!",
            language="ru",
            is_active=False
        )
        client = APIClient()
        url = reverse('signup_request')
        resp = client.post(
            url,
            {'email': 'inactive_ru@example.com', 'password': 'StrongPassword123!', 'name': 'Inactive User'},
            HTTP_ACCEPT_LANGUAGE='ja-JP,ja;q=0.9'
        )
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'Unclassified or disabled operation.'}

    @pytest.mark.parametrize("lang, expected_loc", [
        ("en", "Unknown Location"),
        ("zh-hans", "未知位置"),
        ("ru", "Неизвестное местоположение"),
        ("de", "Unbekannter Standort"),
        ("fr", "Emplacement inconnu"),
        ("nl", "Onbekende locatie"),
    ])
    def test_sharelink_view_notification_email_fallbacks_translated(self, mailoutbox, share_link, lang, expected_loc):
        """Verify fallback values (Unknown Location) are translated to the owner's language."""
        share_link.receive_email_notification = True
        share_link.save()

        owner = share_link.created_by
        owner.language = lang
        owner.save()

        session = ViewSession.objects.create(
            share_link=share_link,
            viewer_email='',
            ip_address='127.0.0.1'
        )

        mailoutbox.clear()
        send_view_notification_email_task(str(session.id))
        assert len(mailoutbox) == 1
        msg = mailoutbox[0]
        assert expected_loc in msg.body or expected_loc in msg.alternatives[0][0]

    def test_sharelink_viewer_email_verification_falls_back_to_en_regardless_of_owner(self, mailoutbox, share_link_requires_email_verification):
        """Phase 1: this legacy workflow is denied at its authorization boundary."""
        # Set owner language to Russian
        owner = share_link_requires_email_verification.created_by
        owner.language = 'ru'
        owner.save()

        mailoutbox.clear()
        client = APIClient()
        url = reverse('share-link-request-access', kwargs={'slug': share_link_requires_email_verification.slug})
        resp = client.post(url, {'email': 'viewer@example.com'}, HTTP_ACCEPT_LANGUAGE='ja-JP,ja;q=0.9')
        # Phase 1: this legacy request is denied before its former handler runs.
        assert resp.status_code == 403
        assert resp.data == {'detail': 'This recipient operation is not enabled in phase 1; use the room entry route.'}

    @pytest.mark.parametrize("accept, user_lang, req_lang, expected", [
        ("zh-CN,zh;q=0.9", "ru", "en", "zh-hans"),
        ("ru-RU,ru;q=0.9", None, "en", "ru"),
        ("de-DE,de;q=0.9", None, "en", "de"),
        ("fr-FR,fr;q=0.9", None, "en", "fr"),
        ("nl-NL,nl;q=0.9", None, "en", "nl"),
        ("nl-BE,nl;q=0.9", None, "en", "nl"),
        ("ja-JP,ja;q=0.9", "zh-hans", "en", "zh-hans"),
        ("ja-JP,ja;q=0.9", None, "zh-hans", "zh-hans"),
        ("ja-JP,ja;q=0.9", None, None, "en"),
        ("", "ru", "en", "ru"),
        ("", "de", "en", "de"),
        ("", "fr", "en", "fr"),
        ("", "nl", "en", "nl"),
        ("", None, "zh-hans", "zh-hans"),
        ("", None, None, "en"),
    ])
    def test_resolve_email_language_priorities(self, accept, user_lang, req_lang, expected):
        """Verify resolve_email_language prioritizes supported headers, then user lang, then req lang, then 'en'."""
        result = resolve_email_language(accept_header=accept, user_lang=user_lang, request_lang=req_lang, default_lang='en')
        assert result == expected




