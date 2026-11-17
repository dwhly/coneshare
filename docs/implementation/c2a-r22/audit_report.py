"""Verify release bars, preserve all baseline files, then write the final report."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRODUCT = 'backend/dealroom_sign/placement.py'
PARTS = ('historical', 'review', 'layouts', 'wrapped', 'new')


def write(name, data):
    path = OUT / name
    assert not path.exists(), path
    path.write_text(json.dumps(data, indent=2) + '\n')


def xml_counts(path):
    root = ET.parse(path).getroot()
    tests = list(root.iter('testcase'))
    counts = {'tests': len(tests), 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    ids = Counter()
    for test in tests:
        ids[(test.attrib['classname'], test.attrib['name'])] += 1
        key = ('failed' if test.find('failure') is not None else 'errors' if test.find('error') is not None
               else 'skipped' if test.find('skipped') is not None else 'passed')
        counts[key] += 1
    return counts, ids


def cell(group, variant, raw=False):
    return ' / '.join(str(group.get(variant + '_' + key, 0))
                      for key in [('raw_wrong' if raw else 'wrong'), 'placed', 'holds', 'bare'])


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    assert head == 'afb9aa6e71a28f3989c9896e0318912a11572891'
    hashes = json.loads((OUT / 'starting-hashes.json').read_text())
    changed = [p for p, digest in hashes.items()
               if not (ROOT / p).is_file() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    production_hash = hashlib.sha256((ROOT / PRODUCT).read_bytes()).hexdigest()
    assert "VERSION = 'c2a.22'" in (ROOT / PRODUCT).read_text()
    summaries = {part: json.loads((OUT / (part + '-summary.json')).read_text()) for part in PARTS}
    stress = json.loads((OUT / 'stress-summary.json').read_text())
    for part, summary in summaries.items():
        assert summary['external_http_calls'] == 0
        assert summary['source_sha256']['r22'] == production_hash
        assert all(g['r22_wrong'] == 0 for g in summary['groups'].values()), part
    assert stress['source_sha256']['r22'] == production_hash
    assert stress['external_http_calls'] == 0
    assert all(g['new_raw_wrong'] == 0 for g in stress['groups'].values())
    assert stress['groups']['M2 36 failing probes']['r21_raw_wrong'] == 36
    assert stress['groups']['M2 36 failing probes']['r22_raw_wrong'] == 0
    assert stress['groups']['M2 36 failing probes']['r22_holds'] == 36
    goldens = summaries['historical']['groups']['Seven goldens']
    assert goldens['r22_golden_diffs'] == goldens['r22_native_diffs'] == 0
    counts, ids = xml_counts(OUT / 'final-full-suite.xml')
    old_counts, old_ids = xml_counts(OUT.parent / 'c2a-r21/r21b-final-full-suite.xml')
    assert counts == {'tests': 24442, 'passed': 24442, 'failed': 0, 'errors': 0, 'skipped': 0}, counts
    assert not old_ids - ids, list((old_ids - ids).items())[:5]
    assert sum((ids - old_ids).values()) == 462
    assert '24442 passed' in (OUT / 'final-full-suite.txt').read_text()
    preserved = {'starting_files': len(hashes), 'unchanged_files': len(hashes) - 1,
                 'changed_files': changed, 'head': head, 'index_changes': False,
                 'original_test_ids': old_counts['tests'], 'preserved_original_ids': sum(old_ids.values()),
                 'added_test_ids': 462, 'full_suite': counts, 'source_sha256': production_hash}
    write('preservation-summary.json', preserved)
    write('family-comparison.json', {**summaries, 'stress': stress})
    write('release-bars.json', {'passed': True, **preserved,
          'required_family_cases': sum(s['cases'] for s in summaries.values()) + 90,
          'required_wrong': 0, 'golden_diffs': 0, 'native_golden_diffs': 0,
          'external_http_calls': 0, 'stress_new_raw_wrong': 0,
          'known_m1_raw_wrong': stress['groups']['Recitals misspelled_M1']['r22_raw_wrong']})
    initial, _ = xml_counts(OUT / 'failing-first.xml')
    probes, _ = xml_counts(OUT / 'probes-failing-first.xml')
    report = [
        '# C2a r22 results', '',
        '**PASS for the requested M-2/L-1 release bars: 24,442 passed, 0 failed, 0 errors, 0 skipped.**', '',
        f'Base HEAD `{head}`; production `VERSION = \'c2a.22\'`. No commit or index changes.', '',
        'M-2 ships as the reviewer’s measured conflict guard. A role defined as dissimilar companies becomes the role word, so the existing unnamed-block/domain-only rule holds. L-1 ships with direct-definition precedence at the same quoted-role occurrence and a conjunction boundary on both the description and company capture. Independent conflicting definitions remain conflicts.', '',
        'All required preserved r21 families and the new conflict/L-1 families have **0 wrong** under the unchanged review classifications. Seven goldens and their native fields are exact except `analysis_version`; golden worker results equal in-process results. Every r21 replay result equals its archived r21 result, with exactly the same archived case inventory. External HTTP calls: **0**. Expected mocked model calls only.', '',
        'The review’s existing Competition and Q4 exceptions are unchanged: Competition retains 96 accepted raw coordinate flags for the printed-other-person cases; Q4 retains its six named-company ambiguity flags. The supplemental recital sweep also retains the carried M-1 misspelling issue. Those observations are shown explicitly below, not presented as newly resolved.', '',
        '## Failing first and test preservation', '',
        '| Run | Failed on r21 | Passed on r21 | Final passed |',
        '| --- | ---: | ---: | ---: |',
        '| Initial r22 regressions | 414 | 12 | 426 |',
        '| Additional 36 conflict probes | 36 | 0 | 36 |', '',
        'The initial failures include both verbatim HLA+NORTHWIND real-worker reproductions, 24 wrong cells among 36 affiliate/layout controls, all 384 recital mapping checks, two conjunction-boundary checks, and two repeated-definition checks. The separate 36-probe file fails all 36 exact-r21 cases and passes all 36 r22 cases; these become holds. Tests use the existing page/column/By–Date oracle unchanged.', '',
        'Three test-tree files were added: `placement_r22_review_cases.py`, `test_placement_r22.py`, and `test_placement_r22_conflict_probes.py` (462 new tests). All 23,980 previous test IDs remain in the complete suite. No test, fixture, assertion, expectation, skip, or earlier evidence file was changed, deleted, weakened, or retargeted.', '',
        f'SHA-256 verification: **{len(hashes) - 1}/{len(hashes) - 1}** original files unchanged apart from the authorized production file. This includes earlier `docs/implementation/c2a-r*/` evidence and `.done` markers. See [preservation audit](preservation-summary.json) and [starting hashes](starting-hashes.json).', '',
        'The final full-suite invocation covers all `dealroom_sign/tests`, without `-x`, filtering or deselection. [Full log](final-full-suite.txt), [JUnit](final-full-suite.xml). The early interrupted `full-suite.txt` is draft evidence only; the complete run includes the later 36-probe addition.', '',
        '## L-1 recovery and limits', '',
        'In the documented 384-cell reconstruction, r21 and the conflict-only variant hold all 384. r22 has **0 wrong / 36 placed / 348 holds**. It recovers **28 of r20’s 32 correct placements**, plus eight r20 holds. Four r20-correct cells still hold with the Fleet company line absent and a separate guarantor block: the existing document-wide ambiguity guard remains binding. No guard was relaxed to force these four placements.', '',
        'The review says its generators ran from stdin and does not preserve them. The exact worker reproduction is verbatim; the new 36-, 384-, 2,112-, and 504-cell sweeps are explicit reconstructions of the documented shapes and axes. Their source and per-cell outcomes are retained. The original r21 family generators are reused unchanged. See [method and commands](method.md).', '',
        '## Per-family r21 → r22', '',
        'Cells are **wrong / placed / holds / bare**; “placed” includes any raw flags accepted by the existing reviewer classifications. Subsets and supplemental stress sweeps are identified separately.', '',
    ]
    for part in PARTS:
        report += [f'### {part}', '', '| Family | Cases | r21 | r22 |', '| --- | ---: | --- | --- |']
        for group, stats in summaries[part]['groups'].items():
            report.append(f'| {group} | {stats["cases"]} | {cell(stats, "r21")} | {cell(stats, "r22")} |')
        report.append('')
    report += ['## Supplemental reviewer-shape stress sweep', '',
               'These cells report **raw coordinate flags / placed / holds / bare**. NORTHWIND flags are the reviewer’s explicitly ruled-correct third-company shape. Misspelled-company flags are carried M-1, outside this M-2/L-1 change. No raw flag is newly introduced. All conflict and description rows have zero r22 raw flags.', '',
               '| Family | Cases | r21 raw | r22 raw |', '| --- | ---: | --- | --- |']
    for group, stats in stress['groups'].items():
        report.append(f'| {group} | {stats["cases"]} | {cell(stats, "r21", True)} | {cell(stats, "r22", True)} |')
    report += ['', '## Evidence', '',
               'Each `*-summary.json` reports family counts, transitions, source hashes, HTTP calls and worker comparisons. Each `*-cases.json` retains per-cell outcomes, including raw flags. [Combined family results](family-comparison.json), [release bars](release-bars.json), [goldens](placements.json).', '',
               'No release-bar blocker remains. The limitations are the unpublished reviewer scratch generators, four retained safe L-1 holds, and the explicitly carried M-1 misspelling issue. No earlier test or evidence file was altered to satisfy the bars.', '']
    target = OUT / 'results-r22.md'
    assert not target.exists()
    target.write_text('\n'.join(report))
    # The completion marker is deliberately last.
    marker = OUT / 'counterparty-c2a-r22.done'
    assert not marker.exists()
    marker.write_text(f'coder rc=0 head={head}\n'
                      'failing-first: 414 failed/12 passed initial; 36 failed/0 passed additional conflict probes; final 462/462 new tests pass\n'
                      'shipped: measured M-2 conflict hold; L-1 direct-definition precedence and bounded company/description; VERSION c2a.22\n'
                      'full-suite: 24442 passed, 0 failed, 0 errors, 0 skipped; no -x, filtering or deselections\n'
                      'test changes: 3 new files, 462 added tests; all 23980 original test IDs retained; no existing test/fixture/evidence edits\n'
                      f'preservation: {len(hashes)-1} original files hash-identical; only placement.py changed; no commit/index changes\n'
                      'validation: all required families 0 wrong under unchanged review classifications; seven goldens exact except analysis_version\n'
                      'blockers: none for requested release bars; exact stdin generators unavailable (reconstructions recorded); 4 L-1 safe holds retained; carried M-1 unchanged\n')
    print(json.dumps(preserved, indent=2))


if __name__ == '__main__':
    main()
