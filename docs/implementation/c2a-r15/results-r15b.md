# C2a r15b results

**Bar not reached; best candidate left uncommitted.**

Chosen rule: **nearest-column ownership + (b′)**, with `VERSION = c2a.15`. Aligned rules sharing a left edge form one column; ownership uses horizontal edge distance and fails closed when distinct columns tie within 2 pt. The (b′) veto propagates a peer block’s zero signer score across a shared physical name row.

The expanded comparison has **10,698 identified cases**, including **944 added control cases** in 90 families. The 72-case L-1 subset is displayed separately and excluded from that total. Both candidates preserve the seven goldens exactly except `analysis_version`, including native fields. External HTTP/model calls: **0**; model callbacks are local deterministic stubs.

Nearest-column ownership alone has **one wrong placement** in the added r3 witness control (`inserted_raw_person_vetoes_across_fixtures`, witness, call 3). The conflicting Lee Harbor row lies nearer the witness column, so removing it from the other block’s printed-name evidence permits a company-only Pat placement. The combined rule holds that case and has **zero wrong placements in every measured family**.

Nearest-only also changes the r4 gap-between-columns hold to retain one high-confidence assignment, violating that control’s diagnostic assertion even though no fields are emitted. The [focused gap audit](gap-control-audit-r15b.json) confirms that the combination preserves all of the existing control’s assertions.

Final full suite: **11,327 passed, 13 failed, 0 errors, 0 skipped**. It completed without `-x`. No existing test or fixture was changed, skipped, weakened or retargeted. The final source matches the measured combined candidate. HEAD remains `d88bfb889f3863796b276a6f0aef3da57539c4c3`; nothing was staged or committed.

## Every final-suite failure

- `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-HARBOR LIGHT ANALYTICS, INC., a Delaware corporation]`
- `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-HARBOR LIGHT ANALYTICS, INC. (the "Recipient")]`
- `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-RECIPIENT]`
- `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-RECIPIENT:]`
- `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-For and on behalf of the Recipient]`
- `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged[caption_row_right-C12-harbor light analytics, inc.]`
- `dealroom_sign.tests.test_placement_r14::test_staggered_without_mixed_heading_stays_placed[left]`
- `dealroom_sign.tests.test_placement_r14::test_staggered_without_mixed_heading_stays_placed[right]`
- `dealroom_sign.tests.test_placement_r4::test_stacked_individual_blocks_place_without_neighbour_veto[80-headings]`
- `dealroom_sign.tests.test_placement_r4::test_stacked_individual_blocks_place_without_neighbour_veto[80-captions]`
- `dealroom_sign.tests.test_placement_r4::test_stacked_individual_blocks_place_without_neighbour_veto[110-headings]`
- `dealroom_sign.tests.test_placement_r5::test_m2_stacked_headings_with_side_dates[True-80]`
- `dealroom_sign.tests.test_placement_r5::test_m2_stacked_headings_with_side_dates[True-110]`

The r14 correct controls expect Pat’s signature/date at y290/y330 in the unambiguous HARBOR column. The combined shared-row veto returns `needs_sender` with empty fields because the unheaded competing block has score zero. The same generalised veto also holds six r10 caption-row-right controls and five r4/r5 stacked-signer controls. These preservation failures were not hidden by changing the tests.

## Per-family comparison

Each cell is **wrong / placed / holds**. Wrong is included in placed. Bare outcomes are recorded separately in the machine-readable data. The `Fxx` IDs map the completion marker to this table.

| ID | Family | Cases | r14 | Nearest | Nearest + (b′) |
| --- | --- | ---: | ---: | ---: | ---: |
| F01 | Matrix 1 | 120 | 0 / 0 / 120 | 0 / 0 / 120 | 0 / 0 / 120 |
| F02 | Matrix 2 | 270 | 0 / 0 / 270 | 0 / 0 / 270 | 0 / 0 / 270 |
| F03 | r11 B-1 | 1020 | 0 / 0 / 1020 | 0 / 0 / 1020 | 0 / 0 / 1020 |
| F04 | Signature controls | 204 | 0 / 6 / 198 | 0 / 6 / 198 | 0 / 6 / 198 |
| F05 | M-1 | 16 | 0 / 16 / 0 | 0 / 16 / 0 | 0 / 16 / 0 |
| F06 | r9 heading matrix | 72 | 0 / 6 / 66 | 0 / 6 / 66 | 0 / 6 / 66 |
| F07 | r9 H-1 | 40 | 0 / 0 / 40 | 0 / 0 / 40 | 0 / 0 / 40 |
| F08 | Seven goldens | 7 | 0 / 6 / 0 | 0 / 6 / 0 | 0 / 6 / 0 |
| F09 | Same-band right host | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F10 | r12 B-1 reproduction | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F11 | r13 same-band grid | 42 | 0 / 0 / 42 | 0 / 0 / 42 | 0 / 0 / 42 |
| F12 | r12 B-1 sweep | 864 | 0 / 0 / 864 | 0 / 0 / 864 | 0 / 0 / 864 |
| F13 | L-1 short-rule controls | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 |
| F14 | L-2 own-company controls | 40 | 0 / 20 / 20 | 0 / 20 / 20 | 0 / 20 / 20 |
| F15 | r14 reproduction | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F16 | r14 grid | 3456 | 0 / 1200 / 2256 | 0 / 2436 / 1020 | 0 / 1176 / 2280 |
| F17 | r14 fixed sweep | 360 | 0 / 128 / 232 | 0 / 244 / 116 | 0 / 128 / 232 |
| F18 | r14 correct controls | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 0 / 2 |
| F19 | r14 L-1 (grid subset) | 72 | 0 / 0 / 72 | 0 / 0 / 72 | 0 / 0 / 72 |
| F20 | r15 M1 reproduction | 2 | 1 / 1 / 1 | 0 / 0 / 2 | 0 / 0 / 2 |
| F21 | r15 M2 reproduction | 2 | 1 / 1 / 1 | 0 / 0 / 2 | 0 / 0 / 2 |
| F22 | r15 M1 | 640 | 100 / 100 / 540 | 0 / 0 / 640 | 0 / 0 / 640 |
| F23 | r15 M2 | 2592 | 432 / 432 / 2160 | 0 / 0 / 2592 | 0 / 0 / 2592 |
| F24 | r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 | 0 / 0 / 5 | 0 / 0 / 5 |
| F25 | r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 | 0 / 12 / 24 | 0 / 12 / 24 |
| F26 | r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F27 | r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| F28 | r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F29 | r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F30 | r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 |
| F31 | r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F32 | r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F33 | r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F34 | r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F35 | r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 | 0 / 0 / 12 | 0 / 0 / 12 |
| F36 | r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 | 1 / 5 / 34 | 0 / 4 / 35 |
| F37 | r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| F38 | r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F39 | r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 | 0 / 3 / 3 | 0 / 3 / 3 |
| F40 | r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| F41 | r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F42 | r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| F43 | r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 | 0 / 8 / 8 | 0 / 8 / 8 |
| F44 | r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F45 | r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 | 0 / 12 / 0 | 0 / 12 / 0 |
| F46 | r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 | 0 / 31 / 0 | 0 / 31 / 0 |
| F47 | r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 | 0 / 1 / 1 | 0 / 1 / 1 |
| F48 | r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 | 0 / 3 / 0 | 0 / 3 / 0 |
| F49 | r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F50 | r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 1 / 3 |
| F51 | r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F52 | r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F53 | r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F54 | r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| F55 | r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F56 | r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 |
| F57 | r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F58 | r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 | 0 / 0 / 6 | 0 / 0 / 6 |
| F59 | r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 | 0 / 3 / 0 | 0 / 3 / 0 |
| F60 | r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 | 0 / 30 / 0 | 0 / 30 / 0 |
| F61 | r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
| F62 | r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F63 | r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 | 0 / 1 / 1 | 0 / 1 / 1 |
| F64 | r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 | 0 / 1 / 2 | 0 / 1 / 2 |
| F65 | r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 | 0 / 2 / 2 | 0 / 2 / 2 |
| F66 | r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 | 0 / 8 / 0 | 0 / 8 / 0 |
| F67 | r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F68 | r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 | 0 / 2 / 2 | 0 / 0 / 4 |
| F69 | r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 | 0 / 5 / 5 | 0 / 5 / 5 |
| F70 | r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F71 | r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 | 0 / 0 / 3 | 0 / 0 / 3 |
| F72 | r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 | 0 / 7 / 0 | 0 / 7 / 0 |
| F73 | r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 | 0 / 2 / 1 | 0 / 2 / 1 |
| F74 | r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 | 0 / 0 / 5 | 0 / 0 / 5 |
| F75 | r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F76 | r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F77 | r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F78 | r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F79 | r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 | 0 / 12 / 6 | 0 / 12 / 6 |
| F80 | r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 | 0 / 2 / 2 | 0 / 2 / 2 |
| F81 | r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 | 0 / 9 / 0 | 0 / 9 / 0 |
| F82 | r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F83 | r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 |
| F84 | r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 | 0 / 10 / 0 | 0 / 10 / 0 |
| F85 | r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 | 0 / 3 / 0 | 0 / 3 / 0 |
| F86 | r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F87 | r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F88 | r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F89 | r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 | 0 / 0 / 15 | 0 / 0 / 15 |
| F90 | r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F91 | r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
| F92 | r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 | 0 / 7 / 0 | 0 / 7 / 0 |
| F93 | r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F94 | r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 0 / 0 / 2 |
| F95 | r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F96 | r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 | 0 / 0 / 25 | 0 / 0 / 25 |
| F97 | r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 | 0 / 1 / 4 | 0 / 1 / 4 |
| F98 | r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 | 0 / 5 / 0 | 0 / 5 / 0 |
| F99 | r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 0 |
| F100 | r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| F101 | r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 | 0 / 0 / 5 | 0 / 0 / 5 |
| F102 | r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F103 | r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 | 0 / 0 / 240 | 0 / 0 / 240 |
| F104 | r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 | 0 / 0 / 60 | 0 / 0 / 60 |
| F105 | r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 | 0 / 6 / 6 | 0 / 6 / 6 |
| F106 | r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 | 0 / 6 / 6 | 0 / 6 / 6 |
| F107 | r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 | 0 / 6 / 6 | 0 / 6 / 6 |
| F108 | r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 | 0 / 6 / 6 | 0 / 0 / 12 |
| F109 | r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 | 0 / 0 / 40 | 0 / 0 / 40 |
| F110 | r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 | 0 / 0 / 56 | 0 / 0 / 56 |
| F111 | r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 | 0 / 48 / 0 | 0 / 48 / 0 |
| F112 | r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 | 0 / 0 / 1 | 0 / 0 / 1 |
| F113 | r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 |

Totals excluding the L-1 subset:

| Source | Wrong | Placed | Holds | Bare |
| --- | ---: | ---: | ---: | ---: |
| r14 | 534 | 2202 | 8483 | 13 |
| nearest | 1 | 3021 | 7664 | 13 |
| combined | 0 | 1631 | 9054 | 13 |

## Correct-placement costs and added families

Nearest alone restores 1,352 r14 holds (1,236 GRID + 116 FIXED) without losing any r14 correct placements, but introduces the one witness wrong placement above. The combination loses 24 r14 GRID placements and both r14 correct controls, plus three r4 stacked-individual, two r5 stacked-heading and six r10 caption-row-right controls: **37 correct placements become holds**. The 26 r14 cases are the same ordinary staggered layouts disclosed in r15; the additional 11 are ordinary stacked and outdented-name layouts. The 72 r14 L-1 holds remain holds under both candidates.

The added control families are listed below with their original test function and full case counts. They include the previously missing r10 `caption_row_right` family as its own table row.

- **r2 reviewer_wrong_signer_goldens**: 5 cases; `dealroom_sign.tests.test_placement_r2::test_reviewer_wrong_signer_goldens`.
- **r2 unnamed_signer_never_takes_named_block**: 42 cases; `dealroom_sign.tests.test_placement_r2::test_unnamed_signer_never_takes_named_block`.
- **r2 nearby_body_is_redacted_and_model_identity_is_minimal**: 1 cases; `dealroom_sign.tests.test_placement_r2::test_nearby_body_is_redacted_and_model_identity_is_minimal`.
- **r2 caption_cannot_claim_next_block**: 3 cases; `dealroom_sign.tests.test_placement_r2::test_caption_cannot_claim_next_block`.
- **r2 date_cannot_be_borrowed_from_next_column**: 2 cases; `dealroom_sign.tests.test_placement_r2::test_date_cannot_be_borrowed_from_next_column`.
- **r2 native_signature_is_tight_and_bottom_anchored**: 1 cases; `dealroom_sign.tests.test_placement_r2::test_native_signature_is_tight_and_bottom_anchored`.
- **r2 printed_name_variants_veto_company_match**: 4 cases; `dealroom_sign.tests.test_placement_r2::test_printed_name_variants_veto_company_match`.
- **r2 named_caption_is_not_dropped_when_it_is_long**: 1 cases; `dealroom_sign.tests.test_placement_r2::test_named_caption_is_not_dropped_when_it_is_long`.
- **r2 unlabelled_unrecognized_caption_cannot_be_ignored**: 2 cases; `dealroom_sign.tests.test_placement_r2::test_unlabelled_unrecognized_caption_cannot_be_ignored`.
- **r2 heading_cannot_cross_a_previous_unlabelled_rule**: 1 cases; `dealroom_sign.tests.test_placement_r2::test_heading_cannot_cross_a_previous_unlabelled_rule`.
- **r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed**: 1 cases; `dealroom_sign.tests.test_placement_r2::test_date_in_close_right_column_with_unlabelled_signature_is_not_borrowed`.
- **r3 other_person_in_whole_raw_extent_never_gets_high**: 12 cases; `dealroom_sign.tests.test_placement_r3::test_other_person_in_whole_raw_extent_never_gets_high`.
- **r3 inserted_raw_person_vetoes_across_fixtures**: 39 cases; `dealroom_sign.tests.test_placement_r3::test_inserted_raw_person_vetoes_across_fixtures`.
- **r3 company_only_requires_every_raw_line_accounted_for**: 3 cases; `dealroom_sign.tests.test_placement_r3::test_company_only_requires_every_raw_line_accounted_for`.
- **r3 matching_printed_name_can_resolve_label_prefix**: 1 cases; `dealroom_sign.tests.test_placement_r3::test_matching_printed_name_can_resolve_label_prefix`.
- **r3 title_case_body_never_leaves_local_evidence**: 6 cases; `dealroom_sign.tests.test_placement_r3::test_title_case_body_never_leaves_local_evidence`.
- **r3 matched_name_does_not_override_unresolved_person_like_line**: 3 cases; `dealroom_sign.tests.test_placement_r3::test_matched_name_does_not_override_unresolved_person_like_line`.
- **r3 company_only_requires_one_signer_even_if_other_signer_has_named_block**: 1 cases; `dealroom_sign.tests.test_placement_r3::test_company_only_requires_one_signer_even_if_other_signer_has_named_block`.
- **r3 second_person_in_same_raw_line_also_vetoes**: 3 cases; `dealroom_sign.tests.test_placement_r3::test_second_person_in_same_raw_line_also_vetoes`.
- **r4 rule_row_name_controls_identity**: 16 cases; `dealroom_sign.tests.test_placement_r4::test_rule_row_name_controls_identity`.
- **r4 side_by_side_company_blocks_keep_their_own_names**: 1 cases; `dealroom_sign.tests.test_placement_r4::test_side_by_side_company_blocks_keep_their_own_names`.
- **r4 golden_harbor_role_suffix_keeps_exact_boxes**: 12 cases; `dealroom_sign.tests.test_placement_r4::test_golden_harbor_role_suffix_keeps_exact_boxes`.
- **r4 golden_harbor_block_wording_keeps_exact_boxes**: 31 cases; `dealroom_sign.tests.test_placement_r4::test_golden_harbor_block_wording_keeps_exact_boxes`.
- **r4 ascii_hyphen_role_preserves_printed_identity**: 2 cases; `dealroom_sign.tests.test_placement_r4::test_ascii_hyphen_role_preserves_printed_identity`.
- **r4 unnamed_company_block_accounts_for_roles**: 3 cases; `dealroom_sign.tests.test_placement_r4::test_unnamed_company_block_accounts_for_roles`.
- **r4 title_person_remains_unresolved_and_holds**: 1 cases; `dealroom_sign.tests.test_placement_r4::test_title_person_remains_unresolved_and_holds`.
- **r4 stacked_individual_blocks_place_without_neighbour_veto**: 4 cases; `dealroom_sign.tests.test_placement_r4::test_stacked_individual_blocks_place_without_neighbour_veto`.
- **r4 stacked_individual_blocks_do_not_accept_company_only**: 2 cases; `dealroom_sign.tests.test_placement_r4::test_stacked_individual_blocks_do_not_accept_company_only`.
- **r4 name_in_gap_between_party_columns_makes_both_uncertain**: 1 cases; `dealroom_sign.tests.test_placement_r4::test_name_in_gap_between_party_columns_makes_both_uncertain`.
- **r4 equidistant_row_between_stacked_rules_is_not_discarded**: 1 cases; `dealroom_sign.tests.test_placement_r4::test_equidistant_row_between_stacked_rules_is_not_discarded`.
- **r5 b1_far_heading_vetoes_company_only**: 3 cases; `dealroom_sign.tests.test_placement_r5::test_b1_far_heading_vetoes_company_only`.
- **r5 b1_far_caption_vetoes_company_only**: 2 cases; `dealroom_sign.tests.test_placement_r5::test_b1_far_caption_vetoes_company_only`.
- **r5 b1_walk_stops_at_prose_or_other_rule**: 2 cases; `dealroom_sign.tests.test_placement_r5::test_b1_walk_stops_at_prose_or_other_rule`.
- **r5 b1_walk_crosses_page_edge**: 2 cases; `dealroom_sign.tests.test_placement_r5::test_b1_walk_crosses_page_edge`.
- **r5 b1_distant_name_never_adds_confidence**: 6 cases; `dealroom_sign.tests.test_placement_r5::test_b1_distant_name_never_adds_confidence`.
- **r5 b2_proven_empty_widget_and_plain_link_keep_placement**: 3 cases; `dealroom_sign.tests.test_placement_r5::test_b2_proven_empty_widget_and_plain_link_keep_placement`.
- **r5 h1_title_wording_keeps_exact_golden**: 30 cases; `dealroom_sign.tests.test_placement_r5::test_h1_title_wording_keeps_exact_golden`.
- **r5 h1_behalf_wording_keeps_exact_golden**: 4 cases; `dealroom_sign.tests.test_placement_r5::test_h1_behalf_wording_keeps_exact_golden`.
- **r5 h1_behalf_other_person_vetoes_named_signer**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_h1_behalf_other_person_vetoes_named_signer`.
- **r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only**: 2 cases; `dealroom_sign.tests.test_placement_r5::test_h1_wrapped_sentence_is_not_a_name_but_blocks_company_only`.
- **r5 h1_company_only_title_rules_stay_strict**: 3 cases; `dealroom_sign.tests.test_placement_r5::test_h1_company_only_title_rules_stay_strict`.
- **r5 h1_positive_name_title_remainder_predicate**: 4 cases; `dealroom_sign.tests.test_placement_r5::test_h1_positive_name_title_remainder_predicate`.
- **r5 m1_compound_name_caption_keeps_exact_golden**: 8 cases; `dealroom_sign.tests.test_placement_r5::test_m1_compound_name_caption_keeps_exact_golden`.
- **r5 m1_compound_caption_keeps_mismatched_person_veto**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_m1_compound_caption_keeps_mismatched_person_veto`.
- **r5 m2_stacked_headings_with_side_dates**: 4 cases; `dealroom_sign.tests.test_placement_r5::test_m2_stacked_headings_with_side_dates`.
- **r5 l1_empty_contact_labels_only_are_accounted**: 10 cases; `dealroom_sign.tests.test_placement_r5::test_l1_empty_contact_labels_only_are_accounted`.
- **r5 l2_single_typed_row_signature_and_date**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_l2_single_typed_row_signature_and_date`.
- **r5 n1_mixed_case_role_shaped_names_veto_company_only**: 3 cases; `dealroom_sign.tests.test_placement_r5::test_n1_mixed_case_role_shaped_names_veto_company_only`.
- **r5 n1_uppercase_role_abbreviations_remain_accounted**: 7 cases; `dealroom_sign.tests.test_placement_r5::test_n1_uppercase_role_abbreviations_remain_accounted`.
- **r5 h1_execution_clause_is_a_heading**: 3 cases; `dealroom_sign.tests.test_placement_r5::test_h1_execution_clause_is_a_heading`.
- **r5 b2_unproven_empty_widget_holds**: 5 cases; `dealroom_sign.tests.test_placement_r5::test_b2_unproven_empty_widget_holds`.
- **r5 b1_named_block_does_not_use_distant_veto**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_b1_named_block_does_not_use_distant_veto`.
- **r5 b1_veto_respects_neighbour_column_band**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_b1_veto_respects_neighbour_column_band`.
- **r5 h1_wrapped_witness_paragraph_keeps_exact_golden**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_h1_wrapped_witness_paragraph_keeps_exact_golden`.
- **r5 b1_cross_page_walk_includes_row_at_page_top**: 1 cases; `dealroom_sign.tests.test_placement_r5::test_b1_cross_page_walk_includes_row_at_page_top`.
- **r6 h2_contact_rule_preserves_typed_identity**: 18 cases; `dealroom_sign.tests.test_placement_r6::test_h2_contact_rule_preserves_typed_identity`.
- **r6 h1_previous_caption_stays_with_its_host**: 4 cases; `dealroom_sign.tests.test_placement_r6::test_h1_previous_caption_stays_with_its_host`.
- **r6 m1_repeated_running_header_is_neutral**: 9 cases; `dealroom_sign.tests.test_placement_r6::test_m1_repeated_running_header_is_neutral`.
- **r6 m1_nonrepeated_header_retains_identity_veto**: 2 cases; `dealroom_sign.tests.test_placement_r6::test_m1_nonrepeated_header_retains_identity_veto`.
- **r6 m1_page_number_does_not_hide_next_page_name**: 4 cases; `dealroom_sign.tests.test_placement_r6::test_m1_page_number_does_not_hide_next_page_name`.
- **r6 m2_behalf_company_suffix_keeps_exact_golden**: 10 cases; `dealroom_sign.tests.test_placement_r6::test_m2_behalf_company_suffix_keeps_exact_golden`.
- **r6 m2_behalf_role_is_not_a_person**: 3 cases; `dealroom_sign.tests.test_placement_r6::test_m2_behalf_role_is_not_a_person`.
- **r6 m3_comma_witness_paragraph_keeps_exact_golden**: 1 cases; `dealroom_sign.tests.test_placement_r6::test_m3_comma_witness_paragraph_keeps_exact_golden`.
- **r6 n1_title_person_before_comma_still_vetoes**: 2 cases; `dealroom_sign.tests.test_placement_r6::test_n1_title_person_before_comma_still_vetoes`.
- **r6 n2_period_name_still_vetoes_named_block**: 2 cases; `dealroom_sign.tests.test_placement_r6::test_n2_period_name_still_vetoes_named_block`.
- **r7 h1_short_contact_caption_preserves_typed_identity**: 15 cases; `dealroom_sign.tests.test_placement_r7::test_h1_short_contact_caption_preserves_typed_identity`.
- **r7 l1_repeated_body_name_retains_identity_veto**: 2 cases; `dealroom_sign.tests.test_placement_r7::test_l1_repeated_body_name_retains_identity_veto`.
- **r7 l1_page_number_is_neutral_in_body**: 4 cases; `dealroom_sign.tests.test_placement_r7::test_l1_page_number_is_neutral_in_body`.
- **r7 l2_prose_ending_keeps_exact_harbor_boxes**: 7 cases; `dealroom_sign.tests.test_placement_r7::test_l2_prose_ending_keeps_exact_harbor_boxes`.
- **r7 l2_period_name_still_holds**: 2 cases; `dealroom_sign.tests.test_placement_r7::test_l2_period_name_still_holds`.
- **r7 n1_hold_reason_agrees_with_signer_count**: 2 cases; `dealroom_sign.tests.test_placement_r7::test_n1_hold_reason_agrees_with_signer_count`.
- **r7 n1_one_missing_signer_keeps_singular_reason**: 1 cases; `dealroom_sign.tests.test_placement_r7::test_n1_one_missing_signer_keeps_singular_reason`.
- **r8 b1_unusual_host_never_places_on_neighbour**: 25 cases; `dealroom_sign.tests.test_placement_r8::test_b1_unusual_host_never_places_on_neighbour`.
- **r8 b1_signature_controls_keep_previous_outcome**: 5 cases; `dealroom_sign.tests.test_placement_r8::test_b1_signature_controls_keep_previous_outcome`.
- **r8 m1_c7_keeps_400_candidate_and_never_places_on_witness**: 5 cases; `dealroom_sign.tests.test_placement_r8::test_m1_c7_keeps_400_candidate_and_never_places_on_witness`.
- **r8 l1_only_authorised_signatory_uses_model_on_its_own_line**: 1 cases; `dealroom_sign.tests.test_placement_r8::test_l1_only_authorised_signatory_uses_model_on_its_own_line`.
- **r8 contact_vocabulary_is_other_without_preceding_host**: 6 cases; `dealroom_sign.tests.test_placement_r8::test_contact_vocabulary_is_other_without_preceding_host`.
- **r9 b1_same_row_right_behalf_holds**: 5 cases; `dealroom_sign.tests.test_placement_r9::test_b1_same_row_right_behalf_holds`.
- **r9 absorbed_identity_vetoes_every_overlapping_host**: 1 cases; `dealroom_sign.tests.test_placement_r9::test_absorbed_identity_vetoes_every_overlapping_host`.
- **r10 b1_out_of_slot_identity_holds**: 240 cases; `dealroom_sign.tests.test_placement_r10::test_b1_out_of_slot_identity_holds`.
- **r10 b1_name_below_caption_holds**: 60 cases; `dealroom_sign.tests.test_placement_r10::test_b1_name_below_caption_holds`.
- **r10 signature_out_of_slot_controls_unchanged / title_then_name**: 12 cases; `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged`.
- **r10 signature_out_of_slot_controls_unchanged / tab_gap**: 12 cases; `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged`.
- **r10 signature_out_of_slot_controls_unchanged / indented**: 12 cases; `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged`.
- **r10 signature_out_of_slot_controls_unchanged / caption_row_right**: 12 cases; `dealroom_sign.tests.test_placement_r10::test_signature_out_of_slot_controls_unchanged`.
- **r10 h1_out_of_slot_stacks_still_hold**: 40 cases; `dealroom_sign.tests.test_placement_r10::test_h1_out_of_slot_stacks_still_hold`.
- **r10 m1_non_exempt_contact_out_of_slot_holds**: 56 cases; `dealroom_sign.tests.test_placement_r10::test_m1_non_exempt_contact_out_of_slot_holds`.
- **r10 six_contact_captions_remain_exempt**: 48 cases; `dealroom_sign.tests.test_placement_r10::test_six_contact_captions_remain_exempt`.
- **r11 subordinating_rule_without_block_keeps_identity_veto**: 1 cases; `dealroom_sign.tests.test_placement_r11::test_subordinating_rule_without_block_keeps_identity_veto`.
- **r14 separate_printing_of_same_name_is_not_vetoed**: 2 cases; `dealroom_sign.tests.test_placement_r14::test_separate_printing_of_same_name_is_not_vetoed`.

## Earlier full attempt: distinct intervals

The first implementation treated aligned rules of different lengths as different columns. It failed the offer golden. Its already-started full suite was allowed to finish without `-x` before the final source was installed. Every failure from that completed run follows.

`{"failure": 6, "passed": 11330}`

- `dealroom_sign.tests.test_placement::test_golden[offer]`
- `dealroom_sign.tests.test_placement_r10::test_seven_goldens_exact[offer]`
- `dealroom_sign.tests.test_placement_r3::test_inserted_raw_person_vetoes_across_fixtures[witness]`
- `dealroom_sign.tests.test_placement_r4::test_name_in_gap_between_party_columns_makes_both_uncertain`
- `dealroom_sign.tests.test_placement_r5::test_b1_all_seven_goldens_exact[offer]`
- `dealroom_sign.tests.test_placement_r7::test_seven_goldens_remain_exact_against_r4_and_r5[offer]`

## Evidence

- [Method and commands](method-r15b.md); [comparison generator](check_evidence-r15b.py).
- [Nearest table data](counterfactual-summary-r15b.json); [combined table data](counterfactual-summary-combined-r15b.json).
- [Every combined case/result](counterfactual-cases-combined-r15b.json); [differences](counterfactual-differences-combined-r15b.json); [worker checks](counterfactual-workers-combined-r15b.json).
- [Geometry audit](geometry-audit-r15b.json): all 4,649 combined fields exactly match accepted r14 geometry.
- [Final full-suite output](full-suite-r15b.txt); [JUnit](full-suite-r15b.xml); [all outcomes](full-suite-cases-r15b.json); [summary](full-suite-summary-r15b.json).
- [Earlier full-suite output](full-suite-distinct-intervals-r15b.txt); [all earlier failures](full-suite-distinct-intervals-summary-r15b.json).
- [Preservation audit](preservation-summary-r15b.json); [final candidate patch](candidate-combined-r15b.patch).

Open: the existing-test preservation requirement is unmet. No permitted candidate reached all three bars. The safest candidate is left uncommitted for review. Project memory remains unchanged; no venv, cache directory or node_modules remains in the repository.
