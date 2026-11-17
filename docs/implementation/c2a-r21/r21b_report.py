"""Append the final r21b result and write its completion marker after auditing."""
import json
from pathlib import Path


OUT = Path(__file__).resolve().parent


def load(name):
    return json.loads((OUT / name).read_text())


def cells(group):
    return ' / '.join(str(group.get('r21_' + key, 0))
                      for key in ('wrong', 'placed', 'holds', 'bare'))


def contributions(summaries, step):
    transitions = ('wrong -> needs_sender', 'wrong -> placed',
                   'placed -> needs_sender', 'needs_sender -> placed')
    return ' / '.join(str(sum(group.get(step, {}).get(transition, 0)
                             for summary in summaries
                             for group in summary['transitions'].values()))
                      for transition in transitions)


def main():
    bars = load('r21b-release-bars.json')
    assert bars['qualified']
    assert bars['full_suite'] == {'passed': 23980, 'failed': 0, 'errors': 0, 'skipped': 0}
    comparison = load('r21b-family-comparison.json')
    patch = (OUT / 'r21b-authorized-test.patch').read_text().rstrip()
    rows, summaries = [], []
    for stem, label in (('historical', 'Historical families'), ('review', 'r20 review families'),
                        ('layouts', 'Literal matrix and B-2 additions'),
                        ('reviewer-layouts', 'Reviewer 5,280 matrix')):
        summary = load('r21b-final-' + stem + '-summary.json')
        summaries.append(summary)
        totals = {key: sum(g.get(key, 0) for g in summary['groups'].values())
                  for key in ('r21_wrong', 'r21_placed', 'r21_holds', 'r21_bare')}
        rows.append(f'| {label} | {summary["cases"]:,} | {cells(totals)} | '
                    f'{len(comparison[stem]["changed_results"])} |')
    layout = load('r21b-final-layouts-summary.json')
    reviewer = load('r21b-final-reviewer-layouts-summary.json')
    b2 = layout['groups']['B2 exact worker']
    source_hash = bars['preservation']['production_sha256']
    table = '\n'.join(rows)
    contribution_table = '\n'.join(
        f'| {label} | {contributions(summaries, step)} | {contributions([reviewer], step)} |'
        for label, step in (('B-1 fix3', 'fix3'), ('B-2', 'b2'),
                            ('ROLE_DEF', 'role_def'), ('L-1', 'r21')))
    added_holds = {stem: sum(row['before_status'] == 'placed'
                            and row['after_status'] == 'needs_sender'
                            for row in comparison[stem]['changed_results'])
                   for stem in comparison}
    section = f'''

## r21b — final result

**PASS — release-qualified candidate (`coder rc=0`).** Full Send backend suite
completed without `-x`: **23,980 passed, 0 failed, 0 errors, 0 skipped**, with no
deselections. All 23,972 incoming r21 test IDs remain, including all 18,376 r20 IDs;
eight new duplicate-role regressions were added. HEAD remains
`{bars['preservation']['head']}` and `VERSION = 'c2a.21'`.

### Manager rulings and implementation

1. **Authorized test correction:** the manager explicitly authorized changing only
   `test_independent_evidence_and_party_count_controls[different_page]` from score
   4 to the document-wide hold score 0 because it asserted the r20 B-1 bug. The
   original expectation expression for every other control is retained verbatim.
2. **Named alias correction:** B-2 now classifies the resolved heading after role
   mapping and behalf normalization. A role mapped to NORTHWIND is named and
   permits score 4 on HARBOR LIGHT GROUP. The existing
   `test_heading_is_normalized_before_identifying_other_party[RECIPIENT:-roles5-4]`
   is byte-identical and passes. Missing mappings and mappings to role words
   remain unnamed.
3. **Duplicate-role boundary:** the simple alias correction exposed the unchanged
   r21 `discloser-False-` vocabulary regression: its role maps to Fleet while a
   separate Fleet block also claims that company. The role is named, but its block
   assignment is ambiguous. A separate, document-wide guard retains the hold when
   two blocks claim the role's company without printed-person evidence to
   distinguish them. It preserves the independent-name and explicit-company paths.
   Eight new tests cover two role spellings, both page arrangements, and printed
   peer controls; four fail before the refinement and all eight pass after it.

The exact authorized existing-test diff is:

```diff
{patch}
```

No other existing test, fixture or evidence file changed, except this explicitly
requested RESULT update. The audit verifies all 1,905 r20 tracked files and all
1,999 incoming r21 files by SHA-256, reconstructs the authorized test change
exactly, and confirms unchanged HEAD and index. The original r21 `.done` and all
its evidence remain intact. No staging, commit or project-memory update.

### Verification

Every one of the **40,924 replay inputs** has 0 wrong under the unchanged reviewer
oracles. Results below are **wrong / placed / holds / bare**; the last column counts
complete result differences from the incoming r21 candidate.

| Family collection | Cases | r21b | Full-result differences from r21 |
| --- | ---: | --- | ---: |
{table}

The narrowed alias policy adds **{added_holds['layouts']} correct→hold outcomes** in
the literal layouts/additions and **{added_holds['reviewer-layouts']}** in the reviewer
matrix relative to r21. A mapped recipient and a domain-matching affiliate on
different pages can now both score, leaving assignment unresolved. These costs
remain visible; no wrong placement is accepted to recover them. Other complete
result changes in those collections are differences in already-held candidates.

Contributions are measured cumulatively from r20 through fix3, B-2, ROLE_DEF and
L-1. Cells are **wrong→hold / wrong→correct / correct→hold / hold→correct**.

| Step | All replay inputs | Reviewer matrix |
| --- | --- | --- |
{contribution_table}

The reviewer matrix's **1,800 cross-page subset** is
**{cells(reviewer['cross_page_1800_subset'])}**. It is a subset, not 1,800 additional
inputs. The 12 exact `THE RECIPIENT` worker/printed-name cases are
**{cells(b2)}**; each worker result equals its in-process result. The 52 role
vocabulary cases remain 0 wrong. Seven goldens and their native fields match
exactly except `analysis_version`. All 21 final-source worker checks match their
in-process results (105 checks across the five cumulative variants). HTTP calls: 0.
The prior 96 Competition raw flags and six Q4 named-company ambiguities retain
their unchanged reviewer-approved classification; no oracle exception expanded.

The 96-test focused alias run passes, as do 42 additional alias score controls.
The full suite includes every matrix and regression test without filtering.
The first simple-narrowing run and its interrupted replays remain as draft
evidence; only `r21b-final-*` records certify this candidate. See the
[r21b method](r21b-method.md) for the exact commands and failing-first sequence.

- [Completed full suite](r21b-final-full-suite.txt) and [JUnit](r21b-final-full-suite.xml).
- [Historical families](r21b-final-historical-summary.json), [review families](r21b-final-review-summary.json),
  [literal matrix and B-2](r21b-final-layouts-summary.json), [reviewer matrix](r21b-final-reviewer-layouts-summary.json).
- [Exact goldens](r21b-final-placements.json), [family comparisons](r21b-family-comparison.json),
  [test counts](r21b-test-runs-summary.json), [test inventory](r21b-test-inventory-summary.json).
- [Preservation audit](r21b-preservation-summary.json), [release bars](r21b-release-bars.json),
  [authorized diff](r21b-authorized-test.patch).

Production SHA-256: `{source_hash}`.

**Blockers: none.**
'''
    result = OUT / 'results-r21.md'
    old = result.read_text()
    assert '## r21b — final result' not in old
    latest = ('**Latest result: r21b PASS — 23,980 passed, 0 failed, 0 errors, 0 skipped.** '
              'See [r21b](#r21b--final-result). The earlier r21 HOLD below is retained as historical evidence.\n\n')
    result.write_text(old.replace('# C2a r21 results\n\n', '# C2a r21 results\n\n' + latest, 1) + section)
    done = OUT / 'counterparty-c2a-r21b.done'
    assert not done.exists()
    done.write_text(f'''coder rc=0 head={bars['preservation']['head']}
changed: role-word classification uses the resolved heading; a named NORTHWIND alias permits score 4; unresolved/role-only aliases hold. Duplicate named-role claims without independent printed identity retain a separate document-wide hold. B-1, ROLE_DEF and L-1 remain; VERSION = 'c2a.21'.
authorization: manager ruling 1 explicitly permits only different_page expectation 4 -> 0. All other existing expectations, including RECIPIENT:-roles5-4, are unchanged. Eight new duplicate-role regression cases added.
exact test diff for ruling 1:
```diff
{patch}
```
full suite: 23980 passed, 0 failed, 0 errors, 0 skipped; completed without -x or deselections. All 23972 incoming r21 IDs and 18376 r20 IDs retained.
replays: 40924 inputs; 0 wrong on every family; 5280 reviewer matrix and its 1800 cross-page subset pass; B-2 cases pass; seven goldens and native fields exact except analysis_version; real workers equal in-process; HTTP calls 0. Existing reviewer-approved raw-flag classifications unchanged.
hold cost versus incoming r21: {added_holds['layouts']} correct-to-hold in literal layouts/additions and {added_holds['reviewer-layouts']} in the reviewer matrix; historical and review-family results unchanged.
preservation: 1905 r20 tracked files and 1999 incoming r21 files hash-verified. Only production, the authorized test assertion and requested RESULT update changed among incoming files. Existing fixtures, other tests, evidence and r21 done marker preserved. HEAD and index unchanged; no commit.
production sha256: {source_hash}
result: docs/implementation/c2a-r21/results-r21.md, r21b section.
blockers: none.
''')


if __name__ == '__main__':
    main()
