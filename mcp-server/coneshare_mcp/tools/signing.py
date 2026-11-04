"""Thin tools: Send's registry, key scope and human approval gate enforce every call."""
from fastmcp import Context, FastMCP
from coneshare_mcp.client import ConeshareClient, _validate_resource_id


def register_signing_tools(mcp: FastMCP):
    @mcp.tool()
    async def send_for_signature(ctx: Context, room_id: str, version_id: str, recipients: list[dict], idempotency_key: str) -> dict:
        """Request signatures for a pinned room PDF. Supply fields per signer. Agent calls await human approval."""
        return await ConeshareClient.from_ctx(ctx)._request('POST', '/dealroom-sign/envelopes/', json_data={
            'room_id': room_id, 'version_id': version_id, 'recipients': recipients, 'idempotency_key': idempotency_key})

    @mcp.tool()
    async def get_envelope_status(ctx: Context, workflow_id: str) -> dict:
        """Get authoritative reconciled status and immutable artifact manifest; never returns signing tokens."""
        return await ConeshareClient.from_ctx(ctx)._request('GET', f'/dealroom-sign/envelopes/{_validate_resource_id(workflow_id)}/')

    @mcp.tool()
    async def who_viewed(ctx: Context, room_id: str) -> dict:
        """List verified members and observed browser engagement for a room."""
        return await ConeshareClient.from_ctx(ctx)._request('GET', f'/dealroom-sign/who-viewed/{_validate_resource_id(room_id)}/')

    @mcp.tool()
    async def signing_list_envelopes(ctx: Context, room_id: str) -> dict:
        """List redacted envelope workflows for a room."""
        data = await ConeshareClient.from_ctx(ctx)._request('GET', '/dealroom-sign/envelopes/', params={'room_id': room_id})
        return data if isinstance(data, dict) else {'results': data}

    @mcp.tool()
    async def signing_list_sources(ctx: Context, room_id: str) -> dict:
        """List pinned PDF versions available to sign in a room."""
        data = await ConeshareClient.from_ctx(ctx)._request('GET', f'/dealroom-sign/sources/{_validate_resource_id(room_id)}/')
        return {'results': data}

    @mcp.tool()
    async def nda_policy_get(ctx: Context, room_id: str) -> dict:
        """Read the current room NDA revision."""
        return await ConeshareClient.from_ctx(ctx)._request('GET', f'/dealroom-sign/nda-policy/{_validate_resource_id(room_id)}/')

    @mcp.tool()
    async def nda_policy_set(ctx: Context, room_id: str, version_id: str, fields: list[dict], enabled: bool = True) -> dict:
        """Set a new pinned NDA revision; agent changes require human approval, including disabling the gate."""
        return await ConeshareClient.from_ctx(ctx)._request('PUT', f'/dealroom-sign/nda-policy/{_validate_resource_id(room_id)}/', json_data={
            'version_id': version_id, 'fields': fields, 'enabled': enabled})

    @mcp.tool()
    async def sign_credential_status(ctx: Context) -> dict:
        """Read whether the owning staff member has configured Sign. Raw tokens are never returned."""
        return await ConeshareClient.from_ctx(ctx)._request('GET', '/dealroom-sign/credentials/')

    async def recipient_call(ctx, room_id, session_cookie, csrf_token, method, suffix=''):
        from urllib.parse import urlsplit
        import httpx
        client = ConeshareClient.from_ctx(ctx)
        # Recipient proof is separate from the staff agent key. Never forward that key.
        if any(c in session_cookie + csrf_token for c in '\r\n;'):
            raise ValueError('Invalid recipient proof encoding.')
        origin = urlsplit(client.settings.api_url)
        headers = {'Cookie': f'sessionid={session_cookie}; csrftoken={csrf_token}',
                   'X-CSRFToken': csrf_token, 'Origin': f'{origin.scheme}://{origin.netloc}'}
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as http:
            response = await http.request(method, client.settings.api_url + f'/dealroom-sign/nda/{_validate_resource_id(room_id)}/{suffix}',
                                          headers=headers, json={} if method == 'POST' else None)
        response.raise_for_status()
        return response.json()

    @mcp.tool()
    async def recipient_nda_status(ctx: Context, room_id: str, recipient_session: str, csrf_token: str) -> dict:
        """Read NDA status using the recipient's own verified session proof, never a staff impersonation."""
        return await recipient_call(ctx, room_id, recipient_session, csrf_token, 'GET')

    @mcp.tool()
    async def recipient_nda_start(ctx: Context, room_id: str, recipient_session: str, csrf_token: str) -> dict:
        """Prepare the current NDA for the verified recipient; signer email cannot be overridden."""
        return await recipient_call(ctx, room_id, recipient_session, csrf_token, 'POST')

    @mcp.tool()
    async def recipient_nda_enter(ctx: Context, room_id: str, recipient_session: str, csrf_token: str) -> dict:
        """Enter native signing with the recipient's own session and CSRF proof. Do not email this bearer URL."""
        return await recipient_call(ctx, room_id, recipient_session, csrf_token, 'POST', 'enter/')

    @mcp.tool()
    async def sign_credential_configure(ctx: Context) -> dict:
        """Credential enrollment is human-only. Never submit a raw team token through an agent tool."""
        return {'status': 'human_staff_required', 'path': '/api/v1/dealroom-sign/credentials/',
                'method': 'PUT', 'reason': 'A human staff JWT is required; raw team tokens are not agent capabilities.'}
