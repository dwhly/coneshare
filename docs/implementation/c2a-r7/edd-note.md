# C2a r7 EDD note — Gate 3 r6 follow-ups

This note is local to Send as required by the r7 worktree boundary. It records
the replacement wording for the placement identity rules in EDD §4.4; the
separate EDD worktree was not edited.

`analysis_version` is `c2a.7`. A rule whose own label is an empty short caption
matching `^[A-Za-z][\w .'/&-]{0,30}:\s*$`, without matching `LABEL`, gets `OTHER`
semantics. It cannot become a signature host, shorten either local extent edge,
bound a neighbouring column, block a side date, or stop the identity walk.
Only the attached blank caption is excluded from identity scoring/walking;
typed names around it remain evidence. This accounts for captions such as
Fax, Mobile, Contact, Attention and Notice Address without a contact vocabulary.
Unattached text and filled values retain their existing identity checks.

Witness remains a real signature host. One necessary deviation from the
review's literal predicate preserves the already-recognized model caption
`Hand of the covenanting party:`. That caption also matches the proposed regex;
classifying it as `OTHER` makes the mandatory `unusual` golden `bare`. Its
existing model path remains intact, with unchanged geometry and confidence.
The seven golden assertions and r4/r5 placement baselines are unchanged.

Running-text neutrality applies to digit-normalised rows repeated at y ±2
points on at least two pages only when each row is in a page margin:
`top < 72` or `bottom > page height - 72`. Repeated body names remain identity
evidence. Page-number rows remain neutral anywhere. These rules affect the
company-only veto walk, not local identity evidence.

Capitalised period-ending names retain their identity veto unless their final
word is in the prose set `date`, `agreement`, `above`, `below`, `hereof` (case
insensitive), or the existing role/company/block-wording exclusions apply.
Closing Date, Execution Date and Commencement Date therefore preserve the
exact Harbor boxes, while DAN WHALEY and Dan Whaley with final periods hold.

Hold reasons use “sign and date” when listing multiple unresolved signers and
“signs and dates” for one, including one unresolved signer in a larger request.
All holds return no fields. Tests cover no workflow or History creation, no
model calls, and no other person's name in results, exceptions or logs.

Verification evidence and the complete outcome are recorded in
[`c1b-report.md`, C2a r7](../c1b-report.md#c2a-r7).
