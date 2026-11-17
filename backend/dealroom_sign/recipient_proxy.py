"""The recipient origin is a scoped Django session boundary, including native assets."""
import ipaddress
import json
import mimetypes
import re
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from django.conf import settings
from django.core.cache import cache
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import content_disposition_header

from .room_return import confirmation_url
from .client import Documenso, SignError, identifier
from .counterparty import (COOKIE, access_state, capability, consent, consume_handoff,
    disclosure_hash, get_session, keyed_hash, new_session, provision, require_auth, resolve,
    verify_code)
from .models import SignCredential
from .presentation import clean_title, display_name, referrer_policy
from .storage import source_bytes
from .tenant_brand import tenant_logo
from .validation import digest
from .workflows import reconcile, record_fact, validate_envelope

# Explicitly scoped subset of the pinned inventory; old document readers/reporting are denied.
RPC = {
    'envelope.field.sign': ('POST', {'token', 'fieldId', 'fieldValue', 'authOptions'}),
    'field.removeSignedFieldWithToken': ('POST', {'token', 'fieldId'}),
    'recipient.completeDocumentWithToken': ('POST', {'token', 'documentId', 'accessAuthOptions'}),
    'recipient.rejectDocumentWithToken': ('POST', {'token', 'documentId', 'reason', 'authOptions'}),
    'envelope.signingStatus': ('GET', {'token'}),
    'envelope.item.getManyByToken': ('GET', {'envelopeId', 'access'}),
    'envelope.attachment.find': ('GET', {'envelopeId', 'token'}),
}
HELP = 'Open the link in your Fleet Dealroom email'
MAX_BODY = 1024 * 1024


class RecipientCsrf(CsrfViewMiddleware):
    def _origin_verified(self, request):
        return request.headers.get('Origin') == origin()



def origin():
    value = getattr(settings, 'SIGN_RECIPIENT_ORIGIN', '').rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path or parsed.username or parsed.query or parsed.fragment:
        raise SignError('recipient_origin_unavailable')
    return value


def boundary(request):
    return (request.META.get('HTTP_X_FLEET_RECIPIENT_LISTENER') == '1' and
            request.META.get('HTTP_HOST', '') == urlsplit(origin()).netloc)


def client_ip(request):
    try:
        return str(ipaddress.ip_address(request.META.get('HTTP_X_FORWARDED_FOR', '')))
    except ValueError:
        raise SignError('recipient_hop_unavailable') from None


def forward_headers(request):
    if not boundary(request):
        raise SignError('recipient_host_mismatch')
    try:
        key = Path(settings.FLEET_PROXY_KEY_FILE).read_text().strip()
    except (OSError, AttributeError):
        key = ''
    if not key:
        raise SignError('recipient_proxy_unavailable')
    public = urlsplit(origin())
    headers = {'X-Forwarded-For': client_ip(request), 'X-Forwarded-Host': public.netloc,
        'X-Forwarded-Proto': public.scheme, 'x-fleet-proxy-key': key, 'Accept-Encoding': 'identity'}
    for name in ('Content-Type', 'User-Agent', 'Accept'):
        if name in request.headers:
            headers[name] = request.headers[name]
    if 'Origin' in request.headers:
        if request.headers['Origin'] != origin():
            raise SignError('recipient_origin_mismatch')
        headers['Origin'] = request.headers['Origin']
    return headers


def bounded_json(raw):
    if len(raw) > MAX_BODY:
        raise SignError('input_too_large')
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise SignError('invalid_input') from None
    if not isinstance(data, dict):
        raise SignError('invalid_input')
    return data


def authorize_rpc(request, access, envelope):
    names = request.path.removeprefix('/api/trpc/').split(',')
    if not names or len(names) > 20 or any(n not in RPC or request.method != RPC[n][0] for n in names):
        raise SignError('recipient_route_denied')
    raw = request.GET.get('input', '') if request.method == 'GET' else request.body
    data = bounded_json(raw)
    batched = request.GET.get('batch') == '1'
    if (batched and set(data) != {str(i) for i in range(len(names))}) or (not batched and len(names) != 1):
        raise SignError('invalid_batch')
    for index, name in enumerate(names):
        member = data[str(index)] if batched else data
        if not isinstance(member, dict) or set(member) - {'json', 'meta'} or not isinstance(member.get('json'), dict):
            raise SignError('invalid_input')
        value = dict(member['json'])
        if 'meta' in member:
            meta = member['meta']
            if not isinstance(meta, dict) or set(meta) - {'values', 'v'} or meta.get('v', 1) != 1 or not isinstance(meta.get('values'), dict):
                raise SignError('invalid_input')
            for key, annotation in meta['values'].items():
                if key not in {'authOptions', 'accessAuthOptions', 'recipientOverride', 'nextSigner'} or annotation != ['undefined'] or value.get(key) is not None:
                    raise SignError('invalid_input')
                value.pop(key, None)
        if set(value) - RPC[name][1] or any(value.get(k) not in (None, {}, {'type': 'EXPLICIT_NONE'}) for k in ('authOptions', 'accessAuthOptions')):
            raise SignError('recipient_scope_mismatch')
        token = value.get('token')
        if name == 'envelope.item.getManyByToken':
            mode = value.get('access')
            if not isinstance(mode, dict) or set(mode) != {'type', 'token'} or mode['type'] != 'recipient':
                raise SignError('recipient_scope_mismatch')
            token = mode['token']
        if not access.native_token or not token or token != access.native_token:
            raise SignError('recipient_scope_mismatch')
        if 'envelopeId' in RPC[name][1] and value.get('envelopeId') != access.workflow.envelope_id:
            raise SignError('recipient_scope_mismatch')
        if 'documentId' in RPC[name][1]:
            # Native completion still calls the legacy-named RPC with the v2 envelope's secondary ID.
            secondary = envelope.get('secondaryId', '')
            expected = int(secondary.removeprefix('document_')) if re.fullmatch(r'document_[0-9]+', secondary) else None
            if expected is None or value.get('documentId') != expected:
                raise SignError('recipient_scope_mismatch')
        if 'fieldId' in RPC[name][1]:
            field = next((f for f in envelope.get('fields', []) if f.get('id') == value.get('fieldId') and
                str(f.get('recipientId')) == access.native_recipient_id and
                f.get('envelopeItemId') in access.workflow.item_ids), None)
            if field is None:
                raise SignError('recipient_scope_mismatch')
        if name == 'recipient.rejectDocumentWithToken' and (not isinstance(value.get('reason'), str) or
                not 1 <= len(value['reason'].strip()) <= 500):
            raise SignError('reason_required')
    return names


def reconcile_native(access):
    work = access.workflow
    credential = SignCredential.objects.get(owner=work.owner, enabled=True)
    with Documenso(credential) as client:
        envelope = client.get(work.envelope_id)
        validate_envelope(work, envelope)
        reconcile(work, client, envelope)
    access.refresh_from_db()
    return envelope


def eligible(access, envelope):
    person = next((p for p in envelope['recipients'] if str(p['id']) == access.native_recipient_id), None)
    if not person or person.get('token') != access.native_token or person['email'].lower() != access.email:
        raise SignError('recipient_scope_mismatch')
    if access_state(access) != 'welcome' or envelope['status'] != 'PENDING' or person.get('signingStatus') != 'NOT_SIGNED':
        return False
    if person.get('role') not in {'SIGNER', 'APPROVER'}:
        return False
    if envelope.get('documentMeta', {}).get('signingOrder') == 'SEQUENTIAL':
        order = person.get('signingOrder')
        if not isinstance(order, int):
            raise SignError('signing_order_unavailable')
        return not any(p.get('role') != 'CC' and p.get('signingStatus') != 'SIGNED' and
            (p.get('signingOrder') is None or p['signingOrder'] < order) for p in envelope['recipients'])
    return True


def page(request, state, *, access=None, status=200):
    return HttpResponse(render_to_string('dealroom_sign/recipient.html', {
        'state': state, 'access': access, 'csrf': get_token(request), 'asset_prefix': '/s/assets',
        'disclosure_hash': disclosure_hash(access) if access else '',
        'entry_path': '/s/' + capability(access) + '/enter' if access else '',
        'title': clean_title(access.context['title']) if access else '',
        'sender_name': display_name(access.sender.get('name')) if access else '',
    }), status=status)


def redirect(path):
    response = HttpResponse(status=303)
    response['Location'] = path
    return response


def cookie_response(response, raw):
    response.set_cookie(COOKIE, raw, secure=True, httponly=True, samesite='Lax', path='/', max_age=8*60*60)
    return response


def limit(request, purpose='entry', maximum=30):
    # Never persist bearer values as cache keys. The listener's trusted hop supplies the IP.
    ip = client_ip(request)
    key = 'sign-rate:' + keyed_hash('rate', purpose + ':' + ip)
    if cache.add(key, 1, timeout=60):
        return
    if cache.incr(key) > maximum:
        raise SignError('rate_limited')


def terminal(request, access, envelope):
    state = access_state(access)
    if state == 'signed' and access.workflow.purpose == 'nda' and access.workflow.state == 'done':
        destination = confirmation_url(access.workflow)
        return redirect(destination or settings.SITE_DOMAIN.rstrip('/') + '/signing/nda/' + str(access.workflow.room_id))
    return page(request, state if state != 'welcome' else 'checking', access=access)


def final_download(request, session, kind):
    from .counterparty_mail import final_files
    if access_state(session.access) != 'signed' or session.access.workflow.state != 'done':
        raise SignError('copy_unavailable')
    files = final_files(session.access)
    if kind not in {'final', 'certificate'}:
        raise SignError('copy_unavailable')
    name, content = files[0 if kind == 'final' else 1]
    record_fact(session.access.workflow, 'signer.download', uuid.uuid4(),
        {'recipient_id': session.access.native_recipient_id, 'kind': kind})
    session.access.refresh_from_db()
    if access_state(session.access) != 'signed':
        raise SignError('copy_unavailable')
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = content_disposition_header(True, name)
    return response


def handle(request):
    if not boundary(request):
        return page(request, 'help', status=403)
    path = request.path
    if '%' in path or '\\' in path or '//' in path or any(p in {'.', '..'} for p in path.split('/')):
        raise SignError('recipient_route_denied')
    if request.method not in {'GET', 'POST'}:
        raise SignError('recipient_route_denied')
    if request.method == 'POST':
        if request.headers.get('Origin') != origin():
            raise SignError('recipient_origin_mismatch')
        if path.startswith('/s/'):
            rejection = RecipientCsrf(lambda r: None).process_view(request, handle, (), {})
            if rejection:
                return rejection
        # Native tRPC uses exact-Origin plus non-simple JSON, as Sign's own CSRF contract does.
        elif request.content_type != 'application/json':
            raise SignError('csrf_required')
    if path in {'/chief/tenant-logo', '/signing/tenant-logo'} and request.method == 'GET':
        return tenant_logo(request)
    raw = request.COOKIES.get(COOKIE)
    session = get_session(raw)
    if path == '/s/assets/entry.js' and request.method == 'GET':
        return HttpResponse("document.querySelector('[data-entry]')?.addEventListener('submit',async e=>{e.preventDefault();const f=e.target;const r=await fetch(f.action,{method:'POST',body:new FormData(f)});if(r.ok){const d=await r.json();location.assign(d.url)}else{location.reload()}});", content_type='application/javascript')
    if path.startswith(('/s/assets/fds/', '/s/assets/dealroom/')) and request.method == 'GET':
        relative = path.removeprefix('/s/assets/')
        roots = getattr(settings, 'SIGN_RECIPIENT_ASSET_ROOTS', None)
        if roots is None:
            roots = [base/'frontend'/build for base in (Path(settings.BASE_DIR), Path(settings.BASE_DIR).parent)
                     for build in ('dist', 'public')]
        for root in roots:
            root = Path(root)
            asset = (root/relative).resolve()
            if asset.is_relative_to(root.resolve()) and asset.suffix in {'.css', '.js', '.woff', '.woff2', '.svg'} and asset.is_file():
                return FileResponse(asset.open('rb'), content_type=mimetypes.guess_type(str(asset))[0] or 'application/octet-stream')
        raise SignError('recipient_asset_unavailable')
    if path == '/articles/signature-disclosure' and request.method == 'GET':
        return page(request, 'disclosure')
    if path == '/s/access':
        if request.method == 'GET':
            return page(request, 'alternate')
        limit(request)
        data = bounded_json(request.body) if request.content_type == 'application/json' else request.POST
        access = resolve(data.get('code', ''), alternate=True)
        if not access:
            raise SignError('recipient_unavailable')
        session, fresh = new_session(access, previous=raw)
        return cookie_response(redirect('/s/session/context'), fresh)
    if path.startswith('/s/nda/') and request.method == 'GET':
        access, session, fresh = consume_handoff(path.removeprefix('/s/nda/'), previous=raw)
        return cookie_response(redirect('/sign/' + identifier(access.native_token)), fresh)
    match = re.fullmatch(r'/s/([A-Za-z0-9_-]{43})(/enter)?', path)
    if match:
        limit(request)
        access = resolve(match[1])
        if not access or access_state(access) in {'withdrawn', 'unavailable'}:
            return page(request, 'help', status=403)
        if access_state(access) == 'expired':
            return page(request, 'expired', status=410)
        if request.method == 'GET' and not match[2]:
            # A scanner sees only a generic shell and does not create a signer session.
            return page(request, 'entry', access=access)
        if request.method != 'POST' or not match[2]:
            raise SignError('recipient_route_denied')
        session, fresh = new_session(access, previous=raw)
        record_fact(access.workflow, 'signer.entered', uuid.uuid4(), {'recipient_id': access.native_recipient_id})
        return cookie_response(JsonResponse({'state': 'code_required' if access.required_auth == 'email_code'
            else access_state(access), 'url': '/s/session/context'}), fresh)
    if not session:
        return page(request, 'help', status=403)
    access = session.access
    if path == '/s/session/code/verify' and request.method == 'POST':
        data = bounded_json(request.body)
        fresh_session, fresh = verify_code(session, raw, data.get('challenge_id'), data.get('code', ''))
        return cookie_response(JsonResponse({'url': '/s/session/context'}), fresh)
    require_auth(session)
    if path == '/s/session/consent' and request.method == 'POST':
        data = bounded_json(request.body) if request.content_type == 'application/json' else request.POST
        fresh_session, fresh = consent(session, raw, data.get('disclosure_hash', ''), data.get('agree') in (True, 'on'))
        return cookie_response(redirect('/sign/' + identifier(access.native_token)), fresh)
    if path == '/s/session/original' and request.method == 'GET':
        content = source_bytes(access.workflow.source_version)
        if digest(content) != access.workflow.source_sha256:
            raise SignError('source_hash_changed')
        record_fact(access.workflow, 'signer.original_view', uuid.uuid4(), {'recipient_id': access.native_recipient_id})
        return HttpResponse(content, content_type='application/pdf')
    if path == '/s/session/download' and request.method == 'POST':
        return final_download(request, session, request.POST.get('kind'))
    if path.startswith('/s/return/'):
        # The callback binds the workflow, never any browser status or arbitrary return URL.
        if path.removeprefix('/s/return/') != str(access.workflow_id) or request.method != 'GET':
            raise SignError('recipient_scope_mismatch')
        envelope = reconcile_native(access)
        return terminal(request, access, envelope)
    if path == '/s/session/context' and request.method == 'GET':
        envelope = reconcile_native(access)
        state = access_state(access)
        if state == 'signed':
            return terminal(request, access, envelope)
        return page(request, state if state != 'welcome' or eligible(access, envelope) else 'waiting', access=access)
    if path == '/s/session/sign' and request.method == 'POST':
        envelope = reconcile_native(access)
        if not eligible(access, envelope):
            return terminal(request, access, envelope)
        if not session.consented_at or session.disclosure_hash != disclosure_hash(access):
            return page(request, 'welcome', access=access)
        return redirect('/sign/' + identifier(access.native_token))
    if path.startswith('/s/'):
        raise SignError('recipient_route_denied')
    return forward(request, session)


def forward(request, session):
    access = session.access
    path = request.path
    static = request.method == 'GET' and (re.fullmatch(r'/(assets|static|fonts|chief)/[A-Za-z0-9_./@-]+', path)
        or path in {'/__manifest', '/api/auth/session-json'})
    envelope = None
    if not static:
        envelope = reconcile_native(access)
        state = access_state(access)
        if state in {'withdrawn', 'expired', 'unavailable'}:
            return page(request, state, status=403)
        if path.startswith('/api/trpc/') and request.method == 'GET':
            names = authorize_rpc(request, access, envelope)
            results = []
            for name in names:
                if name == 'envelope.signingStatus':
                    status = 'COMPLETED' if access.workflow.state == 'done' else 'REJECTED' if state == 'declined' else 'PROCESSING' if all(p.get('role') == 'CC' or p.get('signingStatus') == 'SIGNED' for p in envelope['recipients']) else 'PENDING'
                    value = {'status': status}
                elif name == 'envelope.attachment.find':
                    value = {'data': []}
                else:
                    value = {'data': [{'id': i['id'], 'envelopeId': access.workflow.envelope_id,
                        'title': i.get('title') or access.workflow.title, 'order': i.get('order', 0)}
                        for i in envelope['envelopeItems'] if i['id'] in access.workflow.item_ids]}
                results.append({'result': {'data': {'json': value}}})
            record_fact(access.workflow, 'signer.view', uuid.uuid4(), {'recipient_id': access.native_recipient_id})
            return JsonResponse(results if request.GET.get('batch') == '1' else results[0], safe=False)
        if state != 'welcome':
            return terminal(request, access, envelope)
        if path.startswith('/sign/'):
            match = re.fullmatch(r'/sign/([^/]+?)(?:/(complete|expired|rejected|waiting))?(?:\.data)?', path)
            if request.method != 'GET' or not match or match[1] != access.native_token:
                raise SignError('recipient_scope_mismatch')
            if match[2]:
                return terminal(request, access, envelope) if match[2] != 'waiting' else page(request, 'waiting', access=access)
            if not eligible(access, envelope):
                return page(request, 'waiting', access=access)
            if not session.consented_at or session.disclosure_hash != disclosure_hash(access):
                return page(request, 'welcome', access=access)
        elif path.startswith('/api/trpc/'):
            names = authorize_rpc(request, access, envelope)
            if request.method == 'POST':
                if not eligible(access, envelope):
                    raise SignError('recipient_not_eligible')
                if not session.consented_at or session.disclosure_hash != disclosure_hash(access):
                    raise SignError('consent_required')
                with Documenso(SignCredential.objects.get(owner=access.workflow.owner, enabled=True)) as client:
                    original = client.item_pdf(access.workflow.item_ids[0], 'original')
                if digest(original) != access.workflow.source_sha256:
                    raise SignError('source_hash_changed')
        elif path.startswith('/api/files/token/'):
            match = re.fullmatch(r'/api/files/token/([^/]+)/envelopeItem/([^/]+)(?:/download/(original|pending|signed))?', path)
            # Sign's in-page viewer route accepts only initial|current (get-envelope-item-pdf-by-token.ts).
            long = re.fullmatch(r'/api/files/token/([^/]+)/envelope/([^/]+)/envelopeItem/([^/]+)/dataId/([^/]+)/(initial|current)/item\.pdf', path)
            if request.method != 'GET':
                raise SignError('recipient_scope_mismatch')
            if long:
                item = next((i for i in envelope['envelopeItems'] if i['id'] == long[3]), {})
                valid = (long[1] == access.native_token and long[2] == access.workflow.envelope_id and
                    long[3] in access.workflow.item_ids and long[4] == item.get('documentDataId'))
            else:
                valid = match and match[1] == access.native_token and match[2] in access.workflow.item_ids and match[3] in {None, 'original'}
            if not valid:
                raise SignError('recipient_scope_mismatch')
        elif re.fullmatch(r'/api/branding/logo/team/\d+', path) and request.method == 'GET':
            if path.rsplit('/', 1)[-1] != str(envelope.get('teamId')):
                raise SignError('recipient_scope_mismatch')
        else:
            raise SignError('recipient_route_denied')
        record_fact(access.workflow, 'signer.native_write' if request.method == 'POST' else 'signer.view',
            uuid.uuid4(), {'recipient_id': access.native_recipient_id})
    if len(request.body) > MAX_BODY:
        raise SignError('input_too_large')
    headers = forward_headers(request)
    target = settings.SIGN_RECIPIENT_INTERNAL_URL.rstrip('/') + request.get_full_path()
    # Spool bounded canonical bytes before responding; never decode/rewrite HTML, PDFs or CSP nonces.
    spool = tempfile.SpooledTemporaryFile(max_size=1024*1024)
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            with client.stream(request.method, target, headers=headers, content=request.body) as upstream:
                if 300 <= upstream.status_code < 400:
                    spool.close()
                    location = upstream.headers.get('location', '')
                    allowed = {origin() + '/s/return/' + str(access.workflow_id), '/s/return/' + str(access.workflow_id)}
                    if location in allowed or re.fullmatch('/sign/' + re.escape(access.native_token) + r'/(complete|waiting|expired|rejected)', location):
                        return redirect('/s/return/' + str(access.workflow_id))
                    raise SignError('native_redirect_denied')
                content_type = upstream.headers.get('content-type', '').split(';')[0]
                allowed = {'text/html', 'application/json', 'text/x-script', 'text/javascript', 'application/javascript',
                    'text/css', 'application/pdf', 'image/png', 'image/jpeg', 'image/svg+xml', 'image/webp',
                    'font/woff', 'font/woff2', 'font/ttf', 'font/otf', 'application/font-woff',
                    'application/octet-stream'}
                if content_type not in allowed or upstream.headers.get('content-encoding', 'identity') != 'identity':
                    raise SignError('native_content_denied')
                size = 0
                for chunk in upstream.iter_raw():
                    size += len(chunk)
                    if size > 50*1024*1024:
                        raise SignError('native_response_too_large')
                    spool.write(chunk)
                if not get_session(request.COOKIES.get(COOKIE)):
                    raise SignError('session_expired')
                spool.seek(0)
                response = FileResponse(spool, content_type=upstream.headers.get('content-type'), status=upstream.status_code)
                for name in ('Content-Security-Policy', 'Content-Disposition'):
                    if name in upstream.headers:
                        response[name] = upstream.headers[name]
                if path == '/chief/sign-tenant-logo' and upstream.status_code == 200 and content_type == 'image/png':
                    response['Cache-Control'] = upstream.headers.get('Cache-Control', 'private, no-store')
                return response
    except (httpx.HTTPError, SignError):
        spool.close()
        raise


class RecipientBoundaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        selected = request.META.get('HTTP_X_FLEET_RECIPIENT_LISTENER') == '1'
        recipient_path = request.path.startswith(('/s/', '/sign/'))
        if not selected and not recipient_path:
            return self.get_response(request)
        csrf = RecipientCsrf(lambda r: None)
        csrf.process_request(request)
        try:
            response = handle(request)
        except (SignError, httpx.HTTPError, SignCredential.DoesNotExist, ValueError, TypeError):
            response = page(request, 'help', status=403)
        response = csrf.process_response(request, response)
        cacheable_logo = (request.path in {'/chief/tenant-logo', '/signing/tenant-logo', '/chief/sign-tenant-logo'}
                          and response.status_code == 200
                          and response.get('Content-Type', '').split(';')[0] == 'image/png')
        if not cacheable_logo:
            response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = referrer_policy(response)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        # Own pages use external JS; native responses keep their nonce-bearing CSP intact.
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'; form-action 'self'; style-src 'self' 'unsafe-inline'"
        else:
            directives = [d.strip() for d in response['Content-Security-Policy'].split(';') if d.strip() and not d.strip().startswith('frame-ancestors ')]
            response['Content-Security-Policy'] = '; '.join([*directives, "frame-ancestors 'none'"])
        return response
