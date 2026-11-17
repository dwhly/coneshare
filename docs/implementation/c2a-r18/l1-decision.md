**L-1 retained.** A rightward heading must satisfy `row[2] > other_left`;
a leftward heading must satisfy `row[0] < other.line.x1`. Merely entering
the gutter, or touching the neighbour's boundary, is insufficient. Page and
same-band restrictions remain intact.

Measured first on F (288), F gaps long (432), and F gaps short (432): every
full result is identical to r17, with zero wrong and zero model calls.
Then measured across all 17,064 replay evaluations: zero wrong in all
125 families; seven goldens and native fields exact; every archived r17
full result unchanged except `analysis_version`.

In the affiliate matrix, B-1 alone yields 0 wrong / 96 placed / 1,440 holds;
B-1 plus L-1 yields **0 wrong / 116 placed / 1,420 holds**. All 320 r17 wrong
placements become holds, the 96 correct results remain exact, and 20 former
holds become correct placements. This is a measured recovery in the affiliate
matrix, not a claim to have reproduced the review's unpublished H2/H3 matrices.
The 20 complete before/after results are in [l1-recoveries.json](l1-recoveries.json).

Before applying L-1, 88 new checks were run against B-1 alone:
**20 failed / 68 passed**. The family covers both directions, overhangs
0/30/60/62 pt across a 60 pt gutter, neighbour staggers −30/−29/0/29/30 pt,
same/different pages, and four PDF controls through both in-process extraction
and the real worker. The production source then exactly matched the L-1
candidate used in the full replay. These new checks remain in the full suite.
