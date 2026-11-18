# C2a r24 results

The reviewer’s cand3 fallback (cand plus document-wide company competition) is implemented as `c2a.24`.

Base HEAD `e2bbb7587f7ef100e1fb82fea825000ba6eac705`; live r21 `afb9aa6e`. No staging or commit.

**coder rc=1: the literal release bar is not certified.** The required cand conflicts with 384 immutable r22 recital-precedence assertions. The cand3 fallback also conflicts with 20 immutable r19 cross-page score assertions. Additionally, 210 historical raw flags beyond M-1 remain under both candidates. [Release bars](release-bars.json).

The nine blocking cohorts reproduce exactly 120 B-1 and 42 B-2 wrong cells on r23. All 162 hold under r24. Both literal B-1/B-2 workers, with PAT and DAN+PAT, are safe. The separate uncaptioned H-1 worker also changes wrong → hold.

Full Send suite: 39,782 passed, 404 failed, 0 errors, 0 skipped. It completed without `-x` or selection filters. [Final log](fallback-full-suite.txt), [Final JUnit](fallback-full-suite.xml). The separately completed narrow-candidate suite recorded {'passed': 39802, 'failed': 384}. [Narrow log](full-suite.txt), [Narrow JUnit](full-suite.xml).

Failing first: **239 failed / 8,467 passed** on unchanged r23. This comprises 162 blocking recital failures, 18 boundary fixture flags, 54 reconstructed H-1 failures, four B-1/B-2 worker failures, and one uncaptioned H-1 worker failure. [Counts](failing-first-summary.json).

## Immutable-test blocker

All 384 parameters of `test_placement_r22.py::test_recital_precedence_matrix` assert that `roles["recipient"]` contains `harbor light analytics`. Their recital is `between Fleet Test Co., a Delaware corporation, and Harbor Light Analytics, Inc., a Delaware corporation ("Recipient")`. The bounded grammar contributes HLA; the required byte-identical r21 grammar contributes Fleet. The required unchanged M-2 guard therefore returns `Recipient`, violating that old assertion while retaining a safe hold.

The sole authorised exception concerns r23 `b1_three`, so the r22 assertion is preserved. Neither cand3 nor the narrow page guard changes recital extraction. Satisfying both the exact cand semantics and this immutable role-name expectation requires resolving the conflicting requirements. No assertion, fixture, skip or oracle was changed to hide the conflict. [Exact grammar contributions](immutable-test-conflict.json), [completed-suite failure families](full-suite-failures.json).

The broad fallback additionally returns score 0 for a matching heading on another page, where 20 r19 `test_company_competition_uses_identity_before_vetoes` parameters explicitly require 4. Running the original 40 score assertions unchanged across all five sources gives 40 passed for r21/r23/cand/narrow and 20 passed / 20 failed for cand3. These are safer holds, but the existing assertions are outside the authorised exception. [Score-assertion evidence](fallback-test-conflict.json).

## What changed

`ROLE_DESCRIPTION_WIDE` is byte-identical to r21’s entire `ROLE_DESCRIPTION` assignment apart from its variable name. It contributes alongside the bounded grammar and direct definitions. The existing M-2 conflict guard retains the role word on disagreement.

Both guards were measured. The narrow candidate enables cross-page matching-heading competition only when the document contains an unaccounted party-role label. It retains historical raw flags beyond M-1, so it cannot satisfy the literal zero-wrong condition. The requested cand3 fallback is selected: company/domain-only matching headings compete across pages without that condition. Both candidates retain the article-prefixed alias veto and printed-name path. The fallback also retains those old flags; it is not release-certified.

Per-cell evidence retains its original labels: `r24` means the measured narrow candidate there, and `cand3` means the final choice. The report and `family-comparison.json` map final r24 to cand3 explicitly. The final source differs from the measured cand3 only in VERSION. [Source mapping](final-source-mapping.json).

## Narrow guard versus cand3

| Family | Cells | cand W / correct / hold / bare | cand3 (final r24) W / correct / hold / bare | narrow W / correct / hold / bare | cand3 additional holds | narrow additional holds |
| --- | ---: | --- | --- | --- | ---: | ---: |
| layouts: Review matrix guarantor | 1320 | 0 / 130 / 1190 / 0 | 0 / 65 / 1255 / 0 | 0 / 65 / 1255 / 0 | 65 | 65 |
| wrapped: Wrapped matrix guarantor | 1320 | 0 / 100 / 1220 / 0 | 0 / 50 / 1270 / 0 | 0 / 50 / 1270 / 0 | 50 | 50 |
| stress: Recitals affiliate | 192 | 0 / 40 / 152 / 0 | 0 / 24 / 168 / 0 | 0 / 32 / 160 / 0 | 16 | 8 |
| stress: Recitals simple_between | 192 | 0 / 14 / 178 / 0 | 0 / 12 / 180 / 0 | 0 / 12 / 180 / 0 | 2 | 2 |
| stress: Recitals subsidiary | 192 | 0 / 40 / 152 / 0 | 0 / 24 / 168 / 0 | 0 / 32 / 160 / 0 | 16 | 8 |
| stress: Recitals hereinafter | 192 | 0 / 32 / 160 / 0 | 0 / 24 / 168 / 0 | 0 / 24 / 168 / 0 | 8 | 8 |
| q2: inc_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| q2: description_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| q2: description_repeat_pages | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| q2: signature_same | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| q2: three_quoted | 240 | 0 / 70 / 170 / 0 | 0 / 66 / 174 / 0 | 0 / 66 / 174 / 0 | 4 | 4 |
| q2: llp_short | 240 | 0 / 130 / 110 / 0 | 0 / 120 / 120 / 0 | 0 / 122 / 118 / 0 | 10 | 8 |
| q2: smith_short_description | 240 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 / 126 / 114 / 0 | 14 | 8 |
| q2: b1_inc_address | 240 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 / 126 / 114 / 0 | 14 | 8 |
| q2: b1_co_address | 240 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 / 126 / 114 / 0 | 14 | 8 |
| q2: b1_llc_hereinafter | 240 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 / 126 / 114 / 0 | 14 | 8 |
| q2: research_center | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| extra: procter_short | 240 | 0 / 116 / 124 / 0 | 0 / 108 / 132 / 0 | 0 / 112 / 128 / 0 | 8 | 4 |
| extra: procter_address | 240 | 0 / 116 / 124 / 0 | 0 / 108 / 132 / 0 | 0 / 112 / 128 / 0 | 8 | 4 |
| extra: group_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| extra: holdings_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| extra: light_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 8 | 8 |
| workers: b1 | 36 | 0 / 4 / 32 / 0 | 0 / 0 / 36 / 0 | 0 / 4 / 32 / 0 | 4 | 0 |
| attack: johnson_inc | 240 | 0 / 116 / 124 / 0 | 0 / 108 / 132 / 0 | 0 / 112 / 128 / 0 | 8 | 4 |
| h1_review: H1_REVIEW | 2160 | 60 / 1398 / 702 / 0 | 0 / 1170 / 990 / 0 | 0 / 1170 / 990 / 0 | 228 | 228 |

## Preservation and goldens

**2,243/2,243 other original files are SHA-256 identical.** Every earlier fixture, evidence file and .done marker is preserved. All 31,480 existing test IDs remain, accounting for the single authorised parameter-ID change. Two new test-tree files add 8,706 checks. [Audit](preservation-summary.json).

Seven goldens and native fields match exactly except analysis_version, in-process and on real workers, for all five sources. Historical case inventories and r21/r23 outputs match their archived evidence. HTTP calls: zero. New-case model calls: zero.

The only existing test edit is:

```diff
diff --git a/backend/dealroom_sign/tests/test_placement_r23.py b/backend/dealroom_sign/tests/test_placement_r23.py
index fa1716bb..c192bf57 100644
--- a/backend/dealroom_sign/tests/test_placement_r23.py
+++ b/backend/dealroom_sign/tests/test_placement_r23.py
@@ -56,7 +56,7 @@ def test_additional_conjunction_and_repeat_controls(args, pages, people, allowed
     ('b1_inc_address', 'Smith and Jones, Inc.'),
     ('b1_co_address', 'Smith and Jones Co.'),
     ('b1_llc_hereinafter', 'Smith and Jones LLC'),
-    ('b1_three', 'Smith and Jones, Inc.'),
+    ('b1_three', 'Recipient'),
     ('b2_lazy_tail', 'Recipient'),
     ('research_center', cases.HLA),
 ])
```

## Per-family comparison and no-regression check

Each cell is **wrong / correct placement / hold / bare**. `n → p` counts a live-r21 hold becoming any placement (including a wrong one). `c → w` counts a live-r21 correct placement becoming wrong. Both are zero in every measured family. Historical Competition/Q4 classifications are shown as preserved by their original harness; all raw flags are separately disclosed below. Stress rows use the raw geometry oracle without exceptions.

**59,788 primary cells / 229 family rows / 1,135 real-worker evaluations.** Additional holds relative to cand: cand3 547, narrow candidate 489. The narrow guard preserves 58 correct placements that cand3 holds.

### historical

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Matrix 1 | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 | 0 |
| Matrix 2 | 270 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 / 0 / 270 / 0 | 0 | 0 |
| r11 B-1 | 1020 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 / 0 / 1020 / 0 | 0 | 0 |
| Signature controls | 204 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 / 6 / 198 / 0 | 0 | 0 |
| M-1 | 16 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 / 16 / 0 / 0 | 0 | 0 |
| r9 heading matrix | 72 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 / 6 / 66 / 0 | 0 | 0 |
| r9 H-1 | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 | 0 |
| Seven goldens | 7 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 / 6 / 0 / 1 | 0 | 0 |
| Same-band right host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r12 B-1 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r13 same-band grid | 42 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 / 0 / 42 / 0 | 0 | 0 |
| r12 B-1 sweep | 864 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 / 0 / 864 / 0 | 0 | 0 |
| L-1 short-rule controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| L-2 own-company controls | 40 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 / 20 / 20 / 0 | 0 | 0 |
| r14 reproduction | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r14 grid | 3456 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 / 2436 / 1020 / 0 | 0 | 0 |
| r14 fixed sweep | 360 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 / 244 / 116 / 0 | 0 | 0 |
| r14 correct controls | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| r14 L-1 (grid subset) | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 |
| r15 M1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r15 M2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r15 M1 | 640 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 / 0 / 640 / 0 | 0 | 0 |
| r15 M2 | 2592 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 / 0 / 2592 / 0 | 0 | 0 |
| r2 reviewer_wrong_signer_goldens | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 |
| r2 unnamed_signer_never_takes_named_block | 42 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 / 12 / 24 / 6 | 0 | 0 |
| r2 nearby_body_is_redacted_and_model_identity_is_minimal | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r2 caption_cannot_claim_next_block | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r2 date_cannot_be_borrowed_from_next_column | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r2 native_signature_is_tight_and_bottom_anchored | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r2 printed_name_variants_veto_company_match | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 | 0 |
| r2 named_caption_is_not_dropped_when_it_is_long | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r2 unlabelled_unrecognized_caption_cannot_be_ignored | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r2 heading_cannot_cross_a_previous_unlabelled_rule | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r2 date_in_close_right_column_with_unlabelled_signature_is_not_borrowed | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r3 other_person_in_whole_raw_extent_never_gets_high | 12 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 / 0 / 12 / 0 | 0 | 0 |
| r3 inserted_raw_person_vetoes_across_fixtures | 39 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 / 4 / 35 / 0 | 0 | 0 |
| r3 company_only_requires_every_raw_line_accounted_for | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r3 matching_printed_name_can_resolve_label_prefix | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r3 title_case_body_never_leaves_local_evidence | 6 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 / 3 / 3 / 0 | 0 | 0 |
| r3 matched_name_does_not_override_unresolved_person_like_line | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r3 company_only_requires_one_signer_even_if_other_signer_has_named_block | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r3 second_person_in_same_raw_line_also_vetoes | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r4 rule_row_name_controls_identity | 16 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 / 8 / 8 / 0 | 0 | 0 |
| r4 side_by_side_company_blocks_keep_their_own_names | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r4 golden_harbor_role_suffix_keeps_exact_boxes | 12 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 / 12 / 0 / 0 | 0 | 0 |
| r4 golden_harbor_block_wording_keeps_exact_boxes | 31 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 / 31 / 0 / 0 | 0 | 0 |
| r4 ascii_hyphen_role_preserves_printed_identity | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 | 0 |
| r4 unnamed_company_block_accounts_for_roles | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 |
| r4 title_person_remains_unresolved_and_holds | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r4 stacked_individual_blocks_place_without_neighbour_veto | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 |
| r4 stacked_individual_blocks_do_not_accept_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r4 name_in_gap_between_party_columns_makes_both_uncertain | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r4 equidistant_row_between_stacked_rules_is_not_discarded | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r5 b1_far_heading_vetoes_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r5 b1_far_caption_vetoes_company_only | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r5 b1_walk_stops_at_prose_or_other_rule | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| r5 b1_walk_crosses_page_edge | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r5 b1_distant_name_never_adds_confidence | 6 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 / 0 / 6 / 0 | 0 | 0 |
| r5 b2_proven_empty_widget_and_plain_link_keep_placement | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 |
| r5 h1_title_wording_keeps_exact_golden | 30 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 / 30 / 0 / 0 | 0 | 0 |
| r5 h1_behalf_wording_keeps_exact_golden | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 |
| r5 h1_behalf_other_person_vetoes_named_signer | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r5 h1_wrapped_sentence_is_not_a_name_but_blocks_company_only | 2 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 / 1 / 1 / 0 | 0 | 0 |
| r5 h1_company_only_title_rules_stay_strict | 3 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 / 1 / 2 / 0 | 0 | 0 |
| r5 h1_positive_name_title_remainder_predicate | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 |
| r5 m1_compound_name_caption_keeps_exact_golden | 8 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 / 8 / 0 / 0 | 0 | 0 |
| r5 m1_compound_caption_keeps_mismatched_person_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r5 m2_stacked_headings_with_side_dates | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 |
| r5 l1_empty_contact_labels_only_are_accounted | 10 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 / 5 / 5 / 0 | 0 | 0 |
| r5 l2_single_typed_row_signature_and_date | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 n1_mixed_case_role_shaped_names_veto_company_only | 3 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 / 0 / 3 / 0 | 0 | 0 |
| r5 n1_uppercase_role_abbreviations_remain_accounted | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 | 0 |
| r5 h1_execution_clause_is_a_heading | 3 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 / 2 / 1 / 0 | 0 | 0 |
| r5 b2_unproven_empty_widget_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 |
| r5 b1_named_block_does_not_use_distant_veto | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 b1_veto_respects_neighbour_column_band | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 h1_wrapped_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r5 b1_cross_page_walk_includes_row_at_page_top | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r6 h2_contact_rule_preserves_typed_identity | 18 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 / 12 / 6 / 0 | 0 | 0 |
| r6 h1_previous_caption_stays_with_its_host | 4 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 / 2 / 2 / 0 | 0 | 0 |
| r6 m1_repeated_running_header_is_neutral | 9 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 / 9 / 0 / 0 | 0 | 0 |
| r6 m1_nonrepeated_header_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r6 m1_page_number_does_not_hide_next_page_name | 4 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 / 0 / 4 / 0 | 0 | 0 |
| r6 m2_behalf_company_suffix_keeps_exact_golden | 10 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 / 10 / 0 / 0 | 0 | 0 |
| r6 m2_behalf_role_is_not_a_person | 3 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 / 3 / 0 / 0 | 0 | 0 |
| r6 m3_comma_witness_paragraph_keeps_exact_golden | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r6 n1_title_person_before_comma_still_vetoes | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r6 n2_period_name_still_vetoes_named_block | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 h1_short_contact_caption_preserves_typed_identity | 15 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 / 0 / 15 / 0 | 0 | 0 |
| r7 l1_repeated_body_name_retains_identity_veto | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 l1_page_number_is_neutral_in_body | 4 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 / 4 / 0 / 0 | 0 | 0 |
| r7 l2_prose_ending_keeps_exact_harbor_boxes | 7 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 / 7 / 0 / 0 | 0 | 0 |
| r7 l2_period_name_still_holds | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 n1_hold_reason_agrees_with_signer_count | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| r7 n1_one_missing_signer_keeps_singular_reason | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r8 b1_unusual_host_never_places_on_neighbour | 25 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 / 0 / 25 / 0 | 0 | 0 |
| r8 b1_signature_controls_keep_previous_outcome | 5 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 / 1 / 4 / 0 | 0 | 0 |
| r8 m1_c7_keeps_400_candidate_and_never_places_on_witness | 5 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 / 5 / 0 / 0 | 0 | 0 |
| r8 l1_only_authorised_signatory_uses_model_on_its_own_line | 1 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 / 1 / 0 / 0 | 0 | 0 |
| r8 contact_vocabulary_is_other_without_preceding_host | 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 / 0 / 0 / 6 | 0 | 0 |
| r9 b1_same_row_right_behalf_holds | 5 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 / 0 / 5 / 0 | 0 | 0 |
| r9 absorbed_identity_vetoes_every_overlapping_host | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r10 b1_out_of_slot_identity_holds | 240 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 / 0 / 240 / 0 | 0 | 0 |
| r10 b1_name_below_caption_holds | 60 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 / 0 / 60 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / title_then_name | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / tab_gap | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / indented | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 signature_out_of_slot_controls_unchanged / caption_row_right | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| r10 h1_out_of_slot_stacks_still_hold | 40 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 / 0 / 40 / 0 | 0 | 0 |
| r10 m1_non_exempt_contact_out_of_slot_holds | 56 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 / 0 / 56 / 0 | 0 | 0 |
| r10 six_contact_captions_remain_exempt | 48 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 / 48 / 0 / 0 | 0 | 0 |
| r11 subordinating_rule_without_block_keeps_identity_veto | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |
| r14 separate_printing_of_same_name_is_not_vetoed | 2 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 / 2 / 0 / 0 | 0 | 0 |
| L1 ragged stacked controls | 384 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 / 34 / 350 / 0 | 0 | 0 |
| L1 centred stacked controls | 144 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 / 48 / 96 / 0 | 0 | 0 |
| A2 exact witness captions | 480 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 / 0 / 480 / 0 | 0 | 0 |
| A2 additional dy=20 | 96 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 / 0 / 96 / 0 | 0 | 0 |
| Witness wider sweep | 2496 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 / 0 / 2496 / 0 | 0 | 0 |
| F three-party permutations | 288 | 0 / 123 / 165 / 0 | 0 / 123 / 165 / 0 | 0 / 123 / 165 / 0 | 0 | 0 |
| F heading gaps long | 432 | 0 / 189 / 243 / 0 | 0 / 189 / 243 / 0 | 0 / 189 / 243 / 0 | 0 | 0 |
| F heading gaps short | 432 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 / 216 / 216 / 0 | 0 | 0 |
| B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| B2 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| Affiliate matrix | 1536 | 0 / 0 / 1536 / 0 | 0 / 0 / 1536 / 0 | 0 / 0 / 1536 / 0 | 0 | 0 |
| r18 B1 reproduction | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| Veto matrix | 140 | 0 / 0 / 140 / 0 | 0 / 0 / 140 / 0 | 0 / 0 / 140 / 0 | 0 | 0 |

### review

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Competition | 480 | 0 / 96 / 384 / 0 | 0 / 96 / 384 / 0 | 0 / 96 / 384 / 0 | 0 | 0 |
| L1 boundary pat | 3480 | 0 / 191 / 3289 / 0 | 0 / 191 / 3289 / 0 | 0 / 191 / 3289 / 0 | 0 | 0 |
| L1 boundary fleet | 1800 | 0 / 0 / 1800 / 0 | 0 / 0 / 1800 / 0 | 0 / 0 / 1800 / 0 | 0 | 0 |
| F fine | 3456 | 0 / 2325 / 1131 / 0 | 0 / 2325 / 1131 / 0 | 0 / 2325 / 1131 / 0 | 0 | 0 |
| F fine company-only | 3456 | 0 / 776 / 2680 / 0 | 0 / 776 / 2680 / 0 | 0 / 776 / 2680 / 0 | 0 | 0 |
| Realistic NDA matrix | 48 | 0 / 0 / 48 / 0 | 0 / 0 / 48 / 0 | 0 / 0 / 48 / 0 | 0 | 0 |
| B1 real worker | 2 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| Q4 M1 ambiguity | 6 | 0 / 6 / 0 / 0 | 0 / 6 / 0 / 0 | 0 / 6 / 0 / 0 | 0 | 0 |
| Q4 controls | 32 | 0 / 12 / 20 / 0 | 0 / 12 / 20 / 0 | 0 / 12 / 20 / 0 | 0 | 0 |

### layouts

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Review matrix same | 1320 | 0 / 65 / 1255 / 0 | 0 / 65 / 1255 / 0 | 0 / 65 / 1255 / 0 | 0 | 0 |
| Review matrix guarantor | 1320 | 0 / 130 / 1190 / 0 | 0 / 130 / 1190 / 0 | 0 / 65 / 1255 / 0 | 0 | 0 |
| Review matrix split | 1320 | 0 / 65 / 1255 / 0 | 0 / 65 / 1255 / 0 | 0 / 65 / 1255 / 0 | 0 | 0 |
| Review matrix witness | 1320 | 0 / 0 / 1320 / 0 | 0 / 0 / 1320 / 0 | 0 / 0 / 1320 / 0 | 0 | 0 |
| Cross-page regression guarantor | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 | 0 |
| Cross-page regression split | 120 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 / 0 / 120 / 0 | 0 | 0 |
| B2 exact worker | 12 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 / 6 / 6 / 0 | 0 | 0 |
| B2 role vocabulary | 52 | 0 / 0 / 52 / 0 | 0 / 0 / 52 / 0 | 0 / 0 / 52 / 0 | 0 | 0 |
| ROLE_DEF layouts | 96 | 0 / 12 / 84 / 0 | 0 / 12 / 84 / 0 | 0 / 12 / 84 / 0 | 0 | 0 |

### wrapped

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Wrapped matrix same | 1320 | 0 / 50 / 1270 / 0 | 0 / 50 / 1270 / 0 | 0 / 50 / 1270 / 0 | 0 | 0 |
| Wrapped matrix guarantor | 1320 | 0 / 100 / 1220 / 0 | 0 / 100 / 1220 / 0 | 0 / 50 / 1270 / 0 | 0 | 0 |
| Wrapped matrix split | 1320 | 0 / 50 / 1270 / 0 | 0 / 50 / 1270 / 0 | 0 / 50 / 1270 / 0 | 0 | 0 |
| Wrapped matrix witness | 1320 | 0 / 0 / 1320 / 0 | 0 / 0 / 1320 / 0 | 0 / 0 / 1320 / 0 | 0 | 0 |

### new

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| M2 conflict probes | 36 | 24 / 0 / 12 / 0 | 0 / 0 / 36 / 0 | 0 / 0 / 36 / 0 | 0 | 0 |
| L1 recital matrix | 384 | 0 / 0 / 384 / 0 | 0 / 28 / 356 / 0 | 0 / 0 / 384 / 0 | 0 | 0 |

### stress

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| Recitals northwind | 192 | 48 / 0 / 144 / 0 | 48 / 0 / 144 / 0 | 48 / 0 / 144 / 0 | 0 | 0 |
| Recitals affiliate | 192 | 0 / 40 / 152 / 0 | 0 / 40 / 152 / 0 | 0 / 24 / 168 / 0 | 0 | 0 |
| Recitals misspelled_M1 | 192 | 48 / 0 / 144 / 0 | 48 / 0 / 144 / 0 | 48 / 0 / 144 / 0 | 0 | 0 |
| Recitals role_word | 192 | 0 / 0 / 192 / 0 | 0 / 0 / 192 / 0 | 0 / 0 / 192 / 0 | 0 | 0 |
| Recitals conflict_hla_nw | 192 | 48 / 0 / 144 / 0 | 0 / 0 / 192 / 0 | 0 / 0 / 192 / 0 | 0 | 0 |
| Recitals conflict_nw_hla | 192 | 0 / 32 / 160 / 0 | 0 / 0 / 192 / 0 | 0 / 0 / 192 / 0 | 0 | 0 |
| Recitals description_inline | 192 | 0 / 0 / 192 / 0 | 0 / 14 / 178 / 0 | 0 / 0 / 192 / 0 | 0 | 0 |
| Recitals description_wrapped | 192 | 0 / 0 / 192 / 0 | 0 / 14 / 178 / 0 | 0 / 0 / 192 / 0 | 0 | 0 |
| Recitals simple_between | 192 | 0 / 14 / 178 / 0 | 0 / 14 / 178 / 0 | 0 / 12 / 180 / 0 | 0 | 0 |
| Recitals subsidiary | 192 | 0 / 40 / 152 / 0 | 0 / 40 / 152 / 0 | 0 / 24 / 168 / 0 | 0 | 0 |
| Recitals hereinafter | 192 | 0 / 32 / 160 / 0 | 0 / 32 / 160 / 0 | 0 / 24 / 168 / 0 | 0 | 0 |
| Page probes nw_page2 | 72 | 24 / 0 / 48 / 0 | 24 / 0 / 48 / 0 | 24 / 0 / 48 / 0 | 0 | 0 |
| Page probes nw_page3 | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 |
| Page probes nw_after_sigs_only | 72 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 |
| Page probes nw_section1 | 72 | 24 / 0 / 48 / 0 | 24 / 0 / 48 / 0 | 24 / 0 / 48 / 0 | 0 | 0 |
| Page probes conflict_pages12 | 72 | 24 / 0 / 48 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 |
| Page probes conflict_section1 | 72 | 24 / 0 / 48 / 0 | 0 / 0 / 72 / 0 | 0 / 0 / 72 / 0 | 0 | 0 |
| Page probes the_recipient_page2 | 72 | 12 / 0 / 60 / 0 | 12 / 0 / 60 / 0 | 12 / 0 / 60 / 0 | 0 | 0 |
| M2 36 failing probes | 36 | 36 / 0 / 0 / 0 | 0 / 0 / 36 / 0 | 0 / 0 / 36 / 0 | 0 | 0 |
| B2 54 worker cells | 54 | 0 / 15 / 39 / 0 | 0 / 15 / 39 / 0 | 0 / 15 / 39 / 0 | 0 | 0 |

### q2

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| inc_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| description_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| description_repeat_pages | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| conflict_hla_nw | 240 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| conflict_nw_hla | 240 | 0 / 140 / 100 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| signature_nw | 240 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| signature_hla | 240 | 0 / 140 / 100 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| signature_same | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| three_quoted | 240 | 0 / 70 / 170 / 0 | 0 / 70 / 170 / 0 | 0 / 66 / 174 / 0 | 0 | 0 |
| three_two_joins | 240 | 0 / 60 / 180 / 0 | 0 / 70 / 170 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| three_middle_address | 240 | 0 / 60 / 180 / 0 | 0 / 66 / 174 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| three_last_address | 240 | 0 / 60 / 180 / 0 | 0 / 70 / 170 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| llp_short | 240 | 0 / 130 / 110 / 0 | 0 / 130 / 110 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| llp_address | 240 | 0 / 108 / 132 / 0 | 0 / 108 / 132 / 0 | 0 / 108 / 132 / 0 | 0 | 0 |
| smith_short_description | 240 | 0 / 134 / 106 / 0 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_inc_address | 240 | 0 / 134 / 106 / 0 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_co_address | 240 | 0 / 134 / 106 / 0 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_llc_hereinafter | 240 | 0 / 134 / 106 / 0 | 0 / 134 / 106 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_three | 240 | 0 / 60 / 180 / 0 | 0 / 74 / 166 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| b2_lazy_tail | 240 | 0 / 140 / 100 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| brown_company | 240 | 0 / 140 / 100 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| research_center | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |

### extra

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| johnson_short | 240 | 0 / 96 / 144 / 0 | 0 / 96 / 144 / 0 | 0 / 96 / 144 / 0 | 0 | 0 |
| johnson_address | 240 | 0 / 96 / 144 / 0 | 0 / 96 / 144 / 0 | 0 / 96 / 144 / 0 | 0 | 0 |
| procter_short | 240 | 0 / 116 / 124 / 0 | 0 / 116 / 124 / 0 | 0 / 108 / 132 / 0 | 0 | 0 |
| procter_address | 240 | 0 / 116 / 124 / 0 | 0 / 116 / 124 / 0 | 0 / 108 / 132 / 0 | 0 | 0 |
| group_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| holdings_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| light_repeat | 240 | 0 / 140 / 100 / 0 | 0 / 140 / 100 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |

### workers

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| b1 | 36 | 6 / 4 / 26 / 0 | 0 / 4 / 32 / 0 | 0 / 0 / 36 / 0 | 0 | 0 |
| b2 | 36 | 0 / 12 / 24 / 0 | 0 / 0 / 36 / 0 | 0 / 0 / 36 / 0 | 0 | 0 |

### attack

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| b1_joint_venture | 240 | 0 / 140 / 100 / 0 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_subsidiary | 240 | 0 / 140 / 100 / 0 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_successor_address | 240 | 0 / 140 / 100 / 0 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_successor | 240 | 0 / 140 / 100 / 0 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b1_affiliates | 240 | 0 / 140 / 100 / 0 | 24 / 120 / 96 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| b2_partners | 240 | 0 / 70 / 170 / 0 | 12 / 60 / 168 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| b2_associates | 240 | 0 / 70 / 170 / 0 | 12 / 60 / 168 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| b2_affiliates | 240 | 0 / 70 / 170 / 0 | 12 / 60 / 168 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| b2_smith | 240 | 0 / 72 / 168 / 0 | 6 / 60 / 174 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| johnson_inc | 240 | 0 / 116 / 124 / 0 | 0 / 116 / 124 / 0 | 0 / 108 / 132 / 0 | 0 | 0 |
| ernst_llp | 240 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| three_llc | 240 | 0 / 60 / 180 / 0 | 0 / 70 / 170 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |

### boundary

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| procter_first | 240 | 0 / 116 / 124 / 0 | 12 / 96 / 132 / 0 | 0 / 96 / 144 / 0 | 0 | 0 |
| smith_llp_first | 240 | 0 / 60 / 180 / 0 | 6 / 60 / 174 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| three_lowercase | 240 | 0 / 60 / 180 / 0 | 0 / 70 / 170 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| three_corp | 240 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| trailing_comma | 240 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| offices | 240 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| corporation_offices | 240 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 / 60 / 180 / 0 | 0 | 0 |
| lowercase_inc | 240 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |
| quoted_joins | 240 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 0 / 132 / 108 / 0 | 0 | 0 |
| northwind_first | 240 | 24 / 120 / 96 / 0 | 0 / 140 / 100 / 0 | 0 / 120 / 120 / 0 | 0 | 0 |

### h1_review

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| H1_REVIEW | 2160 | 96 / 1398 / 666 / 0 | 60 / 1398 / 702 / 0 | 0 / 1170 / 990 / 0 | 0 | 0 |

### veto

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| VETO | 1260 | 0 / 608 / 652 / 0 | 0 / 542 / 718 / 0 | 0 / 542 / 718 / 0 | 0 | 0 |

### workers24

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| b1 | 2 | 0 / 0 / 2 / 0 | 2 / 0 / 0 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| b2 | 2 | 0 / 0 / 2 / 0 | 2 / 0 / 0 / 0 | 0 / 0 / 2 / 0 | 0 | 0 |
| h1 | 1 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |

### workers_h1_uncaptioned

| Family | Cells | r21 | r23 | r24 | n → p | c → w |
| --- | ---: | --- | --- | --- | ---: | ---: |
| h1_uncaptioned | 1 | 1 / 0 / 0 / 0 | 1 / 0 / 0 / 0 | 0 / 0 / 1 / 0 | 0 | 0 |

## Raw flags and evidence limits

The carried misspelled-recital M-1 remains exactly 48 wrong cells, unchanged in r21/r23/r24. The following raw flags are also retained, rather than silently applying an expanded exception:

| Collection | Family | r24 raw flags |
| --- | --- | ---: |
| review | Competition | 96 |
| review | Q4 M1 ambiguity | 6 |
| stress | Recitals northwind | 48 |
| stress | Recitals misspelled_M1 | 48 |
| stress | Page probes nw_page2 | 24 |
| stress | Page probes nw_section1 | 24 |
| stress | Page probes the_recipient_page2 | 12 |

The deleted reviewer H-1 and veto generators were not available. The primary H-1 reconstruction (`review_h1.py`, `h1_review-*.json`) reproduces every reported aggregate: r21 96 wrong; r23 60 wrong / 1,398 correct / 702 holds; both guards zero wrong and 228 additional holds. It uses title-case Recipient plus HLA as the fifth own-block form. The initial 2,160-cell reconstruction used RECIPIENT without HLA instead and measured 90/54 wrong. Its unchanged files (`h1-*.json`) remain diagnostic evidence, outside the primary table totals. All those diagnostic cells also have zero final wrong placements and zero unsafe transitions. This is an explicit reconstruction with matching aggregate counts, not a claim of byte-identical recovery of the deleted generator. The 1,260-cell veto reconstruction retains its documented aggregate differences.

The literal captioned H-1 worker holds on unchanged HEAD; a separately retained uncaptioned worker fails first and is fixed. All 60 primary H-1 wrong cells are reproduced on the frozen r23 source, including the six title-case cells absent from the initial pytest matrix.

The nine blocking recital cohorts and the unchanged Q2 inputs are exact; additional attack/boundary strings are explicit reconstructions from the review descriptions. The two documented boundary fixture artefacts remain in the raw table; their r23 flags are 18 here versus 12 reported by the reviewer. Neither produces a wrong r24 placement.

[Method and commands](method.md), [per-cell transitions](vs-live.json), [remaining flags](remaining-flags.json), and the adjacent `*-cases.json` files provide the full evidence and provenance.

## r24b — shipped narrow guard and authorised r22 assertion

HEAD `e2bbb7587f7ef100e1fb82fea825000ba6eac705`. Production is **narrow**, `VERSION = 'c2a.24'`, SHA-256 `6fb94115cef7db2c22ebc1cbd2c7278f5e97b9549a8fa11e14d6a3addc5222c3`. It is byte-identical to the original `r24-source.py.txt` narrow snapshot. This section supersedes the earlier cand3 shipping selection and test blockers; all preceding r24 evidence remains unchanged.

**Full Send suite: 40,186 passed, 0 failed, 0 errors, 0 skipped.** Completed without `-x`, test-selection filters or deselections. The immutable r19 competition family passes all 40 cells; the authorised r22 recital matrix passes all 384 cells. All 31,480 prior test IDs remain (allowing only the existing authorised r23 parameter-ID substitution), plus 8,706 r24 checks. [Log](r24b/full-suite.txt), [JUnit](r24b/full-suite.xml), [command and hashes](r24b/run-provenance.json).

The company/domain-only cross-page guard now requires an unaccounted party-role label. The unchanged article-prefixed alias veto and printed-name path remain in place. The r21 wide description grammar is byte-identical apart from its variable name, contributes alongside the bounded grammar, and uses the unchanged M-2 conflict hold. Cand3 is removed from production.

### Exact authorised test diffs

Only r22 line 38 accepts either the HLA mapping or the literal role word `Recipient`; lines 39 and 41, and every other r22 byte, are unchanged. The standing r23 `b1_three` substitution is retained.

```diff
diff --git a/backend/dealroom_sign/tests/test_placement_r22.py b/backend/dealroom_sign/tests/test_placement_r22.py
index fede4ae2..26bf4914 100644
--- a/backend/dealroom_sign/tests/test_placement_r22.py
+++ b/backend/dealroom_sign/tests/test_placement_r22.py
@@ -35,7 +35,7 @@ def test_recital_precedence_matrix(args, pages, both, allowed):
     model = Mock()
     pdf = rc.pages_pdf(pages)
     _, _, roles = placement.extract(pdf)
-    assert 'harbor light analytics' in roles['recipient'].lower(), roles
+    assert 'harbor light analytics' in roles['recipient'].lower() or roles['recipient'].strip().lower() == 'recipient', roles
     assert 'fleet' not in roles['recipient'].lower(), roles
     result = in_process(placement, pdf, signers(both), model)
     assert not rc.wrong_fields(result, allowed), (args, result)
diff --git a/backend/dealroom_sign/tests/test_placement_r23.py b/backend/dealroom_sign/tests/test_placement_r23.py
index fa1716bb..c192bf57 100644
--- a/backend/dealroom_sign/tests/test_placement_r23.py
+++ b/backend/dealroom_sign/tests/test_placement_r23.py
@@ -56,7 +56,7 @@ def test_additional_conjunction_and_repeat_controls(args, pages, people, allowed
     ('b1_inc_address', 'Smith and Jones, Inc.'),
     ('b1_co_address', 'Smith and Jones Co.'),
     ('b1_llc_hereinafter', 'Smith and Jones LLC'),
-    ('b1_three', 'Smith and Jones, Inc.'),
+    ('b1_three', 'Recipient'),
     ('b2_lazy_tail', 'Recipient'),
     ('research_center', cases.HLA),
 ])
```

### Fresh vs-live replay

**59,788 primary cells across 229 families: `n → p = 0`, `c → w = 0`.** The shipped `c2a.24` source and live r21 were independently parsed and scored anew; 454 real-worker evaluations equal their in-process results. Every complete output equals its corresponding archived r24 narrow/r21 output, including analysis_version. Seven goldens and native fields match except analysis_version. External HTTP calls and new-case model calls are zero. The separate 2,160-cell diagnostic H-1 replay also has zero wrong placements and zero unsafe transitions. [Vs-live](r24b/vs-live.json), [per-family counts](r24b/family-comparison.json), [return codes](r24b/replay-returncodes.json).

All 120 B-1 and 42 B-2 r23 wrong cells hold. Primary H-1 has 2,160 cells: live r21 96 wrong, r23 60 wrong, shipped narrow 0 wrong / 1,170 correct / 990 holds. The literal B-1/B-2 workers and separate uncaptioned H-1 worker pass. Frozen failing-first evidence remains 239 failed / 8,467 passed. Because the shipped source and every result match the archived narrow evidence exactly, the original cand comparison remains applicable: 489 additional holds for narrow versus 547 for cand3, preserving 58 correct placements. H-1 costs 228 additional holds under either candidate. The deleted reviewer-generator reconstruction limitation remains as documented.

| Collection | Cells | n → p | c → w |
| --- | ---: | ---: | ---: |
| historical | 17,204 | 0 | 0 |
| review | 12,760 | 0 | 0 |
| layouts | 5,680 | 0 | 0 |
| wrapped | 5,280 | 0 | 0 |
| new | 420 | 0 | 0 |
| stress | 2,706 | 0 | 0 |
| q2 | 5,280 | 0 | 0 |
| extra | 1,680 | 0 | 0 |
| workers | 72 | 0 | 0 |
| attack | 2,880 | 0 | 0 |
| boundary | 2,400 | 0 | 0 |
| h1_review | 2,160 | 0 | 0 |
| veto | 1,260 | 0 | 0 |
| workers24 | 5 | 0 | 0 |
| workers_h1_uncaptioned | 1 | 0 | 0 |

### Hash preservation and remaining bar

**2,242/2,242 other originally tracked files are SHA-256 identical** to the r24 baseline; only placement.py and the two authorised tests differ. **2,357/2,357 other session-start files are SHA-256 identical**, including all prior r24 tests, fixtures, evidence and markers. The old RESULT is preserved byte for byte as the prefix of this appended report. No staging, commits, memory writes, fixture/oracle edits, skips or configuration changes. [Preservation audit](r24b/preservation-summary.json).

**coder rc=1 for the unchanged literal r24 raw-zero bar.** The two test blockers are resolved. The remaining blocker is the same 210 historical raw-coordinate flags beyond the carried 48-cell M-1 family. They are byte-equivalent in result to live r21 after removing analysis_version; neither authorised test edit changes their classification. The older Competition/Q4 classifications and raw flags are both retained. [Release bars](r24b/release-bars.json), [raw flags](r24b/remaining-flags.json).

| Raw family | Cells |
| --- | ---: |
| review: Competition | 96 |
| review: Q4 M1 ambiguity | 6 |
| stress: Recitals northwind | 48 |
| stress: Recitals misspelled_M1 | 48 |
| stress: Page probes nw_page2 | 24 |
| stress: Page probes nw_section1 | 24 |
| stress: Page probes the_recipient_page2 | 12 |

Reproduction: use the exact full-suite command in `r24b/run-provenance.json`; the new comparison runner is `r24b_replay.py all` (the output directory must be fresh, because existing evidence is never overwritten).
