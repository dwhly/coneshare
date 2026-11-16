# C2a r4 verification evidence

The authoritative baseline replay is `baseline-send-red.txt` (52 failures,
41 controls passing on `ef62c4da`) and `baseline-board-red.txt` (one failure,
two controls passing on `11d1606`). `replay_baselines.py` restores working
production files in `finally`.

`regressions-green.txt` contains all 86 new Send cases passing. The final full
runs are `send-signing-suite.txt` and `board-suite.txt`; the report records their
counts and the three supplied Board cloud baseline failures. `placements.json`
and `golden-comparison.json` record all seven outcomes and exact r3 field/native
geometry comparisons, reproducible with `check_goldens.py`.

The other logs document failing-first iterations and focused verification.
Files named `*-initial-check.txt` contain intermediate checks, including failures
and fixture corrections, and are not final green evidence. The first fixture
insertion check is not the authoritative baseline replay; the final replay above
reproduces both `roles` and `witness` failures with all working fixes removed.
