"""Check preservation, inventories and outcomes before writing the completion marker."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRODUCT = 'backend/dealroom_sign/placement.py'
PARTS = ('historical', 'review', 'layouts', 'wrapped', 'new', 'stress', 'q2', 'extra', 'workers')


def read(name):
    return json.loads((OUT / name).read_text())


def write(name, data):
    target = OUT / name
    assert not target.exists(), target
    target.write_text(json.dumps(data, indent=2) + '\n')


def xml_counts(path):
    counts, ids, families = Counter(), Counter(), defaultdict(Counter)
    for test in ET.parse(path).getroot().iter('testcase'):
        key = 'failed' if test.find('failure') is not None else 'errors' if test.find('error') is not None else 'skipped' if test.find('skipped') is not None else 'passed'
        counts[key] += 1
        ids[(test.attrib['classname'], test.attrib['name'])] += 1
        families[test.attrib['name'].split('[')[0]][key] += 1
    return dict(counts), ids, dict(families)


def cell(stats, version, part):
    wrong = stats.get(version + ('_raw_wrong' if part == 'stress' else '_wrong'), 0)
    placed = stats.get(version + '_placed', 0)
    if part not in {'q2', 'extra', 'workers'}:
        placed -= wrong
    return ' / '.join(str(n) for n in (wrong, placed, stats.get(version + '_holds', 0), stats.get(version + '_bare', 0)))


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    assert head == 'e2d7ba11e138da4f67fbb5562507985f19bde7f5'
    hashes = read('starting-hashes.json')
    changed = [p for p, h in hashes.items() if not (ROOT / p).is_file() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    production_hash = hashlib.sha256((ROOT / PRODUCT).read_bytes()).hexdigest()
    assert "VERSION = 'c2a.23'" in (ROOT / PRODUCT).read_text()
    summaries = {part: read(part + '-summary.json') for part in PARTS}
    for part, summary in summaries.items():
        assert summary['source_sha256']['r23'] == production_hash, part
        assert summary['external_http_calls'] == 0, part
        if part != 'stress':
            assert all(g['r23_wrong'] == 0 for g in summary['groups'].values()), part
        else:
            assert all(g['new_raw_wrong'] == 0 for g in summary['groups'].values())
    gold = summaries['historical']['groups']['Seven goldens']
    for v in ('r21', 'r22', 'r23'):
        assert gold[v + '_golden_diffs'] == gold[v + '_native_diffs'] == 0
    counts, ids, _ = xml_counts(OUT / 'full-suite.xml')
    old_counts, old_ids, _ = xml_counts(OUT.parent / 'c2a-r22/final-full-suite.xml')
    assert counts == {'passed': 31480}, counts
    assert not old_ids - ids
    assert sum((ids - old_ids).values()) == 7038
    first, _, first_families = xml_counts(OUT / 'failing-first.xml')
    supplement, _, _ = xml_counts(OUT / 'supplement-failing-first.xml')
    valid_first = Counter(supplement)
    for family, stats in first_families.items():
        if family != 'test_additional_conjunction_and_repeat_controls':
            valid_first.update(stats)
    assert valid_first == {'failed': 126, 'passed': 6912}, valid_first
    assert read('baseline-source.json')['production_unchanged']
    q2 = read('q2-cases.json')
    cohorts = {}
    for family, prefix, expected in [('B-1', 'b1_', 42), ('B-2', 'b2_', 24)]:
        cohort = [r for r in q2['cases'] if r['group'].startswith(prefix) and r['wrong']['r22']]
        assert len(cohort) == expected
        stats = Counter(cases=len(cohort))
        for row in cohort:
            for version in ('r21', 'r22', 'r23'):
                result = q2['outcomes'][row['results'][version]]
                key = 'wrong' if row['wrong'][version] else {'placed': 'placed', 'needs_sender': 'holds', 'bare': 'bare'}[result['status']]
                stats[version + '_' + key] += 1
        assert stats['r23_wrong'] == 0
        cohorts[family] = dict(stats)
    preserved = {'head': head, 'starting_files': len(hashes), 'unchanged_files': len(hashes)-1,
                 'changed_files': changed, 'index_changes': False, 'original_test_ids': sum(old_ids.values()),
                 'added_test_ids': sum((ids-old_ids).values()), 'full_suite': {**counts, 'failed': 0, 'errors': 0, 'skipped': 0},
                 'source_sha256': production_hash}
    assert all(rc == 0 for rc in read('replay-returncodes.json').values())
    assert sum(g['full_result_diffs'] for g in summaries['historical']['groups'].values()) == 0
    assert sum(g['full_result_diffs'] for g in summaries['review']['groups'].values()) == 0
    write('preservation-summary.json', preserved)
    write('family-comparison.json', summaries)
    write('blocking-cohorts.json', cohorts)
    write('failing-first-summary.json', {'final_input_totals': {'failed': 126, 'passed': 6912}, 'initial_run': first, 'initial_families': first_families,
                                       'final_supplement_inputs': supplement})
    m1 = summaries['stress']['groups']['Recitals misspelled_M1']['r23_raw_wrong']
    write('release-bars.json', {'passed': m1 == 0, 'required_review_classified_wrong': 0, 'golden_diffs': 0,
                              'external_http_calls': 0, 'carried_M1_wrong': m1,
                              'literal_all_families_zero_wrong': m1 == 0, **preserved})
    report = ['# C2a r23 results', '',
              '**The reviewer’s cand closes B-1/B-2: 0 wrong in all 5,280 Q2 cells, including all 42 + 24 r22 failures. Full Send suite: 31,480 passed, 0 failed, 0 errors, 0 skipped.**', '',
              f'Base HEAD `{head}`. `VERSION = \'c2a.23\'`. No staging or commit.', '',
              'The production change uses a completed-party-designation boundary in both the name and description groups, removes direct ROLE_DEF span suppression, and retains the r22 M-2 conflict hold unchanged. The exact candidate additionally exposed six explicit-company/THE RECIPIENT worker failures. A local-label role-alias veto now holds those cases without granting confidence or changing printed-name paths; the unchanged new tests demonstrate failing-first and final behavior. The description suffix vocabulary is unchanged; LLP remains a boundary designation, without broadening the description-name suffix list.', '',
              f'**Carried medium M-1 remains unresolved:** {m1} wrong misspelling cells in the 192-cell supplemental family, unchanged across r21/r22/r23. This is recorded under the request’s conditional medium-item measurement allowance. A literal zero-wrong bar covering that carried family is therefore **not met**. Accepted Competition/Q4/NORTHWIND raw-coordinate exceptions are also shown, without changing their historical classifications.', '',
              '## Failing first', '',
              'The complete Q2 discovery ran on unchanged r22 and reproduced exactly 42 B-1 and 24 B-2 wrong cells. The pytest run also exercises both verbatim inline real-worker reproductions, then expands them across three layouts, three headings, both signer sets, and domain-only/explicit-company signers.', '',
              '| Test family | Failed on r22 | Passed on r22 |', '| --- | ---: | ---: |']
    for family, stats in first_families.items():
        if family != 'test_additional_conjunction_and_repeat_controls':
            report.append(f'| {family} | {stats.get("failed", 0)} | {stats.get("passed", 0)} |')
    report += [f'| Supplemental conjunction/repeat controls (final inputs) | {supplement.get("failed", 0)} | {supplement.get("passed", 0)} |', '',
               'The first draft supplemental fixtures used Harbor Light signer/affiliate identities with Johnson/Procter recitals. During new-fixture construction these were corrected to matching company identities; the separate supplement-failing-first run records all 1,680 final supplemental inputs on unchanged r22. The first draft log is retained. No pre-existing test or fixture was touched.', '',
               'Final-input failing-first counts total 126 failed / 6,912 passed. The exact candidate then leaves six expanded worker failures; the added local-label veto passes all 80 focused worker/mapping checks. All 7,038 final new tests pass in the complete suite. New test-tree files: `placement_r23_review_cases.py` and `test_placement_r23.py`. The page/column/By–Date oracle is reused unchanged.', '',
               '## Blocking cohorts (subsets of Q2)', '',
               'Disjoint counts are **wrong / correctly placed / holds / bare** throughout.', '',
               '| Cohort | Cells | r21 | r22 | r23 |', '| --- | ---: | --- | --- | --- |']
    for family, stats in cohorts.items():
        report.append(f'| {family} | {stats["cases"]} | {cell(stats, "r21", "q2")} | {cell(stats, "r22", "q2")} | {cell(stats, "r23", "q2")} |')
    report += ['', '## Medium and low findings', '',
               'L-1’s Research and Development Center description is restored by the shipped boundary. The Q2 table records its exact placement/hold counts. Conflicting recitals and Brown and Company remain safe holds when identity is unresolved. M-1 is measured, not silently reclassified or repaired with speculative spelling equivalence.', '',
               '## Preservation and complete-suite evidence', '',
               f'SHA-256: **{len(hashes)-1}/{len(hashes)-1} original files unchanged**, excluding only the authorized production file. This includes every earlier test, fixture, c2a evidence file and .done marker. All 24,442 previous test IDs are present; no skips or deselections in the full suite. [Audit](preservation-summary.json), [starting hashes](starting-hashes.json), [full log](full-suite.txt), [JUnit](full-suite.xml).', '',
               'Seven r13 goldens are exact except analysis_version, in process and on the real worker; native fields are also exact. All historical baseline outcomes and case inventories are compared with the preserved r21 and r22 archives. Final r23 also has zero versionless result differences in all 17,204 historical and 12,760 review cells. HTTP calls are zero; only the pre-existing expected mocked model calls occur.', '',
               '## Per-family r21 → r22 → r23', '',
               'Historical required-family tables retain the reviewer’s accepted Competition and Q4 classifications. The 96 Competition and six Q4 raw flags are retained in the machine-readable case evidence. The stress table uses raw geometry flags, including the carried M-1 and the reviewer-approved NORTHWIND third-company cases. Q2, supplements and workers use raw geometry with no exceptions.', '']
    for part, summary in summaries.items():
        report += [f'### {part}', '', '| Family | Cells | r21 | r22 | r23 |', '| --- | ---: | --- | --- | --- |']
        for group, stats in summary['groups'].items():
            report.append(f'| {group} | {stats["cases"]} | {cell(stats, "r21", part)} | {cell(stats, "r22", part)} | {cell(stats, "r23", part)} |')
        report.append('')
    report += ['## Provenance and limits', '',
               'The reviewer’s stdin Q2 generator was not preserved. `placement_r23_review_cases.py` contains an explicit reconstruction of the 22 recitals and documented 5,280-cell axes; it reproduces the 42 + 24 r22 wrong-cell counts exactly. The reconstructed overall Q2 totals are r21 48/2584/2648, r22 66/2452/2762 and r23 0/2544/2736 (wrong/placed/holds). These differ from the review’s unpublished full-matrix totals; only the documented axes, literal worker cases, and 42 + 24 blocking counts are reproduced exactly. The inline worker inputs are verbatim. Additional Johnson and Johnson, Procter and Gamble Co., and repeated-definition variants are explicit repository fixtures. Nothing imports cases from /tmp.', '',
               'The existing r22 family generators and geometry oracles are reused without edits. Evidence commands and isolation are in [method.md](method.md). Per-cell results, source hashes, transitions and worker comparisons are in the JSON files alongside this report.', '',
               'B-1, B-2 and low L-1 are closed. The carried M-1 measurement prevents claiming literal zero wrong across every supplemental family; no existing assertion or evidence was changed to hide it.', '']
    (OUT / 'results-r23.md').write_text('\n'.join(report))
    # A nonzero marker reflects the literal all-family bar, despite the conditional M-1 allowance.
    rc = int(m1 != 0)
    (OUT / 'counterparty-c2a-r23.done').write_text(
        f'coder rc={rc} head={head}\n'
        'failing-first: final new inputs 126 failed/6912 passed on r22 (Q2 66, workers 42, mapping 6, supplement 12); Q2 is 42 B-1 + 24 B-2; exact cand leaves 6 worker failures, final focused 80/80 pass; draft logs retained\n'
        'shipped: reviewer cand; completed-designation boundary in name/description; ROLE_DEF suppression removed; M-2 hold retained; local-label alias veto closes 6 further worker failures; low L-1 restored; VERSION c2a.23\n'
        'full-suite: 31480 passed, 0 failed, 0 errors, 0 skipped; completed without -x, filtering or deselection\n'
        'test changes: 2 new files, 7038 new tests; all 24442 original IDs preserved; no existing test/fixture/evidence edits\n'
        f'preservation: {len(hashes)-1} original files hash-identical; only placement.py modified; no staging/commit\n'
        f'blockers: carried medium M-1 has {m1}/192 wrong cells unchanged across releases; literal all-family zero-wrong bar not met; review-classified required families and Q2 are zero wrong\n')
    print(json.dumps(preserved, indent=2))


if __name__ == '__main__':
    main()
