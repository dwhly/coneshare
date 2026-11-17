"""Write reviewable results and the six-line completion marker after verification."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def read(name):
    return json.loads((OUT / name).read_text())


def counts(group, source):
    return ' / '.join(str(group[source + '_' + key]) for key in ('wrong', 'placed', 'holds'))


def suite(path):
    tree = ET.parse(path)
    totals, failures = Counter(), []
    for case in tree.iter('testcase'):
        status = next((s for s in ('failure', 'error', 'skipped') if case.find(s) is not None), 'passed')
        totals[status] += 1
        if status != 'passed':
            failures.append({'test': case.attrib['classname'] + '::' + case.attrib['name'],
                             'status': status, 'message': case.find(status).text})
    result = {'counts': totals, 'failures': failures,
              'suites': [s.attrib for s in tree.iter('testsuite')]}
    path.with_name(path.stem.removesuffix('-r15b') + '-summary-r15b.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    nearest = read('counterfactual-summary-r15b.json')
    combined = read('counterfactual-summary-combined-r15b.json')
    inventory = read('added-control-families-combined-r15b.json')
    final = read('full-suite-summary-r15b.json')
    preservation = read('preservation-summary-r15b.json')
    trial = suite(OUT / 'full-suite-distinct-intervals-r15b.xml')
    assert not preservation['tracked_existing_test_changes']
    assert nearest['groups'].keys() == combined['groups'].keys()
    assert all(combined['bars'].values())
    passed = final['totals'].get('passed', 0)
    suite_outcome = (f'{passed:,} passed, {final["totals"].get("failure", 0)} failed, '
                     f'{final["totals"].get("error", 0)} errors, {final["totals"].get("skipped", 0)} skipped')
    failures = final['failures']
    rc = int(not final['complete_and_green'])
    lines = ['# C2a r15b results', '',
             '**' + ('Bar reached.' if not rc else 'Bar not reached; best candidate left uncommitted.') + '**', '',
             'Chosen rule: **nearest-column ownership + (b′)**, with `VERSION = c2a.15`. '
             'Aligned rules sharing a left edge form one column; ownership uses horizontal edge distance '
             'and fails closed when distinct columns tie within 2 pt. '
             'The (b′) veto propagates a peer block’s zero signer score across a shared physical name row.', '',
             f'The expanded comparison has **{combined["cases_excluding_L1_subset"]:,} identified cases**, '
             f'including **{combined["added_control_cases"]:,} added control cases** in {len(inventory)} families. '
             'The 72-case L-1 subset is displayed separately and excluded from that total. '
             'Both candidates preserve the seven goldens exactly except `analysis_version`, including native fields. '
             'External HTTP/model calls: **0**; model callbacks are local deterministic stubs.', '',
             'Nearest-column ownership alone has **one wrong placement** in the added r3 witness control '
             '(`inserted_raw_person_vetoes_across_fixtures`, witness, call 3). '
             'The conflicting Lee Harbor row lies nearer the witness column, so removing it from the other '
             'block’s printed-name evidence permits a company-only Pat placement. '
             'The combined rule holds that case and has **zero wrong placements in every measured family**.', '',
             'Nearest-only also changes the r4 gap-between-columns hold to retain one high-confidence '
             'assignment, violating that control’s diagnostic assertion even though no fields are emitted. '
             'The [focused gap audit](gap-control-audit-r15b.json) confirms that the combination preserves '
             'all of the existing control’s assertions.', '',
             f'Final full suite: **{suite_outcome}**. '
             'It completed without `-x`. No existing test or fixture was changed, skipped, weakened or retargeted. '
             'The final source matches the measured combined candidate. HEAD remains `' + combined['base'] + '`; '
             'nothing was staged or committed.', '',
             '## Every final-suite failure', '']
    for failure in failures:
        lines.append('- `' + failure['class'] + '::' + failure['case'] + '`')
    if not failures:
        lines.append('None.')
    lines += ['', 'The r14 correct controls expect Pat’s signature/date at y290/y330 in the unambiguous '
              'HARBOR column. The combined shared-row veto returns `needs_sender` with empty fields '
              'because the unheaded competing block has score zero. The same generalised veto also holds '
              'six r10 caption-row-right controls and five r4/r5 stacked-signer controls. '
              'These preservation failures were not hidden by changing the tests.', '',
              '## Per-family comparison', '',
              'Each cell is **wrong / placed / holds**. Wrong is included in placed. '
              'Bare outcomes are recorded separately in the machine-readable data. '
              'The `Fxx` IDs map the completion marker to this table.', '',
              '| ID | Family | Cases | r14 | Nearest | Nearest + (b′) |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    markers = []
    totals = defaultdict(Counter)
    for index, (group, values) in enumerate(combined['groups'].items(), 1):
        before, nn, after = counts(values, 'r14'), counts(nearest['groups'][group], 'nearest'), counts(values, 'combined')
        key = f'F{index:02}'
        lines.append(f'| {key} | {group} | {values["cases"]} | {before} | {nn} | {after} |')
        markers.append(key + '=' + before.replace(' ', '') + '->' + after.replace(' ', ''))
        if group != 'r14 L-1 (grid subset)':
            for label, data in [('r14', values), ('nearest', nearest['groups'][group]), ('combined', values)]:
                for outcome in ('wrong', 'placed', 'holds', 'bare'):
                    totals[label][outcome] += data[label + '_' + outcome]
    lines += ['', 'Totals excluding the L-1 subset:', '',
              '| Source | Wrong | Placed | Holds | Bare |', '| --- | ---: | ---: | ---: | ---: |']
    for source, values in totals.items():
        lines.append('| ' + source + ' | ' + ' | '.join(str(values[k]) for k in ('wrong', 'placed', 'holds', 'bare')) + ' |')
    lines += ['', '## Correct-placement costs and added families', '',
              'Nearest alone restores 1,352 r14 holds (1,236 GRID + 116 FIXED) without losing any r14 '
              'correct placements, but introduces the one witness wrong placement above. '
              'The combination loses 24 r14 GRID placements and both r14 correct controls, '
              'plus three r4 stacked-individual, two r5 stacked-heading and six r10 caption-row-right controls: '
              '**37 correct placements become holds**. The 26 r14 cases are the same ordinary staggered '
              'layouts disclosed in r15; the additional 11 are ordinary stacked and outdented-name layouts. '
              'The 72 r14 L-1 holds remain holds under both candidates.', '',
              'The added control families are listed below with their original test function and full '
              'case counts. They include the previously missing r10 `caption_row_right` family '
              'as its own table row.', '']
    for group, entry in inventory.items():
        lines.append(f'- **{group}**: {entry["cases"]} cases; `{entry["test"]}`.')
    lines += ['', '## Earlier full attempt: distinct intervals', '',
              'The first implementation treated aligned rules of different lengths as different columns. '
              'It failed the offer golden. Its already-started full suite was allowed to finish without '
              '`-x` before the final source was installed. Every failure from that completed run follows.', '',
              '`' + json.dumps(dict(trial['counts']), sort_keys=True) + '`', '']
    for failure in trial['failures']:
        lines.append('- `' + failure['test'] + '`')
    lines += ['', '## Evidence', '',
              '- [Method and commands](method-r15b.md); [comparison generator](check_evidence-r15b.py).',
              '- [Nearest table data](counterfactual-summary-r15b.json); [combined table data](counterfactual-summary-combined-r15b.json).',
              '- [Every combined case/result](counterfactual-cases-combined-r15b.json); [differences](counterfactual-differences-combined-r15b.json); [worker checks](counterfactual-workers-combined-r15b.json).',
              '- [Geometry audit](geometry-audit-r15b.json): all 4,649 combined fields exactly match accepted r14 geometry.',
              '- [Final full-suite output](full-suite-r15b.txt); [JUnit](full-suite-r15b.xml); [all outcomes](full-suite-cases-r15b.json); [summary](full-suite-summary-r15b.json).',
              '- [Earlier full-suite output](full-suite-distinct-intervals-r15b.txt); [all earlier failures](full-suite-distinct-intervals-summary-r15b.json).',
              '- [Preservation audit](preservation-summary-r15b.json); [final candidate patch](candidate-combined-r15b.patch).', '',
              'Open: the existing-test preservation requirement is unmet. No permitted candidate reached '
              'all three bars. The safest candidate is left uncommitted for review. Project memory remains '
              'unchanged; no venv, cache directory or node_modules remains in the repository.', '']
    (OUT / 'results-r15b.md').write_text('\n'.join(lines))
    failure_names = '; '.join(f['class'] + '::' + f['case'] for f in failures) or 'none'
    marker = [f'coder rc={rc} head={combined["base"]}',
              'rule=nearest-column ownership + (b-prime); same-page aligned columns; edge distance; ties <=2pt count for neither; VERSION=c2a.15',
              'per-family wrong/placed/holds r14->chosen (IDs in results-r15b.md): ' + '; '.join(markers),
              f'full-suite={suite_outcome}; completed without -x; failures: {failure_names}',
              'existing-test changes=none; no weakening/skipping/deleting/retargeting; no staging or commit',
              'open=' + ('none' if not rc else 'bar unmet: r10/r14 and r4/r5 stacked controls hold under combined veto; nearest alone has one wrong r3 witness placement; 72 L-1 holds remain; see results-r15b.md')]
    (OUT / 'counterparty-c2a-r15.done').write_text('\n'.join(marker) + '\n')
    (OUT / 'totals-r15b.json').write_text(json.dumps(totals, indent=2) + '\n')
    print(json.dumps({'rc': rc, 'totals': totals, 'suite': final['totals']}, indent=2))


if __name__ == '__main__':
    main()
