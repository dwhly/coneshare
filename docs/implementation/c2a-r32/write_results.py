"""Write the release result after every requested run and preservation check."""
from collections import Counter
import gzip
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]

def read(name):
    path=OUT/name
    with (gzip.open(path,'rt') if name.endswith('.gz') else path.open()) as stream:
        return json.load(stream)

bars=read('release-bars.json');families=read('family-comparison.json');tests=read('test-audit.json')
counts=bars['full_suite'];first=Counter()
for c in tests['failing_first'].values():first.update(c)
rows=read('shipping-date-cases.json.gz')
recovered=[r for r in rows if r['states']['r29']=='n' and r['states']['r32']=='c']
lost=[r for r in rows if r['states']['r31']=='c' and r['states']['r32']=='n']
date_breakdown={label:{axis:dict(Counter(str(r['axes'][axis]) for r in subset)) for axis in ('recital','signer','datefirst','layout')}
                for label,subset in [('retained',recovered),('given_up',lost)]}
(OUT/'date-recovery-breakdown.json').write_text(json.dumps(date_breakdown,indent=2)+'\n')
prior=read('preservation-summary.json')
q3=('misspell','misspell_sender','role_other','same_company','prev_column','affiliate_sender')
q3tot=Counter()
for name in q3:q3tot.update(families['review/'+name])

def row(name,c):
    return f"| {name} | {c['cells']:,} | {c['r29_wrong']} / {c['r32_wrong']} | {c['n_to_p']} | {c['c_to_w']} | {c['n_to_W']} | {c['c_to_hold']} |"

lines=[
'# C2a r32 results',
'',
f"**coder rc={bars['coder_rc']}. `VERSION = 'c2a.32'`. M-1 is fixed in the worktree; the requested release bar is blocked.** HEAD remains `{bars['head']}`; live base is c2a.29 (`0aa3cbbb`). No staging, commit, deployment or memory update. Source SHA-256 `{bars['source_sha256']}`.",
'',
f"The exact r31 Q3 matrices have **{q3tot['r32_wrong']} wrong / {q3tot['cells']:,} cells**, including all 576 affiliate regressions now held. **{len(recovered)}/686 M-1 recoveries survive**; {len(lost)} return to holds. All live-r29 correct placements are retained in the release matrices; every family has **c → w = 0 and n → W = 0**. All newly placed cells are correct and recorded in [every-n-to-p.json.gz](every-n-to-p.json.gz).",
'',
f"The complete Send suite finished without `-x`: **{counts['passed']:,} passed / {counts['failed']} failed / {counts['errors']} errors / {counts['skipped']} skipped**. All {counts['failed']} failures are the immutable `test_placement_r30_recoveries.py` expectations for the 200 domain-only/no-recital recoveries now required to hold. No test was changed, weakened, skipped or retargeted. [Full completion](shipping-full-suite-completion.json), [exact failing IDs](test-audit.json).",
'',
'## Worktree implementation',
'',
'Only `extended_date_names_owned` changes behavior. The >22 pt band requires an explicit company with identical normalized word tokens, allowing trailing legal-suffix folding, or a recital that maps the block to that signer. Word boundaries, substantive words and digits remain significant; no prefix, sub-span or joined-token match can establish explicit ownership. A domain alone cannot certify an unrecited company, including `HARBORLIGHT, LLC`. Recital mapping retains the existing unique domain association and conflicting-party veto.',
'',
'An unclaimed ruled block on any other page vetoes expansion when its direct company heading is stronger than the current role heading, or is an exact company match where the current heading is only a hint. This includes drawn lines and underscore rules, in either page order. Existing same-page, intervening-rule and unclaimed-stack checks remain in effect. A failed guard returns to the r29 22 pt hold. Unrequested names retain their existing non-signable competition behavior.',
'',
'N-2 is a comment-only clarification: 110 pt is the extraction floor that excludes unlabelled header rules. N-1 is verified by both Git HEAD/diff and SHA-256. An AST comparison confirms that every function outside the widened-band ownership predicate is unchanged from r31. [Structural proof](structural-proof.json), [tested source](shipping-source.py.txt), [source provenance](source-provenance.json).',
'',
'## Exact extraction and failing first',
'',
'Extracted 55 Bash command payloads, their 27 heredoc bodies, all four Write payloads, and both Edit payloads from the requested Gate 3 r31 JSONL. The original `own.py`, the exact successful filter edit, `aff_repro.py` and `b1_close.py` are preserved byte-for-byte under `backend/dealroom_sign/tests/fixtures/r32/`. Twelve copied r30 scripts were reconstructed using the exact r31 transcript transformation; the inherited `inh.py` wrapper was reconstructed by executing the exact line-286 transformation against the frozen r29 payload with in-memory I/O. The generator bodies remain unchanged. [Extraction provenance](extraction-provenance.json), [byte verification](extraction-verification.json), [inherited wrapper](inherited-generator-provenance.json), [body equality](generator-body-verification.json).',
'',
f"Before production edits, untouched c2a.31 produced **{first['failed']} failed / {first['passed']:,} passed / 0 errors / 0 skipped**:",
'',
'- Exact affiliate matrix: 576 failed / 14,004 passed; six exact real-worker variants: six failed.',
'- Exact-company and cross-page checks: nine failed / three passed.',
'- Underscore-rule cross-page checks: two failed.',
'',
'All new assertions and fixtures used in failing-first runs are hash-identical to their snapshots. The subsequently reconstructed inherited wrapper is verified separately against its extraction hash. Three new test files add 14,600 cases; one helper loads the exact reviewer generators. [Failing first](failing-first.txt), [ownership](ownership-failing-first.txt), [underscore rules](rules-failing-first.txt), [preservation](preservation-summary.json).',
'',
'## M-1 recovery tradeoff',
'',
f"Retained: **{len(recovered)}**. Given up: **{len(lost)}**, all with no parsed recital (120 domain-only Pat cases; 80 two-signer cases). This affects no placement live r29 already made. The immutable 686-recovery test explicitly demands the former r30/r31 behavior, so the requested stricter ownership rule and a zero-failure unmodified suite cannot both be satisfied. [All 2,844 cells](shipping-date-cases.json.gz), [breakdown](date-recovery-breakdown.json).",
'',
'| Axis | Retained recovery counts |',
'| --- | --- |',
]
for axis,c in date_breakdown['retained'].items():lines.append(f"| {axis} | `{c}` |")
lines += [
'',
'## Measurement only: the live 16–20 pt policy',
'',
'**1,692 / 5,832 cells** in the affiliate Q3 generator place Pat under an affiliate heading at gap 16 or 20 pt on live c2a.29. This measurement changes only the gap axis of the archived generator, from `(24, 30, 36, 44, 50)` to `(16, 20)`; the fixture itself is untouched. The other cells are 3,582 holds and 558 oracle-correct placements. Separately, the reviewer’s exact five-heading/signer worker-sweep subset gives **72 wrong / 90 cells** (18 holds). These are distinct inventories, not additive unique cases.',
'',
'r32 produces identical outputs to live on both narrow-band inventories, except `analysis_version`; no narrow-band policy change ships. [5,832-cell measurement](shipping-narrow_affiliate_matrix-summary.json), [90-cell measurement](shipping-narrow_affiliate-summary.json).',
'',
'The 1,692 measured flags split evenly by gap: 846 at 16 pt and 846 at 20 pt. By heading: `HARBOR LIGHT GROUP, INC.` 558; `HARBORLIGHT, LLC` 558; `HARBOR LIGHT ANALYTICS HOLDINGS, LLC` 576.',
'',
'## Every live comparison',
'',
'`Wrong` below is the unadjusted reviewer oracle, with no inherited-policy exemptions. The release inventories overlap; counts are not deduplicated. Narrow-band measurement families are listed separately at the end. Every n → p is oracle-correct; all n → W and c → w counts are explicit. [Machine-readable comparisons](family-comparison.json), [every raw-oracle flag](every-strict-wrong.json.gz).',
'',
'| Family | Cells | Wrong live / r32 | n → p correct | c → w | n → W | c → hold |',
'| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
]
for name,c in families.items():
    if 'narrow_affiliate' not in name:lines.append(row(name,c))
lines+=['',
'The inherited raw-oracle flags are unchanged outputs from live. Some are the historical L-2 own-company controls; others include actual name-authoritative/affiliate placements, such as the r27 A-family placement under `HARBOR LIGHT GROUP, INC.`. They are disclosed as raw flags, not relabelled into a zero-wrong claim. Eliminating the pre-existing cases would require widening this task’s scope and resolving the preserved policy controls. The r13 L-2 test remains intact and passes.',
'',
'| Measurement-only family | Cells | Wrong live / r32 | n → p correct | c → w | n → W | c → hold |',
'| --- | ---: | ---: | ---: | ---: | ---: | ---: |',
]
for name,c in families.items():
    if 'narrow_affiliate' in name:lines.append(row(name,c))
lines += [
'',
'All seven goldens and native-field conversions are exact except `analysis_version`. All 21 inherited reviewer worker cases remain holds and equal in-process results; the full suite also includes all 36 B-1 workers and the six new affiliate worker cases. HTTP calls are zero in the comparison runs; model-call counts match live per cell. [Goldens](golden-audit.json), [workers](shipping-exact-workers.json).',
'',
'The current reviewer matrices execute fresh live-r29, r31 and r32 modules. The 27 inherited collections and eight prior-review families execute r32 on every generated cell and compare against immutable r29 output archives, with case keys/axes checked and baseline sources verified against Git. Historical r21/r28 columns remain available in their evidence; release comparisons use r29.',
'',
'## Full-suite completion and preservation',
'',
'Command: `PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r32/run_full_suite_shipping.py`.',
'',
f"Four isolated pytest processes completed all **94,688 collected IDs**, with separate scratch SQLite databases, no `-x`, retries, skip filters or omitted test IDs. All **80,088 pre-existing IDs** are preserved, plus 14,600 new IDs. The merged JUnit IDs match collection exactly. [Manifest](shipping-full-suite-manifest.json), [JUnit](shipping-full-suite-complete.xml), [completion](shipping-full-suite-completion.json).",
'',
f"SHA-256 verifies **{prior['unchanged']:,}/{prior['starting_files']:,} pre-existing tracked files unchanged**; only production `placement.py` differs. Every old test, fixture, implementation evidence file and `.done` marker is preserved, including all {prior['old_test_tree_files']} old test-tree files. No staging or commit. Every new evidence file is under 20,000,000 bytes. [Preservation](preservation-summary.json), [size audit](evidence-size-audit.json).",
'',
'**Blockers:** (1) 200 frozen all-686 recovery assertions conflict with the exact-ownership requirement; (2) the absolute strict-oracle zero-wrong bar includes pre-existing live placements outside the authorized >22 pt change. No existing tests or evidence were altered to conceal either conflict. The `.done` marker therefore reports `coder rc=1`.',
]
(OUT/'results-r32.md').write_text('\n'.join(lines)+'\n')
# The completion marker is written only after the report exists.
marker=[f"coder rc={bars['coder_rc']} head={bars['head']}",
        f"failing-first: {first['failed']} failed, {first['passed']} passed, 0 errors, 0 skipped on untouched c2a.31; exact affiliate 576 + worker 6 + ownership 9 + underscore 2 failures.",
        "what shipped in worktree: VERSION c2a.32; widened-band exact explicit-company or recital ownership; stronger cross-page unclaimed ruled-heading veto; N-2 comment. Not release-ready; no commit.",
        f"vs-live: Q3 {q3tot['cells']} cells, {q3tot['r32_wrong']} wrong; 576 affiliate regressions held; M-1 {len(recovered)}/686 recoveries; every family c->w=0, n->W=0; every correct n->p recorded. Seven goldens exact except analysis_version.",
        f"strict raw-oracle flags in overlapping release inventories: {bars['totals']['r32_wrong']}, all unchanged from live; narrow-band measurement only 1692/5832 and 72/90, unchanged.",
        f"full-suite: {counts['passed']} passed, {counts['failed']} failed, {counts['errors']} errors, {counts['skipped']} skipped; all 94688 IDs completed without -x.",
        "test changes: additions only: 3 files, 14600 tests, 1 generator helper, 102 frozen reviewer fixtures; all pre-existing files hash-verified except placement.py.",
        "blockers: 200 immutable r30 recovery assertions require domain-only/no-recital expansion now forbidden; absolute strict-oracle zero conflicts with preserved pre-existing live behavior outside this task's scope."]
(OUT/'counterparty-c2a-r32.done').write_text('\n'.join(marker)+'\n')
print('\n'.join(marker))
