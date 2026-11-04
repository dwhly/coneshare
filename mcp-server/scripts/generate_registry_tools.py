"""Generate endpoint-specific, typed MCP schemas from the reviewed served registry and OpenAPI."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
registry = json.loads((ROOT/'backend/dealroom/operations.json').read_text())
schema = yaml.safe_load((ROOT/'deploy/chief-send-v1/out/openapi.yaml').read_text())

def expand(value, seen=()):
    if isinstance(value, list):
        return [expand(v,seen) for v in value]
    if not isinstance(value, dict):
        return value
    if '$ref' in value:
        ref=value['$ref']
        if ref in seen:
            return {'type':'object'}
        target=schema
        for part in ref.removeprefix('#/').split('/'):
            target=target[part]
        return expand(target,seen+(ref,))
    return {k:expand(v,seen) for k,v in value.items()}

tools=[]
for path, methods in schema['paths'].items():
    for method, spec in methods.items():
        oid=spec.get('operationId')
        if not oid:
            continue
        if oid not in registry:
            raise RuntimeError(f'OpenAPI operation not in registry: {oid}')
        entry=registry[oid]
        recipient = '/dealroom/recipient/' in path or ('/links/' in path and ('render-page' in path or 'download-file' in path))
        if entry['boundary']!='staff' and not recipient and '/dealroom/brand/' not in path:
            continue
        props={}; required=[]
        for param in spec.get('parameters',[]):
            props[param['name']]=expand(param.get('schema',{}))
            if param.get('required'): required.append(param['name'])
        content=spec.get('requestBody',{}).get('content',{})
        multipart='multipart/form-data' in content and 'application/json' not in content
        if content:
            body=content.get('application/json') or content.get('multipart/form-data') or next(iter(content.values()))
            props['body']=expand(body.get('schema',{'type':'object'}))
            if spec.get('requestBody',{}).get('required'): required.append('body')
            if multipart:
                # Bytes are carried explicitly, never local filesystem paths or arbitrary fetch URLs.
                props['file_base64']={'type':'string','description':'Base64 bytes of the upload, maximum 50 MiB decoded.'}
                props['filename']={'type':'string'}
                required += ['file_base64','filename']
        if recipient:
            props['recipient_session']={'type':'string','description':'Cookie value returned by the preceding challenge/confirm tool; no staff key can supply recipient proof.'}
            props['csrf_token']={'type':'string'}
        tools.append({'name':oid,'operation_id':oid,'method':method.upper(),'path':path,'parameters':{'type':'object','properties':props,'required':required,'additionalProperties':False},'path_params':[p['name'] for p in spec.get('parameters',[]) if p['in']=='path'],'query_params':[p['name'] for p in spec.get('parameters',[]) if p['in']=='query'],'multipart':multipart,'recipient':recipient,'human_only':entry['human_only']})
# Stable ergonomic compatibility alias requested by phase-one acceptance.
room = next(t for t in tools if t['operation_id']=='dealroom_RoomViewSet_list_get')
tools.append({**room, 'name':'list_rooms'})
(ROOT/'mcp-server/coneshare_mcp/dealroom_tools.json').write_text(json.dumps(tools,indent=2,sort_keys=True)+'\n')
print(f'{len(tools)} typed tools generated')
