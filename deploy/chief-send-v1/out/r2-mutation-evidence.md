# Gate 3 r2 mutation evidence

Each code fix was reverted in isolation, its named test run, and the fix restored. The restored security/health suite passed 96 tests. Mutation failures are expected negative evidence, not failed release tests.

| Finding / mutation | Result | Log |
|---|---|---|
| 01-all-edits | 12 failed, 20 passed in 8.69s; restored 32 passed | `r2-01-all-edits-mutation.log` |
| 01-scalar | 4 failed in 0.08s | `r2-01-scalar-mutation.log` |
| 01-transport | 6 failed in 4.31s | `r2-01-transport-mutation.log` |
| 02 | 1 failed in 2.84s | `r2-02-mutation.log` |
| 03 | 1 failed in 2.28s | `r2-03-mutation.log` |
| 04-constraint | 1 failed in 2.80s | `r2-04-constraint-mutation.log` |
| 04 | 1 failed in 2.57s | `r2-04-mutation.log` |
| 05 | 1 failed in 2.53s | `r2-05-mutation.log` |
| 06-api | 1 failed in 2.48s | `r2-06-api-mutation.log` |
| 06-ui | Tests  1 failed (1) | `r2-06-ui-mutation.log` |
| 07 | 1 failed in 2.57s | `r2-07-mutation.log` |
| 08-audit | 1 failed in 2.63s | `r2-08-audit-mutation.log` |
| 08-health | 1 failed in 2.53s | `r2-08-health-mutation.log` |
| 08-render | 1 failed in 2.73s | `r2-08-render-mutation.log` |
| 09 | 1 failed in 2.57s | `r2-09-mutation.log` |
| 10-api | 1 failed in 2.54s | `r2-10-api-mutation.log` |
| 10-ui | Tests 1 failed, 1 passed (2) | `r2-10-ui-mutation.log` |
| 11-visibility | 1 failed in 0.98s | `r2-11-visibility-mutation.log` |
| 12-ceilings | 2 failed in 3.35s | `r2-12-ceilings-mutation.log` |
| 12-idle | 1 failed in 4.00s | `r2-12-idle-mutation.log` |
| 12-member-deny | 1 failed in 2.75s | `r2-12-member-deny-mutation.log` |
| 12-revocation | 1 failed in 2.78s | `r2-12-revocation-mutation.log` |
| 12-room | 1 failed in 5.02s | `r2-12-room-mutation.log` |

The #12 policy coverage finding did not identify defective production checks (executed against original policy: 7 passed in 4.71s): the new room-binding, idle-timeout, revocation, deny and minimum-ceiling tests pass with the original checks. Enforcement mutations fail each test. #11 retains the explicit approved EDD rule that visibility for existing grantees does not widen access; reversing that rule fails its existing regression test. Neither is misrepresented as an old-code defect.

CI smoke: the workflow copied unchanged from origin/chief/ci failed with ModuleNotFoundError: fitz; replacing that import with installed pypdf/reportlab/pdf2image/Pillow passed against chief-send-v1:latest. Remote workflow push awaits a credential with workflow-write scope.
