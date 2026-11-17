# C2a r18 results

Base HEAD: `465e5afa408a219caa4288b762f0c71ce54f16bf`; production `VERSION = 'c2a.18'`. No commit or index changes.

**B-1 closed.** Crossing headings cannot grant company credit, but their role-mapped, behalf-stripped company identity still prevents another block from winning on company alone. A matching printed name remains independent evidence. N-1 changes only the r17 test docstring.

Full Send backend suite: **17,144 passed, 0 failed, 0 errors, 0 skipped**, run to completion without `-x`. All 15,498 prior test cases remain. 1,646 new cases were added.

New tests live exclusively in [test_placement_r18.py](../../../backend/dealroom_sign/tests/test_placement_r18.py): 1,536 affiliate cases, 2 real-worker reproductions, 20 identity checks, 80 L-1 boundary checks, and 8 L-1 PDF checks. The only existing-test change is the authorized N-1 docstring.

Full replay: 17,064 evaluations across 125 families, **0 wrong** for r18. Seven goldens match exactly except `analysis_version`; native fields are exact. 60 worker results equal their in-process counterparts; external HTTP calls: 0.

## Failing first and affiliate matrix

Production was unchanged for both initial pytest runs and the matrix baseline. The first run had 321 failed / 1,217 passed: 320 affiliate matrix failures and the PAT-only real-worker reproduction. Identity normalization checks had 8 failed / 12 passed. All subsequent B-1 targeted tests passed (1,558).

The matrix is 6 affiliate headings × widths {150,180,200,218} × vertical gaps {130,160,200,240} × affiliate column {40,280} × Pat heading {ordinary,international} × PAT/DAN+PAT × Fleet heading off/on = **1,536 cases**. Pat and Fleet columns start at 40 and 280; signature rules are at y=290, dates at y=350, and affiliate rules are shifted by the selected gap. The oracle checks every signature and date against its own signer’s rule.

r17: **320 wrong / 96 correct / 1,120 holds**. B-1 alone: **0 wrong / 96 correct / 1,440 holds**. All 320 wrong placements become holds, and the 96 correct full results are unchanged. The four triggering headings (GROUP, VENTURES, ANALYTICS UK, and repeated ANALYTICS) each account for 80 wrong placements; HOLDINGS and HARBOR LIGHT, LLC each retain 48 correct placements.

## Optional L-1

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

## Per-family comparison

Cells are **wrong / placed / holds / bare**; placed includes wrong placements in r17. The 72-case r14 L-1 subset overlaps its parent grid and is retained as in the prior evidence. B-1 alone preserves every complete result across all 15,526 archived r17 evaluations except `analysis_version`.

| Family | Cases | r17 | B-1 alone | r18 (B-1 + L-1) |
| --- | ---: | --- | --- | --- |
| Matrix 1 | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 |
| Matrix 2 | 270 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 |
| r11 B-1 | 1020 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 |
| Signature controls | 204 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 |
| M-1 | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 |
| r9 H-1 | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 |
| Seven goldens | 7 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 |
| Same-band right host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r13 same-band grid | 42 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 |
| r14 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r14 grid | 3456 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 |
| r14 fixed sweep | 360 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 |
| r14 correct controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 |
| r15 M1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r15 M2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r15 M1 | 640 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 |
| r15 M2 | 2592 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 |
| r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 |
| r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 |
| r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 |
| r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 |
| r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 |
| r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 |
| r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 |
| r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 |
| r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 |
| r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 |
| r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 |
| r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 |
| r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 |
| r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 |
| r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 |
| r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 |
| r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 |
| r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 |
| r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 |
| r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 |
| r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 |
| r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 |
| r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 |
| r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 |
| r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 |
| r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 |
| r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 |
| r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 |
| r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 |
| r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 |
| r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 |
| r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 |
| r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 |
| r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 |
| r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 |
| r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 |
| r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 |
| r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 |
| r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 |
| r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 |
| r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 |
| r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 |
| r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 |
| r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 |
| r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 |
| A2 exact witness captions | 480 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 |
| A2 additional dy=20 | 96 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 |
| Witness wider sweep | 2496 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 |
| F three-party permutations | 288 | 0 / 130 / 158 / 0 | 0 / 130 / 158 / 0 | 0 / 130 / 158 / 0 |
| F heading gaps long | 432 | 0 / 210 / 222 / 0 | 0 / 210 / 222 / 0 | 0 / 210 / 222 / 0 |
| F heading gaps short | 432 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 |
| B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| B2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| Affiliate matrix | 1536 | 320 / 416 / 1120 / 0 | 0 / 96 / 1440 / 0 | 0 / 116 / 1420 / 0 |
| r18 B1 reproduction | 2 | 1 / 1 / 1 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |

## Evidence and preservation

SHA-256 verification covers all 1,698 starting tracked files. Only `placement.py` and the exact N-1 docstring differ. Every other existing test, fixture, evidence file, and `.done` marker—including the restored r16 marker—is byte-for-byte unchanged. Memory, HEAD, and index are unchanged.

- [Replay runner](check_evidence.py), [family counts](counterfactual-summary.json), [all outcomes](counterfactual-cases.json), [worker checks](counterfactual-workers.json).
- [Failing-first matrix](affiliate-failing-first.json), [initial pytest log](failing-first.txt), [identity checks](failing-first-identity.txt), [test-run counts](test-runs-summary.json).
- [Full suite log](full-suite.txt), [JUnit](full-suite.xml), [inventory audit](test-inventory-summary.json), [hash audit](preservation-summary.json).
- [Goldens](placements.json), [method and commands](method.md).

**Blockers:** none.
