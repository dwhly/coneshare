"""Extend N-1's extracted-block ownership contract to overlapping ranges.

This is a direct placement/unit check, not a PDF extraction reproduction.
The optional range merge must not hand a witness-owned name to a party.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock, patch

import check_evidence as evidence

OUT = Path(__file__).resolve().parent


def main():
    source = (evidence.ROOT / evidence.old.PRODUCT).read_text()
    baseline = subprocess.check_output(['git', 'show', '75837b04:' + evidence.old.PRODUCT], cwd=evidence.ROOT).decode()
    sources = {'r16': baseline, 'r17': source, 'l1': evidence.l1_candidate.candidate(source)}
    records = []
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    with ExitStack() as stack:
        stack.enter_context(patch('httpx.Client.send', forbidden))
        modules = {key: evidence.old.make_module(key, value, stack) for key, value in sources.items()}
        for role in ['Witness:', 'Attest:', 'Attestation:']:
            for reverse in [False, True]:
                for key, module in modules.items():
                    # Pat's row starts outside the party range and inside the
                    # witness range. Before merging, only the witness is nearest.
                    row = {'text': 'Name: Pat Smith', 'rect': [300, 312, 375, 322]}
                    blocks = []
                    for x, end, caption in [(72, 290, 'By:'), (92, 310, role)]:
                        label = {'text': caption, 'rect': [x, 290, x + 20, 300]}
                        line = module.Line(1, x + 30, end, 300, 'drawn', label,
                                           'SIGNATURE' if caption == 'By:' else '')
                        blocks.append(module.Block(str(x), line, [row], '', '', False, raw_labels=[row]))
                    party, witness = blocks
                    party.extras['DATE'] = module.Line(1, 105, 290, 360, 'drawn',
                        {'text': 'Date:', 'rect': [72, 350, 95, 360]}, 'DATE')
                    if reverse:
                        blocks.reverse()
                    module.prepare_blocks(blocks, {}, evidence.new.PAT)
                    model = Mock()
                    with patch.object(module, 'bounded_extract', return_value=(blocks, {1: (612, 792)}, {})):
                        result = module.place(b'extracted-block-unit-check', evidence.new.PAT, model_client=model)
                    model.assert_not_called()
                    records.append(dict(candidate=key, role=role, reverse=reverse,
                                        party_scores=party.scores, witness_scores=witness.scores,
                                        wrong=bool(result['fields']), result=result))
        forbidden.assert_not_called()
    summary = {key: dict(cases=sum(r['candidate'] == key for r in records),
                         wrong=sum(r['wrong'] for r in records if r['candidate'] == key),
                         holds=sum(r['result']['status'] == 'needs_sender' for r in records if r['candidate'] == key))
               for key in modules}
    (OUT / 'l1-witness-overlap.json').write_text(json.dumps(dict(summary=summary, records=records), indent=2) + '\n')
    assert summary['r17']['wrong'] == 0 and summary['l1']['wrong'] == 6
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
