"""Preserve the Gate 3 r31 tool payloads and exact generator bodies."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = Path('/root/worktrees/dealroom-sign-edd/docs/edd/briefs/counterparty-c2a-gate3-r31.jsonl')
FIX = ROOT / 'backend/dealroom_sign/tests/fixtures/r32'
FIX.mkdir(exist_ok=True)
records = []
commands = 0

def save(name, content, line, kind):
    data = content.encode()
    target = FIX / name
    assert not target.exists()
    target.write_bytes(data)
    records.append(dict(file=name, line=line, kind=kind, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))

for line, raw in enumerate(SOURCE.read_text().splitlines(), 1):
    message = json.loads(raw).get('message')
    if not isinstance(message, dict) or not isinstance(message.get('content'), list):
        continue
    for item in message['content']:
        if not isinstance(item, dict) or item.get('type') != 'tool_use':
            continue
        value = item.get('input', {})
        if item['name'] == 'Bash':
            commands += 1
            save(f'line{line}.command.txt', value['command'], line, 'Bash command, exact decoded bytes')
            match = re.search(r"<<'(?P<tag>\w+)'\n(?P<body>[\s\S]*?)\n(?P=tag)(?:\n|$)", value['command'])
            if match:
                save(f'line{line}.py.txt', match['body'] + '\n', line, 'exact heredoc body')
        elif item['name'] == 'Write':
            save('reviewer-r31-' + Path(value['file_path']).name + '.txt', value['content'], line, 'Write content, exact decoded bytes')
        elif item['name'] == 'Edit':
            save(f'line{line}.edit.json', json.dumps(value, indent=2) + '\n', line, 'Edit provenance')
# The successful Bash edit at line 456 adds only a run filter. Preserve both versions.
source = (FIX / 'reviewer-r31-own.py.txt').read_text()
a = '    for key, pages, people, allowed in cases(fam):\n        pdf'
b = '    for key, pages, people, allowed in cases(fam):\n        if len(sys.argv) > 2 and sys.argv[2] not in key: continue\n        pdf'
assert source.count(a) == 1
save('reviewer-r31-own-final.py.txt', source.replace(a, b), 456, 'exact successful reviewer edit; generator unchanged')
# Reconstruct files copied at line 131 from already frozen r30 generator bytes.
for prior in sorted((FIX.parent / 'r31').glob('reviewer-r30-*.py.txt')):
    source = prior.read_text()
    source = source.replace('e55bf345', 'a8ad8dcc').replace('r30=', 'r31=').replace("SRC['r30']", "SRC['r31']").replace('r30 worker', 'r31 worker')
    save(prior.name.replace('reviewer-r30-', 'reviewer-r31-'), source, 131, 'exact line131 copy transformation of ' + str(prior.relative_to(ROOT)))
(OUT / 'extraction-provenance.json').write_text(json.dumps(dict(transcript=str(SOURCE), transcript_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), commands=commands, files=records), indent=2) + '\n')
print('extracted', len(records), 'files;', commands, 'commands')
