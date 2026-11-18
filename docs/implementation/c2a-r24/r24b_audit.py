"""Audit the shipped narrow revision and append the r24b result without rewriting evidence."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

from r24b_replay import PARTS

EVIDENCE = Path(__file__).resolve().parent
OUT = EVIDENCE / 'r24b'
ROOT = EVIDENCE.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
R22 = 'backend/dealroom_sign/tests/test_placement_r22.py'
R23 = 'backend/dealroom_sign/tests/test_placement_r23.py'
RESULT = 'docs/implementation/c2a-r24/results-r24.md'


def read(name):
    return json.loads((OUT / name).read_text())


def write(name, data):
    with (OUT / name).open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_results(path):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids = Counter()
    families = Counter()
    for test in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if test.find('failure') is not None else
                 'errors' if test.find('error') is not None else
                 'skipped' if test.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(test.attrib['classname'], test.attrib['name'])] += 1
        families[(test.attrib['classname'], test.attrib['name'].split('[')[0], state)] += 1
    return dict(counts), ids, families


def assignment(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.get_source_segment(source, node)


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    assert head == 'e2bbb7587f7ef100e1fb82fea825000ba6eac705'
    source = (ROOT / PRODUCT).read_bytes()
    source_hash = sha(ROOT / PRODUCT)
    assert source == (EVIDENCE / 'r24-source.py.txt').read_bytes()
    assert b"VERSION = 'c2a.24'" in source
    assert assignment(source.decode(), 'ROLE_DESCRIPTION_WIDE') == assignment(
        (EVIDENCE / 'r21-source.py.txt').read_text(), 'ROLE_DESCRIPTION').replace(
            'ROLE_DESCRIPTION =', 'ROLE_DESCRIPTION_WIDE =', 1)
    old22 = subprocess.check_output(['git', 'show', 'HEAD:' + R22], cwd=ROOT)
    new22 = (ROOT / R22).read_bytes()
    before, after = old22.splitlines(keepends=True), new22.splitlines(keepends=True)
    assert len(before) == len(after)
    assert [i + 1 for i, (a, b) in enumerate(zip(before, after)) if a != b] == [38]
    assert after[37] == b"    assert 'harbor light analytics' in roles['recipient'].lower() or roles['recipient'].strip().lower() == 'recipient', roles\n"
    assert before[38] == after[38] and before[40] == after[40]
    old23 = subprocess.check_output(['git', 'show', 'HEAD:' + R23], cwd=ROOT)
    assert (ROOT / R23).read_bytes() == old23.replace(
        b"('b1_three', 'Smith and Jones, Inc.')", b"('b1_three', 'Recipient')", 1)
    original = json.loads((EVIDENCE / 'starting-hashes.json').read_text())
    original_changes = [p for p, h in original.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    assert set(original_changes) == {PRODUCT, R22, R23}, original_changes
    session = read('starting-hashes.json')
    session_changes = [p for p, h in session.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    assert set(session_changes) == {PRODUCT, R22}, session_changes
    assert (ROOT / RESULT).read_bytes() == (OUT / 'results-r24-before.md').read_bytes()
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    provenance = read('run-provenance.json')
    assert source_hash == provenance['source_sha256']
    assert all(sha(ROOT / p) == h for p, h in provenance['test_hashes'].items())
    counts, ids, families = test_results(OUT / 'full-suite.xml')
    assert counts == dict(passed=40186, failed=0, errors=0, skipped=0), counts
    assert read('full-suite-returncode.json') == 0
    assert families[('dealroom_sign.tests.test_placement_r19', 'test_company_competition_uses_identity_before_vetoes', 'passed')] == 40
    assert families[('dealroom_sign.tests.test_placement_r22', 'test_recital_precedence_matrix', 'passed')] == 384
    _, old_ids, _ = test_results(EVIDENCE.parent / 'c2a-r23/full-suite.xml')
    old_id = ('dealroom_sign.tests.test_placement_r23', 'test_description_role_mapping[b1_three-Smith and Jones, Inc.]')
    new_id = (old_id[0], 'test_description_role_mapping[b1_three-Recipient]')
    old_ids[new_id] += old_ids.pop(old_id)
    assert sum(old_ids.values()) == 31480 and not old_ids - ids
    assert sum((ids - old_ids).values()) == 8706
    assert set(read('replay-returncodes.json')) == set((*PARTS, 'h1'))
    assert not any(read('replay-returncodes.json').values())
    summaries = {part: read(part + '-summary.json') for part in PARTS}
    for part, summary in {**summaries, 'h1': read('h1-summary.json')}.items():
        assert summary['source_sha256']['r24'] == source_hash
        assert summary['archive_results_exact'] and summary['external_http_calls'] == 0
        assert all(g['n_to_p'] == g['c_to_w'] == 0 for g in summary['groups'].values())
    cells = sum(s['cases'] for s in summaries.values())
    family_count = sum(len(s['groups']) for s in summaries.values())
    worker_count = sum(s['worker_evaluations'] for s in summaries.values())
    assert (cells, family_count, worker_count) == (59788, 229, 454)
    h1 = summaries['h1_review']['groups']['H1_REVIEW']
    assert (h1['r21_w'], h1.get('r24_w', 0), h1['r24_c'], h1['r24_n']) == (96, 0, 1170, 990)
    assert all(g.get('r24_w', 0) == 0 for g in read('h1-summary.json')['groups'].values())
    golden = summaries['historical']['groups']['Seven goldens']
    assert all(golden[name + '_golden_diffs'] == golden[name + '_native_diffs'] == 0 for name in ('r21', 'r24'))
    blocking = read('attack-cases.json')
    original_blocking = json.loads((EVIDENCE / 'attack-cases.json').read_text())
    expected = {(r['group'], r['case']): r for r in original_blocking['cases']}
    fixed = Counter()
    for row in blocking['cases']:
        if row['group'].startswith(('b1_', 'b2_')) and expected[(row['group'], row['case'])]['wrong']['r23']:
            assert blocking['outcomes'][row['results']['r24']]['status'] == 'needs_sender'
            fixed[row['group'][:2]] += 1
    assert fixed == {'b1': 120, 'b2': 42}
    raw = {part: {name: g['r24_raw_wrong'] for name, g in summary['groups'].items()
                  if g.get('r24_raw_wrong', 0)} for part, summary in summaries.items()}
    raw = {part: groups for part, groups in raw.items() if groups}
    assert raw == {
        'review': {'Competition': 96, 'Q4 M1 ambiguity': 6},
        'stress': {'Recitals northwind': 48, 'Recitals misspelled_M1': 48,
                   'Page probes nw_page2': 24, 'Page probes nw_section1': 24,
                   'Page probes the_recipient_page2': 12}}
    for part in raw:
        evidence = read(part + '-cases.json')
        for row in evidence['cases']:
            if row['raw_wrong']['r24']:
                assert row['raw_wrong']['r21']
                results = [dict(evidence['outcomes'][row['results'][name]]) for name in ('r21', 'r24')]
                for result in results:
                    result.pop('analysis_version')
                assert results[0] == results[1]
    patch_text = subprocess.check_output(['git', 'diff', '--', R22, R23], cwd=ROOT).decode()
    with (OUT / 'authorised-test-diffs.patch').open('x') as stream:
        stream.write(patch_text)
    preservation = dict(head=head, source_sha256=source_hash, variant='narrow', version='c2a.24',
                        original_files=len(original), original_unchanged=len(original) - 3,
                        original_changed=original_changes, session_files=len(session),
                        session_unchanged_after_report=len(session) - 3,
                        session_changed_after_report=[PRODUCT, R22, RESULT],
                        r22_changed_lines=[38], r22_lines_39_41_unchanged=True,
                        r23_exact_authorised_substitution=True, old_evidence_unchanged=True,
                        prior_result_prefix_unchanged=True, index_unchanged=True,
                        original_test_ids=31480, additional_test_ids=8706, full_suite=counts)
    write('preservation-summary.json', preservation)
    write('family-comparison.json', summaries)
    write('remaining-flags.json', raw)
    vs_live = dict(source_sha256=source_hash, version='c2a.24', variant='narrow',
                   cells=cells, families=family_count, worker_evaluations=worker_count,
                   n_to_p=0, c_to_w=0, diagnostic_h1_cells=2160,
                   diagnostic_h1_n_to_p=0, diagnostic_h1_c_to_w=0,
                   groups={part: {name: {key: g[key] for key in ('n_to_p', 'c_to_w', 'n_to_w', 'c_to_n')}
                                  for name, g in s['groups'].items()} for part, s in summaries.items()})
    write('vs-live.json', vs_live)
    blockers = ['The unchanged strict r24 M-1-only raw-zero bar still has 210 historical raw-coordinate flags beyond the carried 48-cell M-1 family; all are identical to live r21 except analysis_version.']
    bars = dict(rc=1, passed=False, variant='narrow', source_sha256=source_hash,
                full_suite=counts, full_suite_passed=True, n_to_p=0, c_to_w=0,
                H1_wrong=0, B1_wrong=0, B2_wrong=0, golden_diffs=0,
                preservation_passed=True, additional_raw_flags=210, carried_M1_wrong=48,
                blockers=blockers)
    write('release-bars.json', bars)
    report = [
        '', '## r24b — shipped narrow guard and authorised r22 assertion', '',
        f'HEAD `{head}`. Production is **narrow**, `VERSION = \'c2a.24\'`, '
        f'SHA-256 `{source_hash}`. It is byte-identical to the original `r24-source.py.txt` narrow snapshot. '
        'This section supersedes the earlier cand3 shipping selection and test blockers; all preceding r24 evidence remains unchanged.', '',
        '**Full Send suite: 40,186 passed, 0 failed, 0 errors, 0 skipped.** '
        'Completed without `-x`, test-selection filters or deselections. The immutable r19 competition family passes all 40 cells; '
        'the authorised r22 recital matrix passes all 384 cells. All 31,480 prior test IDs remain '
        '(allowing only the existing authorised r23 parameter-ID substitution), plus 8,706 r24 checks. '
        '[Log](r24b/full-suite.txt), [JUnit](r24b/full-suite.xml), [command and hashes](r24b/run-provenance.json).', '',
        'The company/domain-only cross-page guard now requires an unaccounted party-role label. '
        'The unchanged article-prefixed alias veto and printed-name path remain in place. '
        'The r21 wide description grammar is byte-identical apart from its variable name, contributes alongside the bounded grammar, '
        'and uses the unchanged M-2 conflict hold. Cand3 is removed from production.', '',
        '### Exact authorised test diffs', '',
        'Only r22 line 38 accepts either the HLA mapping or the literal role word `Recipient`; '
        'lines 39 and 41, and every other r22 byte, are unchanged. The standing r23 `b1_three` substitution is retained.', '',
        '```diff', patch_text.rstrip(), '```', '',
        '### Fresh vs-live replay', '',
        '**59,788 primary cells across 229 families: `n → p = 0`, `c → w = 0`.** '
        'The shipped `c2a.24` source and live r21 were independently parsed and scored anew; '
        '454 real-worker evaluations equal their in-process results. Every complete output equals its corresponding '
        'archived r24 narrow/r21 output, including analysis_version. Seven goldens and native fields match except analysis_version. '
        'External HTTP calls and new-case model calls are zero. '
        'The separate 2,160-cell diagnostic H-1 replay also has zero wrong placements and zero unsafe transitions. '
        '[Vs-live](r24b/vs-live.json), [per-family counts](r24b/family-comparison.json), [return codes](r24b/replay-returncodes.json).', '',
        'All 120 B-1 and 42 B-2 r23 wrong cells hold. Primary H-1 has 2,160 cells: live r21 96 wrong, '
        'r23 60 wrong, shipped narrow 0 wrong / 1,170 correct / 990 holds. The literal B-1/B-2 workers and '
        'separate uncaptioned H-1 worker pass. Frozen failing-first evidence remains 239 failed / 8,467 passed. '
        'Because the shipped source and every result match the archived narrow evidence exactly, the original '
        'cand comparison remains applicable: 489 additional holds for narrow versus 547 for cand3, preserving 58 correct placements. '
        'H-1 costs 228 additional holds under either candidate. The deleted reviewer-generator reconstruction limitation remains as documented.', '',
        '| Collection | Cells | n → p | c → w |',
        '| --- | ---: | ---: | ---: |']
    report += [f'| {part} | {s["cases"]:,} | 0 | 0 |' for part, s in summaries.items()]
    report += ['', '### Hash preservation and remaining bar', '',
               f'**{len(original) - 3:,}/{len(original) - 3:,} other originally tracked files are SHA-256 identical** '
               'to the r24 baseline; only placement.py and the two authorised tests differ. '
               f'**{len(session) - 3:,}/{len(session) - 3:,} other session-start files are SHA-256 identical**, '
               'including all prior r24 tests, fixtures, evidence and markers. The old RESULT is preserved byte for byte as the prefix '
               'of this appended report. No staging, commits, memory writes, fixture/oracle edits, skips or configuration changes. '
               '[Preservation audit](r24b/preservation-summary.json).', '',
               '**coder rc=1 for the unchanged literal r24 raw-zero bar.** The two test blockers are resolved. '
               'The remaining blocker is the same 210 historical raw-coordinate flags beyond the carried 48-cell M-1 family. '
               'They are byte-equivalent in result to live r21 after removing analysis_version; neither authorised test edit '
               'changes their classification. The older Competition/Q4 classifications and raw flags are both retained. '
               '[Release bars](r24b/release-bars.json), [raw flags](r24b/remaining-flags.json).', '',
               '| Raw family | Cells |', '| --- | ---: |']
    report += [f'| {part}: {name} | {count} |' for part, groups in raw.items() for name, count in groups.items()]
    report += ['', 'Reproduction: use the exact full-suite command in `r24b/run-provenance.json`; '
               'the new comparison runner is `r24b_replay.py all` (the output directory must be fresh, because existing evidence is never overwritten).', '']
    with (ROOT / RESULT).open('a') as stream:
        stream.write('\n'.join(report))
    changed = [p for p, h in session.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    assert set(changed) == {PRODUCT, R22, RESULT}, changed
    assert (ROOT / RESULT).read_bytes().startswith((OUT / 'results-r24-before.md').read_bytes())
    done = [f'coder rc=1 head={head}',
            'what changed: production restored to exact narrow H-1 guard; cand3 removed; VERSION c2a.24; r22 line 38 accepts HLA or literal Recipient; standing r23 b1_three edit retained',
            f'shipped source sha256={source_hash}; exact match to original r24-source.py.txt',
            'exact test diffs:', patch_text.rstrip(),
            'vs-live: fresh 59788 primary cells / 229 families; n -> p = 0; c -> w = 0; 454 real-worker evaluations; 2160 diagnostic H-1 cells also zero wrong and zero unsafe transitions; seven goldens/native fields exact except analysis_version',
            'full-suite: 40186 passed, 0 failed, 0 errors, 0 skipped; completed without -x or selection filters; r19 competition 40/40; r22 recital matrix 384/384; 31480 original test IDs plus 8706 r24 tests',
            f'preservation: {len(original)-3} other original tracked files and {len(session)-3} other session-start files SHA-256 identical; old RESULT prefix preserved; all earlier evidence/fixtures/markers unchanged; index unchanged; no commit',
            'blockers: ' + blockers[0],
            'results: docs/implementation/c2a-r24/results-r24.md (r24b section); fresh artifacts in docs/implementation/c2a-r24/r24b/', '']
    with (EVIDENCE / 'counterparty-c2a-r24b.done').open('x') as stream:
        stream.write('\n'.join(done))
    print(json.dumps(bars, indent=2))


if __name__ == '__main__':
    main()
