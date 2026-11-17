# C2a r8: Gate 3 r7 FIX-FIRST (local brief record)

Review: `/root/worktrees/dealroom-sign-edd/docs/edd/reviews/counterparty-c2a-gate3-r7.md`.
Worktree: `/root/worktrees/send-c1b`, branch `agent/c1b-counterparty`, base `b651e646`.
All writes stay in this worktree. Do not stage or commit. This local copy keeps
the brief and its `.done` marker together without writing to the EDD worktree.

- **B-1:** Unknown short captions become `OTHER` only when subordinate to a
  recognised SIGNATURE or Witness rule in the same column, with
  `5 < caption.y - host.y <= 125` and no intervening company, behalf, person or
  role-map heading. Otherwise preserve r6 host semantics. The six contact
  captions remain unconditional `OTHER`.
- Cover C4, C8, C10, C12 and C13 with `Authorised signatory:`, `Signatory:`,
  `Executed by:`, `Firma:` and `Unterschrift:`. Hold instead of placing on a
  neighbouring party or Witness line. Preserve `Signature:` controls and the
  existing r6/r7 contact tests unchanged.
- **Required independent defence:** Mixed company-heading ownership sets
  `uncertain_identity`. C8, C12 and C13 must hold with the subordinate rule
  stubbed out.
- **M-1:** C7 with a confirming stub retains the 400 candidate and never places
  Dan on Witness 340.
- **L-1:** The only signature line `Authorised signatory:` can place
  `model-high` with a confirming stub.
- **N-1:** Remove `MODEL_SIGNATURE_CAPTION`; keep the unusual golden exact.
- Failing first for every item; never weaken, skip or delete existing tests.
  Keep `test_seven_goldens_remain_exact_against_r4_and_r5` unchanged.
- Set `analysis_version` to `c2a.8`; append `## C2a r8` to `c1b-report.md`;
  add a local EDD note. Evidence consists of summaries and placements JSON.

Verify the entire signing suite with:

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```
