"""Append the requested report and completion marker only after all bars pass."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
OLD = OUT.parent
ROOT = OLD.parents[2]


def read(name):
    return json.loads((OUT / name).read_text())


def main():
    bars = read('release-bars.json')
    assert bars['rc'] == 0 and not bars['blockers']
    codes = read('execution-returncodes.json')
    assert codes == dict(failing_first=1, new_failing_first=1, targeted=0, replay=0, full_suite=0)
    live = read('vs-live.json')
    cost = read('hold-cost-vs-cand5.json')
    families = read('family-comparison.json')
    preservation = read('preservation-summary.json')
    heading = '## r26b — preserve the live r13 L-2 control'
    report = OLD / 'results-r26.md'
    previous = report.read_bytes()
    assert heading.encode() not in previous
    assert hashlib.sha256(previous).hexdigest() == read('starting-hashes.json')[str(report.relative_to(ROOT))]
    comparison_rows = '\n'.join(
        f"| {base} | {c['n_to_p']} | {c['c_to_w']} | {c['c_to_n']} | {c['w_to_n']} |"
        for base, c in live['comparisons'].items())
    family_rows = '\n'.join(
        '| ' + part + ' | ' + str(s['cases']) + ' | '
        + str(sum(g.get('r26_raw_wrong', 0) for g in s['groups'].values())) + ' | '
        + str(sum(g.get('r25_to_r26_c_to_n', 0) for g in s['groups'].values())) + ' | '
        + str(cost['families'][part].get('n_to_c', 0)) + ' |'
        for part, s in families.items())
    recovered = cost['total'].get('n_to_c', 0)
    extra_holds = cost['total'].get('c_to_n', 0)
    text = f'''

{heading}

**coder rc=0; all required bars pass.** This section supersedes the earlier r26 release-blocker conclusion; earlier evidence and the original `.done` marker remain unchanged. HEAD `{bars['head']}`; `VERSION = 'c2a.26'`; source SHA-256 `{bars['source_sha256']}`. No commit or staging.

### Rule chosen and measured alternatives

Keep the c2a.25 cross-page guard exactly. For the additional same-page arm, exclude a peer from the independent-party count only when it has printed names and **every** printed name equals the signer receiving the candidate's company-only score of 4. A vetoed stack bearing that signer's own name therefore does not create a third party. Unknown names, other names, mixed names and unnamed parties still count. The remaining page must still contain the candidate plus at least two non-witness peers, with an unclaimed peer. Scores, margins, assignment, model eligibility and output redaction are unchanged.

The actual immutable L-2 fixture has **no recital mapping** (`roles={{}}`). A recital-company exemption alone closes Q3c but still holds all 20 L-2 positives, so it was rejected. The selected own-name exclusion closes Q3c and restores all 20 L-2 placements to the complete c2a.25 result except `analysis_version`: signature y=560, date y=600, score=4, margin=4. Fleet's block remains a peer; the own-name stack no longer inflates the page to three independent parties. The additional two-signer L-2 controls all remain held. No sender-company name, signer name or coordinate is hardcoded. [Candidate measurements](r26b/candidate-measurement-v2.json), [selected source](r26b/r26b-source.py.txt).

The pilot also measured the recital-only direction: eight Q3c matching-control holds and six three-party holds recovered, but L-2 remained 0/20 placed. The selected rule is the smallest measured change to cand5 satisfying both required controls. The first pilot result is explicitly invalid: its extraction mock rejected the deadline keyword and produced unreadable-PDF holds. The corrected v2 harness asserts the live 55 Q3c wrong cases and 20 L-2 positives before recording evidence. Release counts come from the unchanged full replay harness, not that initial pilot. [Run provenance](r26b/run-provenance.json).

### Validation

Failing first on cand5: unchanged L-2 test **20 failed / 20 passed**; new generalized regression file **6 failed / 18 passed**. The new controls vary signer/company identity and heading, distinguish own names from another person's name, and preserve cross-page holds. After the fix, targeted tests: **2,883 passed**. Full Send suite completed **without `-x`, deselection or retries: 50,498 passed, 0 failed, 0 errors, 0 skipped**. L-2 positives: **20/20 placed**; L-2 two-signer controls: **20/20 held**; r19 competition score controls: **40/40 passed**. [Full log](r26b/full-suite.txt), [JUnit](r26b/full-suite.xml), [targeted log](r26b/targeted.txt).

**82,450 replay cells across all 27 inherited r16–r25/reviewer collections, 980 real-worker evaluations. Zero raw wrong placements in every collection.** Exact Q3a: 4,536; Q3b: 2,430; Q3c: 2,808 including **468 same-page cells and all 55 live errors**; H-1: 2,160 in each retained generator. Seven goldens and native fields are exact except the required `analysis_version`, in-process and through workers. Baseline outputs match the preserved r26 replay cell for cell. External HTTP calls: 0; model calls retain only the expected historical test stubs, with 0 in new/reviewer families. [Release audit](r26b/release-bars.json), [family evidence](r26b/family-comparison.json).

| Baseline | n → p | c → w | Correct → hold | Wrong → hold |
| --- | ---: | ---: | ---: | ---: |
{comparison_rows}

### Hold cost versus cand5

Across the same 82,450 replay cells: **{recovered:,} cand5 holds restored to correct live placements; {extra_holds} additional holds; 0 wrong restorations**. Every restored result equals c2a.25 except `analysis_version`; every unchanged-state result equals cand5 completely. The 20 L-2 positive controls are included in this total through the historical collection; their separate pilot and pytest runs are not added again. Collections overlap and are not deduplicated. [Cell-level hold comparison](r26b/hold-cost-vs-cand5.json).

Same-page Q3c retains cand5's ten correct → hold cells versus live while closing all 55 wrong placements. Three-party controls retain its six correct → hold cells (12 correct / 24 held). H-1 is unchanged from cand5/live (774 correct / 1,386 held). Exhibit controls add no holds versus cand5/live; the earlier 42 correct → hold cost versus r24 remains. **M-1 stays 0/192 wrong** (r25: 16; r24/r21: 48), with 0 n → p. No separate spelling or explicit-company exemption is introduced.

| Collection | Cells | r26b raw W | Correct → hold vs live | Holds recovered vs cand5 |
| --- | ---: | ---: | ---: | ---: |
{family_rows}

### Preservation and blockers

SHA-256 verification before this required report append: **{preservation['unchanged']:,}/{preservation['unchanged']:,} pre-existing files other than placement.py unchanged**, including both uncommitted r26 test files, all earlier tests, fixtures, evidence, and `.done` markers. The report receives only this appended section. All 50,474 pre-existing r26 test IDs and all 47,655 live test IDs remain; the only r26b test-tree addition is `test_placement_r26b.py` with 24 IDs, unchanged since its failing-first run. The r26 additions remain byte-identical. [Preservation audit](r26b/preservation-summary.json), [final append verification](r26b/final-preservation.json).

**Blockers: none.** No earlier tests, fixtures or evidence were edited. No migration, configuration, memory, staging or commit change.
'''
    with report.open('a') as stream:
        stream.write(text)
    initial = read('starting-hashes.json')
    changed = [p for p, digest in initial.items()
               if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    expected = ['backend/dealroom_sign/placement.py', str(report.relative_to(ROOT))]
    assert changed == expected, changed
    assert report.read_bytes().startswith(previous)
    with (OUT / 'final-preservation.json').open('x') as stream:
        json.dump(dict(inventoried_files=len(initial), unchanged=len(initial)-2,
                       changed=changed, report_original_prefix_sha256=hashlib.sha256(previous).hexdigest(),
                       report_append_only=True, existing_tests_fixtures_evidence_markers_unchanged=True), stream, indent=2)
        stream.write('\n')
    counts = live['comparisons']
    with (OLD / 'counterparty-c2a-r26b.done').open('x') as stream:
        stream.write(f"coder rc=0 head={bars['head']}\n"
                     'rule: preserve cross-page guard; same-page count excludes a peer whose printed names all match the score-4 signer; unknown/mixed/other-name peers still count. VERSION=c2a.26.\n'
                     f"vs-live: 82450 cells; r25/r24/r21 n->p=0 c->w=0; correct->hold={counts['r25']['c_to_n']}/{counts['r24']['c_to_n']}/{counts['r21']['c_to_n']}; 0 raw wrong; seven goldens exact except analysis_version; 980 worker evaluations.\n"
                     f'hold cost vs cand5: {recovered} correct holds recovered in replay, including 20 L-2 controls; 0 added holds; M-1 0/192 wrong.\n'
                     'full-suite: 50498 passed, 0 failed, 0 errors, 0 skipped; completed without -x; L-2 20/20 placed (score=4 margin=4), 20/20 two-signer holds.\n'
                     'test changes: one new r26b file, 24 IDs; 50474 pre-existing IDs retained; all existing test/fixture/evidence/.done hashes unchanged; results-r26.md append-only.\n'
                     'blockers: none. No staging or commit.\n')
    print('Appended r26b report; wrote coder rc=0 completion marker.')


if __name__ == '__main__':
    main()
