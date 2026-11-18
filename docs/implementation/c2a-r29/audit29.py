"""Check release evidence, source provenance and immutable project files."""
from collections import Counter, defaultdict
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
BASES = ('r21', 'r27', 'r28')


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    return json.loads(path.read_text())


def write(name, data):
    text = json.dumps(data, indent=2) + '\n'
    target = OUT / name
    if target.exists():
        assert target.read_text() == text, name
        return
    with target.open('x') as stream:
        stream.write(text)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tests(path):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids, families = Counter(), Counter()
    root = ET.parse(path).getroot()
    for case in root.iter('testcase'):
        state = ('failed' if case.find('failure') is not None else
                 'errors' if case.find('error') is not None else
                 'skipped' if case.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(case.attrib['classname'], case.attrib['name'])] += 1
        families[(case.attrib['classname'], case.attrib['name'].split('[')[0], state)] += 1
    assert sum(int(s.get('failures', 0)) for s in root.iter('testsuite')) == counts['failed']
    assert sum(int(s.get('errors', 0)) for s in root.iter('testsuite')) == counts['errors']
    assert sum(int(s.get('skipped', 0)) for s in root.iter('testsuite')) == counts['skipped']
    return counts, ids, families


def transitions(counts, before, after):
    for key, condition in (
        ('n_to_p', before in {'n', 'b'} and after in {'c', 'w'}),
        ('c_to_w', before == 'c' and after == 'w'),
        ('c_to_n', before == 'c' and after == 'n'),
        ('w_to_n', before == 'w' and after == 'n'),
    ):
        counts[key] += condition


def versionless(result):
    return {k: v for k, v in result.items() if k != 'analysis_version'}


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '3e3f33de3f06742b13b4d8a85c7cbf48e7538598'
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(OUT / 'release-source.py.txt')
    assert b"VERSION = 'c2a.29'" in (ROOT / PRODUCT).read_bytes()
    provenance = {}
    for version, commit in {'r28': head, 'r27': '1c425e1bfc7b508cc977eb5e5e3fffefb1eba0b7',
                            'r21': 'afb9aa6e71a28f3989c9896e0318912a11572891'}.items():
        data = subprocess.check_output(['git', 'show', commit + ':' + PRODUCT], cwd=ROOT)
        assert data == (OUT / (version + '-source.py.txt')).read_bytes()
        provenance[version] = dict(commit=commit, sha256=hashlib.sha256(data).hexdigest())
    write('source-provenance.json', provenance)
    counts, ids, families = tests(OUT / 'full-suite-complete.xml')
    old_counts, old_ids, _ = tests(OUT.parent / 'c2a-r28/full-suite.xml')
    assert old_counts['passed'] == 53690 and not old_ids - ids
    completion = read(OUT / 'full-suite-completion.json')
    assert completion['source_sha256'] == source_hash and completion['collected_ids_exact']
    assert not any(completion['returncodes'].values())
    assert counts == completion['counts']
    assert counts == dict(passed=58058, failed=0, errors=0, skipped=0), counts
    assert sum((ids - old_ids).values()) == 4368
    first, _, first_families = tests(OUT / 'failing-first.xml')
    assert first == dict(passed=2656, failed=680, errors=0, skipped=0), first
    targeted = tests(OUT / 'corrected-controls.xml')[0]
    assert targeted['failed'] == targeted['errors'] == targeted['skipped'] == 0
    assert families[('dealroom_sign.tests.test_placement_r13',
                     'test_l2_separate_own_company_line_preserves_scoring', 'passed')] == 40
    for path, digest in read(OUT / 'new-tests-failing-first-hashes.json').items():
        assert sha(ROOT / path) == digest, path
    assert tests(OUT / 'hidden-failing-first-final.xml')[0] == dict(passed=948, failed=60, errors=0, skipped=0)
    for path, digest in read(OUT / 'hidden-test-failing-first-hashes.json').items():
        assert sha(ROOT / path) == digest, path
    assert tests(OUT / 'columns-failing-first.xml')[0] == dict(passed=0, failed=24, errors=0, skipped=0)
    for path, digest in read(OUT / 'column-test-failing-first-hashes.json').items():
        assert sha(ROOT / path) == digest, path
    extraction = read(OUT / 'extraction-provenance.json')
    transcript = Path(extraction['transcript'])
    assert sha(transcript) == extraction['sha256']
    commands = []
    for line in transcript.read_text().splitlines():
        msg = json.loads(line).get('message', {})
        if not isinstance(msg, dict) or not isinstance(msg.get('content'), list):
            continue
        commands += [c['input']['command'] for c in msg['content']
                     if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Bash']
    fixtures = ROOT / 'backend/dealroom_sign/tests/fixtures/r29'
    assert len(commands) == len(extraction['calls'])
    for command, record in zip(commands, extraction['calls']):
        assert command.encode() == (fixtures / record['command_file']).read_bytes()
        if 'python_file' in record:
            match = re.search(r"<<'?(\w+)'?\n", command)
            end = command.index('\n' + match[1], match.end())
            assert command[match.end():end + 1].encode() == (fixtures / record['python_file']).read_bytes()
    write('extraction-verification.json', dict(commands=len(commands), python_bodies=sum(
        'python_file' in r for r in extraction['calls']), byte_exact=True, transcript_sha256=extraction['sha256']))
    inherited_codes = read(OUT / 'verified/returncodes.json')
    assert len(inherited_codes) == 27 and not any(inherited_codes.values()), inherited_codes
    assert not any(read(OUT / 'verified-review-returncodes.json').values())
    inherited, comparisons, ordinary = {}, {b: Counter() for b in BASES}, {}
    total, workers = 0, 0
    for part in inherited_codes:
        summary = read(OUT / 'verified' / (part + '-summary.json'))
        data = read(OUT / 'verified' / (part + '-cases.json.gz'))
        assert summary['source_sha256']['r29'] == source_hash
        assert summary['external_http_calls'] == 0 and summary['archive_results_exact']
        archived_summary = read(OUT.parent / 'c2a-r28/final' / (part + '-summary.json'))
        for base in BASES:
            assert summary['source_sha256'][base] == archived_summary['source_sha256'][base]
        groups = defaultdict(Counter)
        for row in data['cases']:
            states = {v: 'w' if row['raw_wrong'][v] else
                      {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[
                          data['outcomes'][row['results'][v]]['status']]
                      for v in (*BASES, 'r29')}
            assert states['r29'] != 'w', (part, row['case'])
            group = groups[row['group']]
            group['cases'] += 1
            for v, state in states.items():
                group[v + '_' + state] += 1
            for base in BASES:
                transitions(comparisons[base], states[base], states['r29'])
                local = Counter()
                transitions(local, states[base], states['r29'])
                group.update({base + '_' + k: value for k, value in local.items()})
        summary['raw_groups'] = dict(groups)
        inherited[part] = summary
        total += len(data['cases'])
        workers += summary['worker_evaluations']
        if part in {'ordinary_ndas', 'exhibits'}:
            ordinary[part] = dict(cases=len(data['cases']),
                added_holds={b: sum(g[b + '_c_to_n'] for g in groups.values()) for b in BASES})
            assert ordinary[part]['added_holds']['r28'] == ordinary[part]['added_holds']['r27'] == 0
        if part in {'q3b', 'q3b_aligned'}:
            ordinary[part] = {name: dict(g) for name, g in groups.items() if 'ordinary' in name.lower()}
            assert all(g['r28_c_to_n'] == g['r27_c_to_n'] == 0 for g in ordinary[part].values())
    assert total == 82450 and workers == 245, (total, workers)
    assert all(c['n_to_p'] == c['c_to_w'] == 0 for c in comparisons.values())
    golden = inherited['historical']['groups']['Seven goldens']
    assert golden['cases'] == 7 and golden['r29_golden_diffs'] == golden['r29_native_diffs'] == 0
    new, new_comparisons, policies = {}, {b: Counter() for b in BASES}, defaultdict(Counter)
    for part in read(OUT / 'verified-review-returncodes.json'):
        folder = OUT / ('verified-review-' + part)
        summary, rows = read(folder / 'summary.json'), read(folder / 'cases.json.gz')
        assert summary['source_sha256']['r29'] == source_hash and summary['external_http_calls'] == 0
        assert summary['model_calls']['r29'] == summary['model_calls']['r28']
        for row in rows:
            assert row['states']['r29'] != 'w', (part, row['axes'])
            for base in BASES:
                transitions(new_comparisons[base], row['raw_states'][base], row['raw_states']['r29'])
            if row['raw_states']['r29'] == 'w':
                assert row['retained_policy_control'] and row['raw_states']['r28'] == 'w'
                assert versionless(row['results']['r28']) == versionless(row['results']['r29'])
                policies[part]['unchanged_raw_flags'] += 1
        new[part] = summary
    assert all(c['n_to_p'] == c['c_to_w'] == 0 for c in new_comparisons.values())
    for part, n in {'conformed': 144, 'no_rule': 648, 'geometry': 1728, 'ruleless_name': 810,
                    'variants': 700}.items():
        assert new[part]['cases'] == n
        assert sum(g['r29_raw_wrong'] for g in new[part]['groups'].values()) == 0
    for group in new['ordinary']['groups'].values():
        assert group['r28_to_r29_c_to_n'] == group['r27_to_r29_c_to_n'] == 0
    ordinary['reviewer_ordinary'] = new['ordinary']
    notices = new['notices']['groups']
    l1_cost = sum(g['r27_to_r28_c_to_n'] for g in notices.values())
    assert l1_cost == 180, l1_cost
    initial = read(OUT / 'starting-hashes.json')
    changed = [p for p, digest in initial.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    oversized = [str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and p.stat().st_size >= 20_000_000]
    assert not oversized, oversized
    write('family-comparison.json', inherited)
    write('new-family-comparison.json', new)
    write('ordinary-hold-cost.json', ordinary)
    write('vs-live.json', dict(inherited_cells=total, inherited=comparisons,
          new_cells=sum(s['cases'] for s in new.values()), new=new_comparisons))
    write('preservation-summary.json', dict(base_head=head, inventoried_files=len(initial),
          unchanged=len(initial)-1, changed=changed, prior_test_ids_preserved=53690,
          new_test_ids=4368, new_tests_frozen_since_failing_first=True, oversized_evidence=oversized))
    write('full-suite-summary.json', counts)
    write('release-bars.json', dict(rc=0, base_head=head, working_tree_version='c2a.29',
          source_sha256=source_hash, full_suite=counts, targeted=targeted, failing_first=first,
          inherited_cells=total, inherited_comparisons=comparisons, new_comparisons=new_comparisons,
          worker_evaluations=workers+24, seven_goldens_exact_except_analysis_version=True,
          inherited_raw_wrong=0, new_required_scope_raw_wrong=0, retained_policy_controls=policies,
          l1_retained_holds=l1_cost, preservation_passed=True, blockers=[]))
    print(json.dumps(dict(cells=total, comparisons=comparisons, new_comparisons=new_comparisons,
                         full_suite=counts, preservation=len(initial)-1), indent=2))


if __name__ == '__main__':
    main()
