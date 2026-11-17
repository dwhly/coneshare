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


def test_visitor_page_has_fleet_lockup_and_an_empty_room_context():
    # The room name is filled in from the authorised recipient API only (review v0.9 r1 [1]); the page renders none.
    html = render_to_string('dealroom_sign/room.html', {'slug': 's', 'room_id': 'r', 'room_name': 'Project Atlas'})
    text = _visible(html)
    assert '{#' not in html and '#}' not in html and 'AmForge' not in html
    assert 'dr-header--visitor' in html and 'fds-lockup' in html
    assert 'id="context-room"></span>' in html and 'Project Atlas' not in html
    assert 'Fleet' in text and 'Dealroom' in text


def _stylesheets(html):
    return re.findall(r'<link rel="stylesheet" href="([^"?]+)', html)


def test_layer_order_statement_is_the_first_stylesheet_on_every_entry_page():
    # fds v0.9 (DESIGN.md §11): /dealroom/layers.css declares `@layer dr.reset, fds.tokens, fds.brand, fds.components` and
    # must load before any package CSS, or dr.reset would sort ABOVE the package layers. Entry pages: every glue page
    # (all extend base.html) and the React console's index.html (checked when the frontend is in the tree).
    import glob
    import os
    pages = [(n, render_to_string(n, c)) for n, c in (('dealroom_sign/staff.html', {'sign_url': ''}),
                                                      ('dealroom_sign/room.html', {'slug': 's', 'room_id': 'r'}))]
    here = os.path.dirname(os.path.abspath(__file__))
    for path in glob.glob(os.path.join(here, '..', '..', '..', 'frontend', 'index.html')):
        pages.append(('frontend/index.html', open(path, encoding='utf-8').read()))
    for name, html in pages:
        sheets = _stylesheets(html)
        assert sheets and sheets[0] == '/dealroom/layers.css', (name, sheets)
        assert all(s.startswith('/fds/') or s.startswith('/dealroom/') for s in sheets), (name, sheets)
    templates = os.path.join(here, '..', 'templates', 'dealroom_sign')
    for path in glob.glob(os.path.join(templates, '*.html')):
        src = open(path, encoding='utf-8').read()
        if '<html' in src or '/fds/' in src:  # a standalone page must be base.html itself
            assert os.path.basename(path) == 'base.html', path


def test_theme_control_is_the_empty_package_icon_button():
    # fds v0.10 (owner decision 2026-11-15): theme.js draws sun / moon / sun-moon into an EMPTY [data-fds-theme-toggle]
    # and sets title + aria-label. A word inside the button or a product toggle rule in shell.css brings back the old
    # labelled box (DESIGN.md §6 migration notes).
    for name, ctx in (('dealroom_sign/staff.html', {'sign_url': ''}), ('dealroom_sign/room.html', {'slug': 's', 'room_id': 'r'})):
        html = render_to_string(name, ctx)
        buttons = re.findall(r'<button[^>]*data-fds-theme-toggle[^>]*>(.*?)</button>', html, flags=re.S)
        assert buttons == [''], (name, buttons)
        assert '/fds/theme.js?v=0.10.0' in html, name
    # (the "no product CSS re-boxes it" check lives in frontend/src/tests/components/layout/ThemeToggle.test.jsx, which
    # always has shell.css on disk)
