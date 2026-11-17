# C2a r16 results

**Bar met.**

Chosen: nearest-column ownership with witness/attestation exclusion and ambiguous-name scoring. `VERSION = 'c2a.16'`. No generalised (b-prime) shared-row veto.

Full Send suite (`dealroom_sign/tests`): **11,362 passed, 0 failed, 0 errors, 0 skipped**. It completed without `-x`, selection filters, or a maximum-failures override. The 11,340 existing tests and 22 added r16 cases all ran.

Every family in the r15b table was replayed: **10,698 cases**, **0 wrong placements**, including all r15 M1/M2 reproductions and sweeps. The 72-case L-1 subset remains separately displayed and is excluded from totals. **Seven goldens match exactly except `analysis_version`**, including native fields.

Hash verification: **245 existing test/fixture files checked; 0 changed**. No existing test or fixture was changed, skipped, weakened, deleted, or retargeted. HEAD remains `d88bfb889f3863796b276a6f0aef3da57539c4c3`; nothing was staged or committed. The inherited report and project memory are unchanged.

## Chosen rule and bounded experiments

Aligned rules sharing a left edge remain one column. Ownership uses horizontal edge distance; nearest columns within 2 pt fail closed. A witness signs next to a party but is never that party: Witness, Attest, and Attestation line labels are excluded from candidate party columns and cannot receive party scores. All scores are computed before role labels are redacted, preserving traversal-order independence.

A printed-name row intersecting the open gutter between neighbouring party columns (existing vertical band: less than 30 pt) makes scoring return zero in each affected raw extent. Nearest-column ties also return zero rather than falling back to company hints or another name. Staggered outdented captions retain nearest-column ownership. The r14 mixed-heading veto remains unchanged.

**Fixture correction:** the r3 `witness`, call 3 reproduction has two party blocks, Harbor and Fleet, both labelled `By:`; no witness/attestation block exists in its extracted candidates. Lee’s row starts at x296.4 in the x266.4–316.8 gutter and extends to x362.2 inside Fleet’s column. Witness exclusion alone therefore cannot fix it. Gutter variant 1 (whole row inside the gap) fixed the r4 diagnostic but retained this wrong placement. Variant 2 (row intersects the gap) fixes both. No broader company-only guard was needed. One role-exclusion rule and two gutter variants were tried.

Failing first against nearest-only: **2 existing failures; 14 new failures and 4 new passes**. Before gutter variant 2: **4 additional crossing-row failures**. The initial role implementation also exposed two reverse-order attestation failures; computing all scores before redaction fixes them. Final focused run: **55 passed**. The earlier preservation run completed with **713 passed**; all those controls also run in the final full suite.

Relative to nearest-only: **1 placement-to-hold transitions** (1 previously wrong), **0 hold-to-placement transitions**, and **0 correct placements lost**. All 8,741 emitted fields in the comparison retain exact nearest-only geometry. The complete transitions are recorded in `nearest-transitions.json`.

Full results differ from nearest-only in seven cases: the two requested controls and five r8 C7 witness controls. The latter retain their exact fields, status, score, and model behavior; their assignment margin rises from 2 to 6 because the witness no longer has a competing party score. [Every result difference](nearest-result-differences.json) and the [gap diagnostic audit](gap-control-audit.json) record these changes explicitly.

## Per-family comparison

Cells are **wrong / placed / holds**; wrong is included in placed. Bare outcomes are recorded separately. Both historical columns are recomputed and checked against the archived r15b counts.

| ID | Family | Cases | r14 | Nearest | Chosen |
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
| F16 | r14 grid | 3456 | 0 / 1200 / 2256 | 0 / 2436 / 1020 | 0 / 2436 / 1020 |
| F17 | r14 fixed sweep | 360 | 0 / 128 / 232 | 0 / 244 / 116 | 0 / 244 / 116 |
| F18 | r14 correct controls | 2 | 0 / 2 / 0 | 0 / 2 / 0 | 0 / 2 / 0 |
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
| F50 | r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
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
| F68 | r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 | 0 / 2 / 2 | 0 / 2 / 2 |
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
| F108 | r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 | 0 / 6 / 6 | 0 / 6 / 6 |
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
| chosen | 0 | 3020 | 7665 | 13 |

## Full-suite summary and evidence

**11,362 passed, 0 failed, 0 errors, 0 skipped**.

[Full log](full-suite.txt), [JUnit](full-suite.xml), [summary and all failures](full-suite-summary.json), [every test outcome](full-suite-cases.json). The unchanged launcher’s scratch-directory warning is retained in the log.

[Method and exact commands](method.md), [comparison runner](check_evidence.py), [family counts](counterfactual-summary.json), [all cases and results](counterfactual-cases.json), [real-worker checks](counterfactual-workers.json), [seven goldens](placements.json).

[Failing-first counts](failing-first-summary.json), [fixture geometry](witness-fixture-audit.json), [preservation audit](preservation-summary.json), [field geometry audit](geometry-audit.json), [source patch](candidate.patch). External HTTP/model calls: **0**; model callbacks are deterministic local stubs.
