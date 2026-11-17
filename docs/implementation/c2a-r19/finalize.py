"""Audit final evidence and protected inputs; write the handoff marker last."""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRODUCT = 'backend/dealroom_sign/placement.py'
sys.path.insert(0, str(ROOT / 'backend'))
from dealroom_sign.tests import placement_r19_review_cases as review_cases
from dealroom_sign.tests.test_placement_r19_review import justified_company_only


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((OUT / (name + '.json')).read_text())


def write(name, value):
    path = OUT / (name + '.json')
    content = json.dumps(value, indent=2) + '\n'
    if path.exists():
        assert path.read_text() == content, path
    else:
        path.write_text(content)


def suite(path):
    tree = ET.parse(path)
    counts, cases = Counter(passed=0, failed=0, errors=0, skipped=0), []
    for case in tree.iter('testcase'):
        tag = next((t for t in ['failure', 'error', 'skipped'] if case.find(t) is not None), None)
        status = {'failure': 'failed', 'error': 'errors', 'skipped': 'skipped', None: 'passed'}[tag]
        counts[status] += 1
        cases.append({'classname': case.attrib['classname'], 'case': case.attrib['name'], 'status': status})
    return counts, cases


def classify_competition(archive):
    rows_by_case = {case: (rows, both, allowed) for _, case, rows, both, allowed in review_cases.competition()}
    records, breakdown = [], Counter()
    lines = ['# Exact competition-family classification', '',
             'The unchanged review oracle flags 348 r18 placements and 300 broad-candidate placements. '
             'The candidate residue is exactly 60 company-heading collisions and 240 sole-domain-company matches. '
             'The final source holds all 60 collisions. The 240 remaining raw flags are justified below, '
             'one row per case, without changing the original oracle or its allowed-rule map.', '',
             'For every `sole match` row: the supplied signer is Pat Smith / pat@harborlight.fleet.test, '
             'with **no explicit company**. The original blank has no Harbor company heading and no Pat name; '
             '`RECIPIENT:` has no role definition, `COMPANY` names no legal entity, and `none` has no heading. '
             'The affiliate shown in that row is the only Harbor-named company in the PDF. '
             'The input therefore does not identify Analytics (or any other legal entity) as Pat’s company. '
             'The placement follows the requested company-only exception; claiming a different known legal entity '
             'would require information absent from the input. Chris Jones / Witness / Schedule captions do not '
             'supply Pat’s company. The separate 24 controls confirm that explicitly supplying Analytics as '
             'Pat’s company makes the Group-only layouts hold.', '',
             'For every `held collision` row, the candidate put Pat on a different named company while '
             'the original row included Analytics. The final result is `needs_sender` with no fields. '
             'Every such case also passed the real worker comparison.', '',
             'IDs follow the exact 480-case generator order (zero based). The table includes all 300 '
             'candidate raw flags. Full inputs, original oracle, output fields and adjudication for all 480 '
             'cases are in [competition-classification.json](competition-classification.json).', '',
             '| ID | Original heading | Extra line | Affiliate | Affiliate column | Long Fleet | Signers | Final classification | Pat signature/date y |',
             '| ---: | --- | --- | --- | --- | --- | --- | --- | --- |']
    index = 0
    for record in archive['cases']:
        if record['group'] != 'Competition':
            continue
        head, extra, affiliate, column, fleet_cross, both = ast.literal_eval(record['case'])
        rows, _, allowed = rows_by_case[record['case']]
        chosen = archive['outcomes'][record['results']['chosen']]
        if record['raw_wrong']['chosen']:
            assert justified_company_only(record['case'], chosen, allowed)
            classification = 'sole match'
        elif record['raw_wrong']['candidate']:
            assert (chosen['status'], chosen['fields']) == ('needs_sender', [])
            classification = 'held collision'
        else:
            classification = 'held veto or ambiguity' if chosen['status'] == 'needs_sender' else 'correct original rule'
        if record['raw_wrong']['candidate']:
            breakdown[classification] += 1
            breakdown['heading: ' + str(head)] += 1
            values = [str(index), str(head or 'none'), str(extra or 'none'), affiliate,
                      'left' if column == 0 else 'right', str(fleet_cross), 'DAN+PAT' if both else 'PAT',
                      classification, '450 / 510' if classification == 'sole match' else 'none']
            lines.append('| ' + ' | '.join(v.replace('|', '\\|') for v in values) + ' |')
        records.append({'id': index, 'case': record['case'], 'rows': rows,
                        'signers': review_cases.TWO[1:2] + review_cases.PAT if both else review_cases.PAT,
                        'original_allowed_rules': allowed, 'raw_wrong': record['raw_wrong'],
                        'justified': record['justified'], 'wrong_after_adjudication': record['wrong'],
                        'classification': classification,
                        'results': {name: archive['outcomes'][key] for name, key in record['results'].items()}})
        index += 1
    assert index == 480
    assert breakdown['held collision'] == 60 and breakdown['sole match'] == 240
    write('competition-classification', {'cases': records, 'candidate_residue_breakdown': breakdown})
    path = OUT / 'competition-classification.md'
    content = '\n'.join(lines) + '\n'
    if path.exists():
        assert path.read_text() == content
    else:
        path.write_text(content)
    return breakdown


def main():
    initial, state = read('starting-hashes'), read('starting-state')
    changed = [p for p, sha in initial.items() if not (ROOT / p).is_file() or digest(ROOT / p) != sha]
    assert changed == [PRODUCT], changed
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    index = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT).decode()
    assert head == state['head'] and index == state['index']
    whitespace = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, capture_output=True, text=True)
    assert whitespace.returncode == 0, whitespace.stdout + whitespace.stderr
    for path, sha in read('review-input-hashes').items():
        assert digest(Path(path)) == sha
    original_ast = ast.parse((OUT / 'reviewer-q3.py.txt').read_text())
    copied_ast = ast.parse((ROOT / 'backend/dealroom_sign/tests/placement_r19_review_cases.py').read_text())
    assert [ast.dump(n) for n in original_ast.body if isinstance(n, ast.FunctionDef)] == [
        ast.dump(n) for n in copied_ast.body if isinstance(n, ast.FunctionDef)]
    core, exact = read('release-summary'), read('release-review-summary')
    source_sha = digest(ROOT / PRODUCT)
    assert source_sha == core['source_sha256']['chosen'] == exact['source_sha256']['chosen']
    for variant in ['r18', 'candidate', 'narrower']:
        assert core['source_sha256'][variant] == exact['source_sha256'][variant]
    assert core['source_sha256']['r18'] == initial[PRODUCT]
    assert source_sha == read('full-suite-source-sha256')['placement_sha256']
    assert "VERSION = 'c2a.19'" in (ROOT / PRODUCT).read_text()
    assert core['cases'] == 17204 and exact['cases'] == 12672
    assert all(g['chosen_wrong'] == 0 for g in [*core['groups'].values(), *exact['groups'].values()])
    assert core['groups']['Veto matrix']['r18_wrong'] == 84
    assert core['groups']['Seven goldens']['chosen_golden_diffs'] == core['groups']['Seven goldens']['chosen_native_diffs'] == 0
    assert exact['groups']['Competition']['chosen_raw_wrong'] == exact['groups']['Competition']['chosen_justified'] == 240
    assert core['external_http_calls'] == exact['external_http_calls'] == 0
    assert core['groups']['Veto matrix']['narrower_wrong'] > 0
    summaries = {}
    for path in sorted(OUT.glob('*.xml')):
        counts, cases = suite(path)
        summaries[path.stem] = counts
        if path.stem == 'full-suite':
            current_cases = cases
            write('full-suite-cases', cases)
    full = summaries['full-suite']
    assert full == {'passed': 17832, 'failed': 0, 'errors': 0, 'skipped': 0}, full
    previous_cases = json.loads((OUT.parent / 'c2a-r18/full-suite-cases.json').read_text())
    before = Counter((c['classname'], c['case']) for c in previous_cases)
    after = Counter((c['classname'], c['case']) for c in current_cases)
    missing = list((before - after).elements())
    assert not missing
    assert len(previous_cases) == 17144 and sum((after - before).values()) == 688
    inventory = {'previous_cases': len(previous_cases), 'current_cases': len(current_cases),
                 'new_cases': sum((after - before).values()), 'missing_existing_test_cases': missing}
    write('test-runs-summary', summaries)
    write('test-inventory-summary', inventory)
    preservation = {'tracked_files_hash_checked': len(initial), 'changed_tracked_files': changed,
                    'all_existing_tests_fixtures_evidence_done_markers_hash_exact': True,
                    'memory_unchanged': digest(ROOT / '.agent/memory.md') == initial['.agent/memory.md'],
                    'head': head, 'head_unchanged': True, 'index_unchanged': True,
                    'review_inputs_unchanged': True, 'review_generator_functions_ast_exact': True,
                    'source_matches_full_suite_and_all_final_replays': True, 'source_sha256': source_sha,
                    'whitespace_check_rc': whitespace.returncode}
    assert preservation['memory_unchanged']
    write('preservation-summary', preservation)
    breakdown = classify_competition(read('release-review-cases'))
    rows = []
    for evidence in [core, exact]:
        for group, counts in evidence['groups'].items():
            cell = lambda name: ' / '.join(str(counts[name + '_' + key]) for key in ['wrong', 'placed', 'holds', 'bare'])
            transitions = evidence['transitions'][group]['chosen']
            rows.append(f'| {group} | {counts["cases"]} | {cell("r18")} | {cell("candidate")} | {cell("narrower")} | {cell("chosen")} | '
                        f'{transitions.get("placed -> needs_sender", 0)} | {transitions.get("wrong -> needs_sender", 0)} |')
    costs = {group: {'correct_to_hold': evidence['transitions'][group]['chosen'].get('placed -> needs_sender', 0),
                    'wrong_to_hold': evidence['transitions'][group]['chosen'].get('wrong -> needs_sender', 0)}
             for evidence in [core, exact] for group in evidence['groups']}
    write('hold-costs', costs)
    lines = ['# C2a r19 results', '',
             f'Base HEAD: `{head}`. Production `VERSION = \'c2a.19\'`. No commit or index changes.', '',
             '**All required bars pass.** The final Send backend suite completed without `-x`: '
             '**17,832 passed, 0 failed, 0 errors, 0 skipped**. All 17,144 existing test cases remain, '
             'with 688 new cases. SHA-256 verification covers all 1,746 starting tracked files; '
             '`placement.py` is the only starting file changed.', '',
             '**Chosen rule:** company-only credit requires unique company attribution on the same page. '
             'Every other block with a matching role-mapped, behalf-stripped heading competes using the existing '
             'similarity predicate, regardless of veto, zero score, crossing, or unresolved identity. '
             'A matching printed name remains independent evidence. M-1 separately makes a heading row spanning '
             'two same-band party columns unresolved for the page, including colliding text, lost legal-form '
             'tokens, separators, and mapped roles. These checks only remove credit.', '',
             '**Narrower rejected:** the measured variant retains r18 crossing competitors and adds only '
             'non-crossing blocks whose local score is zero, excluding mismatched/ambiguous printed identities '
             'and unresolved-person vetoes. It retains all 116 correct affiliate placements but also retains '
             f'{core["groups"]["Veto matrix"]["narrower_wrong"]} wrong veto-matrix placements and '
             f'{exact["groups"]["Competition"]["narrower_wrong"]} unjustified competition placements. '
             'It therefore fails the required zero-wrong standard. The broad rule accepts all 116 affiliate holds.', '',
             '## Failing first and tests', '',
             'Before any production edit, the new 140-case veto matrix had **84 failures / 56 passes**, '
             'the 16 collision checks had **8 failures / 8 passes**, and 40 identity/page checks had '
             '**20 failures / 20 passes**: **112 failed / 84 passed** in total. '
             'Two further collision checks failed before recognizing slash/colon rows (2 failed / 4 passed); '
             'mapped-role collisions then failed before the final heading-shape guard (3 failed / 3 passed). '
             'The exact 480-case competition assertions were also evaluated against isolated historical r18: '
             '**108 failed / 372 passed**, versus **480 passed** on the final implementation. '
             'This historical replay is recorded separately from the original unchanged-production red runs.', '',
             'Only new test files were added: `test_placement_r19.py` (208 cases), '
             '`test_placement_r19_review.py` (480 cases), and `placement_r19_review_cases.py` (generator support). '
             'The review generator function source is copied verbatim and AST-verified against the preserved '
             'scratch source. No existing test, fixture, assertion, oracle, skip, selection, or evidence was retargeted.', '',
             '## Exact replay and competition classification', '',
             'The required replay covers **29,876 evaluations in 131 families**: every r18 published family '
             'plus the veto matrix (17,204), and the exact review boundary, fine-gap, and competition generators '
             '(12,672). These are evaluation counts; historical subset families and coarse/fine grids overlap. '
             '**Zero unjustified wrong placements in every family.** Seven goldens and native fields are exact '
             'except `analysis_version`. Real workers match in-process outputs on the goldens, veto reproductions, '
             'and every one of the 60 candidate collision cases. Evidence runners block external HTTP; calls: 0.', '',
             'The exact competition family reproduces **348 raw oracle flags in r18 → 300 under the broad '
             'candidate → 240 in r19**. The 300 candidate residuals are fully classified: **60 collisions become '
             'holds; 240 are the explicitly permitted sole-company/domain case**, with no company identifying '
             'the original blank as Pat’s and no explicit legal company supplied for Pat. The original oracle '
             'and all raw flags are retained. Every case naming Analytics on the original block and placing Pat '
             'on a different legal entity now holds. See the [300-row case-by-case explanation]'
             '(competition-classification.md) and [all 480 inputs and outputs](competition-classification.json). '
             'The 24 [identity controls](release-competition-controls.json) additionally show that supplying Analytics '
             'as Pat’s explicit company holds the Group-only layouts.', '',
             'The exact L-1 counts are **3,480 Pat / 1,800 Fleet**: r18 has **94 / 192 wrong**, respectively; '
             'r19 has **0 / 0**. Both exact F fine variants have 3,456 cases and zero wrong. '
             'Early reconstructed sweeps are retained as exploratory evidence and are excluded from these exact-family claims.', '',
             '## Per-family comparison and hold cost', '',
             'Cells are **wrong / placed / holds / bare**. “Wrong” uses the unchanged original oracle, '
             'with the competition exception explicitly adjudicated as above; its raw counts remain in the '
             'JSON and case-by-case report. `candidate` is exactly the reviewer’s one-line r18 change. '
             '`narrower` is the restricted competition alternative, without M-1. `r19` includes the broad '
             'same-page rule and M-1. Hold cost counts previously correct/permitted placements becoming holds; '
             'wrong placements becoming holds are shown separately.', '',
             '| Family | Cases | r18 | Candidate | Narrower | r19 | Correct → hold | Wrong → hold |',
             '| --- | ---: | --- | --- | --- | --- | ---: | ---: |', *rows, '',
             '## Evidence and preservation', '',
             '- [Final full suite](full-suite.txt), [JUnit](full-suite.xml), [test inventory](test-inventory-summary.json).',
             '- [Final historical replay](release-summary.json), [complete outcomes](release-cases.json).',
             '- [Exact review replay](release-review-summary.json), [complete outcomes](release-review-cases.json).',
             '- [Test run counts](test-runs-summary.json), [hold costs](hold-costs.json), [hash audit](preservation-summary.json).',
             '- [Seven final goldens](release-placements.json), [method and commands](method.md).', '',
             'Every existing test, fixture, earlier evidence file and `.done` marker is byte-for-byte unchanged. '
             'HEAD, index, project memory and the read-only reviewer inputs are unchanged. '
             'The first full-suite pass (17,340 tests) is retained as preliminary evidence; the final '
             '17,832-test run includes every later addition and uses the exact final source hash.', '',
             '**Blockers:** none.', '']
    (OUT / 'results-r19.md').write_text('\n'.join(lines))
    marker = [f'coder rc=0 head={head}',
              'Failing first: unchanged r18 112 failed / 84 passed (veto 84/56, collision 8/8, identity 20/20); slash/colon 2 failed / 4 passed; mapped-role collisions 3 failed / 3 passed; historical competition assertions 108 failed / 372 passed.',
              'Chosen rule: same-page company uniqueness across all role-mapped, behalf-stripped matching headings regardless of veto/score/crossing; M-1 shared/colliding heading rows hold the page; VERSION=c2a.19. Narrower rejected: veto wrong=84; 116 affiliate correct placements become holds.',
              'Competition: exact 480 cases; raw r18/candidate/r19=348/300/240; candidate residue=60 collisions held + 240 sole-domain-company matches justified case by case; zero unjustified wrong; no known different legal entity placement remains.',
              'Full suite: 17832 passed, 0 failed, 0 errors, 0 skipped; completion without -x; all 17144 prior nodes retained; final-source hash verified.',
              'Test changes: only new test_placement_r19.py (208), test_placement_r19_review.py (480), placement_r19_review_cases.py; no existing test/fixture/evidence/done marker changed; 1746 starting file hashes checked.',
              'Evidence: 29876 exact-family evaluations; every family zero unjustified wrong; seven goldens/native fields exact except analysis_version; hold cost per family in results-r19.md and hold-costs.json; HTTP=0.',
              'Blockers: none. No commit; HEAD/index/memory unchanged.', '']
    (OUT / 'counterparty-c2a-r19.done').write_text('\n'.join(marker))
    print(json.dumps({'preservation': preservation, 'full_suite': full, 'inventory': inventory,
                      'competition_candidate_residue': breakdown}, indent=2))


if __name__ == '__main__':
    main()
