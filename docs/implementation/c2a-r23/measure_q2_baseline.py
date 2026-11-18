import sys
from pathlib import Path
from collections import Counter, defaultdict
from unittest.mock import Mock, patch
import json
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from dealroom_sign import placement
from dealroom_sign.tests.test_placement_r14 import in_process
from q2_inputs import matrix, rc
counts = defaultdict(Counter)
wrong = []
with patch('httpx.Client.send', Mock(side_effect=AssertionError('http'))):
    for i, (args, pages, people, allowed) in enumerate(matrix()):
        model = Mock()
        result = in_process(placement, rc.pages_pdf(pages), people, model)
        bad = bool(rc.wrong_fields(result, allowed))
        counts[args[0]]['wrong' if bad else result['status']] += 1
        if bad:
            wrong.append(args)
        model.assert_not_called()
        if (i+1) % 240 == 0:
            print(args[0], dict(counts[args[0]]), flush=True)
Path(__file__).with_name('q2-baseline-discovery.json').write_text(json.dumps({'counts':counts,'wrong_cases':wrong}, indent=2)+'\n')
