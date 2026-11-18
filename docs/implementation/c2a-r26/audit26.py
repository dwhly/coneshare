"""Verify release evidence, then write the r26 report and completion marker."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
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


def raw_summary(part, summary):
    """Separate accepted historical flags from truly correct hold cost.

    Earlier replay harnesses classify accepted raw flags as correct. Preserve
    those original files, but derive report transitions from raw geometry and
    complete outputs so closing an accepted wrong cell is not called a cost.
    """
    data = read('final/' + part + '-cases.json')
    versions = ('r21', 'r24', 'r25', 'r26')
    groups, transitions = {}, {}
    for row in data['cases']:
        counts = groups.setdefault(row['group'], Counter())
        states = {}
        for version in versions:
            result = data['outcomes'][row['results'][version]]
            states[version] = ('w' if row['raw_wrong'][version] else
                               {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[result['status']])
            counts[version + '_' + states[version]] += 1
        for base in versions[:-1]:
            prefix = base + '_to_r26_'
            counts[prefix + 'n_to_p'] += states[base] == 'n' and states['r26'] in {'c', 'w'}
            counts[prefix + 'c_to_w'] += states[base] == 'c' and states['r26'] == 'w'
            counts[prefix + 'c_to_n'] += states[base] == 'c' and states['r26'] == 'n'
            counts[prefix + 'w_to_n'] += states[base] == 'w' and states['r26'] == 'n'
        transitions.setdefault(row['group'], Counter())[' -> '.join(states[v] for v in versions)] += 1
    for name, group in summary['groups'].items():
        for version in versions:
            for state in ('c', 'n', 'w', 'b'):
                group[version + '_' + state] = groups[name][version + '_' + state]
        group.update({k: v for k, v in groups[name].items() if '_to_' in k})
    summary['transitions'] = transitions
    summary['report_classification'] = 'Raw geometry flags; accepted exceptions remain visible as wrong.'
    return summary


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '701f6aeeabfc47bf5b997b1187705b039aea4f40'
    source = ROOT / PRODUCT
    assert source.read_bytes() == (OUT / 'r26-source.py.txt').read_bytes()
    assert b"VERSION = 'c2a.26'" in source.read_bytes()
    source_hash = sha(source)
    assert read('run-provenance.json')['source_sha256'] == source_hash
    assert read('cand5-equivalence.json')['r26_source_sha256'] == source_hash
    initial = read('starting-hashes.json')
    changed = [p for p, digest in initial.items()
               if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    for p, digest in read('failing-first-provenance.json')['new_tests'].items():
        assert sha(ROOT / p) == digest, ('new regression changed after failing first', p)
    for record in read('review-provenance.json'):
        assert sha(OUT / record['body_file']) == record['body_sha256']
        assert sha(Path(record['transcript'])) == record['transcript_sha256']
    # The review hashes omit the heredoc's trailing newline.
    for call, prefix in ((19, 'e41a8ab17b73'), (20, '431acfa07d6c')):
        body = (OUT / f'reviewer-r24-call{call}.py.txt').read_bytes()
        assert hashlib.sha256(body.rstrip(b'\n')).hexdigest().startswith(prefix)

    counts, ids, families = tests(OUT / 'full-suite.xml')
    assert counts == dict(passed=50454, failed=20, errors=0, skipped=0), counts
    assert read('full-suite-returncode.json') == 1
    assert read('targeted-returncode.json') == 0
    assert read('low-exemption-returncode.json') == 0
    old_counts, old_ids, _ = tests(OUT.parent / 'c2a-r25/final-full-suite.xml')
    assert old_counts == dict(passed=47655, failed=0, errors=0, skipped=0)
    assert not old_ids - ids
    assert sum((ids - old_ids).values()) == 2819
    assert families[('dealroom_sign.tests.test_placement_r19',
                     'test_company_competition_uses_identity_before_vetoes', 'passed')] == 40
    first = read('failing-first-summary.json')
    assert first['counts'] == {'failed': 62, 'passed': 2757}
    assert read('failing-first-returncode.json') == 1
    conflict = read('suite-conflict.json')
    assert conflict['cases'] == 40
    assert conflict['counts']['immutable_test_conflicts'] == 20
    assert conflict['worker_evaluations'] == 160
    assert conflict['external_http_calls'] == conflict['model_calls'] == 0
    assert families[('dealroom_sign.tests.test_placement_r13',
                     'test_l2_separate_own_company_line_preserves_scoring', 'failed')] == 20

    returns = read('final/returncodes.json')
    assert len(returns) == 27 and not any(returns.values()), returns
    summaries = {p: raw_summary(p, read('final/' + p + '-summary.json')) for p in returns}
    raw = {}
    for part, summary in summaries.items():
        assert summary['source_sha256']['r26'] == source_hash
        assert summary['external_http_calls'] == 0
        if not part.startswith('exact_') and part not in {'exhibits', 'three_party', 'workers26'}:
            assert summary['archive_results_exact'], part
        for name, group in summary['groups'].items():
            for before in ('r21', 'r24', 'r25'):
                assert group.get(before + '_to_r26_n_to_p', 0) == 0, (part, name)
                assert group.get(before + '_to_r26_c_to_w', 0) == 0, (part, name)
            if group.get('r26_raw_wrong', 0):
                assert (part, name) in EXCEPTIONS, (part, name, group)
                assert group.get('r26_remaining_flag_differs_r21', 0) == 0
                raw[part + ': ' + name] = group['r26_raw_wrong']
    for part, size in [('exact_q3a', 4536), ('exact_q3b', 2430), ('exact_q3c', 2808),
                       ('h1', 2160), ('h1_review', 2160), ('workers26', 10),
                       ('exhibits', 576), ('three_party', 36)]:
        assert summaries[part]['cases'] == size
        assert total(summaries[part], 'r26_raw_wrong') == 0
    same = summaries['exact_q3c']['groups']['exact_q3c same_page3']
    assert total(summaries['exact_q3a'], 'r24_raw_wrong') == 248
    assert total(summaries['exact_q3b'], 'r24_raw_wrong') == 84
    assert same['cases'] == 468 and same['r25_raw_wrong'] == 55
    assert same['r25_to_r26_c_to_n'] == 10
    assert total(summaries['three_party'], 'r25_to_r26_c_to_n') == 6
    assert total(summaries['three_party'], 'r26_c') == 12
    assert total(summaries['three_party'], 'r26_n') == 24
    assert total(summaries['exhibits'], 'r25_to_r26_c_to_n') == 0
    assert total(summaries['exhibits'], 'r24_to_r26_c_to_n') == 42
    cost = read('hold-cost.json')
    assert cost['exhibits']['groups']['explicit']['correct_to_hold'] == 28
    assert cost['exhibits']['groups']['domain']['correct_to_hold'] == 14
    golden = summaries['historical']['groups']['Seven goldens']
    assert golden['cases'] == 7
    assert golden['r26_golden_diffs'] == golden['r26_native_diffs'] == 0
    assert total(summaries['workers26'], 'r25_raw_wrong') == 7
    cells = sum(s['cases'] for s in summaries.values())
    assert cells == 82450
    workers = sum(s['worker_evaluations'] for s in summaries.values())
    comparisons = {base: {key: sum(total(s, base + '_to_r26_' + key) for s in summaries.values())
                          for key in ('n_to_p', 'c_to_w', 'c_to_n', 'w_to_n')}
                   for base in ('r25', 'r24', 'r21')}
    low = read('low-exemption-measurement.json')
    assert low['cases'] == 576 and low['model_calls'] == low['external_http_calls'] == 0
    assert sum(g.get('r26_to_candidate_n_to_p', 0) for g in low['groups'].values()) == 28
    assert sum(g.get('explicit_exemption_w', 0) for g in low['groups'].values()) == 0
    preservation = dict(head=head, source_sha256=source_hash, tracked_files=len(initial),
                        unchanged=len(initial)-1, changed=changed,
                        existing_tests_fixtures_evidence_markers_unchanged=True,
                        preserved_test_ids=sum(old_ids.values()), added_test_ids=sum((ids-old_ids).values()),
                        full_suite=counts, index_unchanged=True, commit_created=False)
    write('preservation-summary.json', preservation)
    write('family-comparison.json', summaries)
    write('remaining-flags.json', raw)
    write('vs-live.json', dict(cells=cells, worker_evaluations=workers, comparisons=comparisons))
    blockers = ['The exact cand5 rule conflicts with 20 immutable r13 L-2 positive controls. '
                'Each has three non-witness blocks on one page with scores [0], [0], [4]. '
                'cand5 must hold the score-4 placement, while the existing test requires placed '
                'with score=4 and margin=4. Full suite completed with 20 failed, 50454 passed, '
                '0 errors, 0 skipped. Neither the guard nor the tests were weakened.']
    write('release-bars.json', dict(rc=1, source_sha256=source_hash, version='c2a.26',
                                   full_suite=counts, measured_cells=cells, comparisons=comparisons,
                                   goldens_exact=True, historical_raw_flags=raw,
                                   all_nonexception_families_zero_wrong=True,
                                   preservation_passed=True, full_suite_passed=False, blockers=blockers))

    lines = ['# C2a r26 results', '',
             '**Exact cand5 implemented as `c2a.26`; coder rc=1. Not release-ready. No commit.**', '',
             f'Base HEAD `{head}`; implemented source SHA-256 `{source_hash}`.', '',
             '**Release blocker:** the full suite completed with 20 failures in the unchanged r13 L-2 '
             'positive controls. They require a company-only placement on a page with three non-witness '
             'blocks and two unclaimed blocks—the exact condition cand5 must hold. All replay safety '
             'bars pass, but the required zero-failure full-suite bar does not. '
             '[Conflict reproduction](suite-conflict.json).', '',
             '## Change and failing first', '',
             'The existing unclaimed-block flag now also arms when another non-witness block on the same '
             'page is unclaimed and that page has at least three non-witness blocks. The final company-only '
             'placement becomes an `ambiguous_identity` hold. Scoring, assignment and margins are unchanged. '
             'The implementation of `prepare_blocks` is AST-identical to the reviewer’s cand5. '
             'The hold message now covers both same-page and cross-page ambiguity. '
             '[Equivalence](cand5-equivalence.json).', '',
             '**Unchanged c2a.25: 62 failed / 2,757 passed**: 55 exact Q3c cases and seven real-worker cases. '
             'Failures cover `same_named` (both signer sets), `same_harbour` (both), '
             '`same_caption_nocompany` (both), and `same_msa_supplier_nocompany` (Pat only). '
             'The two MSA-with-company controls and MSA-without-company/both-signers already held. '
             '[Failing-first log](failing-first.txt), [source/test hashes](failing-first-provenance.json).', '',
             '**Final new-test run: 2,819 passed. Full Send suite: 50,454 passed, 20 failed, 0 errors, 0 skipped**, '
             'completed without `-x`, deselection, test edits or fixture edits. All 47,655 old IDs remain; '
              '2,819 new IDs are in the new r26 test file. All 40 r19 identity-before-veto score cases pass. '
             '[Full log](full-suite.txt), [JUnit](full-suite.xml), [commands](run-provenance.json).', '',
             'The 20 failures are `test_placement_r13.py::test_l2_separate_own_company_line_preserves_scoring` '
             'with Pat alone: four headings × five captions. The original fixture has By blocks at '
             'y=270, 310 and 560 on page 1. Their scores are `[0], [0], [4]`; none is a witness. '
             'The middle block has an uncertain printed-name identity, so it remains unclaimed. '
             'r21/r24/r25 place at y=560 with score=4 and margin=4; exact cand5 sets the guard and holds. '
             'All 40 original positive/hold controls were replayed across four versions, with **160 '
             'real-worker evaluations matching in-process results**. Tests and input fixtures remain '
             'unchanged. No exception was added merely to restore these placements. '
             '[Measured conflict](suite-conflict.json), [reproducer](suite_conflict.py).', '',
             '## Exact reviewer inputs and count corrections', '',
             'Generator bodies were extracted byte-for-byte from the supplied r24/r25 transcripts, with '
             'full commands, line numbers and SHA-256 hashes retained. Tests execute their original generator '
             'bodies with only the evaluator replaced by a case collector; no axis is reconstructed. '
             'Q3a/Q3b body hashes, excluding the heredoc trailing newline, match review prefixes '
             '`e41a8ab17b73` / `431acfa07d6c`. [Provenance](review-provenance.json).', '',
             'The review prose has two arithmetic errors: Q3a’s 42 shapes × 108 combinations generate '
             '**4,536**, not 3,888 cells; Q3c’s 26 shapes × 18 same-page combinations generate **468**, '
             'not 324 cells. The six Q3c layouts total 2,808. The transcript output itself totals 468 '
             'same-page cells and reproduces all 55 wrong placements. Every generated cell is retained '
             'and evaluated, including all controls. Q3b is exactly 2,430 cells.', '',
             '## Comparison against r25 live, r24 and r21', '',
             f'**{cells:,} replay cells across 27 collections; {workers:,} real-worker evaluations.** '
             'Every family has `n → p = 0` and `c → w = 0` against all three baselines. '
             f'**Raw wrong placements remaining: {sum(raw.values())}.** '
             'All seven goldens and their native fields are exact except `analysis_version`, both '
             'in-process and through real workers. All retained baseline results equal their prior '
             'archived outputs. External HTTP calls are zero; new-family model calls are zero '
             '(historical golden/control stubs retain exactly their expected calls). '
             'Report transitions use raw geometry: closing an accepted historical wrong cell is '
             'counted as wrong → hold, not correct → hold. The original harness logs are retained.', '',
             '| Collection | Cells | r21 raw W | r24 raw W | r25 raw W | r26 raw W | r25 correct → hold |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    order = ('historical', 'review', 'layouts', 'wrapped', 'new', 'stress', 'q2', 'extra', 'workers',
             'attack', 'boundary', 'h1_review', 'veto', 'workers24', 'workers_h1_uncaptioned',
             'h1', 'q3a', 'q3b', 'workers25', 'q3b_aligned', 'ordinary_ndas',
             'exact_q3a', 'exact_q3b', 'exact_q3c', 'exhibits', 'three_party', 'workers26')
    for part in order:
        summary = summaries[part]
        vals = [part, str(summary['cases'])] + [str(total(summary, v + '_raw_wrong')) for v in ('r21', 'r24', 'r25', 'r26')]
        vals += [str(total(summary, 'r25_to_r26_c_to_n'))]
        lines.append('| ' + ' | '.join(vals) + ' |')
    lines += ['', 'The inherited `q3a`, `q3b`, and `q3b_aligned` rows retain the r25 reconstructions; '
              '`exact_*` rows separately use transcript generators. Overlapping collections are intentionally '
              'not deduplicated. [All family counts](family-comparison.json), [all transitions](vs-live.json).', '',
              '| Baseline | n → p | c → w | Correct → hold | Wrong → hold |',
              '| --- | ---: | ---: | ---: | ---: |']
    for base, c in comparisons.items():
        lines.append(f"| {base} | {c['n_to_p']} | {c['c_to_w']} | {c['c_to_n']} | {c['w_to_n']} |")
    m1 = summaries['stress']['groups']['Recitals misspelled_M1']
    lines += ['', '## Medium and low items', '',
              f"**M-1:** remeasured all {m1['cases']} misspelled-recital cells: "
              f"r21 {m1.get('r21_raw_wrong', 0)} W, r24 {m1.get('r24_raw_wrong', 0)} W, "
              f"r25 {m1.get('r25_raw_wrong', 0)} W, r26 {m1.get('r26_raw_wrong', 0)} W. "
              'No separate spelling heuristic shipped. The same-page guard supplies any improvement shown. '
              f'Total remaining historical raw flags: {sum(raw.values())}. Any residual flags '
              'are restricted to the previously accepted classes and '
              'each complete result equals r21 except `analysis_version`. [Remaining flags](remaining-flags.json).', '',
              '**L-1:** the proposed explicit-company exemption was measured on all 576 exact NDA/exhibit '
              'cells. It has zero wrong placements there but creates **28 n → p** versus both r25 and cand5: '
              'seven each for personal guarantees, company guarantees, blank forms and joinders. '
              'It is rejected under the monotonic-hold bar; no broader safety claim is made for this '
              'unshipped candidate. [Candidate source](low-exemption-source.py.txt), '
              '[complete measurement](low-exemption-measurement.json).', '',
              '## Hold cost', '',
              '**Ordinary two-party NDAs with attached exhibits:** 504 cells, plus 72 no-exhibit controls. '
              'cand5 adds zero holds versus r25. The 42 correct → hold cost versus r24 remains '
              '(28 explicit-company and 14 domain-only signers). The exact generator corrects the '
              'review prose’s claimed 21 explicit-company cases. [Detailed hold cost](hold-cost.json).', '',
              '| Attached page (72 cells each) | r24 correct | r25 correct | r26 correct | New holds vs r25 |',
              '| --- | ---: | ---: | ---: | ---: |']
    for name, group in summaries['exhibits']['groups'].items():
        lines.append('| ' + name.removeprefix('exhibits ') + ' | ' + ' | '.join(str(group.get(k, 0)) for k in
                     ('r24_c', 'r25_c', 'r26_c', 'r25_to_r26_c_to_n')) + ' |')
    lines += ['', '**Three-party same-page controls:** 36 cells; six correct → hold versus r25 '
              '(four named third-party controls, two unnamed), leaving 12 correct / 24 hold and zero wrong. '
              'The 468-cell same-page Q3c layout adds ten correct → hold among matching controls while '
              'closing all 55 wrong placements. H-1’s 2,160 states are unchanged versus r25: '
              '774 correct / 1,386 hold.', '', '## Preservation and blockers', '',
              f'**{len(initial)-1:,}/{len(initial)-1:,} other originally tracked files are SHA-256 identical** '
              'to the starting inventory. This includes every earlier test, fixture, evidence file and '
              '`.done` marker. Only `placement.py` changed among existing files. The two test-tree '
              'additions are `placement_r26_review_cases.py` and `test_placement_r26.py`; their hashes '
              'are unchanged since the failing-first run. No staging, commit, migration/config change '
              'or memory write. [Preservation audit](preservation-summary.json).', '',
              '**Blocker: 20 full-suite failures.** Exact cand5 and the existing r13 placement requirements '
              'cannot both hold for the measured inputs. Resolving that policy conflict requires a changed '
              'guard requirement or changed test expectations; neither is authorized by this task. '
              'The review’s count discrepancies are disclosed above; the exact generator inventories '
              'were executed in full. [Release checks](release-bars.json).', '',
              'Replay commands are recorded in `run-provenance.json`. For reruns, use a fresh output '
              'directory: evidence writers open files exclusively and never replace earlier results.', '']
    with (OUT / 'results-r26.md').open('x') as stream:
        stream.write('\n'.join(lines))
    with (OUT / 'counterparty-c2a-r26.done').open('x') as stream:
        stream.write(f'coder rc=1 head={head}\n'
                     'failing-first: 62 failed, 2757 passed (55 Q3c, 7 real-worker failures); final new tests 2819 passed.\n'
                     'implemented, not release-ready: c2a.26 exact cand5 same-page guard; M-1 now 0/192 wrong; explicit-company exemption rejected (28 n->p).\n'
                     f'vs-live: {cells} cells; r25/r24/r21 n->p=0 c->w=0; accepted residual flags exact r21; seven goldens exact except analysis_version.\n'
                     'full-suite: 50454 passed, 20 failed, 0 errors, 0 skipped; completed without -x.\n'
                     'test changes: two new files, 2819 new IDs; all 47655 existing IDs preserved; existing tests/fixtures/evidence/.done hashes unchanged.\n'
                     'blocker: 20 immutable r13 L-2 controls require placed for three same-page non-witness blocks with scores [0],[0],[4]; exact cand5 must hold. Tests and guard were not weakened.\n'
                     'count corrections: exact Q3a=4536; same-page Q3c=468, including all 55 r25 wrong cells; exhibit cost is 28 explicit + 14 domain holds vs r24.\n')
    print(json.dumps(dict(rc=1, cells=cells, comparisons=comparisons, full_suite=counts,
                          remaining_flags=raw, blockers=blockers), indent=2))


if __name__ == '__main__':
    main()
