"""Execute all 21 exact r29 worker shapes against the release source."""
from contextlib import nullcontext
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from dealroom_sign import placement
from dealroom_sign.tests import placement_r30_review_cases as review
from dealroom_sign.tests.test_placement_r14 import in_process

source = (review.FIXTURES/'reviewer-r29-workers.py.txt').read_text()
body = source[source.index('fleet ='):]
rows = []
def capture(pages, people, model_client):
    local = inspect.currentframe().f_back.f_locals
    axes = {k: copy.deepcopy(local[k]) for k in ('sig','head','x','aff','name') if k in local}
    rows.append((axes, copy.deepcopy(pages), copy.deepcopy(people)))
    return dict(status='capture', reason_code='capture', fields=[])
namespace = dict(X=72, rc=SimpleNamespace(pages_pdf=lambda p:p, RECITALS=review.rc.RECITALS, PE=review.rc.PE),
                 placement=SimpleNamespace(place=capture), Mock=Mock, http=Mock(),
                 patch=lambda *a, **k:nullcontext(), print=lambda *a, **k:None,
                 in_process=lambda *a:dict(status='capture',reason_code='capture',fields=[]))
exec(compile(body,'reviewer-r29-workers.py.txt','exec'),namespace)
assert len(rows)==21
for key in ('OPENROUTER_API_KEY','PLACE_MODEL'):
    os.environ.pop(key,None)
http=Mock(side_effect=AssertionError('External HTTP forbidden'))
results=[]
with patch('httpx.Client.send',http):
    for axes,pages,people in rows:
        pdf=review.rc.pages_pdf(pages); client=Mock()
        actual=placement.place(pdf,people,model_client=client)
        assert actual==in_process(placement,pdf,people,Mock())
        assert actual['status']=='needs_sender' and not actual['fields'],(axes,actual)
        client.assert_not_called()
        results.append(dict(axes=axes,result=actual))
http.assert_not_called()
(OUT/'shipping-exact-workers.json').write_text(json.dumps(dict(cases=21,wrong=0,model_calls=0,external_http_calls=0,worker_equals_in_process=True,source_sha256=hashlib.sha256(Path(placement.__file__).read_bytes()).hexdigest(),results=results),indent=2)+'\n')
print('21 exact reviewer workers: all held; worker == in-process; model/HTTP calls 0')
