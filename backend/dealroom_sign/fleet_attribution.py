"""Canonical fleet-attribution/page, /email-html and /email-text templates."""
import html
import re

KEYS = ('FLEET_TENANT_NAME', 'FLEET_ABOUT_URL', 'FLEET_SOURCE_URL')
URL = re.compile(r'''^https://(?:[a-z0-9.-]+|\[[a-f0-9:]+\])(?::([0-9]{1,5}))?(?:[/?#][^\s\\<>"']*)?$''', re.I)


def safe_url(value):
    value = value.strip()
    match = URL.fullmatch(value)
    if not match or re.search(r'[\x00-\x20\x7f-\x9f]', value):
        return ''
    if match[1] and not 1 <= int(match[1]) <= 65535:
        return ''
    return value


def render_attribution(slug, config):
    operator = config.get('FLEET_TENANT_NAME', '').strip()
    if re.search(r'[\x00-\x1f\x7f-\x9f]', operator):
        operator = ''
    fleet_url = safe_url(config.get('FLEET_ABOUT_URL', ''))
    source_url = safe_url(config.get('FLEET_SOURCE_URL', ''))
    prefix = 'Open-source software' + (f' run by {operator},' if operator else '') + ' built on '
    if slug == 'email-text':
        return ('This is ' + prefix[0].lower() + prefix[1:] + 'the Fleet' +
                (f' ({fleet_url})' if fleet_url else '') + ', open-source agentic software.' +
                (f' Source: {source_url}' if source_url else ''))
    if slug not in {'page', 'email-html'}:
        raise ValueError('Unknown fleet-attribution slug')
    fleet = f'<a href="{html.escape(fleet_url)}">the Fleet</a>' if fleet_url else 'the Fleet'
    source = f' <a href="{html.escape(source_url)}">Source</a>' if source_url else ''
    return html.escape(prefix) + fleet + '.' + source
