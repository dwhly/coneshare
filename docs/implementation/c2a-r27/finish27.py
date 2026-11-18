"""Write the report, then the completion marker, only after the release audit."""
from pathlib import Path
import json

OUT = Path(__file__).resolve().parent


def read(name):
    return json.loads((OUT / name).read_text())


def main():
    bars = read('release-bars.json')
    assert bars['rc'] == 0 and not bars['blockers']
    live = read('vs-live.json')
    families = read('family-comparison.json')
    preservation = read('preservation-summary.json')
    ordinary = read('ordinary-hold-cost.json')
    new = read('new-family-audit.json')
    controls = read('measured-controls-summary.json')
    comparison_rows = '\n'.join(
        f"| {base} | {c['n_to_p']} | {c['c_to_w']} | {c['c_to_n']} | {c['w_to_n']} |"
        for base, c in live['comparisons'].items())
    new_rows = '\n'.join(
        f"| {base} | {c['n_to_p']} | {c['c_to_w']} | {c['c_to_n']} | {c['w_to_n']} |"
        for base, c in live['new_comparisons'].items())
    family_rows = '\n'.join(
        f"| {part} | {summary['cases']:,} | 0 | "
        f"{sum(g.get('r26_c_to_n', 0) for g in summary['raw_groups'].values())} |"
        for part, summary in sorted(families.items()))
    report = f'''# C2a r27 results

**coder rc=0.** `VERSION = 'c2a.27'`. All release checks below passed. The working tree is uncommitted; base HEAD is `{bars['base_head']}` (c2a.26), and the tested r27 source SHA-256 is `{bars['source_sha256']}`. HEAD identifies the base commit, not a committed r27 revision. [Provenance](run-provenance.json), [release audit](release-bars.json).

## Shipped

**B-1:** ship the reviewer's measured `r26c` restriction. A printed-name peer exemption applies only when there is no recital mapping, or the block under consideration matches a mapped recital company. A matching printed name therefore cannot suppress the guard for an affiliate outside the recital parties. Scores and margins are unchanged.

**B-2:** retain an otherwise undetected drawn rule as an **unclaimed peer**, without making it eligible for assignment, when its next aligned row is `Name:` (within the existing 22-point caption band) and an aligned `Date:` rule follows within the existing 125-point companion band, without an intervening signing rule. This is independent of caption vocabulary. The hidden peer participates in the guard with the same recital-bound name exemption. Its temporary name evidence is cleared before worker serialization. Existing attribution, scoring, geometry, assignment, model eligibility, and output redaction functions are unchanged. [Source audit](source-audit.json), [tested source](r27-source.py.txt).

The requested captions and additional `Autograph:`, `Conforme:`, and blank-caption controls are covered. `Signed:` was already recognised and keeps its correct placement. No new placement is enabled by the structural rule.

## Failing first and exact reproductions

Final regression tests on untouched c2a.26: **104 failed / 1,822 passed / 0 errors / 0 skipped**. Failures comprise 18 A, 8 B, 60 E, and 18 supplementary caption cells. On r27, these tests plus immutable L-2 and r26b controls give **1,990 passed / 0 failed / 0 errors / 0 skipped**. [Failing-first log](failing-first-final.txt), [JUnit](failing-first-final.xml), [targeted result](targeted-final.txt).

The exact r26 transcript loops produce **4,461 cells**: A 1,512; B 96; C 72; D 189; E 2,592 (1,296 affiliate and 1,296 separate-own-company controls). Attack E reproduces **50 WWW** cells against r25/r26/cand5, including **30 with recitals**. All 30 recital-present B-2 errors now hold. The separate B-1 E cohort contributes another **30 W → hold**. The full blocking scope closes **86 r26 errors**: A 18, B 8, E 60.

The reviewer's smaller measured `r26c` subset is also exact: **A 6/6, B 8/8, E 30/30 W → hold**. Immutable r13 L-2: **20/20 placed at y=560/600 with score=4 and margin=4; 20/20 two-signer holds**. [Exact new-family baseline](baseline-v2/summary.json), [candidate comparison](candidate/summary.json), [measured subset](measured-controls-summary.json).

The full transcript E loop contains 1,296 affiliate cells, correcting the review prose's 1,200; the reported 50/30 error cohorts reproduce exactly. Across all new loops, **1,499 no-recital outputs are byte-equivalent to r26 after removing only `analysis_version`**. The review's no-recital L-2-equivalent controls, one-signer shared-name B controls, and explicitly name-authoritative D/own-company controls remain visible with their raw geometry flags in the evidence. Their **346 retained raw geometry flags** are unchanged from r26 and remain outside the reviewer's blocking scope; no case is removed from the run. All recital-present A, two-signer B, and affiliate E cells have **0 raw wrong placements**. [Scope and retained raw flags](new-family-audit.json), [complete compressed cases](candidate/cases.json.gz).

The exact real-worker reproduction bodies (r26 calls 29 and 43) ran on r26 and r27: baseline 10 wrong cases, r27 all 18 held, with worker/in-process equality throughout; **0 HTTP calls and 0 model calls**. Supplementary caption controls and the refined vocabulary comparison add 44 worker checks. Together with 980 inherited worker evaluations, total **1,060 worker evaluations**. [Worker reproductions](worker-reproductions.txt), [caption controls](measured-controls-cases.json.gz).

## Alternatives, low item, and nits

Two vocabulary-only peer variants were measured on all 4,461 new cells and the exact measured subset. Counting matching captions as unnamed peers closes the known errors with 0 n → p but holds **all 20 immutable L-2 positive controls**. A refined variant that also retains printed-name evidence preserves all 40 L-2 outcomes and closes the known A/B/E errors with 0 n → p. It still leaves **4 wrong placements** in the additional `Autograph:`/`Conforme:` controls, whereas the structural rule holds all four. The structural rule therefore preserves L-2 and covers captions outside the enumerated vocabulary. [Refined vocabulary matrix](vocabulary-names/summary.json), [refined controls](vocabulary-names-controls-summary.json). Plain `r26c` alone leaves the **30 recital-present B-2 errors**, confirming that both fixes are needed.

**L-1 rejected:** the explicit-company exemption still has 0 wrong placements over the 576 exhibit cells but produces **28 n → p against each of r26, r25, and r27**. The strict monotonic bar prohibits shipping it. [Low-item measurement](low-exemption-measurement.json).

**N-1:** Q3a is **4,536** cells; Q3c's same-page portion is **468** cells. **N-2:** new provenance separates `base_head`, `working_tree_version`, and `source_sha256`; old evidence remains byte-identical.

## All inherited families and monotonic comparisons

**82,450 cells across all 27 inherited r16–r26/reviewer collections; 0 raw wrong placements in every collection.** Q3a 4,536; Q3b 2,430; Q3c 2,808 including 468 same-page cells; both H-1 generators 2,160 each. All seven goldens, native fields, and real-worker outputs are exact except `analysis_version`. Historical baseline outputs match preserved r26 evidence cell for cell. Collections overlap and are not deduplicated. [Per-family audit](family-comparison.json), [comparison totals](vs-live.json).

Inherited collections:

| Baseline | n → p | c → w | Correct → hold | Wrong → hold |
| --- | ---: | ---: | ---: | ---: |
{comparison_rows}

New exact review collections (separate totals):

| Baseline | n → p | c → w | Correct → hold | Wrong → hold |
| --- | ---: | ---: | ---: | ---: |
{new_rows}

The two new correct → hold cells versus r26 are three-block shared-name B controls with an explicit-company signer and a role-only own block. They are not ordinary two-party documents.

**Ordinary two-party hold cost versus r26 and r25: 0.** This is measured separately on {ordinary['ordinary_ndas']['cases']} ordinary NDA cells, {ordinary['exhibits']['cases']} NDA/exhibit/guarantee/witness/notary/joinder cells, and the ordinary MSA subsets of Q3b and aligned Q3b. [Ordinary hold-cost evidence](ordinary-hold-cost.json).

| Collection | Cells | r27 raw W | Correct → hold vs r26 |
| --- | ---: | ---: | ---: |
{family_rows}

## Full suite and preservation

The **full Send suite completed without `-x`, deselection, retries, or skips: 52,424 passed, 0 failed, 0 errors, 0 skipped**. All 50,498 prior test IDs remain, including the live r13 L-2 controls. New files add 1,926 test IDs. [Full log](full-suite.txt), [JUnit](full-suite.xml), [counts](full-suite-summary.json).

SHA-256 verification: **{preservation['unchanged']:,} / {preservation['unchanged']:,} pre-existing tracked files other than placement.py unchanged**, including every existing test, fixture, earlier implementation evidence file, and `.done` marker. Only two new test-tree files were added. Their final assertions are frozen from the final failing-first run through the full suite. No old test was changed, skipped, weakened, deleted, or retargeted. New evidence JSON files are all below 20 MB; large cell dumps are gzip-compressed. [Preservation audit](preservation-summary.json).

Harness provenance is retained rather than overwritten. Early new-test drafts incorrectly demanded a hold for an already-correct `Signed:` block and included name-authoritative single-signer B controls; those drafts and runs remain archived. The final tests were corrected before the final failing-first run. The first broad new replay also incorrectly asserted zero synthetic model-stub calls; exact transcript loops actually make 600 per revision, unchanged across all variants, with 0 HTTP calls. The measured subset makes 60 per revision. Real-worker reproductions and supplementary captions make 0 model calls.

The first historical replay reached an old-schema capture assertion: the immutable r15 harness combines an r14 extractor with today's `prepare_blocks`. The new r27 adapter supplies only the new metadata's empty default on those legacy generator objects. Revision scorers, production parsing, existing assertions, fixtures, and the full suite are untouched. The historical collection was rerun completely; its original failure log is retained. [Successful historical rerun](historical-retry.txt), [effective replay return codes](effective-replay-returncodes.json).

**Blockers: none.** No staging, commit, migration, configuration, memory, or earlier evidence changes.
'''
    with (OUT / 'results-r27.md').open('x') as stream:
        stream.write(report)
    with (OUT / 'counterparty-c2a-r27.done').open('x') as stream:
        stream.write(f"coder rc=0 head={bars['base_head']}\n")
        stream.write('failing-first: 104 failed, 1822 passed, 0 errors, 0 skipped on untouched r26; E 50 WWW, 30 recital-present; A/B/E blocking scope 86 W.\n')
        stream.write('shipped: VERSION=c2a.27; measured r26c recital-bound printed-name exemption plus structural Name/Date unclaimed peers. Vocabulary-only and explicit-company alternatives rejected. Nits corrected only in new report/provenance.\n')
        stream.write('vs-live: 82450 inherited cells + 4461 new review cells; r26/r25/r21 n->p=0 c->w=0; 0 wrong in required blocking scope and all inherited families; seven goldens exact except analysis_version; ordinary two-party added holds=0.\n')
        stream.write('full-suite: 52424 passed, 0 failed, 0 errors, 0 skipped; no -x; all 50498 prior IDs retained. Targeted 1990 passed. L-2 20 placed/20 two-signer holds.\n')
        stream.write(f"test changes: two new files, 1926 IDs; {preservation['unchanged']} existing file hashes unchanged except placement.py; no existing tests/fixtures/evidence/.done edits. New large dumps gzip; JSON files under 20 MB.\n")
        stream.write('blockers: none. Historical capture schema adapted only in new replay harness and completely rerun; full suite ran once to completion. No staging or commit.\n')
    print('Wrote results-r27.md, then counterparty-c2a-r27.done.')


if __name__ == '__main__':
    main()
