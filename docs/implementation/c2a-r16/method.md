# C2a r16 verification

Base: `d88bfb889f3863796b276a6f0aef3da57539c4c3`. The initial source and
nearest-only source are archived here. The latter is reconstructed from the
unchanged r15b patch and SHA-256 checked against its recorded candidate.
All prior tests, fixtures, and r15/r15b evidence remain unchanged.

## Candidate rules

Aligned rules sharing a left edge form one column, with the longest right
edge. The column includes the inline label. Printed rows use horizontal edge
distance, with distinct nearest columns within 2 pt failing closed. Different
pages never compete. The existing raw extents and stacked-row partitioning
continue to determine vertical membership.

Witness, Attest, and Attestation line labels are excluded from party columns
and cannot receive party scores. A witness signs next to a party but is never
that party. Every block is scored before any role label is redacted, preserving
the same ownership decision in either traversal order.

The existing extraction definition of neighbouring rules (vertical separation
strictly less than 30 pt) defines a shared gutter. A printed-name row intersecting
the open horizontal gap between such party columns is ambiguous for either
block whose raw extent contains it. This includes a row wholly in the gap and
a row crossing its edge into a party column. Distinct nearest-column ties are
also ambiguous. Scoring returns zero for a block with ambiguous printed-name
evidence, so company hints or another local name cannot leave a high-confidence
assignment. No peer score is propagated. The r14 mixed-heading veto remains.
Staggered outdented captions retain nearest-column ownership.

## Failing first and bounded variants

The two unchanged existing controls fail against the exact nearest-only source.
The first 18 added cases record 14 failures and four staggered-control passes.
They cover witness/attestation roles, traversal order, the 30 pt band boundary,
and tied names with company-only fallback. Role exclusion initially revealed
two reverse-order failures because redaction preceded later scoring; scoring
all blocks first resolves these without changing the role or ownership rule.

Gutter variant 1 requires the entire printed row inside the gutter. It fixes
the r4 gap diagnostic but leaves the r3 fixture case. Four added crossing-row
cases fail against this variant before gutter variant 2 admits any intersection
with the gutter. Only these two gutter variants and one role-exclusion rule
are tried. The generalised (b-prime) veto and a broader foreign-name/company-only
guard are not used.

The failing fixture's name, `witness`, does not describe its competing block:
the actual PDF has Harbor and Fleet party blocks, both labelled `By:`, plus
the execution clause “IN WITNESS WHEREOF”. On call 3 Lee's row spans
x=296.4..362.2 at y=269.656..277.656. The party columns are x=72..266.4 and
x=316.8..511.2, with both signature rules at y=276. Its intersection with
the x=266.4..316.8 gutter explains the hold. Excluding witnesses alone cannot
fix that case. The complete original geometry is in `witness-fixture-audit.json`.

## Comparisons and full suite

`check_evidence.py` imports the unchanged r15b case generator and oracles.
It evaluates r14, exact nearest-only, and the final worktree source on every
original case, including M1/M2 reproductions and all 944 added controls.
The 72-case L-1 subset is displayed separately and excluded from the 10,698
total. Every r14 and nearest family count must match the archived r15b table.
Original test assertions validate the captured r14 control oracles.

Seven full golden results are compared against the r13 archive, ignoring only
`analysis_version`; native fields must also match. Selected goldens, reproductions,
and positive controls additionally compare real worker and in-process results.
External model keys are removed, HTTP sends raise, and model replies are local
deterministic stubs. Per-case results, model call counts, wrong placements,
worker comparisons, and source hashes are retained.

Commands, run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r16/check_evidence.py > docs/implementation/c2a-r16/counterfactual-run.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests --junitxml=/root/worktrees/send-c1b/docs/implementation/c2a-r16/full-suite.xml > docs/implementation/c2a-r16/full-suite.txt 2>&1
python3 docs/implementation/c2a-r16/final_audit.py
```

The full suite has no `-x`, filter, or maximum-failures override. The supplied
launcher and its retained scratch-directory warning are unchanged. The final
audit parses every JUnit outcome and checks all 245 initially present test and
fixture files across the repository, including the inherited uncommitted r15
tests. It also checks HEAD, index, source identity, existing report, memory,
whitespace, and every placed field against nearest-only geometry.
