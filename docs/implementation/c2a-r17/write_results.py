"""Render the verified counts; the completion marker is written separately."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def load(name):
    return json.loads((OUT / (name + '.json')).read_text())


def main():
    data = load('counterfactual-summary')
    old = json.loads((OUT.parent / 'c2a-r16/counterfactual-summary.json').read_text())
    runs = load('test-runs-summary')
    audit = load('preservation-summary')
    counts = runs['full-suite']
    lines = [
        '# C2a r17 RESULT', '',
        '**B-1 and B-2 closed.** Zero wrong placements in every replayed r16 family, A2, the 2,496-case witness sweep, and F. '
        'All seven goldens and native fields are exact except `analysis_version`. `VERSION = \'c2a.17\'`.', '',
        f"Full `dealroom_sign/tests` suite: **{counts['passed']:,} passed, {counts['failed']} failed, {counts['errors']} errors, {counts['skipped']} skipped**, run to completion without `-x` or a test filter.", '',
        'Base/unchanged HEAD: `75837b04da05c3b736d6f48648536627bd062ca0`. No staging or commit.', '',
        '## Changes', '',
        '- **B-1:** Keep witness/attestation blocks in column ownership geometry. The early witness return still yields no names and an ambiguous score, so witnesses score zero. '
        'Also retain explicit witness/attestation rules during extraction when a name is beyond the 22 pt caption window and no heading was attributed. '
        'The measured one-line fix alone closes A2 but leaves 112 wrong placements in the wider sweep because those rules never became blocks. '
        'Rules whose subordinate identity is already quarantined by the absorbed-name veto retain the existing r11 behavior and are not added as candidates.',
        '- **B-2:** Deny the company-score increment when the selected heading row intersects the gutter between same-page blocks whose signature rules are less than 30 pt apart. '
        'This uses the same open-gap intersection rule as printed names. It applies symmetrically, including when one company is not a signer. '
        'A separate mixed-company text parser was unnecessary. Authoritative printed-name scoring is unchanged.',
        '- **N-1:** `test_placement_r16.test_witness_column_never_owns_party_name` now asserts `party.scores == [0]`; '
        '`witness.scores == [0]` remains intact. The witness scores zero, and the party does not gain Pat from the witness column. '
        'This one assertion is the only change to an existing test.', '',
        '## Failing first', '',
        '| Run on r16 | Failed | Passed | Errors | Skipped |',
        '| --- | ---: | ---: | ---: | ---: |',
    ]
    for stem in ['failing-first', 'failing-first-heading']:
        c = runs[stem]
        lines.append(f"| {stem} | {c['failed']} | {c['passed']} | {c['errors']} | {c['skipped']} |")
    lines += ['', 'The first run includes all 480 A2 cases, all 2,496 sweep cases, F permutations and gaps, the two real-worker reproductions with both signer sets, and corrected N-1. '
              'The four direct heading assertions were then run on unchanged r16 and all failed. '
              'The first production candidate (the one-line B-1 fix plus B-2) still failed 112 sweep cases; '
              'retaining the missing witness blocks made all 4,158 targeted cases pass. '
              'The first complete suite then found one existing r11 structural assertion: 1 failed, 15,497 passed, 0 errors/skipped. '
              'No test was edited: narrowing retention around the existing absorbed-name veto restored that assertion. '
              'The unchanged r11 test passed, then all 5,399 combined targeted cases passed with 0 failures/errors/skips before the final full-suite result above. '
              'The complete unsuccessful suite is retained in `retained-witness-candidate/full-suite.*`.', '',
              '## Per-family results', '',
              'Cells are **wrong / placed / holds / bare**. Wrong is counted within placed, not as another status. '
              'Every emitted field in the new families is checked against its signer’s own rule. '
              'The original family oracles and generators are reused unchanged. The 72-case r14 L-1 subset is listed separately and is already included in the r14 grid.', '',
              '| Family | Cases | r16 | r17 |', '| --- | ---: | --- | --- |']
    def cell(c, version):
        return ' / '.join(str(c[version + '_' + key]) for key in ['wrong', 'placed', 'holds', 'bare'])
    for group, c in data['groups'].items():
        lines.append(f"| {group} | {c['cases']} | {cell(c, 'r16')} | {cell(c, 'r17')} |")
    lines += ['', 'Original r16 table totals exclude the overlapping 72-case L-1 subset:', '',
              '| Source | Cases | Wrong | Placed | Holds | Bare |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for version in ['r16', 'r17']:
        groups = [data['groups'][g] for g in old['groups'] if g != 'r14 L-1 (grid subset)']
        totals = [sum(g[version + '_' + k] for g in groups) for k in ['wrong', 'placed', 'holds', 'bare']]
        lines.append('| ' + version + ' | ' + str(sum(g['cases'] for g in groups)) + ' | ' + ' | '.join(map(str, totals)) + ' |')
    lines += ['', '## Matrix definitions and optional L-1', '',
              '- **A2 (480):** six exact captions × dy {0, 40, 60, 80, 100} × four headings × both orientations × PAT/DAN+PAT. '
              'The review’s verbal dy 0–100 axes would also include 20; those 96 additional cases are measured separately, so all six staggers are covered.',
              '- **Wider sweep (2,496):** Witness:/Attest: × dy 0–120 in 10 pt steps × name gaps 12/24/40 × our printed name off/on × '
              'HARBOR / Harbor Light / RECIPIENT: / no heading × both orientations × PAT/DAN+PAT. '
              'Both orientations make the stated count 2,496; the axes without orientation yield 1,248. r16 reproduces the review’s 184 wrong.',
              '- **F (288):** six party permutations × six Fleet staggers {0,20,40,60,80,100} × short/long Harbor heading × our printed name off/on × PAT/DAN+PAT. '
              'The rule gap is 22 pt. This explicit reconstruction reproduces the verbatim B-2 case and has 8 r16 wrong; it is not claimed to be the reviewer’s unpublished exact 3/288 matrix.',
              '- **F gaps (864):** gaps 8/16/22/28/34/40 × short/long headings × six permutations × six staggers × PAT/DAN+PAT, without our printed name. '
              'All fields must remain on Fleet’s or Harbor’s own signature/date rule; Northwind is never an allowed signer block.',
              '- **L-1 experiment:** an in-memory candidate merges column ranges with at least 80% overlap relative to the larger width. '
              'It is measured on the entire table plus new ragged (384) and centred (144) controls. These new controls have explicit axes in `l1_candidate.py`; '
              'they are not asserted to be the reviewer’s unpublished matrices behind the 150 correct-to-hold count.', '',
              '| L-1 candidate family | Cases | r17 | Optional merge |', '| --- | ---: | --- | --- |']
    for group, c in data['groups'].items():
        if group.startswith('L1 ') or c['l1_wrong'] or any(c['l1_' + key] != c['r17_' + key] for key in ['placed', 'holds', 'bare']):
            lines.append(f"| {group} | {c['cases']} | {cell(c, 'r17')} | {cell(c, 'l1')} |")
    lines += ['', '**L-1 dropped:** six direct extracted-block checks reintroduce B-1: r16 6 wrong/0 holds, r17 0 wrong/6 holds, optional merge 6 wrong/0 holds. This extends N-1 to overlapping witness/party ranges and emits actual signature/date fields. It is not a PDF extraction reproduction. See [decision](l1-decision.md) and [all placements](l1-witness-overlap.json). The review’s 150 correct-to-hold layouts are not claimed recovered.', '',
              '## Evidence and preservation', '',
              f"- SHA-256 checked all {audit['tracked_files_hash_checked']:,} initially tracked files. Only `placement.py` and the exact N-1 assertion differ; all other existing tests, fixtures, golden archives, and evidence are byte-for-byte unchanged. Memory is unchanged.",
              f"- {data['worker_evaluations']} real-worker evaluations match their in-process counterparts, including the seven goldens, prior reproductions/controls, and B-1/B-2. No external HTTP calls; model callbacks are local deterministic stubs.",
              '- The one-line B-1-only variant preserves every r16 family’s wrong/placed/hold/bare count. The final r17 preserves every original full result except analysis_version: 0 full-result differences across the original 10,770 evaluations. r8 C7 remains 0 wrong / 5 placed / 0 holds, with all five model calls and complete results unchanged; its scores and margins are therefore unchanged.',
              '- All 11,362 original test cases remain in the completed suite; 4,136 new cases were added. [Test inventory audit](test-inventory-summary.json).',
              '- [Full suite log](full-suite.txt), [JUnit](full-suite.xml), [all outcomes](full-suite-cases.json), [suite summary](full-suite-summary.json). '
              'The unchanged launcher’s scratch-directory warning is retained; pytest itself completed successfully.',
              '- [Replay runner](check_evidence.py), [per-family counts](counterfactual-summary.json), [all cases/results](counterfactual-cases.json), '
              '[worker checks](counterfactual-workers.json), [goldens](placements.json), [hash audit](preservation-summary.json), '
              '[test-run counts](test-runs-summary.json), [commands/method](method.md).', '',
              '**Blockers:** none.', '']
    (OUT / 'results-r17.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
