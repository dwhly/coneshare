"""Render final evidence only after the full suite and preservation audit pass."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from audit import audit

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def main():
    audit()
    historical = json.loads((OUT / 'historical-summary.json').read_text())
    review = json.loads((OUT / 'review-summary.json').read_text())
    assert historical['cases'] == 17204
    assert review['cases'] == 12760
    groups = {**historical['groups'], **review['groups']}
    transitions = {**historical['transitions'], **review['transitions']}
    source_hash = hashlib.sha256((ROOT / 'backend/dealroom_sign/placement.py').read_bytes()).hexdigest()
    for summary in [historical, review]:
        assert summary['source_sha256']['r20'] == source_hash
        assert summary['external_http_calls'] == 0
    assert all(counts['r20_wrong'] == 0 for counts in groups.values())
    assert groups['Seven goldens']['r20_golden_diffs'] == groups['Seven goldens']['r20_native_diffs'] == 0
    assert groups['Competition']['r19_wrong'] == 144
    assert groups['Realistic NDA matrix']['r19_wrong'] == 34
    assert groups['Realistic NDA matrix']['r20_holds'] == 48
    added = {'L1 ragged stacked controls', 'L1 centred stacked controls',
             'A2 exact witness captions', 'A2 additional dy=20', 'Witness wider sweep',
             'F three-party permutations', 'F heading gaps long', 'F heading gaps short',
             'B1 reproduction', 'B2 reproduction', 'Affiliate matrix',
             'r18 B1 reproduction', 'Veto matrix'}
    original = {g: c for g, c in historical['groups'].items() if g not in added}
    assert len(original) == 113 and sum(c['cases'] for c in original.values()) == 10770
    assert all(c['r20_full_diffs'] == 0 for c in original.values())
    optional_costs = {}
    for group in groups:
        optional_costs[group] = {}
        for name in ['r20', 'role_def', 'l1', 'm1']:
            tr = transitions[group][name]
            optional_costs[group][name] = {
                'correct_to_hold': tr.get('placed -> needs_sender', 0),
                'hold_to_correct': tr.get('needs_sender -> placed', 0),
                'wrong_to_hold': tr.get('wrong -> needs_sender', 0),
                'wrong': groups[group].get(name + '_wrong', 0),
            }
    (OUT / 'hold-costs.json').write_text(json.dumps(optional_costs, indent=2) + '\n')
    assert all(cost['r20']['correct_to_hold'] == 0 for cost in optional_costs.values())

    totals = {name: Counter() for name in ['role_def', 'l1', 'm1']}
    for costs in optional_costs.values():
        for name in totals:
            totals[name].update(costs[name])
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    lines = [
        '# C2a r20 results', '',
        f"Base HEAD: `{head}`. Production `VERSION = 'c2a.20'`. No commit or index changes.", '',
        '**B-1 ships and all required bars pass.** Full Send backend suite, without `-x`: '
        '**18,376 passed, 0 failed, 0 errors, 0 skipped**. All 17,832 prior test IDs remain, '
        'with 544 additions. All 1,846 starting tracked files were hash-verified; '
        '`placement.py` is the only changed starting file.', '',
        'Production implements the reviewer’s exact fix2: domain-only company credit holds '
        'on pages with at least three non-witness blocks if another non-witness block '
        'has no printed name and its role-mapped, behalf-stripped heading names nobody. '
        'Explicit-company and printed-name scoring retain their existing behavior. '
        'The full production AST matches fix2 except the version value and comments.', '',
        '## Failing first', '',
        '| New tests | Cases | Failed before | Passed before | Passed after |',
        '| --- | ---: | ---: | ---: | ---: |',
        '| Competition | 480 | 144 | 336 | 480 |',
        '| Realistic NDA matrix | 48 | 34 | 14 | 48 |',
        '| Exact real worker, PAT and DAN+PAT | 2 | 2 | 0 | 2 |',
        '| Page, witness, role, behalf and identity scope | 14 | 5 | 9 | 14 |',
        '| Total | 544 | 185 | 359 | 544 |', '',
        'The exact reviewer scripts ran before the production edit. `q1real.py` reproduces '
        '**34/48 wrong here, not the review prose’s 38**: address 12, hereinafter 12, '
        'parsed 4, no recital 6. The copied tests independently reproduce 34. Inputs '
        'were preserved; all 48 now hold. See [original script output](reviewer-real-before.txt).', '',
        'The 480 competition cases go from **144 blocking wrong → 0**, with placements '
        '240 → 96 and holds 240 → 384. The remaining 96 are exactly the review-permitted '
        'cases with Chris Jones printed in the other block. Their original raw coordinate '
        'flags remain in the evidence; they are not counted as matches to Pat’s original '
        'blank. Both real-worker reproductions now return `needs_sender`, no fields and '
        'zero model calls.', '',
        '## Replay and optional measurements', '',
        '**29,924 required family evaluations**, plus two worker cases and 38 Q4 checks: '
        '**29,964 inputs / 149,820 in-process variant evaluations**. Every r19 family '
        'and the realistic matrix has zero blocking wrong placements under r20. '
        'B-1 costs **0 correct → hold**. The 10,770-case original replay has no full-result '
        'diffs except `analysis_version`. Seven goldens and native fields are exact, '
        'and their real-worker results equal in-process results. External HTTP calls: 0. '
        'Historical deterministic model mocks, including the unusual-label golden, remain in use.', '',
        '**Only B-1 ships. ROLE_DEF, L-1 and M-1 are measured separately and are not in '
        'production.** Their costs below are relative to B-1-only r20; they are not '
        'combined. The optional source snapshots and complete outputs are retained.', '',
        '| Optional candidate | Wrong | Correct/permitted → hold | Hold → correct | Decision |',
        '| --- | ---: | ---: | ---: | --- |',
    ]
    decisions = {
        'role_def': 'Measured only; recital mapping verified, release kept to B-1.',
        'l1': 'Measured only; release kept to B-1.',
        'm1': 'Measured only; hold cost is too large.',
    }
    for name in totals:
        t = totals[name]
        lines.append(f"| {name} | {t['wrong']} | {t['correct_to_hold']} | {t['hold_to_correct']} | {decisions[name]} |")
    lines += ['',
        'ROLE_DEF correctly maps the address and hereinafter recitals, with no placement '
        'changes in the measured families. The conservative L-1 exemption recovers '
        '**354** cases (303 F fine, 24 F permutations, 27 F long), fewer than the '
        'review’s 581 because it retains all other identity vetoes. Neither optional '
        'proposal is included in the full-suite-qualified production source. M-1 '
        'costs **850** accepted/permitted placements: 776 F fine company-only, '
        '20 L-2 controls, 48 competition cases, and the six Q4 ambiguous cases.', '',
        'The six Q4 M-1 cases remain explicitly ambiguous in production, as in r19: '
        'a named company spelling does not match the domain while a named affiliate '
        'does. Their six raw flags are reported separately, as the review requests; '
        'M-1 measures the broader hold instead of silently changing their oracle. '
        'The per-family table below shows the cost of that proposal, including F company-only.', '',
        'Cells in the first two result columns are **wrong / placed / holds / bare**. '
        'Each optional cell is **correct/permitted → hold / hold → correct / wrong**. '
        'Permitted includes the separately listed Q4 ambiguous placements; it does '
        'not claim their original coordinates were correct. '
        'Every family is listed, including zero-cost families.', '',
        '| Family | Cases | r19 | r20 | B-1 correct → hold | ROLE_DEF | L-1 | M-1 |',
        '| --- | ---: | --- | --- | ---: | --- | --- | --- |',
    ]
    for group, count in groups.items():
        result = lambda name: ' / '.join(str(count.get(name + '_' + key, 0)) for key in ['wrong', 'placed', 'holds', 'bare'])
        costs = optional_costs[group]
        optional = lambda name: ' / '.join(str(costs[name][key]) for key in ['correct_to_hold', 'hold_to_correct', 'wrong'])
        lines.append(f"| {group} | {count['cases']} | {result('r19')} | {result('r20')} | {costs['r20']['correct_to_hold']} | {optional('role_def')} | {optional('l1')} | {optional('m1')} |")
    lines += ['', '## Preservation, tests and evidence', '',
        'Only new test files were added: `test_placement_r20.py` (530 cases), '
        '`test_placement_r20_boundaries.py` (14 cases), and '
        '`placement_r20_review_cases.py` (copied reviewer inputs). No existing test, '
        'fixture, assertion, evidence file or `.done` marker changed. The exact '
        'competition generator remains in the unchanged r19 support module.', '',
        '- [Full suite](full-suite.txt), [JUnit](full-suite.xml), [test inventory](test-inventory-summary.json).',
        '- [Failing-first counts](test-runs-summary.json), [preservation audit](preservation-summary.json), [fix2 AST equivalence](fix2-equivalence.json).',
        '- [Historical summary](historical-summary.json), [all historical outcomes](historical-cases.json).',
        '- [Review summary](review-summary.json), [all review outcomes](review-cases.json).',
        '- [Per-family hold costs](hold-costs.json), [seven goldens](placements.json), [method and commands](method.md).',
        '', f'Final production SHA-256: `{source_hash}`.', '',
        '**Blockers:** none. The 34-versus-38 baseline discrepancy is disclosed above; '
        'the exact supplied inputs all pass. Project memory, HEAD and index are unchanged.', '',
    ]
    (OUT / 'results-r20.md').write_text('\n'.join(lines))
    # Completion marker is written only after results and all required audits.
    done = [f'coder rc=0 head={head}',
            'failing-first: 185 failed, 359 passed (competition 144; realistic 34; worker 2; boundaries 5 failures).',
            'shipped: B-1 exact fix2; VERSION = c2a.20.',
            'measured only: ROLE_DEF, L-1, M-1; per-family costs in results-r20.md and hold-costs.json.',
            'full suite: 18376 passed, 0 failed, 0 errors, 0 skipped; no -x.',
            'tests: 544 added across two new test modules; new copied reviewer support; all 17832 prior IDs retained.',
            'replay: 29924 required cases plus 40 worker/Q4 checks; 0 blocking wrong; 0 B-1 correct-to-hold; seven goldens exact except analysis_version.',
            'preservation: 1846 starting files hash-verified; only placement.py changed; prior tests/fixtures/evidence/done markers unchanged; no commit or index change.',
            'blockers: none; exact q1real.py baseline is 34 wrong, versus review prose 38; all 48 cases now hold.']
    (OUT / 'counterparty-c2a-r20.done').write_text('\n'.join(done) + '\n')


if __name__ == '__main__':
    main()
