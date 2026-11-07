"""Glue pages render the Fleet Dealroom shell only (docs/design/dealroom-shell.md §0-§4)."""
import re

from django.template.loader import render_to_string


def _visible(html):
    html = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', html)


def test_staff_page_is_fleet_only_and_has_no_template_leaks():
    html = render_to_string('dealroom_sign/staff.html', {'sign_url': 'https://sign.example.test'})
    assert '<title>Signing · Fleet Dealroom</title>' in html
    assert '{#' not in html and '#}' not in html and 'AmForge' not in html
    assert 'class="fds-header dr-header"' in html and 'data-fds-theme-toggle' in html
    assert '<a href="/activity">Activity</a>' in html and '<a href="/approvals">Approvals</a>' in html
    assert '<select' not in html and 'type="file"' not in html
    assert 'href="https://sign.example.test/inbox"' in html


def test_visitor_page_has_fleet_lockup_and_room_context():
    html = render_to_string('dealroom_sign/room.html', {'slug': 's', 'room_id': 'r', 'room_name': 'Project Atlas'})
    text = _visible(html)
    assert '{#' not in html and '#}' not in html and 'AmForge' not in html
    assert 'dr-header--visitor' in html and 'fds-lockup' in html
    assert 'id="context-room">Project Atlas<' in html
    assert 'Fleet' in text and 'Dealroom' in text
