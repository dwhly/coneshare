# C2a r21 results

**Latest result: r21b PASS — 23,980 passed, 0 failed, 0 errors, 0 skipped.** See [r21b](#r21b--final-result). The earlier r21 HOLD below is retained as historical evidence.

Base HEAD: `e0ed35e70be90f983fbe4701e758ad812e97e936`. Production `VERSION = 'c2a.21'`. No commit or index changes.

**HOLD — candidate is not release-qualified (`coder rc=1`).** All four requested items are implemented, but the full Send backend suite, completed without `-x`, has **23,970 passed, 2 failed, 0 errors, 0 skipped**. All 18,376 r20 test IDs remain, with 5,596 additions. All 1,905 starting tracked files were hash-verified; `placement.py` is the only changed starting file.

The full-suite bar is not met. The untouched r20 boundary test for `different_page` requires score 4 where the exact requested document-wide fix3 returns 0. Running **fix3 alone** against that old module confirms 13 passed / 1 failed. A second old assertion requires a role mapped to `NORTHWIND TRADERS LLC` to count as named; the candidate’s conservative B-2 policy holds pure role headings before alias expansion, and returns 0 there too. No test was changed to make these green. The candidate remains in the working tree for review; none is claimed as shipped.

All 40,924 replay inputs across historical, review, literal-row and reviewer-wrapped families have **0 wrong** under r21. The 1,800 cross-page cells are an explicitly reported subset of the 5,280 reviewer matrix, not additional inputs. Seven goldens and their native fields are exact except `analysis_version`; real-worker results equal in-process results. External HTTP calls: 0.

The original 10,770-case replay has no full-result differences apart from `analysis_version`. Across the r20 families, the only changes are the conservative L-1 recoveries and associated hold-score improvements.

## Candidate implementation (not release-qualified)

- **B-1 / fix3:** the exact two-part review change removes the page filter from the unnamed-block loop and counts non-witness blocks across the document. The earlier matching-company uniqueness loop remains unchanged.
- **B-2:** singular/plural party-role vocabulary, optionally preceded by `the`, is excluded from printed persons and the fallback unresolved-person predicate. Pure role headings are unnamed before alias expansion in the document hold, so an alias mapped to the other party cannot silently clear that hold. Real person names containing additional words retain their identity evidence. Existing output redaction is preserved.
- **ROLE_DEF:** the exact r20 candidate adds bounded descriptive text after a legal company suffix and optional `hereinafter` wording. Both direct mapping regressions fail on r20 and pass on r21.
- **L-1:** the exact r20 printed-name exemption bypasses only the shared-heading page flag, preserving the other vetoes. It recovers **354** placements in the r20 families.
- The optional `WITNESS:`-over-`By:` recognition is **not shipped**. Its conservative holds remain visible in the matrix costs.

## Failing first and test preservation

The unchanged r20 production run had 1,173 failures and 4,421 passes across the first 5,594 new tests. The two L-1 tests also failed. The two role-definition tests initially had a draft call-signature error; corrected calls independently fail because r20 has no recipient mapping. The L-1 draft two-signer expectation was corrected to preserve Dan’s hold and require Pat’s high score; both final assertions still fail against exact r20. These are changes to newly authored drafts only, not to any starting test. All runs and draft source are retained.

| New family | Cases | Failed on r20 | Passed on r20 |
| --- | ---: | ---: | ---: |
| Requested cross-page regressions | 240 | 180 | 60 |
| Literal-row matrix | 5,280 | 950 | 4,330 |
| B-2 exact/printed-name worker cases | 12 | 11 | 1 |
| Role vocabulary, singular/plural | 52 | 26 | 26 |
| Combined roles | 4 | 4 | 0 |
| Real-person controls | 4 | 0 | 4 |
| ROLE_DEF corrected mapping checks | 2 | 2 | 0 |
| L-1 final own-name checks | 2 | 2 | 0 |
| Total final assertions | 5,596 | 1,175 | 4,421 |

Only `placement_r21_review_cases.py`, `test_placement_r21.py`, and `test_placement_r21_l1.py` are added to the test tree. No starting test, fixture, evidence file, assertion, or `.done` marker changed, and no original test was skipped, removed or retargeted. See [hash audit](preservation-summary.json) and [test inventory](test-inventory-summary.json).

## Reviewer matrix and recital layout

The review supplies the matrix axes and inline reproduction rows, but no standalone r20 matrix generator. Both forms are retained: the literal inline rows and the same axes using the 95-character recital wrap from the existing r19 `q1real.py` generator. Wrapping affects the pre-existing cross-page identity walk. The literal-row r20 matrix has 950 wrong cells; the wrapped matrix below is compared directly with the review’s reported counts.

| Matrix | Cases | r20 wrong / placed / holds / bare | r21 wrong / placed / holds / bare |
| --- | ---: | --- | --- |
| Reviewer-style matrix | 5,280 | 790 / 940 / 4340 / 0 | 0 / 260 / 5020 / 0 |
| Cross-page subset | 1,800 | 750 / 760 / 1040 / 0 | 0 / 90 / 1710 / 0 |

## Contributions and every family

Result cells are **wrong / placed / holds / bare**. Contribution cells are **wrong→hold / wrong→correct / correct→hold / hold→correct**, measured cumulatively: r20 → fix3 → B-2 → ROLE_DEF → L-1. They are document-level outcomes; a partial signer recovery that still holds the document is not counted as a placement.

| Step | All replay inputs | Reviewer 5,280 matrix |
| --- | --- | --- |
| B-1 fix3 | 1680 / 0 / 75 / 0 | 680 / 0 / 30 / 0 |
| B-2 | 297 / 5 / 0 / 69 | 110 / 0 / 0 / 20 |
| ROLE_DEF | 0 / 0 / 0 / 264 | 0 / 0 / 0 / 120 |
| L-1 | 0 / 0 / 0 / 354 | 0 / 0 / 0 / 0 |

The old Competition oracle retains 96 raw flags accepted by the reviewer only when another person is printed in Pat’s block. The six Q4 named-company ambiguities also retain their raw flags and prior reviewer classification. Neither exception was expanded; these are not new wrong placements or claims that Pat’s original coordinates matched.

### Historical r20 families

| Family | Cases | r20 | r21 | B-1 | B-2 | ROLE_DEF | L-1 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Matrix 1 | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Matrix 2 | 270 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r11 B-1 | 1020 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Signature controls | 204 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| M-1 | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r9 H-1 | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Seven goldens | 7 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Same-band right host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r13 same-band grid | 42 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r14 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r14 grid | 3456 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r14 fixed sweep | 360 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r14 correct controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r15 M1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r15 M2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r15 M1 | 640 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r15 M2 | 2592 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| A2 exact witness captions | 480 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| A2 additional dy=20 | 96 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Witness wider sweep | 2496 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| F three-party permutations | 288 | 0 / 99 / 189 / 0 | 0 / 123 / 165 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 24 |
| F heading gaps long | 432 | 0 / 162 / 270 / 0 | 0 / 189 / 243 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 27 |
| F heading gaps short | 432 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| B2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Affiliate matrix | 1536 | 0 / 0 / 1536 / 0 | 0 / 0 / 1536 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| r18 B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Veto matrix | 140 | 0 / 0 / 140 / 0 | 0 / 0 / 140 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

### r20 review families

| Family | Cases | r20 | r21 | B-1 | B-2 | ROLE_DEF | L-1 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Competition | 480 | 0 / 96 / 384 / 0 | 0 / 96 / 384 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| L1 boundary pat | 3480 | 0 / 191 / 3289 / 0 | 0 / 191 / 3289 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| L1 boundary fleet | 1800 | 0 / 0 / 1800 / 0 | 0 / 0 / 1800 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| F fine | 3456 | 0 / 2022 / 1434 / 0 | 0 / 2325 / 1131 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 303 |
| F fine company-only | 3456 | 0 / 776 / 2680 / 0 | 0 / 776 / 2680 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Realistic NDA matrix | 48 | 0 / 0 / 48 / 0 | 0 / 0 / 48 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| B1 real worker | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Q4 M1 ambiguity | 6 | 0 / 6 / 0 / 0 | 0 / 6 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Q4 controls | 32 | 0 / 12 / 20 / 0 | 0 / 12 / 20 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

### Literal inline rows and B-2 additions

| Family | Cases | r20 | r21 | B-1 | B-2 | ROLE_DEF | L-1 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Review matrix same | 1320 | 50 / 95 / 1225 / 0 | 0 / 65 / 1255 / 0 | 0 / 0 / 0 / 0 | 50 / 0 / 0 / 0 | 0 / 0 / 0 / 20 | 0 / 0 / 0 / 0 |
| Review matrix guarantor | 1320 | 460 / 550 / 770 / 0 | 0 / 210 / 1110 / 0 | 410 / 0 / 0 / 0 | 50 / 0 / 0 / 40 | 0 / 0 / 0 / 80 | 0 / 0 / 0 / 0 |
| Review matrix split | 1320 | 440 / 485 / 835 / 0 | 0 / 65 / 1255 / 0 | 410 / 0 / 0 / 0 | 30 / 0 / 0 / 0 | 0 / 0 / 0 / 20 | 0 / 0 / 0 / 0 |
| Review matrix witness | 1320 | 0 / 45 / 1275 / 0 | 0 / 0 / 1320 / 0 | 0 / 0 / 45 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| Cross-page regression guarantor | 120 | 92 / 92 / 28 / 0 | 0 / 16 / 104 / 0 | 82 / 0 / 0 / 0 | 10 / 0 / 0 / 8 | 0 / 0 / 0 / 8 | 0 / 0 / 0 / 0 |
| Cross-page regression split | 120 | 88 / 88 / 32 / 0 | 0 / 0 / 120 / 0 | 82 / 0 / 0 / 0 | 6 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| B2 exact worker | 12 | 10 / 10 / 2 / 0 | 0 / 6 / 6 / 0 | 0 / 0 / 0 / 0 | 5 / 5 / 0 / 1 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| B2 role vocabulary | 52 | 26 / 26 / 26 / 0 | 0 / 0 / 52 / 0 | 0 / 0 / 0 / 0 | 26 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| ROLE_DEF layouts | 96 | 26 / 26 / 70 / 0 | 0 / 16 / 80 / 0 | 16 / 0 / 0 / 0 | 10 / 0 / 0 / 0 | 0 / 0 / 0 / 16 | 0 / 0 / 0 / 0 |

### Reviewer-wrapped matrix

| Family | Cases | r20 | r21 | B-1 | B-2 | ROLE_DEF | L-1 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| Review matrix same | 1320 | 40 / 70 / 1250 / 0 | 0 / 50 / 1270 / 0 | 0 / 0 / 0 / 0 | 40 / 0 / 0 / 0 | 0 / 0 / 0 / 20 | 0 / 0 / 0 / 0 |
| Review matrix guarantor | 1320 | 380 / 440 / 880 / 0 | 0 / 160 / 1160 / 0 | 340 / 0 / 0 / 0 | 40 / 0 / 0 / 20 | 0 / 0 / 0 / 80 | 0 / 0 / 0 / 0 |
| Review matrix split | 1320 | 370 / 400 / 920 / 0 | 0 / 50 / 1270 / 0 | 340 / 0 / 0 / 0 | 30 / 0 / 0 / 0 | 0 / 0 / 0 / 20 | 0 / 0 / 0 / 0 |
| Review matrix witness | 1320 | 0 / 30 / 1290 / 0 | 0 / 0 / 1320 / 0 | 0 / 0 / 30 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

## Evidence

- [Full suite](full-suite.txt), [JUnit](full-suite.xml), [test-run counts](test-runs-summary.json).
- [Historical summary](release-historical-summary.json), [all outcomes](release-historical-cases.json).
- [Review summary](release-review-summary.json), [all outcomes](release-review-cases.json).
- [Literal layouts](release-layouts-summary.json), [reviewer matrix](reviewer-layouts-summary.json).
- [Goldens](release-placements.json), [source audit](source-equivalence.json), [method](method.md).

Production SHA-256: `712f04beabd2d51d6174499d3b6943d005bb10f211d725b2e0cfa20b737b4543`.

## Blockers

1. `backend/dealroom_sign/tests/test_placement_r20_boundaries.py:47`, `test_independent_evidence_and_party_count_controls[different_page]`: the frozen assertion expects 4 for a third unnamed block on another page; the requested fix3 requires 0. This fails with **fix3 alone**, independently of B-2, ROLE_DEF, and L-1. See [isolated proof](fix3-existing-boundaries.txt).
2. The same file at line 30, `test_heading_is_normalized_before_identifying_other_party[RECIPIENT:-roles5-4]`: the candidate’s B-2 alias policy returns 0 instead of the existing expected 4. This is an additional candidate/test conflict, not an unavoidable consequence of fix3.

Under the instruction to preserve all existing assertions, the exact fix3 and a zero-failure full suite cannot both be delivered. No source special-case or test retargeting was added to bypass the conflicting synthetic fixture. No commit, index or project-memory update.


## r21b — final result

**PASS — release-qualified candidate (`coder rc=0`).** Full Send backend suite
completed without `-x`: **23,980 passed, 0 failed, 0 errors, 0 skipped**, with no
deselections. All 23,972 incoming r21 test IDs remain, including all 18,376 r20 IDs;
eight new duplicate-role regressions were added. HEAD remains
`e0ed35e70be90f983fbe4701e758ad812e97e936` and `VERSION = 'c2a.21'`.

### Manager rulings and implementation

1. **Authorized test correction:** the manager explicitly authorized changing only
   `test_independent_evidence_and_party_count_controls[different_page]` from score
   4 to the document-wide hold score 0 because it asserted the r20 B-1 bug. The
   original expectation expression for every other control is retained verbatim.
2. **Named alias correction:** B-2 now classifies the resolved heading after role
   mapping and behalf normalization. A role mapped to NORTHWIND is named and
   permits score 4 on HARBOR LIGHT GROUP. The existing
   `test_heading_is_normalized_before_identifying_other_party[RECIPIENT:-roles5-4]`
   is byte-identical and passes. Missing mappings and mappings to role words
   remain unnamed.
3. **Duplicate-role boundary:** the simple alias correction exposed the unchanged
   r21 `discloser-False-` vocabulary regression: its role maps to Fleet while a
   separate Fleet block also claims that company. The role is named, but its block
   assignment is ambiguous. A separate, document-wide guard retains the hold when
   two blocks claim the role's company without printed-person evidence to
   distinguish them. It preserves the independent-name and explicit-company paths.
   Eight new tests cover two role spellings, both page arrangements, and printed
   peer controls; four fail before the refinement and all eight pass after it.

The exact authorized existing-test diff is:

```diff
diff --git a/backend/dealroom_sign/tests/test_placement_r20_boundaries.py b/backend/dealroom_sign/tests/test_placement_r20_boundaries.py
index 54541b1f..705d86f0 100644
--- a/backend/dealroom_sign/tests/test_placement_r20_boundaries.py
+++ b/backend/dealroom_sign/tests/test_placement_r20_boundaries.py
@@ -44,4 +44,5 @@ def test_independent_evidence_and_party_count_controls(control):
     signer = dict(PAT[0])
     if control == 'explicit_company':
         signer['company'] = 'HARBOR LIGHT GROUP, INC.'
-    assert placement.score(signer, target, {}, blocks) == (10 if control == 'printed_signer' else 4)
+    assert placement.score(signer, target, {}, blocks) == (
+        0 if control == 'different_page' else (10 if control == 'printed_signer' else 4))
```

No other existing test, fixture or evidence file changed, except this explicitly
requested RESULT update. The audit verifies all 1,905 r20 tracked files and all
1,999 incoming r21 files by SHA-256, reconstructs the authorized test change
exactly, and confirms unchanged HEAD and index. The original r21 `.done` and all
its evidence remain intact. No staging, commit or project-memory update.

### Verification

Every one of the **40,924 replay inputs** has 0 wrong under the unchanged reviewer
oracles. Results below are **wrong / placed / holds / bare**; the last column counts
complete result differences from the incoming r21 candidate.

| Family collection | Cases | r21b | Full-result differences from r21 |
| --- | ---: | --- | ---: |
| Historical families | 17,204 | 0 / 3630 / 13561 / 13 | 0 |
| r20 review families | 12,760 | 0 / 3406 / 9354 / 0 | 0 |
| Literal matrix and B-2 additions | 5,680 | 0 / 278 / 5402 / 0 | 100 |
| Reviewer 5,280 matrix | 5,280 | 0 / 200 / 5080 / 0 | 80 |

The narrowed alias policy adds **100 correct→hold outcomes** in
the literal layouts/additions and **60** in the reviewer
matrix relative to r21. A mapped recipient and a domain-matching affiliate on
different pages can now both score, leaving assignment unresolved. These costs
remain visible; no wrong placement is accepted to recover them. Other complete
result changes in those collections are differences in already-held candidates.

Contributions are measured cumulatively from r20 through fix3, B-2, ROLE_DEF and
L-1. Cells are **wrong→hold / wrong→correct / correct→hold / hold→correct**.

| Step | All replay inputs | Reviewer matrix |
| --- | --- | --- |
| B-1 fix3 | 1680 / 0 / 75 / 0 | 680 / 0 / 30 / 0 |
| B-2 | 297 / 5 / 0 / 1 | 110 / 0 / 0 / 0 |
| ROLE_DEF | 0 / 0 / 0 / 172 | 0 / 0 / 0 / 80 |
| L-1 | 0 / 0 / 0 / 354 | 0 / 0 / 0 / 0 |

The reviewer matrix's **1,800 cross-page subset** is
**0 / 30 / 1770 / 0**. It is a subset, not 1,800 additional
inputs. The 12 exact `THE RECIPIENT` worker/printed-name cases are
**0 / 6 / 6 / 0**; each worker result equals its in-process result. The 52 role
vocabulary cases remain 0 wrong. Seven goldens and their native fields match
exactly except `analysis_version`. All 21 final-source worker checks match their
in-process results (105 checks across the five cumulative variants). HTTP calls: 0.
The prior 96 Competition raw flags and six Q4 named-company ambiguities retain
their unchanged reviewer-approved classification; no oracle exception expanded.

The 96-test focused alias run passes, as do 42 additional alias score controls.
The full suite includes every matrix and regression test without filtering.
The first simple-narrowing run and its interrupted replays remain as draft
evidence; only `r21b-final-*` records certify this candidate. See the
[r21b method](r21b-method.md) for the exact commands and failing-first sequence.

- [Completed full suite](r21b-final-full-suite.txt) and [JUnit](r21b-final-full-suite.xml).
- [Historical families](r21b-final-historical-summary.json), [review families](r21b-final-review-summary.json),
  [literal matrix and B-2](r21b-final-layouts-summary.json), [reviewer matrix](r21b-final-reviewer-layouts-summary.json).
- [Exact goldens](r21b-final-placements.json), [family comparisons](r21b-family-comparison.json),
  [test counts](r21b-test-runs-summary.json), [test inventory](r21b-test-inventory-summary.json).
- [Preservation audit](r21b-preservation-summary.json), [release bars](r21b-release-bars.json),
  [authorized diff](r21b-authorized-test.patch).

Production SHA-256: `06b0d22d19ebf75a37fd499d3567229ee74d66687d1409cddd789af496917311`.

**Blockers: none.**
