# C2a r9: Gate 3 r8 FIX-FIRST — fail closed on absorbed identity

Local brief record for `/root/worktrees/send-c1b`, branch
`agent/c1b-counterparty`, base `5e5ee6ea`. Review read in full:
`/root/worktrees/dealroom-sign-edd/docs/edd/reviews/counterparty-c2a-gate3-r8.md`.
All changes stay in this worktree; do not stage or commit. The local brief and
completion marker live together here without writing to the review worktree.

- Apply the manager-selected main B-1/H-1 fix: when `subordinate_caption`
  makes a rule `OTHER`, a `person_text` row in its caption slot
  (`0 <= top - rule.y < 22`, `abs(x - column) < 35`) sets
  `uncertain_identity` on every host whose extent contains that row. Hold with
  no fields. Exempt the six unconditional contact captions.
- Only permitted existing expectation edit: the ten Lee/LEE and Pat/PAT cases
  in `test_h1_short_contact_caption_preserves_typed_identity` become holds,
  with a comment citing Gate 3 r8 B-1. The other five and all other existing
  expectations stay unchanged. Any further existing expectation change stops
  the task.
- Execute failing-first: C12/C13 × six headings × five captions, the same-row
  behalf line at x=300, and H-1 stacks with Title, blank Name or no intervening
  row, for both parties. Keep Signature controls, seven exact goldens, r6 H-2,
  and the review's previously held cases.
- Add the L-1 runbook sentence acknowledging intended single-block false holds
  from the second-company defence. Record B-1 and H-1 executed outcomes in
  `regression-placements.json`. Use `analysis_version = c2a.9`.
- Run the complete signing suite, retain compact evidence only, append
  `## C2a r9` to `../c1b-report.md`, and write the adjacent `.done` marker.

```bash
SIGN_INTERNAL_URL=http://sign.test /root/work/sign-product/run-send-local.sh /root/worktrees/send-c1b dealroom_sign/tests
```
