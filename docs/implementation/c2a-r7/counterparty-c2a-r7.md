# C2a r7 brief (local record)

User-requested Gate 3 r6 follow-ups, based on
`/root/worktrees/dealroom-sign-edd/docs/edd/reviews/counterparty-c2a-gate3-r6.md`.
All changes belong to `/root/worktrees/send-c1b`, branch
`agent/c1b-counterparty`, starting at `be30d623`. Do not commit.

- H-1: replace the contact-label vocabulary with the review's structural short
  caption rule, excluding known `LABEL` matches and Witness signature hosts.
  Exercise Fax, Mobile, Contact, Attention and Notice Address for mismatched
  typed identity and both matching typed identities.
- L-1: only neutralize repeated rows in the top/bottom 72-point margins;
  page-number rows remain neutral anywhere.
- L-2: recognize prose endings date/agreement/above/below/hereof; retain the
  period-ending person-name veto and exact Harbor boxes.
- N-1: use “sign and date” for plural subjects in the placement hold reason.
- Failing first; preserve every existing test and all seven exact r4/r5 goldens.
- Set `analysis_version` to `c2a.7`. Run the supplied Send test runner with
  `SIGN_INTERNAL_URL=http://sign.test` against `dealroom_sign/tests`.
- Append `## C2a r7` to `docs/implementation/c1b-report.md`; provide an EDD note
  and a completion marker beside this local brief.

This local brief records the supplied request because this worktree contains
no EDD brief directory. The EDD note and completion marker are kept here to
honor the instruction to write only in this worktree.
