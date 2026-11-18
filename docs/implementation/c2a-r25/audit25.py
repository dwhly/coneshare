"""Certify measured bars and preserve the distinction from unavailable review inputs."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
PARTS = ('historical', 'review', 'layouts', 'wrapped', 'new', 'stress', 'q2',
         'extra', 'workers', 'attack', 'boundary', 'h1_review', 'veto',
         'workers24', 'workers_h1_uncaptioned', 'h1', 'q3a', 'q3b', 'workers25',
         'q3b_aligned', 'ordinary_ndas')
EXCEPTIONS = {
    ('review', 'Competition'), ('review', 'Q4 M1 ambiguity'),
    ('stress', 'Recitals northwind'), ('stress', 'Recitals misspelled_M1'),
    ('stress', 'Page probes nw_page2'), ('stress', 'Page probes nw_section1'),
    ('stress', 'Page probes the_recipient_page2'),
}


def read(name):
    return json.loads((OUT / name).read_text())


def write(name, data):
    with (OUT / name).open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tests(path):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids, families = Counter(), Counter()
    for case in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if case.find('failure') is not None else
                 'errors' if case.find('error') is not None else
                 'skipped' if case.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(case.attrib['classname'], case.attrib['name'])] += 1
        families[(case.attrib['classname'], case.attrib['name'].split('[')[0], state)] += 1
    return counts, ids, families


def total(summary, key):
    return sum(g.get(key, 0) for g in summary['groups'].values())


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '9a91a4b99d0df4d913780914379bf7e0fa374e1d'
    source = (ROOT / PRODUCT).read_bytes()
    source_hash = sha(ROOT / PRODUCT)
    assert source == (OUT / 'structural-source.py.txt').read_bytes()
    assert b"VERSION = 'c2a.25'" in source
    provenance = read('run-provenance.json')
    assert provenance['source_sha256'] == source_hash
    assert all(sha(ROOT / p) == h for p, h in provenance['test_hashes'].items())
    initial = read('starting-hashes.json')
    changed = [p for p, h in initial.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    # Extraction is unchanged; sharing a pristine r24 parse in the replay is valid.
    nodes = []
    for text in (source.decode(), (OUT / 'r24-source.py.txt').read_text()):
        nodes.append(ast.dump(next(n for n in ast.parse(text).body
                                  if isinstance(n, ast.FunctionDef) and n.name == 'extract')))
    assert nodes[0] == nodes[1]
    counts, ids, families = tests(OUT / 'final-full-suite.xml')
    assert counts == dict(passed=47655, failed=0, errors=0, skipped=0), counts
    assert read('final-full-suite-returncode.json') == 0
    assert not any(read('additional-returncodes.json').values())
    old_counts, old_ids, _ = tests(OUT.parent / 'c2a-r24/r24b/full-suite.xml')
    assert old_counts == dict(passed=40186, failed=0, errors=0, skipped=0)
    assert not old_ids - ids and sum((ids - old_ids).values()) == 7469
    assert families[('dealroom_sign.tests.test_placement_r19', 'test_company_competition_uses_identity_before_vetoes', 'passed')] == 40
    ff = Counter(read('failing-first-summary.json')['counts'])
    ff.update(read('failing-first-boundaries-final-summary.json')['counts'])
    assert ff == {'failed': 422, 'passed': 7047}
    summaries = {p: read('final/' + p + '-summary.json') for p in PARTS}
    assert not any(read('final/returncodes.json').values())
    raw = {}
    for part, summary in summaries.items():
        assert summary['source_sha256']['r25'] == source_hash
        assert summary['external_http_calls'] == 0
        if part not in {'q3a', 'q3b', 'workers25', 'q3b_aligned', 'ordinary_ndas'}:
            assert summary['archive_results_exact']
        for name, group in summary['groups'].items():
            for before in ('r21', 'r24'):
                assert group.get(before + '_to_r25_n_to_p', 0) == 0
                assert group.get(before + '_to_r25_c_to_w', 0) == 0
            if group.get('r25_raw_wrong', 0):
                assert (part, name) in EXCEPTIONS, (part, name, group)
                assert group.get('r25_remaining_flag_differs_r21', 0) == 0
                raw[part + ': ' + name] = group['r25_raw_wrong']
    golden = summaries['historical']['groups']['Seven goldens']
    assert golden['r25_golden_diffs'] == golden['r25_native_diffs'] == 0
    cells = sum(s['cases'] for s in summaries.values())
    workers = sum(s['worker_evaluations'] for s in summaries.values())
    remaining = sum(raw.values())
    carried_m1 = raw.get('stress: Recitals misspelled_M1', 0)
    preservation = dict(head=head, source_sha256=source_hash,
                        tracked_files=len(initial), unchanged=len(initial)-1, changed=changed,
                        existing_tests_fixtures_evidence_markers_unchanged=True,
                        preserved_test_ids=sum(old_ids.values()), added_test_ids=sum((ids-old_ids).values()),
                        full_suite=counts, index_unchanged=True, commit_created=False)
    write('preservation-summary.json', preservation)
    write('family-comparison.json', summaries)
    write('remaining-flags.json', raw)
    comparisons = {b: {key: sum(total(s, b + '_to_r25_' + key) for s in summaries.values())
                       for key in ('n_to_p', 'c_to_w', 'c_to_n', 'w_to_n')} for b in ('r21', 'r24')}
    write('vs-live.json', dict(cells=cells, families=sum(len(s['groups']) for s in summaries.values()),
                              worker_evaluations=workers, comparisons=comparisons))
    # The reviewer explicitly says its original generator was stdin-only. The
    # prose omits six Q3a selection choices and Q3b's exact role-pair list.
    # Report measured reconstructions honestly rather than inventing exactness.
    blockers = ['The exact review Q3a/Q3b stdin generators were not supplied. '
                'Every stated Q3a shape is covered (4,536 cells; r24 248 wrong and cand4 152, matching the review), '
                'but its reported 3,888-cell selection is unspecified. Q3b\'s nine role pairs are not enumerated; '
                'the explicit 2,430-cell reconstruction is independently measured, not certified as the exact review input set.']
    bars = dict(rc=1, source_sha256=source_hash, version='c2a.25', full_suite=counts,
                measured_cells=cells, comparisons=comparisons, goldens_exact=True,
                historical_raw_flags=raw, all_measured_nonexception_families_zero_wrong=True,
                preservation_passed=True, blockers=blockers)
    write('release-bars.json', bars)
    lines = ['# C2a r25 results', '',
             '**Structural guard implemented as `c2a.25`; no commit.** '
             '**coder rc=1** solely because the exact review Q3 matrices are unavailable; '
             'all executed release checks below pass. The broader reconstructed measurements must not be described as the exact 6,318 review cells.', '',
             f'Base HEAD `{head}`; shipped source SHA-256 `{source_hash}`.', '',
             '## What shipped', '',
             'Before redaction, `prepare_blocks` records whether another page contains a non-witness signing block '
             'that no provided signer scores positively. Only after the original assignment and validation succeed, '
             'a company/domain-only assignment (score 4) landing across that unresolved page boundary becomes a hold. '
             'Printed-name assignments keep their path. Every provided signer, including a supplied sender, participates '
             'in accounting for blocks. If the sender is omitted, its identity cannot be distinguished from another '
             'unclaimed party without extra input, so separated pages conservatively hold; that cost is measured below. '
             'Existing r24 scoring/role guards remain in force. The new guard adds no vocabulary.', '',
             'Scores and assignment margins are unchanged. Applying the guard only to an otherwise valid placement '
             'makes it a hold-only change by construction. A discarded candidate zeroed company scores before assignment '
             'and produced eight hold → correct-placement transitions in Q3a. It was rejected; all eight remain holds '
             'under the shipped implementation. Its partial suite and replay logs are retained, and are not release evidence. '
             '[Tie check](final-tie-preservation.json), [discarded Q3a](v1/q3a-summary.json).', '',
             '## Failing first and tests', '',
             '**422 failed / 7,047 passed on unchanged c2a.24** across the final new tests: '
             '248 Q3a failures, 166 in the broader Q3b matrix, seven worker failures, and one cross-page ownership boundary. '
             'The first draft of the new boundary fixture accidentally overprinted a Name placeholder; its original log '
             'is retained separately, and the corrected new fixture was rerun on c2a.24 before the fix. '
             'No pre-existing test or fixture was edited. [Initial matrix run](failing-first.txt), '
             '[final boundary baseline](failing-first-boundaries-final.txt).', '',
             '**Full Send suite: 47,655 passed, 0 failed, 0 errors, 0 skipped**, completed without `-x` '
             'or test selection. All 40,186 existing test IDs remain; 7,469 new IDs come from two added test-tree files. '
             'All 40 r19 identity-before-veto score cells pass, including the 20 cross-page cells. '
             '[Full log](final-full-suite.txt), [JUnit](final-full-suite.xml), [command/hashes](run-provenance.json).', '',
             '## Candidate and final comparison', '',
             'Columns count raw wrong placements. The only remaining raw flags belong to the explicitly accepted '
             'historical classes, and each remaining output equals r21 except analysis_version. '
             f'Of the original 258 accepted flags (48 M-1 plus 210 historical), 104 now hold; '
             f'{remaining} remain: {carried_m1} M-1 and {remaining-carried_m1} historical flags. '
             'Both r21 and r24 are freshly executed and match their archived complete outputs in every retained family. '
             'All new cases use zero model calls; historical golden/control stubs retain their expected calls. '
             'External HTTP calls are zero. Real workers parse independently and match in-process results.', '',
             '| Collection | Cells | r21 wrong | r24 wrong | cand4 wrong | r25 wrong | r24 correct → hold | r21 correct → hold |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for part, s in summaries.items():
        values = [s['cases'], *[total(s, v + '_raw_wrong') for v in ('r21', 'r24', 'cand4', 'r25')],
                  total(s, 'r24_to_r25_c_to_n'), total(s, 'r21_to_r25_c_to_n')]
        lines.append('| ' + part + ' | ' + ' | '.join(f'{v:,}' for v in values) + ' |')
    lines += ['', f'**{cells:,} measured cells; {workers:,} real-worker evaluations.** '
              '`n → p = 0` and `c → w = 0` against both c2a.24 and r21 in every measured family. '
              'Seven goldens and native fields are exact except analysis_version, in-process and on workers. '
              '[Per-family counts](family-comparison.json), [comparisons](vs-live.json).', '',
              '## Ordinary two-party NDA hold cost', '',
              'The Q3b reconstruction uses five affiliate layouts: one without an affiliate and before/after '
              'for each of two affiliate captions. The separate ordinary-NDA measurement also tests split and '
              'reversed signature pages; no affiliate is present.', '',
              '| Ordinary subset | Cells | r24 correct | r24 holds | r25 correct | r25 holds | New holds |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    ordinary = {'Q3b reconstructed, same page': summaries['q3b_aligned']['groups']['Q3b ordinary'],
                **summaries['ordinary_ndas']['groups']}
    for name, g in ordinary.items():
        values = [g['cases'], *[g.get(k, 0) for k in ('r24_c', 'r24_n', 'r25_c', 'r25_n', 'r24_to_r25_c_to_n')]]
        lines.append('| ' + name + ' | ' + ' | '.join(str(v) for v in values) + ' |')
    lines += ['', 'The review itself reports 322 correct / 164 holds among its 486 ordinary cells. '
              'That exact split is not asserted for the reconstructed role-pair list. '
              '[Ordinary inputs](ordinary_ndas.py), [Q3b reconstruction](review_q3b.py).', '',
              '## Preservation and remaining limitation', '',
              f'**{len(initial)-1:,}/{len(initial)-1:,} other originally tracked files are SHA-256 identical** '
              'to the session-start inventory. This includes every earlier test, fixture, evidence file and `.done` marker. '
              'Only `backend/dealroom_sign/placement.py` changed among pre-existing files. No staging, commits, '
              'migration/config changes or project-memory writes. [Audit](preservation-summary.json).', '',
              blockers[0], '',
              'The review prose describes 12 role headings with/without a company, four named headings with/without '
              '`RECIPIENT:`, and five captions with/without a company: 42 × 108 = 4,536 Q3a cells. '
              'The complete written axes reproduce its 248 r24 wrong / 152 cand4 wrong cells; r25 is zero. '
              'The Q3b role pairs are explicit in the new generator, and its 2,430-cell aligned reconstruction '
              'and 2,916-cell broader test matrix both have zero r25 wrong placements. '
              'The exact generator was requested during work; absent that input, the literal exact-matrix certification '
              'remains blocked. [Release bars](release-bars.json).', '',
              'Reproduce the full suite with the command in `run-provenance.json`. Replay all retained families '
              'using `replay25.py all <fresh-output-directory> structural-source.py.txt`; existing evidence '
              'is opened exclusively and is never overwritten.', '']
    with (OUT / 'results-r25.md').open('x') as stream:
        stream.write('\n'.join(lines))
    done = [f'coder rc=1 head={head}',
            'failing-first: 422 failed, 7047 passed on unchanged c2a.24; 248 Q3a, 166 broader Q3b, 7 worker, 1 boundary failures',
            'what shipped: VERSION c2a.25; structural cross-page unclaimed-block flag and final hold-only guard; original scores/margins preserved; cand4 rejected; first score-zeroing candidate rejected for 8 n -> p transitions',
            f'vs-live: {cells} measured cells; n -> p = 0 and c -> w = 0 versus c2a.24 AND r21; {workers} worker evaluations; all nonexception measured families 0 wrong; remaining {carried_m1} M-1 and {remaining-carried_m1} historical flags exact to r21 except analysis_version; seven goldens exact',
            'full-suite: 47655 passed, 0 failed, 0 errors, 0 skipped; completed without -x or selection; r19 competition 40/40',
            f'test changes: 2 added test-tree files, 7469 added tests; all 40186 old IDs retained; {len(initial)-1} other pre-existing tracked files hash-identical, including tests/fixtures/evidence/.done; no commit',
            'blockers: ' + blockers[0],
            'results: docs/implementation/c2a-r25/results-r25.md', '']
    with (OUT / 'counterparty-c2a-r25.done').open('x') as stream:
        stream.write('\n'.join(done))
    print(json.dumps(bars, indent=2))


if __name__ == '__main__':
    main()
