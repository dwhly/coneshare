import base64
import json
from http.cookies import SimpleCookie
import os
from pathlib import Path
from urllib.parse import quote
import httpx
import jsonschema
from fastmcp.tools import Tool, ToolResult
from fastmcp.server.dependencies import get_http_request


class RegistryTool(Tool):
    endpoint: dict

    async def run(self, arguments: dict) -> ToolResult:
        body_arg = arguments.get('body')
        kind = body_arg.get('kind') if isinstance(body_arg, dict) else None
        if isinstance(kind, str) and kind in self.endpoint.get('human_only_kinds', []):
            raise ValueError('403: This export kind requires a verified human board session.')
        jsonschema.validate(arguments, self.parameters)
        endpoint = self.endpoint
        path = endpoint['path']
        for name in endpoint['path_params']:
            path = path.replace('{'+name+'}', quote(str(arguments[name]),safe=''))
        headers={}
        try:
            request=get_http_request()
            authorization=request.headers.get('authorization','')
        except RuntimeError:
            authorization='Bearer '+os.environ.get('CONESHARE_API_KEY','')
        if not endpoint['recipient']:
            headers['Authorization']=authorization
        else:
            headers['Cookie']=arguments.get('recipient_session','')
            headers['X-CSRFToken']=arguments.get('csrf_token','')
        body=arguments.get('body')
        options={'params':{k:arguments[k] for k in endpoint['query_params'] if k in arguments}, 'headers':headers}
        if endpoint['multipart']:
            data=base64.b64decode(arguments['file_base64'],validate=True)
            if len(data)>50*1024*1024: raise ValueError('Upload too large')
            options.update(files={'file':(arguments['filename'],data)},data={k:v for k,v in (body or {}).items() if k!='file'})
        elif body is not None or endpoint['method'] not in ('GET', 'HEAD', 'OPTIONS'):
            options['json'] = body if body is not None else {}
        base=os.environ.get('CONESHARE_URL','http://localhost:8795').rstrip('/')
        # One client per invocation: no shared recipient cookie jar between callers.
        async with httpx.AsyncClient(timeout=90, follow_redirects=False) as client:
            response=await client.request(endpoint['method'],base+path,**options)
        if response.status_code>=400:
            raise ValueError(f'{response.status_code}: {response.text[:2000]}')
        if 'json' in response.headers.get('content-type',''):
            result=response.json()
        else:
            result={'content_type':response.headers.get('content-type'),'base64':base64.b64encode(response.content).decode(),
                    'headers':{k:response.headers[k] for k in ['content-disposition','x-content-sha256','x-dealroom-artifact-id','x-dealroom-audit-id','cache-control','referrer-policy'] if k in response.headers}}
        if endpoint['recipient']:
            cookies=SimpleCookie(); cookies.load(arguments.get('recipient_session',''))
            for key,value in response.cookies.items(): cookies[key]=value
            result={'result':result,'recipient_session':'; '.join(f'{k}={m.value}' for k,m in cookies.items())}
        return ToolResult(content=json.dumps(result))


def register(mcp):
    for entry in json.loads(Path(__file__).with_name('dealroom_tools.json').read_text()):
        if entry['operation_id'] in {
            'dealroom_sign_SignaturePageListView_endpoint_get', 'dealroom_sign_SignaturePageView_endpoint_get'
        }:
            policy = 'Verified human board session required.'
        elif entry['human_only']:
            policy = 'Human staff JWT required.'
        else:
            policy = 'Uses the central operation policy and approval gate.'
        mcp.add_tool(RegistryTool(name=entry['name'], description=f"{entry['operation_id']}. {policy}",
            parameters=entry['parameters'], endpoint=entry))
