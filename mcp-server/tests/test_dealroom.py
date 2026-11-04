"""The generated tools must honor the central JSON-only mutation boundary."""
import asyncio
import httpx
import pytest
from coneshare_mcp.dealroom import RegistryTool


@pytest.mark.parametrize('method', ['POST', 'PATCH', 'DELETE'])
def test_bodyless_agent_mutations_send_json(method, monkeypatch):
    original = httpx.AsyncClient
    seen = []
    def transport(request):
        seen.append(request)
        assert request.headers.get('content-type') == 'application/json'
        assert request.content == b'{}'
        return httpx.Response(200, json={'status': 'ok'})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(transport), **kwargs))
    tool = RegistryTool(name='bodyless_mutation', description='Contract regression', parameters={'type':'object', 'properties':{}}, endpoint={'path':'/api/v1/dealroom/rooms/example/', 'path_params':[], 'query_params':[], 'recipient':False, 'multipart':False, 'method':method})
    asyncio.run(tool.run({}))
    assert len(seen) == 1
