"""Write the final per-family report only after release audits pass."""
from collections import Counter
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def read(name):
    return json.loads((OUT / (name + '.json')).read_text())


def cell(counts, variant):
    return ' / '.join(str(counts.get(variant + '_' + key, 0))
                      for key in ('wrong', 'placed', 'holds', 'bare'))


def change(transitions):
    return ' / '.join(str(transitions.get(key, 0)) for key in (
        'wrong -> needs_sender', 'wrong -> placed', 'placed -> needs_sender', 'needs_sender -> placed'))


def main():
    bars = read('release-bars')
    assert bars['wrong'] == 0
    historical, review, layouts, matrix = [read(name) for name in (
        'release-historical-summary', 'release-review-summary',
        'release-layouts-summary', 'reviewer-layouts-summary')]
    head = read('starting-state')['head']
    all_summaries = (historical, review, layouts, matrix)
    totals = Counter()
    for summary in all_summaries:
        for counts in summary['groups'].values():
            totals.update(counts)
    matrix_totals = Counter()
    for counts in matrix['groups'].values():
        matrix_totals.update(counts)
    steps = {variant: Counter() for variant in ('fix3', 'b2', 'role_def', 'r21')}
    for summary in all_summaries:
        for transitions in summary['transitions'].values():
            for variant, values in transitions.items():
                steps[variant].update(values)
    matrix_steps = {variant: Counter() for variant in steps}
    for transitions in matrix['transitions'].values():
        for variant, values in transitions.items():
            matrix_steps[variant].update(values)
    recoveries = sum(s['groups'][group].get('r21_placed', 0) - s['groups'][group].get('role_def_placed', 0)
                     for s in (historical, review) for group in s['groups'])
    text = [
        '# C2a r21 results', '',
        f'Base HEAD: `{head}`. Production `VERSION = \'c2a.21\'`. No commit or index changes.', '',
        f'**HOLD — candidate is not release-qualified (`coder rc=1`).** All four requested '
        f'items are implemented, but the full Send backend suite, completed without `-x`, has '
        f'**{bars["full_suite"]["passed"]:,} passed, {bars["full_suite"]["failed"]} failed, '
        f'{bars["full_suite"]["errors"]} errors, {bars["full_suite"]["skipped"]} skipped**. '
        'All 18,376 r20 test IDs remain, with 5,596 additions. All 1,905 starting '
        'tracked files were hash-verified; `placement.py` is the only changed starting file.', '',
        'The full-suite bar is not met. The untouched r20 boundary test for `different_page` '
        'requires score 4 where the exact requested document-wide fix3 returns 0. Running '
        '**fix3 alone** against that old module confirms 13 passed / 1 failed. A second '
        'old assertion requires a role mapped to `NORTHWIND TRADERS LLC` to count as named; '
        'the candidate’s conservative B-2 policy holds pure role headings before alias '
        'expansion, and returns 0 there too. No test was changed to make these green. '
        'The candidate remains in the working tree for review; none is claimed as shipped.', '',
        f'All {totals["cases"]:,} replay inputs across historical, review, literal-row and reviewer-wrapped '
        'families have **0 wrong** under r21. The 1,800 cross-page cells are an explicitly '
        'reported subset of the 5,280 reviewer matrix, not additional inputs. Seven goldens '
        'and their native fields are exact except `analysis_version`; real-worker results '
        'equal in-process results. External HTTP calls: 0.', '',
        'The original 10,770-case replay has no full-result differences apart from '
        '`analysis_version`. Across the r20 families, the only changes are the '
        'conservative L-1 recoveries and associated hold-score improvements.', '',
        '## Candidate implementation (not release-qualified)', '',
        '- **B-1 / fix3:** the exact two-part review change removes the page filter from '
        'the unnamed-block loop and counts non-witness blocks across the document. '
        'The earlier matching-company uniqueness loop remains unchanged.',
        '- **B-2:** singular/plural party-role vocabulary, optionally preceded by `the`, '
        'is excluded from printed persons and the fallback unresolved-person predicate. '
        'Pure role headings are unnamed before alias expansion in the document hold, '
        'so an alias mapped to the other party cannot silently clear that hold. '
        'Real person names containing additional words retain their identity evidence. '
        'Existing output redaction is preserved.',
        '- **ROLE_DEF:** the exact r20 candidate adds bounded descriptive text after a '
        'legal company suffix and optional `hereinafter` wording. Both direct mapping '
        'regressions fail on r20 and pass on r21.',
        f'- **L-1:** the exact r20 printed-name exemption bypasses only the shared-heading '
        f'page flag, preserving the other vetoes. It recovers **{recoveries}** placements '
        'in the r20 families.',
        '- The optional `WITNESS:`-over-`By:` recognition is **not shipped**. Its conservative '
        'holds remain visible in the matrix costs.', '',
        '## Failing first and test preservation', '',
        'The unchanged r20 production run had 1,173 failures and 4,421 passes across '
        'the first 5,594 new tests. The two L-1 tests also failed. The two role-definition '
        'tests initially had a draft call-signature error; corrected calls independently '
        'fail because r20 has no recipient mapping. The L-1 draft two-signer expectation '
        'was corrected to preserve Dan’s hold and require Pat’s high score; both final '
        'assertions still fail against exact r20. These are changes to newly authored '
        'drafts only, not to any starting test. All runs and draft source are retained.', '',
        '| New family | Cases | Failed on r20 | Passed on r20 |',
        '| --- | ---: | ---: | ---: |',
        '| Requested cross-page regressions | 240 | 180 | 60 |',
        '| Literal-row matrix | 5,280 | 950 | 4,330 |',
        '| B-2 exact/printed-name worker cases | 12 | 11 | 1 |',
        '| Role vocabulary, singular/plural | 52 | 26 | 26 |',
        '| Combined roles | 4 | 4 | 0 |',
        '| Real-person controls | 4 | 0 | 4 |',
        '| ROLE_DEF corrected mapping checks | 2 | 2 | 0 |',
        '| L-1 final own-name checks | 2 | 2 | 0 |',
        '| Total final assertions | 5,596 | 1,175 | 4,421 |', '',
        'Only `placement_r21_review_cases.py`, `test_placement_r21.py`, and '
        '`test_placement_r21_l1.py` are added to the test tree. No starting test, '
        'fixture, evidence file, assertion, or `.done` marker changed, and no original '
        'test was skipped, removed or retargeted. See [hash audit](preservation-summary.json) '
        'and [test inventory](test-inventory-summary.json).', '',
        '## Reviewer matrix and recital layout', '',
        'The review supplies the matrix axes and inline reproduction rows, but no '
        'standalone r20 matrix generator. Both forms are retained: the literal inline '
        'rows and the same axes using the 95-character recital wrap from the existing '
        'r19 `q1real.py` generator. Wrapping affects the pre-existing cross-page identity '
        'walk. The literal-row r20 matrix has 950 wrong cells; the wrapped matrix below '
        'is compared directly with the review’s reported counts.', '',
        '| Matrix | Cases | r20 wrong / placed / holds / bare | r21 wrong / placed / holds / bare |',
        '| --- | ---: | --- | --- |',
        f'| Reviewer-style matrix | 5,280 | {cell(matrix_totals, "r20")} | {cell(matrix_totals, "r21")} |',
        f'| Cross-page subset | 1,800 | {cell(matrix["cross_page_1800_subset"], "r20")} | {cell(matrix["cross_page_1800_subset"], "r21")} |', '',
        '## Contributions and every family', '',
        'Result cells are **wrong / placed / holds / bare**. Contribution cells are '
        '**wrong→hold / wrong→correct / correct→hold / hold→correct**, measured '
        'cumulatively: r20 → fix3 → B-2 → ROLE_DEF → L-1. They are document-level '
        'outcomes; a partial signer recovery that still holds the document is not '
        'counted as a placement.', '',
        '| Step | All replay inputs | Reviewer 5,280 matrix |',
        '| --- | --- | --- |',
    ]
    for name, variant in [('B-1 fix3', 'fix3'), ('B-2', 'b2'), ('ROLE_DEF', 'role_def'), ('L-1', 'r21')]:
        text.append(f'| {name} | {change(steps[variant])} | {change(matrix_steps[variant])} |')
    text += ['', 'The old Competition oracle retains 96 raw flags accepted by the reviewer '
             'only when another person is printed in Pat’s block. The six Q4 named-company '
             'ambiguities also retain their raw flags and prior reviewer classification. '
             'Neither exception was expanded; these are not new wrong placements or '
             'claims that Pat’s original coordinates matched.', '']
    for title, summary in [('Historical r20 families', historical), ('r20 review families', review),
                           ('Literal inline rows and B-2 additions', layouts), ('Reviewer-wrapped matrix', matrix)]:
        text += ['### ' + title, '',
                 '| Family | Cases | r20 | r21 | B-1 | B-2 | ROLE_DEF | L-1 |',
                 '| --- | ---: | --- | --- | --- | --- | --- | --- |']
        for group, counts in summary['groups'].items():
            changes = summary['transitions'].get(group, {})
            text.append('| ' + ' | '.join([group, str(counts['cases']), cell(counts, 'r20'), cell(counts, 'r21')]
                         + [change(changes.get(v, {})) for v in steps]) + ' |')
        text.append('')
    text += ['## Evidence', '',
             '- [Full suite](full-suite.txt), [JUnit](full-suite.xml), [test-run counts](test-runs-summary.json).',
             '- [Historical summary](release-historical-summary.json), [all outcomes](release-historical-cases.json).',
             '- [Review summary](release-review-summary.json), [all outcomes](release-review-cases.json).',
             '- [Literal layouts](release-layouts-summary.json), [reviewer matrix](reviewer-layouts-summary.json).',
             '- [Goldens](release-placements.json), [source audit](source-equivalence.json), [method](method.md).', '',
             f'Production SHA-256: `{read("source-equivalence")["sha256"]}`.', '',
             '## Blockers', '',
             '1. `backend/dealroom_sign/tests/test_placement_r20_boundaries.py:47`, '
             '`test_independent_evidence_and_party_count_controls[different_page]`: '
             'the frozen assertion expects 4 for a third unnamed block on another page; '
             'the requested fix3 requires 0. This fails with **fix3 alone**, independently '
             'of B-2, ROLE_DEF, and L-1. See [isolated proof](fix3-existing-boundaries.txt).',
             '2. The same file at line 30, '
             '`test_heading_is_normalized_before_identifying_other_party[RECIPIENT:-roles5-4]`: '
             'the candidate’s B-2 alias policy returns 0 instead of the existing expected 4. '
             'This is an additional candidate/test conflict, not an unavoidable consequence of fix3.', '',
             'Under the instruction to preserve all existing assertions, the exact fix3 '
             'and a zero-failure full suite cannot both be delivered. No source special-case '
             'or test retargeting was added to bypass the conflicting synthetic fixture. '
             'No commit, index or project-memory update.', '']
    (OUT / 'results-r21.md').write_text('\n'.join(text))
    (OUT / 'contributions.json').write_text(json.dumps({'all_replays': steps, 'reviewer_matrix': matrix_steps}, indent=2) + '\n')
    assert matrix_totals['r20_wrong'] == 790, matrix_totals
    assert matrix['cross_page_1800_subset']['r20_wrong'] == 750
    assert matrix_steps['fix3']['wrong -> needs_sender'] == 680
    assert matrix_steps['fix3']['placed -> needs_sender'] == 30
    assert recoveries == 354
    done = [f'coder rc=1 head={head}',
            'failing-first: 1175 failed, 4421 passed across 5596 final new assertions; draft corrections and raw runs retained.',
            'shipped: none; candidate implements B-1 document-wide fix3, B-2 role vocabulary, ROLE_DEF, conservative L-1; VERSION = c2a.21; optional witness change deferred.',
            f'full suite: {bars["full_suite"]["passed"]} passed, {bars["full_suite"]["failed"]} failed, 0 errors, 0 skipped; completed without -x.',
            'tests: 5596 added in test_placement_r21.py and test_placement_r21_l1.py, with new placement_r21_review_cases.py; 18376 prior IDs retained; no starting tests, fixtures, evidence or done markers changed.',
            f'replay: {totals["cases"]} inputs, five cumulative variants, 0 new wrong; 5280 reviewer matrix and its 1800 cross-page subset pass; seven goldens exact except version.',
            'preservation: 1905 starting files hash-verified; only placement.py changed; HEAD and index unchanged; no commit.',
            'blockers: frozen r20 different_page assertion contradicts exact fix3 (isolated fix3: 13 passed, 1 failed); mapped-role boundary assertion also rejects the conservative B-2 alias hold. No existing assertion changed; release bar not met.']
    (OUT / 'counterparty-c2a-r21.done').write_text('\n'.join(done) + '\n')


if __name__ == '__main__':
    main()
