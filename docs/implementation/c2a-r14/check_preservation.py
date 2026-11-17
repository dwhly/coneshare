"""Audit the selected source, complete golden results, and unchanged old tests."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

from check_evidence import BASE, OUT, PRODUCT, ROOT, candidate_sources, versionless, write

from dealroom_sign import placement
from dealroom_sign.tests.test_placement import EXPECTED, FIXTURES, assert_golden, model_answer


NEW_TEST = 'backend/dealroom_sign/tests/test_placement_r14.py'
REPORT = 'docs/implementation/c1b-report.md'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    os.environ.pop('OPENROUTER_API_KEY', None)
    os.environ.pop('PLACE_MODEL', None)
    sys.dont_write_bytecode = True
    table = json.loads((OUT / 'counterfactual-summary.json').read_text())
    chosen = table['chosen']
    assert chosen in {'a', 'b'} and table['bars'][chosen]['passes']
    original = git('show', BASE + ':' + PRODUCT).decode()
    actual = (ROOT / PRODUCT).read_text()
    assert actual == candidate_sources(original)[chosen]
    assert placement.VERSION == 'c2a.14'
    assert hashlib.sha256(actual.encode()).hexdigest() == table['source_sha256'][chosen]
    before = json.loads((OUT / 'failing-first-summary.json').read_text())
    assert before['source_sha256'][PRODUCT] == hashlib.sha256(original.encode()).hexdigest()
    assert before['source_sha256'][NEW_TEST] == hashlib.sha256((ROOT / NEW_TEST).read_bytes()).hexdigest()
    assert (before['tests'], before['failures'], before['passed'], before['errors'], before['skipped']) == (
        3823, 105, 3718, 0, 0)
    previous = json.loads((OUT.parent / 'c2a-r13/placements.json').read_text())
    goldens, comparison = {}, {}
    forbidden = Mock(side_effect=AssertionError('External HTTP forbidden'))
    with patch('httpx.Client.send', forbidden):
        for name, expected in EXPECTED['fixtures'].items():
            signers = expected['signers']
            model = Mock(side_effect=model_answer)
            result = placement.place((FIXTURES / (name + '.pdf')).read_bytes(), signers, model_client=model)
            assert versionless(result) == versionless(previous[name]), name
            if name != 'bare':
                assert_golden(result, name, signers)
            else:
                assert result['status'] == 'bare' and not result['fields']
            assert model.call_count == (1 if name == 'unusual' else 0)
            for signer in signers:
                assert placement.to_native_fields(result, signer['email']) == placement.to_native_fields(
                    previous[name], signer['email'])
            goldens[name] = result
            comparison[name] = {'full_result_exact_except_analysis_version': True,
                                'native_fields_exact': True, 'model_calls': model.call_count}
    forbidden.assert_not_called()
    write('placements.json', goldens)
    write('golden-comparison.json', comparison)
    assert git('rev-parse', 'HEAD').decode().strip() == BASE
    assert git('branch', '--show-current').decode().strip() == 'agent/c1b-counterparty'
    tracked = git('diff', '--name-only', BASE).decode().splitlines()
    assert set(tracked) == {PRODUCT, REPORT}, tracked
    untracked = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    assert all(p == NEW_TEST or p.startswith('docs/implementation/c2a-r14/') for p in untracked)
    tests = git('ls-tree', '-r', '--name-only', BASE, 'backend/dealroom_sign/tests').decode().splitlines()
    assert all((ROOT / p).read_bytes() == git('show', BASE + ':' + p) for p in tests)
    assert (ROOT / REPORT).read_bytes().startswith(git('show', BASE + ':' + REPORT))
    assert not git('diff', '--cached', '--name-only')
    assert not git('diff', BASE, '--', '.agent/memory.md')
    git('diff', '--check')
    original_functions = {n.name: ast.dump(n) for n in ast.parse(original).body if isinstance(n, ast.FunctionDef)}
    current_functions = {n.name: ast.dump(n) for n in ast.parse(actual).body if isinstance(n, ast.FunctionDef)}
    assert original_functions.keys() == current_functions.keys()
    changed_functions = [name for name in original_functions if original_functions[name] != current_functions[name]]
    assert changed_functions == ['extract']
    after = json.loads((OUT / 'full-suite-summary.json').read_text())
    assert (after['tests'], after['passed'], after['failures'], after['errors'], after['skipped']) == (
        8073, 8073, 0, 0, 0)
    assert after['source_sha256'][PRODUCT] == table['source_sha256'][chosen]
    assert after['source_sha256'][NEW_TEST] == before['source_sha256'][NEW_TEST]
    summary = {
        'base': BASE, 'chosen': chosen, 'HEAD_unchanged': True, 'index_empty': True,
        'existing_test_files_and_fixtures_unchanged': len(tests), 'existing_test_changes': [],
        'new_test_cases': 3823, 'failing_first_production_exact_to_base': True,
        'failing_first_and_final_tests_identical': True,
        'counterfactual_and_final_production_identical': True,
        'changed_product_functions': changed_functions,
        'goldens_exact_except_analysis_version': 7, 'external_http_calls': forbidden.call_count,
        'report_append_only': True, 'memory_unchanged': True, 'diff_check_passed': True,
        'changed_tracked_files': tracked,
    }
    write('preservation-summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
