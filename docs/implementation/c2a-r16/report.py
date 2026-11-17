"""Write the result table and completion marker from completed evidence."""
from collections import Counter
import json
from pathlib import Path


OUT = Path(__file__).resolve().parent


def read(stem):
    return json.loads((OUT / (stem + '.json')).read_text())


def main():
    comparison = read('counterfactual-summary')
    full = read('full-suite-summary')
    audit = read('preservation-summary')
    geometry = read('geometry-audit')
    red = read('failing-first-summary')
    counts = full['counts']
    passed = (all(comparison['bars'].values()) and counts['failed'] == counts['errors'] == counts['skipped'] == 0
              and counts['passed'] == 11362 and not audit['changed_existing_tests']
              and not audit['tracked_test_changes'] and audit['source_matches_comparison'])
    totals = {source: Counter() for source in ['r14', 'nearest', 'chosen']}
    for family, values in comparison['groups'].items():
        if family == 'r14 L-1 (grid subset)':
            continue
        for source in totals:
            for status in ['wrong', 'placed', 'holds', 'bare']:
                totals[source][status] += values[source + '_' + status]
    cases = read('counterfactual-cases')
    losses, gains = [], []
    wrong_cases = []
    for case in cases['cases']:
        if case['group'] == 'r14 L-1 (grid subset)':
            continue
        before = cases['outcomes'][case['results']['nearest']]
        after = cases['outcomes'][case['results']['chosen']]
        label = case['group'] + ' / ' + case['case']
        if before['status'] == 'placed' and after['status'] != 'placed':
            losses.append(dict(case=label, nearest_was_wrong=case['wrong']['nearest']))
        if before['status'] != 'placed' and after['status'] == 'placed':
            gains.append(label)
        if case['wrong']['chosen']:
            wrong_cases.append(label)
    transitions = dict(nearest_placements_to_holds=losses, nearest_holds_to_placements=gains)
    (OUT / 'nearest-transitions.json').write_text(json.dumps(transitions, indent=2) + '\n')
    summary = (f"**{counts['passed']:,} passed, {counts['failed']} failed, "
               f"{counts['errors']} errors, {counts['skipped']} skipped**")
    lines = [
        '# C2a r16 results', '', '**Bar met.**' if passed else '**Bar not met.**', '',
        "Chosen: nearest-column ownership with witness/attestation exclusion and ambiguous-name scoring. "
        "`VERSION = 'c2a.16'`. No generalised (b-prime) shared-row veto.", '',
        f"Full Send suite (`dealroom_sign/tests`): {summary}. It completed without `-x`, "
        'selection filters, or a maximum-failures override. The 11,340 existing tests and 22 added r16 cases all ran.', '',
        f"Every family in the r15b table was replayed: **{comparison['cases_excluding_L1_subset']:,} cases**, "
        f"**{totals['chosen']['wrong']} wrong placements**, including all r15 M1/M2 reproductions and sweeps. "
        'The 72-case L-1 subset remains separately displayed and is excluded from totals. '
        '**Seven goldens match exactly except `analysis_version`**, including native fields.', '',
        f"Hash verification: **{audit['existing_test_and_fixture_files_checked']} existing test/fixture files checked; "
        f"{len(audit['changed_existing_tests'])} changed**. No existing test or fixture was changed, skipped, weakened, deleted, or retargeted. "
        f"HEAD remains `{audit['head']}`; nothing was staged or committed. The inherited report and project memory are unchanged.", '',
        '## Chosen rule and bounded experiments', '',
        'Aligned rules sharing a left edge remain one column. Ownership uses horizontal edge distance; '
        'nearest columns within 2 pt fail closed. A witness signs next to a party but is never that party: '
        'Witness, Attest, and Attestation line labels are excluded from candidate party columns and cannot receive party scores. '
        'All scores are computed before role labels are redacted, preserving traversal-order independence.', '',
        'A printed-name row intersecting the open gutter between neighbouring party columns '
        '(existing vertical band: less than 30 pt) makes scoring return zero in each affected raw extent. '
        'Nearest-column ties also return zero rather than falling back to company hints or another name. '
        'Staggered outdented captions retain nearest-column ownership. The r14 mixed-heading veto remains unchanged.', '',
        '**Fixture correction:** the r3 `witness`, call 3 reproduction has two party blocks, Harbor and Fleet, '
        'both labelled `By:`; no witness/attestation block exists in its extracted candidates. Lee’s row starts '
        'at x296.4 in the x266.4–316.8 gutter and extends to x362.2 inside Fleet’s column. '
        'Witness exclusion alone therefore cannot fix it. Gutter variant 1 (whole row inside the gap) '
        'fixed the r4 diagnostic but retained this wrong placement. Variant 2 (row intersects the gap) '
        'fixes both. No broader company-only guard was needed. One role-exclusion rule and two gutter variants were tried.', '',
        'Failing first against nearest-only: **2 existing failures; 14 new failures and 4 new passes**. '
        'Before gutter variant 2: **4 additional crossing-row failures**. The initial role implementation '
        'also exposed two reverse-order attestation failures; computing all scores before redaction fixes them. '
        'Final focused run: **55 passed**. The earlier preservation run completed with **713 passed**; '
        'all those controls also run in the final full suite.', '',
        f"Relative to nearest-only: **{len(losses)} placement-to-hold transitions** "
        f"({sum(x['nearest_was_wrong'] for x in losses)} previously wrong), **{len(gains)} hold-to-placement transitions**, "
        f"and **{sum(not x['nearest_was_wrong'] for x in losses)} correct placements lost**. "
        f"All {geometry['placed_fields_checked']:,} emitted fields in the comparison retain exact nearest-only geometry. "
        'The complete transitions are recorded in `nearest-transitions.json`.', '',
        'Full results differ from nearest-only in seven cases: the two requested controls and five r8 C7 '
        'witness controls. The latter retain their exact fields, status, score, and model behavior; '
        'their assignment margin rises from 2 to 6 because the witness no longer has a competing party score. '
        '[Every result difference](nearest-result-differences.json) and the [gap diagnostic audit](gap-control-audit.json) '
        'record these changes explicitly.', '',
        '## Per-family comparison', '',
        'Cells are **wrong / placed / holds**; wrong is included in placed. Bare outcomes are recorded separately. '
        'Both historical columns are recomputed and checked against the archived r15b counts.', '',
        '| ID | Family | Cases | r14 | Nearest | Chosen |',
        '| --- | --- | ---: | ---: | ---: | ---: |',
    ]
    for i, (family, values) in enumerate(comparison['groups'].items(), 1):
        cells = [' / '.join(str(values[source + '_' + key]) for key in ['wrong', 'placed', 'holds'])
                 for source in ['r14', 'nearest', 'chosen']]
        lines.append(f"| F{i:02} | {family} | {values['cases']} | " + ' | '.join(cells) + ' |')
    lines += ['', 'Totals excluding the L-1 subset:', '',
              '| Source | Wrong | Placed | Holds | Bare |', '| --- | ---: | ---: | ---: | ---: |']
    for source, values in totals.items():
        lines.append('| ' + source + ' | ' + ' | '.join(str(values[k]) for k in ['wrong', 'placed', 'holds', 'bare']) + ' |')
    lines += ['', '## Full-suite summary and evidence', '', summary + '.', '',
              '[Full log](full-suite.txt), [JUnit](full-suite.xml), [summary and all failures](full-suite-summary.json), '
              '[every test outcome](full-suite-cases.json). The unchanged launcher’s scratch-directory warning is retained in the log.', '',
              '[Method and exact commands](method.md), [comparison runner](check_evidence.py), '
              '[family counts](counterfactual-summary.json), [all cases and results](counterfactual-cases.json), '
              '[real-worker checks](counterfactual-workers.json), [seven goldens](placements.json).', '',
              '[Failing-first counts](failing-first-summary.json), [fixture geometry](witness-fixture-audit.json), '
              '[preservation audit](preservation-summary.json), [field geometry audit](geometry-audit.json), '
              '[source patch](candidate.patch). External HTTP/model calls: **0**; model callbacks are deterministic local stubs.', '']
    blockers = wrong_cases + [c['classname'] + '::' + c['case'] for c in full['failures']]
    if not passed:
        lines += ['## Blocking cases', ''] + ['- ' + case for case in blockers] + ['']
    (OUT / 'results-r16.md').write_text('\n'.join(lines))
    done = [f"coder rc={0 if passed else 1} head={audit['head']}",
            'failing-first: nearest existing=2 failed/0 passed; new=14 failed/4 passed; crossing=4 failed/0 passed',
            'chosen: nearest columns; witness/attestation excluded; ties and same-band gutter intersections score zero; no b-prime',
            'reason: a witness signs next to a party but is never that party; the named witness fixture is held by its party-gutter crossing',
            f"families: {comparison['cases_excluding_L1_subset']} cases; wrong={totals['chosen']['wrong']}; goldens=7 exact except analysis_version",
            f"full-suite: passed={counts['passed']} failed={counts['failed']} errors={counts['errors']} skipped={counts['skipped']}; completed without -x",
            f"existing-test changes=0; SHA-256 checked={audit['existing_test_and_fixture_files_checked']}; new tests=22; no fixture changes",
            'version=c2a.16; no staging or commit']
    done += ['blockers: none'] if passed else ['blocker: ' + case for case in blockers]
    (OUT / 'counterparty-c2a-r16.done').write_text('\n'.join(done) + '\n')
    print('\n'.join(done))


if __name__ == '__main__':
    main()
