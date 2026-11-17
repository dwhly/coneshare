# C2a r13 — absorbed caption label and rule

Base: `4ad9f7e20822ca15e8c5a5196f8b61c8cb59a312` on
`agent/c1b-counterparty`. Review: `counterparty-c2a-gate3-r12.md`, read in full.
The requested change is fix A′ only: the absorbed caption rectangle is
`[min(label.x0, line.x0), label.y0, max(label.x1, line.x1), line.y]`.
Fix A's existing same-page containment test consumes that rectangle. Host
selection, extent construction, scoring, exemptions, partitioning, and the
worker payload remain unchanged. The requested version is `c2a.13`.

## Failing first

On byte-for-byte `4ad9f7e2` product source, the new file completed with
**573 failed, 376 passed, 0 errors, 0 skipped, in 234.430 seconds**. These counts
were recorded here before the production edit. All failures were placements
where a hold was required: the reproduction (1), same-band grid (32 of 42),
and short-caption sweep (540 of 864). All 42 Low controls passed.
[Summary and source hashes](failing-first-summary.json) ·
[Every case](failing-first-summary-cases.json).

The new file contains **949 real-worker cases**: one verbatim B-1 reproduction,
42 same-band cases (seven captions × three caption x positions × two dy
values), 864 sweep cases, two L-1 controls, and 40 L-2 controls. Every B-1 hold
requires `needs_sender/ambiguous_identity`, no fields, and zero model calls.
HTTP sends are forbidden and model environment configuration is removed by
the existing `no_network` fixture. No existing test is edited or skipped.

The sweep uses the six specified short captions, caption x 200/230/260/280,
right-column x 300/330/360, dy 0/20, and plain/prefixed names. Its top variants
are FLEET on the left only, FLEET on both columns, and left FLEET with
`RECIPIENT:` between the rules and caption. The separate verbatim reproduction
includes both FLEET headings and `RECIPIENT:` together. All coordinates and
case identifiers are defined in `test_placement_r13.py`.

## Review Low and Nit

**L-1:** A short rule ending at x285, with a `Firma:` label at x150 or x200,
stays entirely before the right block's left edge x290. Pat's printed name at
x340 remains authoritative under that FLEET-headed column. These two controls
pin the residual printed-name policy: signature y290/date y400, high confidence,
and zero model calls. They do not claim to recreate the review's unspecified
36-case grid, and do not broaden this gate into a scoring-policy change.

**L-2:** Matrix 1 plus HARBOR at y520, `By:` at y560 and `Date:` at y600 is tested
across five captions, four recipient headings, and PAT-only/Dan+Pat signer
sets. PAT-only places on Pat's own company line (score 4, margin 4); Dan+Pat
holds. These 40 controls pin the existing company-only behavior and require
zero model calls. No new reassignment policy is introduced.

**N-1:** The r12 EDD note and preservation audit describe their execution-time
tree, before the manager committed r12 as `4ad9f7e2`. Their `HEAD_unchanged`
claim applies to that pre-commit run based on `0c190e9b`; it is not a statement
about today's HEAD. Historical evidence stays intact. This r13 run starts on
`4ad9f7e2` and performs no staging or commit.

## Reproduction

```bash
# Before applying the product fix, on 4ad9f7e2:
python3 docs/implementation/c2a-r13/run_summary.py failing-first-summary dealroom_sign/tests/test_placement_r13.py

# After applying the fix; stops and records any unexpected full-result change:
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r13/check_evidence.py

# Full requested signing suite, with compact per-case reporting:
python3 docs/implementation/c2a-r13/run_summary.py full-suite-summary dealroom_sign/tests

# Scope, baseline provenance, and unchanged-test audit:
python3 docs/implementation/c2a-r13/check_preservation.py
```

The summary runner invokes
`SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests`
with only `--tb=short` and a temporary JUnit report added. It retains compact
JSON summaries and every case outcome, then removes the temporary XML.

## Executed counterfactual table

`check_evidence.py` loads the exact committed r11 and r12 sources into separate
in-memory modules and compares them with the working r13 product. Each case
uses `place` with `bounded_extract` replaced by `extract` + `prepare_blocks`,
matching the review's counterfactual method. Goldens also run through the real
worker, and pytest exercises every new test through that worker.

All **2,699 cases** completed. Complete results are compared after removing only
`analysis_version`; no other field is normalized. The runner stops, saves the
case/results, and appends a STOP entry here on an unexpected difference.
**Unexpected differences: 0.**

| Family | Cases | r11 placed | r12 placed | A′ placed | r12 vs r11 full diffs | A′ vs r12 full diffs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Matrix 1 | 120 | 120 | 0 | 0 | 120 | 0 |
| Matrix 2 | 270 | 135 | 0 | 0 | 270 | 0 |
| r11 B-1 | 1020 | 0 | 0 | 0 | 0 | 0 |
| Signature controls | 204 | 6 | 6 | 6 | 0 | 0 |
| M-1 | 16 | 16 | 16 | 16 | 0 | 0 |
| r9 heading matrix | 72 | 6 | 6 | 6 | 0 | 0 |
| r9 H-1 | 40 | 0 | 0 | 0 | 0 | 0 |
| Seven goldens | 7 | 6 + bare | 6 + bare | 6 + bare | 0 | 0 |
| Same-band right host | 1 | 1 | 0 | 0 | 1 | 0 |
| r12 B-1 reproduction | 1 | 1 | 1 | 0 | 0 | 1 |
| r13 same-band grid | 42 | 42 | 32 | 0 | 10 | 32 |
| r12 B-1 sweep | 864 | 864 | 540 | 0 | 324 | 540 |
| L-1 short-rule controls | 2 | 2 | 2 | 2 | 0 | 0 |
| L-2 own-company controls | 40 | 20 | 20 | 20 | 40 | 0 |

The 573 full-result differences are exactly the failing-first placements
changed into holds: 1 reproduction + 32 same-band grid + 540 sweep. There are
**0 differences across the original 1,750 preserved cases** (including the
original same-band case), and 0 across the 42 Low controls. The reviewer text
says 1,751, but its enumerated table sums to 1,750. No case is omitted.

Matrix 2's 270 r12-vs-r11 full differences include 135 Dan+Pat cases whose
status was already a hold but whose assignments changed. L-2 also has 40
r12-vs-r11 full differences despite identical placement totals; all of those
r12 results remain exact in r13. These are historical differences, not new
r13 behavior.

[Counterfactual summary](counterfactual-summary.json) ·
[Every full result and case](counterfactual-cases.json). Results are deduplicated
by SHA-256 without dropping any result keys or case identifiers. All
non-golden cases make zero model calls. Both model environment variables are
removed, clients are local mocks, and HTTP sends raise. External calls: **0**.

## Goldens

All **seven complete real-worker results match r4, r5, r11, and r12 exactly
except `analysis_version`**. Native field conversions also match. Six pass
`assert_golden`; `bare` remains bare with no fields. Only `unusual` calls its
local confirming stub once; the other six make zero calls.
[Placements](placements.json) · [Exact comparison](golden-comparison.json).

## Full suite and preservation

**4,250 passed, 0 failures, 0 errors, 0 skipped, 82 warnings, in 1,178.745
seconds.** This is all 3,301 existing cases plus 949 new cases. The requested
full-suite command ran with reporting arguments only; no stop, selection, or
skip flag was added. [Summary](full-suite-summary.json) ·
[Every test outcome](full-suite-summary-cases.json).

The [preservation audit](preservation-summary.json) passes: all **51 existing
test and fixture files** are byte-for-byte unchanged; the new test file is
identical between failing-first and final execution; the production hash is
identical between the counterfactual and final-suite runs. The complete
product source equals r12 with exactly the requested union rectangle and
version substitution. No other product change is present.

The report is append-only, project memory and the index are unchanged,
`git diff --check` passes, and HEAD remains
`4ad9f7e20822ca15e8c5a5196f8b61c8cb59a312` for this r13 execution. No staging or
commit was performed. No existing test was changed, weakened, skipped, or
removed. No unexpected full-result differences required an implementation
adjustment.

## Completion-marker delivery

The local [marker](counterparty-c2a-r13.done) was written first, after the
successful suite and preservation audit. It has the required `coder rc=0`
HEAD line and five-line summary. The subsequent write to
`/root/worktrees/dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-r13.done`
failed with exit code 1: **Read-only file system**. This destination is outside
this session's writable roots; approval escalation is unavailable. No external
marker was written by this run. The local payload is ready to copy, and its
final line records the delivery blocker.

Implementation, tests, and evidence are complete and uncommitted. The external
marker delivery is the only unfinished action.
