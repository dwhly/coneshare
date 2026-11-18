"""Run existing placement controls unchanged before the full release suite."""
import ast
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
functions = {}
files = {}
for path in (ROOT/'backend/dealroom_sign/tests').glob('test_placement*.py'):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.FunctionDef):
            functions.setdefault(node.name, []).append(node)
            if node.name.startswith('test_'):
                files[(str(path.relative_to(ROOT/'backend')), node.name)] = node
relevant = {name for name, nodes in functions.items() if any(
    any(isinstance(n, ast.Constant) and n.value == 'placed' for n in ast.walk(node))
    for node in nodes)}
for _ in range(20):
    more = {name for name, nodes in functions.items() if any(
        any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in relevant
            for n in ast.walk(node)) for node in nodes)}
    if more <= relevant:
        break
    relevant |= more
ids = [path+'::'+name for (path, name) in files if name in relevant]
(OUT/'live-control-nodes.json').write_text(json.dumps(ids,indent=2)+'\n')
result = subprocess.run([sys.executable,str(OUT/'run_tests.py'),*ids,'--tb=short',
                         '--junitxml=../docs/implementation/c2a-r29/live-controls.xml'])
sys.exit(result.returncode)
