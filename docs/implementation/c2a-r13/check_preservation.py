"""Verify unchanged existing tests, scoped edits, and failing-first provenance."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = '4ad9f7e20822ca15e8c5a5196f8b61c8cb59a312'
PRODUCT = 'backend/dealroom_sign/placement.py'
NEW_TEST = 'backend/dealroom_sign/tests/test_placement_r13.py'
REPORT = 'docs/implementation/c1b-report.md'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert git('branch', '--show-current').decode().strip() == 'agent/c1b-counterparty'
    tracked = git('diff', '--name-only', BASE).decode().splitlines()
    assert set(tracked) == {PRODUCT, REPORT}, tracked
    untracked = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    assert all(path == NEW_TEST or path.startswith('docs/implementation/c2a-r13/') for path in untracked)
    tests = git('ls-tree', '-r', '--name-only', BASE, 'backend/dealroom_sign/tests').decode().splitlines()
    for path in tests:
        assert (ROOT / path).read_bytes() == git('show', BASE + ':' + path), path
    assert (ROOT / REPORT).read_bytes().startswith(git('show', BASE + ':' + REPORT))
    assert not git('diff', '--cached', '--name-only')
    assert not git('diff', BASE, '--', '.agent/memory.md')
    git('diff', '--check')
    before = json.loads((OUT / 'failing-first-summary.json').read_text())
    after = json.loads((OUT / 'full-suite-summary.json').read_text())
    table = json.loads((OUT / 'counterfactual-summary.json').read_text())
    assert before['source_sha256'][PRODUCT] == hashlib.sha256(git('show', BASE + ':' + PRODUCT)).hexdigest()
    original_source = git('show', BASE + ':' + PRODUCT).decode()
    expected_source = original_source.replace("VERSION = 'c2a.12'", "VERSION = 'c2a.13'")
    expected_source = expected_source.replace(
        "                        absorbed_names[pno].extend((host, line.label, t) for t in texts",
        "                        caption = dict(rect=[min(line.label['rect'][0], line.x0),\n"
        "                                             line.label['rect'][1],\n"
        "                                             max(line.label['rect'][2], line.x1), line.y])\n"
        "                        absorbed_names[pno].extend((host, caption, t) for t in texts")
    assert (ROOT / PRODUCT).read_text() == expected_source
    original_tree = ast.parse(original_source)
    current_tree = ast.parse((ROOT / PRODUCT).read_text())
    original_functions = {node.name: ast.dump(node) for node in original_tree.body
                          if isinstance(node, ast.FunctionDef)}
    current_functions = {node.name: ast.dump(node) for node in current_tree.body
                         if isinstance(node, ast.FunctionDef)}
    assert original_functions.keys() == current_functions.keys()
    assert [name for name in original_functions
            if original_functions[name] != current_functions[name]] == ['extract']
    assert after['source_sha256'][PRODUCT] == table['production_sha256'] == hashlib.sha256((ROOT / PRODUCT).read_bytes()).hexdigest()
    assert before['source_sha256'][NEW_TEST] == after['source_sha256'][NEW_TEST] == hashlib.sha256((ROOT / NEW_TEST).read_bytes()).hexdigest()
    assert before['tests'] == 949
    assert before['failures'] == 573 and before['passed'] == 376
    assert before['errors'] == before['skipped'] == 0
    assert after['passed'] == 4250
    assert table['unexpected_differences'] == []
    assert table['cases'] == 2699
    assert after['failures'] == after['errors'] == after['skipped'] == 0
    summary = {
        'base': BASE, 'branch': 'agent/c1b-counterparty',
        'HEAD_unchanged': True, 'index_empty': True,
        'existing_test_files_and_fixtures_unchanged': len(tests),
        'existing_test_changes': [], 'new_test_cases': 949,
        'only_changed_product_function': 'extract',
        'product_exactly_requested_union_and_version': True,
        'host_lookup_and_boolean_hook_unchanged': True,
        'failing_first_production_exact_to_base': True,
        'failing_first_and_final_tests_identical': True,
        'final_suite_and_evidence_production_identical': True,
        'report_append_only': True, 'memory_unchanged': True,
        'diff_check_passed': True, 'changed_tracked_files': tracked,
    }
    (OUT / 'preservation-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
