import asyncio
import json
import sys

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    fixture = json.load(sys.stdin)
    transport = StreamableHttpTransport('http://web/mcp', headers={'Authorization': 'Bearer ' + fixture['agent_key']})
    async with Client(transport) as client:
        names = {tool.name for tool in await client.list_tools()}
        assert {'send_for_signature', 'get_envelope_status', 'who_viewed'} <= names
        viewed = await client.call_tool('who_viewed', {'room_id': fixture['room_id']})
        assert not viewed.is_error
        envelopes = await client.call_tool('signing_list_envelopes', {'room_id': fixture['room_id']})
        result = envelopes.data
        items = result.get('results', result) if isinstance(result, dict) else result
        assert items
        status = await client.call_tool('get_envelope_status', {'workflow_id': items[0]['id']})
        assert not status.is_error
        pending = await client.call_tool('send_for_signature', {'room_id': fixture['room_id'],
            'version_id': fixture['versions']['Investment agreement'], 'idempotency_key': 'mcp-acceptance-1',
            'recipients': [{'email': 'agent-recipient@acme.test', 'name': 'Agent Recipient', 'fields': [
                {'type':'SIGNATURE','page':1,'positionX':10,'positionY':70,'width':35,'height':8}]}]})
        assert not pending.is_error
        assert pending.data['status'] == 'pending_approval'
        print(json.dumps({'tools': len(names), 'checks_passed': 3, 'send_result': pending.data,
                          'who_viewed_members': len(viewed.data['members']), 'status': status.data['state']}))

asyncio.run(main())
