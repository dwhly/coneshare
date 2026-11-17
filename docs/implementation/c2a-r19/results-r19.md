# C2a r19 results

Base HEAD: `9ebf85a0720a6cefdf07a8ab10e0d2fbf38b474e`. Production `VERSION = 'c2a.19'`. No commit or index changes.

**All required bars pass.** The final Send backend suite completed without `-x`: **17,832 passed, 0 failed, 0 errors, 0 skipped**. All 17,144 existing test cases remain, with 688 new cases. SHA-256 verification covers all 1,746 starting tracked files; `placement.py` is the only starting file changed.

**Chosen rule:** company-only credit requires unique company attribution on the same page. Every other block with a matching role-mapped, behalf-stripped heading competes using the existing similarity predicate, regardless of veto, zero score, crossing, or unresolved identity. A matching printed name remains independent evidence. M-1 separately makes a heading row spanning two same-band party columns unresolved for the page, including colliding text, lost legal-form tokens, separators, and mapped roles. These checks only remove credit.

**Narrower rejected:** the measured variant retains r18 crossing competitors and adds only non-crossing blocks whose local score is zero, excluding mismatched/ambiguous printed identities and unresolved-person vetoes. It retains all 116 correct affiliate placements but also retains 84 wrong veto-matrix placements and 92 unjustified competition placements. It therefore fails the required zero-wrong standard. The broad rule accepts all 116 affiliate holds.

## Failing first and tests

Before any production edit, the new 140-case veto matrix had **84 failures / 56 passes**, the 16 collision checks had **8 failures / 8 passes**, and 40 identity/page checks had **20 failures / 20 passes**: **112 failed / 84 passed** in total. Two further collision checks failed before recognizing slash/colon rows (2 failed / 4 passed); mapped-role collisions then failed before the final heading-shape guard (3 failed / 3 passed). The exact 480-case competition assertions were also evaluated against isolated historical r18: **108 failed / 372 passed**, versus **480 passed** on the final implementation. This historical replay is recorded separately from the original unchanged-production red runs.

Only new test files were added: `test_placement_r19.py` (208 cases), `test_placement_r19_review.py` (480 cases), and `placement_r19_review_cases.py` (generator support). The review generator function source is copied verbatim and AST-verified against the preserved scratch source. No existing test, fixture, assertion, oracle, skip, selection, or evidence was retargeted.

## Exact replay and competition classification

The required replay covers **29,876 evaluations in 131 families**: every r18 published family plus the veto matrix (17,204), and the exact review boundary, fine-gap, and competition generators (12,672). These are evaluation counts; historical subset families and coarse/fine grids overlap. **Zero unjustified wrong placements in every family.** Seven goldens and native fields are exact except `analysis_version`. Real workers match in-process outputs on the goldens, veto reproductions, and every one of the 60 candidate collision cases. Evidence runners block external HTTP; calls: 0.

The exact competition family reproduces **348 raw oracle flags in r18 → 300 under the broad candidate → 240 in r19**. The 300 candidate residuals are fully classified: **60 collisions become holds; 240 are the explicitly permitted sole-company/domain case**, with no company identifying the original blank as Pat’s and no explicit legal company supplied for Pat. The original oracle and all raw flags are retained. Every case naming Analytics on the original block and placing Pat on a different legal entity now holds. See the [300-row case-by-case explanation](competition-classification.md) and [all 480 inputs and outputs](competition-classification.json). The 24 [identity controls](release-competition-controls.json) additionally show that supplying Analytics as Pat’s explicit company holds the Group-only layouts.

The exact L-1 counts are **3,480 Pat / 1,800 Fleet**: r18 has **94 / 192 wrong**, respectively; r19 has **0 / 0**. Both exact F fine variants have 3,456 cases and zero wrong. Early reconstructed sweeps are retained as exploratory evidence and are excluded from these exact-family claims.

## Per-family comparison and hold cost

Cells are **wrong / placed / holds / bare**. “Wrong” uses the unchanged original oracle, with the competition exception explicitly adjudicated as above; its raw counts remain in the JSON and case-by-case report. `candidate` is exactly the reviewer’s one-line r18 change. `narrower` is the restricted competition alternative, without M-1. `r19` includes the broad same-page rule and M-1. Hold cost counts previously correct/permitted placements becoming holds; wrong placements becoming holds are shown separately.

| Family | Cases | r18 | Candidate | Narrower | r19 | Correct → hold | Wrong → hold |
| --- | ---: | --- | --- | --- | --- | ---: | ---: |
| Matrix 1 | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 | 0 |
| Matrix 2 | 270 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 | 0 |
| r11 B-1 | 1020 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 | 0 |
| Signature controls | 204 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 | 0 |
| M-1 | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 | 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 | 0 |
| r9 H-1 | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 | 0 |
| Seven goldens | 7 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 | 0 |
| Same-band right host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r13 same-band grid | 42 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 | 0 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 | 0 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 | 0 |
| r14 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r14 grid | 3456 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 | 0 |
| r14 fixed sweep | 360 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 | 0 |
| r14 correct controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 |
| r15 M1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r15 M2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r15 M1 | 640 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 | 0 |
| r15 M2 | 2592 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 | 0 |
| r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 |
| r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 | 0 |
| r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 | 0 |
| r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 | 0 |
| r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 | 0 |
| r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 | 0 |
| r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 | 0 |
| r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 | 0 |
| r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 | 0 |
| r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 | 0 |
| r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 |
| r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 |
| r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 | 0 |
| r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 |
| r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 | 0 |
| r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 |
| r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 | 0 |
| r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 | 0 |
| r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 |
| r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 | 0 |
| r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 |
| r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 | 0 |
| r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 | 0 |
| r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 | 0 |
| r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 |
| r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 | 0 |
| r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 |
| r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 | 0 |
| r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 | 0 |
| r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 | 0 |
| r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 |
| r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 | 0 |
| r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 |
| r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 | 0 |
| r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 | 0 |
| r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 | 0 |
| r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 | 0 |
| r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 | 0 |
| r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 |
| r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 | 0 |
| r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 | 0 |
| r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 | 0 |
| r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 | 0 |
| r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 | 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 | 0 |
| A2 exact witness captions | 480 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 | 0 |
| A2 additional dy=20 | 96 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 | 0 |
| Witness wider sweep | 2496 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 | 0 |
| F three-party permutations | 288 | 0 / 130 / 158 / 0 | 0 / 130 / 158 / 0 | 0 / 130 / 158 / 0 | 0 / 99 / 189 / 0 | 31 | 0 |
| F heading gaps long | 432 | 0 / 210 / 222 / 0 | 0 / 210 / 222 / 0 | 0 / 210 / 222 / 0 | 0 / 162 / 270 / 0 | 48 | 0 |
| F heading gaps short | 432 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 | 0 |
| B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| B2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| Affiliate matrix | 1536 | 0 / 116 / 1420 / 0 | 0 / 0 / 1536 / 0 | 0 / 116 / 1420 / 0 | 0 / 0 / 1536 / 0 | 116 | 0 |
| r18 B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| Veto matrix | 140 | 84 / 84 / 56 / 0 | 0 / 0 / 140 / 0 | 84 / 84 / 56 / 0 | 0 / 0 / 140 / 0 | 0 | 84 |
| Competition | 480 | 108 / 348 / 132 / 0 | 60 / 300 / 180 / 0 | 92 / 332 / 148 / 0 | 0 / 240 / 240 / 0 | 0 | 108 |
| L1 boundary pat | 3480 | 94 / 285 / 3195 / 0 | 0 / 191 / 3289 / 0 | 0 / 191 / 3289 / 0 | 0 / 191 / 3289 / 0 | 0 | 94 |
| L1 boundary fleet | 1800 | 192 / 192 / 1608 / 0 | 192 / 192 / 1608 / 0 | 192 / 192 / 1608 / 0 | 0 / 0 / 1800 / 0 | 0 | 192 |
| F fine | 3456 | 0 / 2524 / 932 / 0 | 0 / 2524 / 932 / 0 | 0 / 2524 / 932 / 0 | 0 / 2022 / 1434 / 0 | 502 | 0 |
| F fine company-only | 3456 | 0 / 783 / 2673 / 0 | 0 / 783 / 2673 / 0 | 0 / 783 / 2673 / 0 | 0 / 776 / 2680 / 0 | 7 | 0 |

## Evidence and preservation

- [Final full suite](full-suite.txt), [JUnit](full-suite.xml), [test inventory](test-inventory-summary.json).
- [Final historical replay](release-summary.json), [complete outcomes](release-cases.json).
- [Exact review replay](release-review-summary.json), [complete outcomes](release-review-cases.json).
- [Test run counts](test-runs-summary.json), [hold costs](hold-costs.json), [hash audit](preservation-summary.json).
- [Seven final goldens](release-placements.json), [method and commands](method.md).

Every existing test, fixture, earlier evidence file and `.done` marker is byte-for-byte unchanged. HEAD, index, project memory and the read-only reviewer inputs are unchanged. The first full-suite pass (17,340 tests) is retained as preliminary evidence; the final 17,832-test run includes every later addition and uses the exact final source hash.

**Blockers:** none.
