# L-1: measured and dropped

The optional candidate merges columns when their ranges overlap by at least
80% of the larger width. Its exact source is `l1-placement.py.txt`; the entire
r16 table and the added PDF families are measured in `counterfactual-summary.json`.
Ragged and centred controls are included there with explicit axes in
`l1_candidate.py`. The candidate has 0 wrong in the 15,526 PDF cases and leaves
all original families unchanged. It converts 238 ragged holds and 48 centred
holds to correct placements in the added controls. These gains do not excuse
the six wrong placements in the separate ownership check below.

**Do not ship this candidate.** It reintroduces B-1 when heavily overlapping
party/witness ranges are merged. The direct extracted-block check extends N-1:
party range 72–290, witness range 92–310, Pat's row 300–375. Pat's row starts
outside the party range and inside the witness range, so the unmerged geometry
owns it exclusively to the witness. The witness scores zero, and neither block
can sign for Pat. Merging the ranges instead gives the party score 6 and places
Pat on the party's signature and date rules.

| Candidate | Cases | Wrong | Holds |
| --- | ---: | ---: | ---: |
| r16 | 6 | 6 | 0 |
| r17 without L-1 | 6 | 0 | 6 |
| optional overlap merge | 6 | 6 | 0 |

The six cases cover Witness:/Attest:/Attestation: in both traversal orders.
This is an **extracted-block placement/unit check**, using the same kind of
controlled block geometry as N-1; it is not claimed as a PDF extraction
reproduction. A date companion is present, so the incorrect score results in
actual emitted signature/date fields rather than merely an incorrect score.
No model or HTTP call is made.

Reproduce with:

```sh
PYTHONDONTWRITEBYTECODE=1 /root/work/sign-product/send-venv/bin/python docs/implementation/c2a-r17/check_l1_witness.py
```

[All inputs, scores, placements and counts](l1-witness-overlap.json).
The production source remains the B-1/B-2 candidate without column merging.
The review's 150 correct-to-hold layouts are not claimed recovered.
