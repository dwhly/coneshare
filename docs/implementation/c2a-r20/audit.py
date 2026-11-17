"""Verify preservation, source provenance and exact test inventory for r20."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def write(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')


def audit():
    hashes = json.loads((OUT / 'starting-hashes.json').read_text())
    changed, missing = [], []
    for name, expected in hashes.items():
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(name)
    start = json.loads((OUT / 'starting-state.json').read_text())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    index = hashlib.sha256(subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT)).hexdigest()
    preservation = {'starting_files': len(hashes), 'changed': changed, 'missing': missing,
                    'head_unchanged': head == start['head'], 'index_unchanged': index == start['index_sha256']}
    write('preservation-summary', preservation)
    assert changed == ['backend/dealroom_sign/placement.py'], changed
    assert not missing and preservation['head_unchanged'] and preservation['index_unchanged']

    # Rebuild the reviewer's exact fix2 replacement from the preserved inputs,
    # without importing their harness or accessing /tmp.
    h = ast.parse((OUT / 'reviewer-h.py.txt').read_text())
    assigned = {n.targets[0].id: n.value for n in h.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    anchor = ast.literal_eval(assigned['_anchor'])
    fix = anchor + ast.literal_eval(assigned['FIX'].right)
    h2 = ast.parse((OUT / 'reviewer-h2.py.txt').read_text())
    small_anchor = next(ast.literal_eval(n.value) for n in h2.body
                        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == '_a')
    replacement = next(ast.literal_eval(n.value.args[1]) for n in h2.body
                       if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call))
    expected = (OUT / 'review-r19.py.txt').read_text().replace(anchor, fix.replace(small_anchor, replacement))
    actual = (ROOT / 'backend/dealroom_sign/placement.py').read_text().replace("VERSION = 'c2a.20'", "VERSION = 'c2a.19'")
    assert ast.dump(ast.parse(actual)) == ast.dump(ast.parse(expected))
    write('fix2-equivalence', {'ast_equal_except_version': True,
                             'production_sha256': hashlib.sha256(actual.replace("VERSION = 'c2a.19'", "VERSION = 'c2a.20'").encode()).hexdigest()})

    original = ast.parse((OUT / 'reviewer-q1real.py.txt').read_text())
    copied = ast.parse((ROOT / 'backend/dealroom_sign/tests/placement_r20_review_cases.py').read_text())
    original_loop = next(n for n in ast.walk(original)
                         if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
                         and len(n.target.elts) == 4)
    copied_loop = next(n for n in ast.walk(copied)
                       if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
                       and len(n.target.elts) == 4)
    split = next(i for i, n in enumerate(original_loop.body)
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                 and n.targets[0].id == 'res')
    original_loop.body = original_loop.body[:split]
    copied_loop.body = copied_loop.body[:-1]  # only the new yield replaces printing

    class Normalize(ast.NodeTransformer):
        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == 'new18' and node.attr == 'TWO':
                return ast.Name(id='TWO', ctx=ast.Load())
            return self.generic_visit(node)

    assert ast.dump(Normalize().visit(original_loop)) == ast.dump(copied_loop)

    def literal(tree, name):
        return ast.literal_eval(next(n.value for n in tree.body
                                     if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                                     and n.targets[0].id == name))

    for name in ['RECITALS', 'SECOND']:
        assert literal(original, name) == literal(copied, name)
    worker = ast.parse((OUT / 'reviewer-q1worker.py.txt').read_text())
    assert literal(worker, 'ROWS') == literal(copied, 'WORKER_ROWS')
    write('input-provenance', {'realistic_generator_ast_equal': True,
                               'recitals_and_affiliates_equal': True,
                               'worker_rows_equal': True,
                               'review_script_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                        for p in OUT.glob('reviewer-*.py.txt')}})

    runs = {}
    for name in ['failing-first', 'failing-first-boundaries', 'targeted', 'full-suite']:
        root = ET.parse(OUT / (name + '.xml'))
        counts = Counter()
        per_test = Counter()
        for test in root.iter('testcase'):
            status = ('failed' if test.find('failure') is not None else
                      'errors' if test.find('error') is not None else
                      'skipped' if test.find('skipped') is not None else 'passed')
            counts[status] += 1
            per_test[test.attrib['name'].split('[')[0] + ':' + status] += 1
        runs[name] = {'counts': {key: counts[key] for key in ['passed', 'failed', 'errors', 'skipped']},
                      'per_test': per_test}
    write('test-runs-summary', runs)
    assert runs['full-suite']['counts'] == {'passed': 18376, 'failed': 0, 'errors': 0, 'skipped': 0}

    def inventory(path):
        return Counter((test.attrib['classname'], test.attrib['name'])
                       for test in ET.parse(path).iter('testcase'))

    before = inventory(OUT.parent / 'c2a-r19/full-suite.xml')
    after = inventory(OUT / 'full-suite.xml')
    removed = before - after
    additions = after - before
    assert not removed
    assert sum(additions.values()) == 544
    write('test-inventory-summary', {'before': sum(before.values()), 'after': sum(after.values()),
                                     'removed': list(removed), 'added': sum(additions.values())})
    print(json.dumps({'preservation': preservation, 'full_suite': runs['full-suite']['counts'],
                      'new_tests': 544, 'fix2_ast_equal': True}, indent=2))


if __name__ == '__main__':
    audit()
