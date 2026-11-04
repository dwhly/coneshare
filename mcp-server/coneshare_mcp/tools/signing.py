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

    @mcp.tool()
    async def nda_workflow_reset(ctx: Context) -> dict:
        """NDA recovery requires a human staff JWT on the Signing page."""
        return {'status': 'human_staff_required', 'path': '/signing/'}

    @mcp.tool()
    async def sign_credential_configure(ctx: Context) -> dict:
        """Credential enrollment is human-only. Never submit a raw team token through an agent tool."""
        return {'status': 'human_staff_required', 'path': '/api/v1/dealroom-sign/credentials/',
                'method': 'PUT', 'reason': 'A human staff JWT is required; raw team tokens are not agent capabilities.'}
