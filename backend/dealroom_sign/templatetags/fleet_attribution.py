from django import template
from django.utils.safestring import mark_safe

from dealroom_sign.fleet_mail import attribution

register = template.Library()


@register.simple_tag
def fleet_attribution(slug):
    # HTML is escaped in the canonical renderer; email-text is a plain-text MIME part.
    return mark_safe(attribution(slug))
