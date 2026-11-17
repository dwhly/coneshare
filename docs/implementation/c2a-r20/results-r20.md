# C2a r20 results

Base HEAD: `ddfcc595041f5db88e59024670ac37aa0b9349a6`. Production `VERSION = 'c2a.20'`. No commit or index changes.

**B-1 ships and all required bars pass.** Full Send backend suite, without `-x`: **18,376 passed, 0 failed, 0 errors, 0 skipped**. All 17,832 prior test IDs remain, with 544 additions. All 1,846 starting tracked files were hash-verified; `placement.py` is the only changed starting file.

Production implements the reviewer’s exact fix2: domain-only company credit holds on pages with at least three non-witness blocks if another non-witness block has no printed name and its role-mapped, behalf-stripped heading names nobody. Explicit-company and printed-name scoring retain their existing behavior. The full production AST matches fix2 except the version value and comments.

## Failing first

| New tests | Cases | Failed before | Passed before | Passed after |
| --- | ---: | ---: | ---: | ---: |
| Competition | 480 | 144 | 336 | 480 |
| Realistic NDA matrix | 48 | 34 | 14 | 48 |
| Exact real worker, PAT and DAN+PAT | 2 | 2 | 0 | 2 |
| Page, witness, role, behalf and identity scope | 14 | 5 | 9 | 14 |
| Total | 544 | 185 | 359 | 544 |

The exact reviewer scripts ran before the production edit. `q1real.py` reproduces **34/48 wrong here, not the review prose’s 38**: address 12, hereinafter 12, parsed 4, no recital 6. The copied tests independently reproduce 34. Inputs were preserved; all 48 now hold. See [original script output](reviewer-real-before.txt).

The 480 competition cases go from **144 blocking wrong → 0**, with placements 240 → 96 and holds 240 → 384. The remaining 96 are exactly the review-permitted cases with Chris Jones printed in the other block. Their original raw coordinate flags remain in the evidence; they are not counted as matches to Pat’s original blank. Both real-worker reproductions now return `needs_sender`, no fields and zero model calls.

## Replay and optional measurements

**29,924 required family evaluations**, plus two worker cases and 38 Q4 checks: **29,964 inputs / 149,820 in-process variant evaluations**. Every r19 family and the realistic matrix has zero blocking wrong placements under r20. B-1 costs **0 correct → hold**. The 10,770-case original replay has no full-result diffs except `analysis_version`. Seven goldens and native fields are exact, and their real-worker results equal in-process results. External HTTP calls: 0. Historical deterministic model mocks, including the unusual-label golden, remain in use.

**Only B-1 ships. ROLE_DEF, L-1 and M-1 are measured separately and are not in production.** Their costs below are relative to B-1-only r20; they are not combined. The optional source snapshots and complete outputs are retained.

| Optional candidate | Wrong | Correct/permitted → hold | Hold → correct | Decision |
| --- | ---: | ---: | ---: | --- |
| role_def | 0 | 0 | 0 | Measured only; recital mapping verified, release kept to B-1. |
| l1 | 0 | 0 | 354 | Measured only; release kept to B-1. |
| m1 | 0 | 850 | 0 | Measured only; hold cost is too large. |

ROLE_DEF correctly maps the address and hereinafter recitals, with no placement changes in the measured families. The conservative L-1 exemption recovers **354** cases (303 F fine, 24 F permutations, 27 F long), fewer than the review’s 581 because it retains all other identity vetoes. Neither optional proposal is included in the full-suite-qualified production source. M-1 costs **850** accepted/permitted placements: 776 F fine company-only, 20 L-2 controls, 48 competition cases, and the six Q4 ambiguous cases.

The six Q4 M-1 cases remain explicitly ambiguous in production, as in r19: a named company spelling does not match the domain while a named affiliate does. Their six raw flags are reported separately, as the review requests; M-1 measures the broader hold instead of silently changing their oracle. The per-family table below shows the cost of that proposal, including F company-only.

Cells in the first two result columns are **wrong / placed / holds / bare**. Each optional cell is **correct/permitted → hold / hold → correct / wrong**. Permitted includes the separately listed Q4 ambiguous placements; it does not claim their original coordinates were correct. Every family is listed, including zero-cost families.

| Family | Cases | r19 | r20 | B-1 correct → hold | ROLE_DEF | L-1 | M-1 |
| --- | ---: | --- | --- | ---: | --- | --- | --- |
| Matrix 1 | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Matrix 2 | 270 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r11 B-1 | 1020 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Signature controls | 204 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| M-1 | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r9 H-1 | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Seven goldens | 7 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Same-band right host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r13 same-band grid | 42 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 20 / 0 / 0 |
| r14 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r14 grid | 3456 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r14 fixed sweep | 360 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r14 correct controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r15 M1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r15 M2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r15 M1 | 640 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r15 M2 | 2592 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| A2 exact witness captions | 480 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| A2 additional dy=20 | 96 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Witness wider sweep | 2496 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| F three-party permutations | 288 | 0 / 99 / 189 / 0 | 0 / 99 / 189 / 0 | 0 | 0 / 0 / 0 | 0 / 24 / 0 | 0 / 0 / 0 |
| F heading gaps long | 432 | 0 / 162 / 270 / 0 | 0 / 162 / 270 / 0 | 0 | 0 / 0 / 0 | 0 / 27 / 0 | 0 / 0 / 0 |
| F heading gaps short | 432 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| B2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Affiliate matrix | 1536 | 0 / 0 / 1536 / 0 | 0 / 0 / 1536 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| r18 B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Veto matrix | 140 | 0 / 0 / 140 / 0 | 0 / 0 / 140 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Competition | 480 | 144 / 240 / 240 / 0 | 0 / 96 / 384 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 48 / 0 / 0 |
| L1 boundary pat | 3480 | 0 / 191 / 3289 / 0 | 0 / 191 / 3289 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| L1 boundary fleet | 1800 | 0 / 0 / 1800 / 0 | 0 / 0 / 1800 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| F fine | 3456 | 0 / 2022 / 1434 / 0 | 0 / 2022 / 1434 / 0 | 0 | 0 / 0 / 0 | 0 / 303 / 0 | 0 / 0 / 0 |
| F fine company-only | 3456 | 0 / 776 / 2680 / 0 | 0 / 776 / 2680 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 776 / 0 / 0 |
| Realistic NDA matrix | 48 | 34 / 34 / 14 / 0 | 0 / 0 / 48 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| B1 real worker | 2 | 2 / 2 / 0 / 0 | 0 / 0 / 2 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Q4 M1 ambiguity | 6 | 0 / 6 / 0 / 0 | 0 / 6 / 0 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 6 / 0 / 0 |
| Q4 controls | 32 | 0 / 12 / 20 / 0 | 0 / 12 / 20 / 0 | 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

## Preservation, tests and evidence

Only new test files were added: `test_placement_r20.py` (530 cases), `test_placement_r20_boundaries.py` (14 cases), and `placement_r20_review_cases.py` (copied reviewer inputs). No existing test, fixture, assertion, evidence file or `.done` marker changed. The exact competition generator remains in the unchanged r19 support module.

- [Full suite](full-suite.txt), [JUnit](full-suite.xml), [test inventory](test-inventory-summary.json).
- [Failing-first counts](test-runs-summary.json), [preservation audit](preservation-summary.json), [fix2 AST equivalence](fix2-equivalence.json).
- [Historical summary](historical-summary.json), [all historical outcomes](historical-cases.json).
- [Review summary](review-summary.json), [all review outcomes](review-cases.json).
- [Per-family hold costs](hold-costs.json), [seven goldens](placements.json), [method and commands](method.md).

Final production SHA-256: `c747a21aefadcaadaf794a1811ab7810bb74bbf5d206841136053e27fda395d9`.

**Blockers:** none. The 34-versus-38 baseline discrepancy is disclosed above; the exact supplied inputs all pass. Project memory, HEAD and index are unchanged.
