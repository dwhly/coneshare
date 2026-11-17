"""Apply deployment attribution to Send's mail and template entry points."""
import re

from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from django.utils.html import escape

from .fleet_attribution import KEYS, render_attribution


def attribution(slug):
    return render_attribution(slug, {key: getattr(settings, key, '') for key in KEYS})


def attributed_parts(text, html=None):
    html = html if html is not None else '<html><body><p>' + escape(text).replace('\n', '<br>') + '</p></body></html>'
    footer = '<p style="margin:16px 0;font-size:12px;color:#585e6a">' + attribution('email-html') + '</p>'
    closing = re.search(r'</body\s*>', html, re.I)
    html = html[:closing.start()] + footer + html[closing.start():] if closing else html + footer
    return text.rstrip() + '\n\n' + attribution('email-text'), html


def send_mail(subject, message, from_email, recipient_list, fail_silently=False,
              auth_user=None, auth_password=None, connection=None, html_message=None):
    text, html = attributed_parts(message, html_message)
    return django_send_mail(subject, text, from_email, recipient_list, fail_silently=fail_silently,
                            auth_user=auth_user, auth_password=auth_password,
                            connection=connection, html_message=html)
