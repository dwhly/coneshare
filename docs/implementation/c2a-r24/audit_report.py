"""Verify immutable inputs, completed tests, source identity and cell transitions."""
import ast
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
EXCEPTION = 'backend/dealroom_sign/tests/test_placement_r23.py'
PARTS = ('historical', 'review', 'layouts', 'wrapped', 'new', 'stress', 'q2',
         'extra', 'workers', 'attack', 'boundary', 'h1_review', 'veto', 'workers24',
         'workers_h1_uncaptioned')


def read(name):
    return json.loads((OUT / name).read_text())


def write(name, data):
    target = OUT / name
    assert not target.exists(), target
    target.write_text(json.dumps(data, indent=2) + '\n')


def tests(path):
    counts, ids = Counter(), Counter()
    for test in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if test.find('failure') is not None else
                 'errors' if test.find('error') is not None else
                 'skipped' if test.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(test.attrib['classname'], test.attrib['name'])] += 1
    return dict(counts), ids


def cell(stats, version):
    return ' / '.join(str(stats.get(version + '_' + key, 0)) for key in ('w', 'c', 'n', 'b'))


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    assert head == 'e2bbb7587f7ef100e1fb82fea825000ba6eac705'
    hashes = read('starting-hashes.json')
    changed = [p for p, h in hashes.items() if not (ROOT / p).is_file()
               or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    assert set(changed) == {PRODUCT, EXCEPTION}, changed
    old_test = subprocess.check_output(['git', 'show', head + ':' + EXCEPTION], cwd=ROOT)
    assert (ROOT / EXCEPTION).read_bytes() == old_test.replace(
        b"('b1_three', 'Smith and Jones, Inc.')", b"('b1_three', 'Recipient')", 1)
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    source = (ROOT / PRODUCT).read_bytes()
    assert source == (OUT / 'fallback-source.py.txt').read_bytes()
    assert source == (OUT / 'cand3-source.py.txt').read_bytes().replace(
        b"VERSION = 'c2a.23'", b"VERSION = 'c2a.24'", 1)
    assert b"VERSION = 'c2a.24'" in source
    source_hash = hashlib.sha256(source).hexdigest()
    r21 = (OUT / 'r21-source.py.txt').read_text()

    def assignment(text, name):
        tree = ast.parse(text)
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
        return ast.get_source_segment(text, node)

    assert assignment(source.decode(), 'ROLE_DESCRIPTION_WIDE') == assignment(
        r21, 'ROLE_DESCRIPTION').replace('ROLE_DESCRIPTION =', 'ROLE_DESCRIPTION_WIDE =', 1)
    measured = {part: read(part + '-summary.json') for part in PARTS}
    summaries = copy.deepcopy(measured)
    # Original evidence calls the narrow candidate r24. Final r24 uses cand3;
    # preserve those raw files and explicitly map the measured variant here.
    for summary in summaries.values():
        assert summary['source_sha256']['cand3'] == hashlib.sha256(
            (OUT / 'cand3-source.py.txt').read_bytes()).hexdigest()
        assert summary['source_sha256']['r24'] == hashlib.sha256(
            (OUT / 'r24-source.py.txt').read_bytes()).hexdigest()
        summary['source_sha256']['narrow'] = summary['source_sha256']['r24']
        summary['source_sha256']['r24'] = source_hash
        summary['final_variant'] = 'cand3, with analysis_version c2a.24'
        summary['candidate_transitions'] = summary.pop('transitions')
        summary['candidate_transition_order'] = ['r21', 'r23', 'cand', 'cand3', 'narrow']
        summary['transitions'] = {}
        for group, transitions in summary['candidate_transitions'].items():
            final = Counter()
            for states, count in transitions.items():
                values = states.split(' -> ')
                final[' -> '.join(values[i] for i in (0, 1, 3))] += count
            summary['transitions'][group] = dict(final)
        for g in summary['groups'].values():
            g.update({'narrow_' + k[4:]: v for k,v in list(g.items()) if k.startswith('r24_')})
            for k in list(g):
                if k.startswith('r24_'):
                    del g[k]
            g.update({'r24_' + k[6:]: v for k,v in list(g.items()) if k.startswith('cand3_')})
    assert all(rc == 0 for rc in read('complete-measure-returncodes.json').values())
    h1 = summaries['h1_review']['groups']['H1_REVIEW']
    assert (h1['r21_w'], h1['r23_w'], h1.get('r24_w', 0), h1['r23_c'],
            h1['r23_n'], h1['r24_cand_c_to_n']) == (96, 60, 0, 1398, 702, 228)
    diagnostic = read('h1-summary.json')
    assert all(g.get('r24_n_to_p', 0) == g.get('r24_c_to_w', 0) == g.get('r24_w', 0) == 0
               for g in diagnostic['groups'].values())
    for part, summary in summaries.items():
        assert summary['source_sha256']['r24'] == source_hash, part
        assert summary['external_http_calls'] == 0, part
        assert all(g.get('r24_n_to_p', 0) == g.get('r24_c_to_w', 0) == 0
                   for g in summary['groups'].values()), part
    golden = summaries['historical']['groups']['Seven goldens']
    assert all(golden[v + '_golden_diffs'] == golden[v + '_native_diffs'] == 0
               for v in ('r21', 'r23', 'cand', 'cand3', 'r24'))
    counts, ids = tests(OUT / 'fallback-full-suite.xml')
    failures = Counter()
    for test in ET.parse(OUT / 'fallback-full-suite.xml').getroot().iter('testcase'):
        if test.find('failure') is not None or test.find('error') is not None:
            failures[test.attrib['classname'] + '::' + test.attrib['name'].split('[')[0]] += 1
    narrow_counts, narrow_ids = tests(OUT / 'full-suite.xml')
    assert ids == narrow_ids
    provenance = read('fallback-suite-provenance.json')
    assert provenance['source_sha256'] == source_hash and provenance['scratch_removed']
    assert provenance['returncode'] == int(bool(counts.get('failed') or counts.get('errors')))
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
               for p,h in provenance['test_hashes'].items())
    old_counts, old_ids = tests(OUT.parent / 'c2a-r23/full-suite.xml')
    old_id = ('dealroom_sign.tests.test_placement_r23',
              'test_description_role_mapping[b1_three-Smith and Jones, Inc.]')
    new_id = (old_id[0], 'test_description_role_mapping[b1_three-Recipient]')
    assert old_ids[old_id] == ids[new_id] == 1
    old_ids[new_id] += old_ids.pop(old_id)
    assert not old_ids - ids, old_ids - ids
    assert sum((ids - old_ids).values()) == 8706
    assert sum(ids.values()) == 40186
    first = read('failing-first-summary.json')
    assert first['counts'] == {'failed': 239, 'passed': 8467}
    assert first['production_unchanged']
    for family, expected in [('b1_', 120), ('b2_', 42)]:
        groups = [g for n,g in summaries['attack']['groups'].items() if n.startswith(family)]
        assert sum(g['r23_w'] for g in groups) == expected
        assert sum(g.get('r24_w', 0) for g in groups) == 0
    blocking = read('attack-cases.json')
    for row in blocking['cases']:
        if row['group'].startswith(('b1_', 'b2_')) and row['wrong']['r23']:
            assert blocking['outcomes'][row['results']['cand3']]['status'] == 'needs_sender'
    # Preserve both historical classifications and every raw coordinate flag.
    raw_flags = {part: {n: g['r24_raw_wrong'] for n,g in summary['groups'].items()
                       if g.get('r24_raw_wrong', 0)} for part,summary in summaries.items()}
    raw_flags = {part: groups for part,groups in raw_flags.items() if groups}
    classified = {part: {n: g['r24_w'] for n,g in summary['groups'].items()
                        if g.get('r24_w', 0)} for part,summary in summaries.items()}
    classified = {part: groups for part,groups in classified.items() if groups}
    m1 = summaries['stress']['groups']['Recitals misspelled_M1']
    assert m1['r21_w'] == m1['r23_w'] == m1['r24_w'] == 48
    for part in ('review', 'stress'):
        evidence = read(part + '-cases.json')
        for row in evidence['cases']:
            assert all(not row['raw_wrong'][v] or row['raw_wrong']['r21']
                       for v in ('r24', 'cand3')), (part, row['case'])
            if row['raw_wrong']['r24'] or row['raw_wrong']['cand3'] or row['group'] == 'Recitals misspelled_M1':
                results = []
                for version in ('r21', 'r23', 'cand', 'cand3', 'r24'):
                    result = dict(evidence['outcomes'][row['results'][version]])
                    result.pop('analysis_version', None)
                    results.append(result)
                assert all(result == results[0] for result in results), (part, row['case'])
    preservation = dict(head=head, starting_files=len(hashes), unchanged_files=len(hashes)-2,
                        changed_files=changed, authorised_expectation_exact=True,
                        original_test_ids=31480, added_test_ids=8706,
                        full_suite={**dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0), **counts},
                        narrow_full_suite=narrow_counts, final_variant='cand3',
                        source_sha256=source_hash, wide_assignment_byte_identical=True,
                        index_changes=False)
    write('preservation-summary.json', preservation)
    write('full-suite-failures.json', dict(failures))
    write('family-comparison.json', summaries)
    write('final-source-mapping.json', dict(measured_variant='cand3',
          measured_source_sha256=hashlib.sha256((OUT / 'cand3-source.py.txt').read_bytes()).hexdigest(),
          final_source_sha256=source_hash, difference="VERSION = 'c2a.23' -> 'c2a.24' only",
          original_evidence_r24_key='narrow candidate; final-family tables use cand3'))
    write('remaining-flags.json', dict(raw=raw_flags, classified=classified))
    write('vs-live.json', {part: {name: {k: g.get('r24_' + k, 0) for k in
                                         ('n_to_p', 'c_to_w', 'n_to_w', 'c_to_n')}
                                 for name,g in summary['groups'].items()}
                          for part,summary in summaries.items()})
    patch_text = subprocess.check_output(['git', 'diff', '--', EXCEPTION], cwd=ROOT).decode()
    (OUT / 'authorised-expectation.patch').write_text(patch_text)
    total_cases = sum(s['cases'] for s in summaries.values())
    total_groups = sum(len(s['groups']) for s in summaries.values())
    total_workers = sum(s['worker_evaluations'] for s in summaries.values())
    extra_holds = {v: sum(g.get(v + '_cand_c_to_n', 0) for s in summaries.values()
                         for g in s['groups'].values()) for v in ('cand3', 'narrow')}
    non_m1_raw = sum(sum(g.values()) for g in raw_flags.values()) - 48
    bars = dict(passed=False, rc=1, full_suite=preservation['full_suite'],
                full_suite_passed=counts == {'passed': 40186},
                cases=total_cases, families=total_groups, worker_evaluations=total_workers,
                n_to_p=0, c_to_w=0, golden_diffs=0, preservation_passed=True,
                carried_M1_wrong=48, additional_raw_flags=non_m1_raw,
                reviewer_H1_totals_reproduced=True, H1_cells=2160, H1_wrong=0,
                reviewer_H1_generator_available=False, additional_holds_vs_cand=extra_holds,
                candidate='cand3 fallback; not release-certified',
                blockers=['The strict M-1-only raw-zero bar retains 210 historical raw flags; both candidates retain them unchanged.'])
    if counts != {'passed': 40186}:
        bars['blockers'].append('The completed full suite did not meet the zero-failure/error/skip bar.')
    if failures.get('dealroom_sign.tests.test_placement_r22::test_recital_precedence_matrix'):
        bars['blockers'].insert(0, 'The required cand returns Recipient on disagreement, but 384 immutable r22 recital-precedence assertions require Harbor Light Analytics. Only the r23 b1_three expectation was authorised to change.')
    if failures.get('dealroom_sign.tests.test_placement_r19::test_company_competition_uses_identity_before_vetoes'):
        bars['blockers'].insert(1, 'The cand3 fallback returns score 0 across pages, but 20 immutable r19 controls require score 4. The narrow guard passes those controls.')
    bars['failed_test_families'] = dict(failures)
    write('release-bars.json', bars)
    report = ['# C2a r24 results', '',
              'The reviewer’s cand3 fallback (cand plus document-wide company competition) is implemented as `c2a.24`.', '',
              f'Base HEAD `{head}`; live r21 `afb9aa6e`. No staging or commit.', '',
              '**coder rc=1: the literal release bar is not certified.** '
              'The required cand conflicts with 384 immutable r22 recital-precedence assertions. '
              'The cand3 fallback also conflicts with 20 immutable r19 cross-page score assertions. '
              'Additionally, 210 historical raw flags beyond M-1 remain under both candidates. '
              '[Release bars](release-bars.json).', '',
              'The nine blocking cohorts reproduce exactly 120 B-1 and 42 B-2 wrong cells on r23. '
              'All 162 hold under r24. Both literal B-1/B-2 workers, with PAT and DAN+PAT, are safe. '
              'The separate uncaptioned H-1 worker also changes wrong → hold.', '',
              f'Full Send suite: {counts.get("passed", 0):,} passed, {counts.get("failed", 0)} failed, '
              f'{counts.get("errors", 0)} errors, {counts.get("skipped", 0)} skipped. '
              'It completed without `-x` or selection filters. [Final log](fallback-full-suite.txt), [Final JUnit](fallback-full-suite.xml). '
              f'The separately completed narrow-candidate suite recorded {narrow_counts}. '
              '[Narrow log](full-suite.txt), [Narrow JUnit](full-suite.xml).', '',
              'Failing first: **239 failed / 8,467 passed** on unchanged r23. '
              'This comprises 162 blocking recital failures, 18 boundary fixture flags, 54 reconstructed '
              'H-1 failures, four B-1/B-2 worker failures, and one uncaptioned H-1 worker failure. '
              '[Counts](failing-first-summary.json).', '',
              '## Immutable-test blocker', '',
              'All 384 parameters of `test_placement_r22.py::test_recital_precedence_matrix` '
              'assert that `roles["recipient"]` contains `harbor light analytics`. Their recital is '
              '`between Fleet Test Co., a Delaware corporation, and Harbor Light Analytics, Inc., '
              'a Delaware corporation ("Recipient")`. The bounded grammar contributes HLA; the '
              'required byte-identical r21 grammar contributes Fleet. The required unchanged M-2 '
              'guard therefore returns `Recipient`, violating that old assertion while retaining a safe hold.', '',
              'The sole authorised exception concerns r23 `b1_three`, so the r22 assertion is '
              'preserved. Neither cand3 nor the narrow page guard changes recital extraction. '
              'Satisfying both the exact cand semantics and this immutable role-name expectation '
              'requires resolving the conflicting requirements. No assertion, fixture, skip or '
              'oracle was changed to hide the conflict. [Exact grammar contributions](immutable-test-conflict.json), '
              '[completed-suite failure families](full-suite-failures.json).', '',
              'The broad fallback additionally returns score 0 for a matching heading on another page, '
              'where 20 r19 `test_company_competition_uses_identity_before_vetoes` parameters explicitly '
              'require 4. Running the original 40 score assertions unchanged across all five sources '
              'gives 40 passed for r21/r23/cand/narrow and 20 passed / 20 failed for cand3. '
              'These are safer holds, but the existing assertions are outside the authorised exception. '
              '[Score-assertion evidence](fallback-test-conflict.json).', '',
              '## What changed', '',
              '`ROLE_DESCRIPTION_WIDE` is byte-identical to r21’s entire `ROLE_DESCRIPTION` assignment '
              'apart from its variable name. It contributes alongside the bounded grammar and direct definitions. '
              'The existing M-2 conflict guard retains the role word on disagreement.', '',
              'Both guards were measured. The narrow candidate enables cross-page matching-heading '
              'competition only when the document contains an unaccounted party-role label. It retains '
              'historical raw flags beyond M-1, so it cannot satisfy the literal zero-wrong condition. '
              'The requested cand3 fallback is selected: company/domain-only matching headings compete '
              'across pages without that condition. Both candidates retain the article-prefixed alias '
              'veto and printed-name path. The fallback also retains those old flags; it is not release-certified.', '',
              'Per-cell evidence retains its original labels: `r24` means the measured narrow candidate '
              'there, and `cand3` means the final choice. The report and `family-comparison.json` map '
              'final r24 to cand3 explicitly. The final source differs from the measured cand3 only '
              'in VERSION. [Source mapping](final-source-mapping.json).', '',
              '## Narrow guard versus cand3', '',
              '| Family | Cells | cand W / correct / hold / bare | cand3 (final r24) W / correct / hold / bare | narrow W / correct / hold / bare | cand3 additional holds | narrow additional holds |',
              '| --- | ---: | --- | --- | --- | ---: | ---: |']
    for part,summary in summaries.items():
        for name,g in summary['groups'].items():
            if g.get('cand3_cand_c_to_n', 0) or g.get('narrow_cand_c_to_n', 0) or part == 'h1_review':
                report.append(f'| {part}: {name} | {g["cases"]} | {cell(g,"cand")} | {cell(g,"cand3")} | {cell(g,"narrow")} | {g.get("cand3_cand_c_to_n",0)} | {g.get("narrow_cand_c_to_n",0)} |')
    report += ['', '## Preservation and goldens', '',
               f'**{len(hashes)-2:,}/{len(hashes)-2:,} other original files are SHA-256 identical.** '
               'Every earlier fixture, evidence file and .done marker is preserved. '
               'All 31,480 existing test IDs remain, accounting for the single authorised parameter-ID change. '
               'Two new test-tree files add 8,706 checks. [Audit](preservation-summary.json).', '',
               'Seven goldens and native fields match exactly except analysis_version, in-process and on '
               'real workers, for all five sources. Historical case inventories and r21/r23 outputs '
               'match their archived evidence. HTTP calls: zero. New-case model calls: zero.', '',
               'The only existing test edit is:', '', '```diff', patch_text.rstrip(), '```', '',
               '## Per-family comparison and no-regression check', '',
               'Each cell is **wrong / correct placement / hold / bare**. '
               '`n → p` counts a live-r21 hold becoming any placement (including a wrong one). '
               '`c → w` counts a live-r21 correct placement becoming wrong. '
               'Both are zero in every measured family. Historical Competition/Q4 classifications are '
               'shown as preserved by their original harness; all raw flags are separately disclosed below. '
               'Stress rows use the raw geometry oracle without exceptions.', '']
    report += [f'**{total_cases:,} primary cells / {total_groups} family rows / {total_workers:,} real-worker '
               f'evaluations.** Additional holds relative to cand: cand3 {extra_holds["cand3"]}, '
               f'narrow candidate {extra_holds["narrow"]}. The narrow guard preserves '
               f'{extra_holds["cand3"]-extra_holds["narrow"]} correct placements that cand3 holds.', '']
    for part,summary in summaries.items():
        report += [f'### {part}', '', '| Family | Cells | r21 | r23 | r24 | n → p | c → w |',
                   '| --- | ---: | --- | --- | --- | ---: | ---: |']
        for name,g in summary['groups'].items():
            report.append(f'| {name} | {g["cases"]} | {cell(g,"r21")} | {cell(g,"r23")} | {cell(g,"r24")} | {g.get("r24_n_to_p",0)} | {g.get("r24_c_to_w",0)} |')
        report.append('')
    report += ['## Raw flags and evidence limits', '',
               'The carried misspelled-recital M-1 remains exactly 48 wrong cells, unchanged in r21/r23/r24. '
               'The following raw flags are also retained, rather than silently applying an expanded exception:', '',
               '| Collection | Family | r24 raw flags |', '| --- | --- | ---: |']
    for part, groups in raw_flags.items():
        for name,count in groups.items():
            report.append(f'| {part} | {name} | {count} |')
    report += ['',
               'The deleted reviewer H-1 and veto generators were not available. The primary H-1 '
               'reconstruction (`review_h1.py`, `h1_review-*.json`) reproduces every reported aggregate: '
               'r21 96 wrong; r23 60 wrong / 1,398 correct / 702 holds; both guards zero wrong and '
               '228 additional holds. It uses title-case Recipient plus HLA as the fifth own-block form. '
               'The initial 2,160-cell reconstruction used RECIPIENT without HLA instead and measured '
               '90/54 wrong. Its unchanged files (`h1-*.json`) remain diagnostic evidence, outside the '
               'primary table totals. All those diagnostic cells also have zero final wrong placements '
               'and zero unsafe transitions. This is an explicit reconstruction with matching aggregate '
               'counts, not a claim of byte-identical recovery of the deleted generator. The 1,260-cell '
               'veto reconstruction retains its documented aggregate differences.', '',
               'The literal captioned H-1 worker holds on unchanged HEAD; a separately retained '
               'uncaptioned worker fails first and is fixed. All 60 primary H-1 wrong cells are '
               'reproduced on the frozen r23 source, including the six title-case cells absent from '
               'the initial pytest matrix.', '',
               'The nine blocking recital cohorts and the unchanged Q2 inputs are exact; additional '
               'attack/boundary strings are explicit reconstructions from the review descriptions. '
               'The two documented boundary fixture artefacts remain in the raw table; their r23 '
               'flags are 18 here versus 12 reported by the reviewer. Neither produces a wrong r24 placement.', '',
               '[Method and commands](method.md), [per-cell transitions](vs-live.json), '
               '[remaining flags](remaining-flags.json), and the adjacent `*-cases.json` files provide '
               'the full evidence and provenance.', '']
    (OUT / 'results-r24.md').write_text('\n'.join(report))
    print(json.dumps(preservation, indent=2))


if __name__ == '__main__':
    main()
