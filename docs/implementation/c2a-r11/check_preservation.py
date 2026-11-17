"""Audit the permitted test edit, baselines, and unstaged working tree."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = '945ad159'
ALLOWED_TEST = 'backend/dealroom_sign/tests/test_placement_r9.py'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def without_boundary_test(source):
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'test_caption_identity_slot_edges')
    lines = source.splitlines(keepends=True)
    start = min([function.lineno] + [node.lineno for node in function.decorator_list]) - 1
    return b''.join(lines[:start] + lines[function.end_lineno:])


def main():
    changed = git('diff', '--name-only', BASE).decode().splitlines()
    changed_tests = [path for path in changed if path.startswith('backend/dealroom_sign/tests/')]
    assert changed_tests == [ALLOWED_TEST], changed_tests
    original = git('show', f'{BASE}:{ALLOWED_TEST}')
    current = (ROOT / ALLOWED_TEST).read_bytes()
    assert without_boundary_test(original) == without_boundary_test(current)
    assert not any('/fixtures/' in path or path.startswith('docs/implementation/c2a-r10/')
                   for path in changed)
    report = 'docs/implementation/c1b-report.md'
    assert (ROOT / report).read_bytes().startswith(git('show', f'{BASE}:{report}'))
    assert (ROOT / '.agent/memory.md').read_bytes() == git('show', f'{BASE}:.agent/memory.md')
    assert not git('diff', '--cached', '--name-only')
    assert git('rev-parse', '--short', 'HEAD').decode().strip() == BASE
    assert not (ROOT / '.agent/r11-placement.py.tmp').exists()
    git('diff', '--check')
    before = json.loads((OUT / 'failing-first-summary.json').read_text())
    after = json.loads((OUT / 'full-suite-summary.json').read_text())
    baseline = json.loads((OUT / 'baseline-source.json').read_text())
    evidence = json.loads((OUT / 'placement-summary.json').read_text())
    assert before['source_sha256']['backend/dealroom_sign/placement.py'] == baseline['production_sha256']
    assert after['source_sha256']['backend/dealroom_sign/placement.py'] == evidence['production_sha256']
    for path, digest in before['source_sha256'].items():
        if '/tests/' in path:
            assert digest == after['source_sha256'][path] == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert after['failures'] == after['errors'] == after['skipped'] == 0
    assert after['groups']['test_h1_out_of_slot_stacks_still_hold'] == {'passed': 40}
    assert after['groups']['test_h1_stacked_signers_hold'] == {'passed': 40}
    assert after['groups']['test_seven_goldens_exact'] == {'passed': 7}
    assert after['groups']['test_absorbed_identity_vetoes_every_overlapping_host'] == {'passed': 1}
    assert after['groups']['test_subordinate_caption_host_band_and_distance'] == {'passed': 8}
    assert after['groups']['test_second_company_holds_without_subordinate_rule'] == {'passed': 15}
    summary = {
        'base': BASE,
        'only_existing_test_changed': ALLOWED_TEST + '::test_caption_identity_slot_edges',
        'all_other_existing_tests_unchanged': True,
        'r10_H-1_cases_passed_unchanged': 40,
        'r9_H-1_cases_passed_unchanged': 40,
        'overlapping_host_veto_preserved': True,
        'r8_boolean_wrapper_and_forced_classification_preserved': True,
        'golden_fixtures_and_baselines_unchanged': True,
        'failing_first_production_matches_base': True,
        'failing_first_and_final_test_hashes_match': True,
        'report_append_only': True,
        'memory_unchanged': True,
        'index_empty': True,
        'HEAD_unchanged': True,
        'diff_check_passed': True,
        'raw_logs_and_temporary_xml_absent': not list(OUT.glob('*.xml')) and not list(OUT.glob('*.log')),
        'changed_tracked_files': changed,
    }
    (OUT / 'preservation-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
