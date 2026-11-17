# C2a r17 RESULT

**B-1 and B-2 closed.** Zero wrong placements in every replayed r16 family, A2, the 2,496-case witness sweep, and F. All seven goldens and native fields are exact except `analysis_version`. `VERSION = 'c2a.17'`.

Full `dealroom_sign/tests` suite: **15,498 passed, 0 failed, 0 errors, 0 skipped**, run to completion without `-x` or a test filter.

Base/unchanged HEAD: `75837b04da05c3b736d6f48648536627bd062ca0`. No staging or commit.

## Changes

- **B-1:** Keep witness/attestation blocks in column ownership geometry. The early witness return still yields no names and an ambiguous score, so witnesses score zero. Also retain explicit witness/attestation rules during extraction when a name is beyond the 22 pt caption window and no heading was attributed. The measured one-line fix alone closes A2 but leaves 112 wrong placements in the wider sweep because those rules never became blocks. Rules whose subordinate identity is already quarantined by the absorbed-name veto retain the existing r11 behavior and are not added as candidates.
- **B-2:** Deny the company-score increment when the selected heading row intersects the gutter between same-page blocks whose signature rules are less than 30 pt apart. This uses the same open-gap intersection rule as printed names. It applies symmetrically, including when one company is not a signer. A separate mixed-company text parser was unnecessary. Authoritative printed-name scoring is unchanged.
- **N-1:** `test_placement_r16.test_witness_column_never_owns_party_name` now asserts `party.scores == [0]`; `witness.scores == [0]` remains intact. The witness scores zero, and the party does not gain Pat from the witness column. This one assertion is the only change to an existing test.

## Failing first

| Run on r16 | Failed | Passed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| failing-first | 308 | 3846 | 0 | 0 |
| failing-first-heading | 4 | 0 | 0 | 0 |

The first run includes all 480 A2 cases, all 2,496 sweep cases, F permutations and gaps, the two real-worker reproductions with both signer sets, and corrected N-1. The four direct heading assertions were then run on unchanged r16 and all failed. The first production candidate (the one-line B-1 fix plus B-2) still failed 112 sweep cases; retaining the missing witness blocks made all 4,158 targeted cases pass. The first complete suite then found one existing r11 structural assertion: 1 failed, 15,497 passed, 0 errors/skipped. No test was edited: narrowing retention around the existing absorbed-name veto restored that assertion. The unchanged r11 test passed, then all 5,399 combined targeted cases passed with 0 failures/errors/skips before the final full-suite result above. The complete unsuccessful suite is retained in `retained-witness-candidate/full-suite.*`.

## Per-family results

Cells are **wrong / placed / holds / bare**. Wrong is counted within placed, not as another status. Every emitted field in the new families is checked against its signer’s own rule. The original family oracles and generators are reused unchanged. The 72-case r14 L-1 subset is listed separately and is already included in the r14 grid.

| Family | Cases | r16 | r17 |
| --- | ---: | --- | --- |
| Matrix 1 | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 |
| Matrix 2 | 270 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 |
| r11 B-1 | 1020 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 |
| Signature controls | 204 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 |
| M-1 | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 |
| r9 H-1 | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 |
| Seven goldens | 7 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 |
| Same-band right host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r13 same-band grid | 42 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 |
| r14 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r14 grid | 3456 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 |
| r14 fixed sweep | 360 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 |
| r14 correct controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 |
| r15 M1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r15 M2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r15 M1 | 640 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 |
| r15 M2 | 2592 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 |
| r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 |
| r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 |
| r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 |
| r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 |
| r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 |
| r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 |
| r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 |
| r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 |
| r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 |
| r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 |
| r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 |
| r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 |
| r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 |
| r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 |
| r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 |
| r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 |
| r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 |
| r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 |
| r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 |
| r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 |
| r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 |
| r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 |
| r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 |
| r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 |
| r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 |
| r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 |
| r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 |
| r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 |
| r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 |
| r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 |
| r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 |
| r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 |
| r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 |
| r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 |
| r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 |
| r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 |
| r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 |
| r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 |
| r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 |
| r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 |
| r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 |
| r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 |
| r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 |
| r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 |
| r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 |
| r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 |
| r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 |
| r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 |
| r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 |
| r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 |
| A2 exact witness captions | 480 | 96 / 96 / 384 / 0 | 0 / 0 / 480 / 0 |
| A2 additional dy=20 | 96 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 |
| Witness wider sweep | 2496 | 184 / 184 / 2312 / 0 | 0 / 0 / 2496 / 0 |
| F three-party permutations | 288 | 8 / 138 / 150 / 0 | 0 / 130 / 158 / 0 |
| F heading gaps long | 432 | 12 / 222 / 210 / 0 | 0 / 210 / 222 / 0 |
| F heading gaps short | 432 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 |
| B1 reproduction | 2 | 1 / 1 / 1 / 0 | 0 / 0 / 2 / 0 |
| B2 reproduction | 2 | 1 / 1 / 1 / 0 | 0 / 0 / 2 / 0 |

Original r16 table totals exclude the overlapping 72-case L-1 subset:

| Source | Cases | Wrong | Placed | Holds | Bare |
| --- | ---: | ---: | ---: | ---: | ---: |
| r16 | 10698 | 0 | 3020 | 7665 | 13 |
| r17 | 10698 | 0 | 3020 | 7665 | 13 |

## Matrix definitions and optional L-1

- **A2 (480):** six exact captions × dy {0, 40, 60, 80, 100} × four headings × both orientations × PAT/DAN+PAT. The review’s verbal dy 0–100 axes would also include 20; those 96 additional cases are measured separately, so all six staggers are covered.
- **Wider sweep (2,496):** Witness:/Attest: × dy 0–120 in 10 pt steps × name gaps 12/24/40 × our printed name off/on × HARBOR / Harbor Light / RECIPIENT: / no heading × both orientations × PAT/DAN+PAT. Both orientations make the stated count 2,496; the axes without orientation yield 1,248. r16 reproduces the review’s 184 wrong.
- **F (288):** six party permutations × six Fleet staggers {0,20,40,60,80,100} × short/long Harbor heading × our printed name off/on × PAT/DAN+PAT. The rule gap is 22 pt. This explicit reconstruction reproduces the verbatim B-2 case and has 8 r16 wrong; it is not claimed to be the reviewer’s unpublished exact 3/288 matrix.
- **F gaps (864):** gaps 8/16/22/28/34/40 × short/long headings × six permutations × six staggers × PAT/DAN+PAT, without our printed name. All fields must remain on Fleet’s or Harbor’s own signature/date rule; Northwind is never an allowed signer block.
- **L-1 experiment:** an in-memory candidate merges column ranges with at least 80% overlap relative to the larger width. It is measured on the entire table plus new ragged (384) and centred (144) controls. These new controls have explicit axes in `l1_candidate.py`; they are not asserted to be the reviewer’s unpublished matrices behind the 150 correct-to-hold count.

| L-1 candidate family | Cases | r17 | Optional merge |
| --- | ---: | --- | --- |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 272 / 112 / 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 96 / 48 / 0 |

**L-1 dropped:** six direct extracted-block checks reintroduce B-1: r16 6 wrong/0 holds, r17 0 wrong/6 holds, optional merge 6 wrong/0 holds. This extends N-1 to overlapping witness/party ranges and emits actual signature/date fields. It is not a PDF extraction reproduction. See [decision](l1-decision.md) and [all placements](l1-witness-overlap.json). The review’s 150 correct-to-hold layouts are not claimed recovered.

## Evidence and preservation

- SHA-256 checked all 1,636 initially tracked files. Only `placement.py` and the exact N-1 assertion differ; all other existing tests, fixtures, golden archives, and evidence are byte-for-byte unchanged. Memory is unchanged.
- 72 real-worker evaluations match their in-process counterparts, including the seven goldens, prior reproductions/controls, and B-1/B-2. No external HTTP calls; model callbacks are local deterministic stubs.
- The one-line B-1-only variant preserves every r16 family’s wrong/placed/hold/bare count. The final r17 preserves every original full result except analysis_version: 0 full-result differences across the original 10,770 evaluations. r8 C7 remains 0 wrong / 5 placed / 0 holds, with all five model calls and complete results unchanged; its scores and margins are therefore unchanged.
- All 11,362 original test cases remain in the completed suite; 4,136 new cases were added. [Test inventory audit](test-inventory-summary.json).
- [Full suite log](full-suite.txt), [JUnit](full-suite.xml), [all outcomes](full-suite-cases.json), [suite summary](full-suite-summary.json). The unchanged launcher’s scratch-directory warning is retained; pytest itself completed successfully.
- [Replay runner](check_evidence.py), [per-family counts](counterfactual-summary.json), [all cases/results](counterfactual-cases.json), [worker checks](counterfactual-workers.json), [goldens](placements.json), [hash audit](preservation-summary.json), [test-run counts](test-runs-summary.json), [commands/method](method.md).

**Blockers:** none.
