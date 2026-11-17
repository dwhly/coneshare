"""Case-level controls for the review's no-Harbor-heading justification.

These 24 explicitly defined controls are not the unavailable 480-case scratch
family. Each record retains the full rows, signer identity and emitted fields.
"""
from contextlib import ExitStack
from itertools import product
import hashlib
import os
from unittest.mock import Mock, patch

import check_evidence as replay


def main():
    for key in ['OPENROUTER_API_KEY', 'PLACE_MODEL']:
        os.environ.pop(key, None)
    variants = replay.sources()
    records = []
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    with ExitStack() as stack:
        modules = {n: replay.make_module('competition_control_' + n, s, stack) for n, s in variants.items()}
        stack.enter_context(patch('httpx.Client.send', forbidden))
        for heading, affiliate_x, both, explicit_company in product(
                ['RECIPIENT:', 'COMPANY', None], [40, 280], [False, True], [False, True]):
            rows = [(250, replay.new.FLEET, False, 40), (290, 'By:', True, 40, 220),
                    (350, 'Date:', True, 40, 220), (290, 'By:', True, 280, 460),
                    (350, 'Date:', True, 280, 460),
                    (410, replay.new.AFFILIATES[0], False, affiliate_x),
                    (450, 'By:', True, affiliate_x, affiliate_x + 180),
                    (510, 'Date:', True, affiliate_x, affiliate_x + 180)]
            if heading:
                rows.append((250, heading, False, 280))
            signers = [dict(s) for s in replay.new.signers(both)]
            if explicit_company:
                signers[-1]['company'] = replay.new.HARBOR
            record = {'case': repr((heading, affiliate_x, both, explicit_company)),
                      'rows': rows, 'signers': signers, 'results': {},
                      'classification': ('Explicit legal company excludes the Group heading; hold required.' if explicit_company else
                       'No Harbor heading or Pat name on the blank rule; Pat supplies only the harborlight domain, '
                       'and Group is the only matching heading. The input does not identify a different legal entity '
                       'as Pat\'s company. Company-only placement on Group is permitted by the requested exception.')}
            allowed = {replay.new.PAT[0]['email']: (affiliate_x, 450, affiliate_x + 180),
                       replay.new.TWO[1]['email']: (40, 290, 220)}
            for name, module in modules.items():
                model = Mock()
                result = replay.old.r14.in_process(module, replay.new.rows_pdf(rows), signers, model)
                assert model.call_count == 0
                if explicit_company:
                    assert (result['status'], result['fields']) == ('needs_sender', []), (record['case'], name, result)
                else:
                    assert not replay.new.wrong_fields(result, allowed), (record['case'], name, result)
                record['results'][name] = result
            records.append(record)
    forbidden.assert_not_called()
    replay.write('release-competition-controls', {'cases': records, 'source_sha256': {n: hashlib.sha256(s.encode()).hexdigest() for n,s in variants.items()},
                                        'external_http_calls': forbidden.call_count})
    print(f'{len(records)} controls passed; these are not the reviewer scratch family', flush=True)


if __name__ == '__main__':
    main()
