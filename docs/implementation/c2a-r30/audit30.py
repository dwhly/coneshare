"""Verify every release bar from immutable baselines and completed runs."""
from collections import Counter
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
BASES = ('r21', 'r28', 'r29')


def read(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return json.load(stream)
    return json.loads(path.read_text())


def write(name, data):
    with (OUT / name).open('x') as stream:
        stream.write(json.dumps(data, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def versionless(result):
    return {k: v for k, v in result.items() if k != 'analysis_version'}


def tests(path):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids = Counter()
    for case in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if case.find('failure') is not None else 'errors' if case.find('error') is not None
                 else 'skipped' if case.find('skipped') is not None else 'passed')
        counts[state] += 1
        ids[(case.attrib['classname'], case.attrib['name'])] += 1
    return counts, ids


def compare(counter, before, after):
    counter[before + '_to_' + after] += 1
    counter['n_to_p'] += before in {'n', 'b'} and after in {'c', 'w'}
    counter['n_to_W'] += before in {'n', 'b'} and after == 'w'
    counter['c_to_w'] += before == 'c' and after == 'w'


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == '0aa3cbbb1331b9416649bfcbdef14ed788cf7684'
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(OUT / 'shipping-source.py.txt')
    assert b"VERSION = 'c2a.30'" in (ROOT / PRODUCT).read_bytes()
    provenance = {}
    for base, commit in dict(r29=head, r28='3e3f33de3f06742b13b4d8a85c7cbf48e7538598',
                             r21='afb9aa6e71a28f3989c9896e0318912a11572891').items():
        data = subprocess.check_output(['git', 'show', commit + ':' + PRODUCT], cwd=ROOT)
        assert data == (OUT / (base + '-source.py.txt')).read_bytes()
        provenance[base] = dict(commit=commit, sha256=hashlib.sha256(data).hexdigest())

    extraction = read(OUT / 'extraction-provenance.json')
    transcript = Path(extraction['transcript'])
    assert sha(transcript) == extraction['transcript_sha256']
    commands, writes = [], []
    for line in transcript.read_text().splitlines():
        message = json.loads(line).get('message', {})
        if not isinstance(message, dict) or not isinstance(message.get('content'), list):
            continue
        for content in message['content']:
            if not isinstance(content, dict) or content.get('type') != 'tool_use':
                continue
            if content['name'] == 'Bash':
                commands.append(content['input']['command'])
            elif content['name'] == 'Write':
                writes.append(content['input'])
    fixtures = ROOT / 'backend/dealroom_sign/tests/fixtures/r30'
    body_count = 0
    for index, command in enumerate(commands, 1):
        assert command.encode() == (fixtures / f'reviewer-r29-call{index}.command.txt').read_bytes()
        for j, match in enumerate(re.finditer(r"<<\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\1(?:\n|$)", command, re.S), 1):
            assert (match[2] + '\n').encode() == (fixtures / f'reviewer-r29-call{index}-body{j}.txt').read_bytes()
            body_count += 1
    for item in writes:
        path = fixtures / ('reviewer-r29-' + Path(item['file_path']).name + '.txt')
        assert path.read_bytes() == item['content'].encode()
    for name in ('failing-first-hashes.json', 'recoveries-failing-first-hashes.json'):
        for path, digest in read(OUT / name).items():
            assert sha(ROOT / path) == digest, path

    initial = read(OUT / 'starting-hashes.json')
    changed = [p for p, digest in initial.items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git', 'diff', '--cached'], cwd=ROOT)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)

    first, _ = tests(OUT / 'failing-first.xml')
    recovered_first, _ = tests(OUT / 'recoveries-failing-first.xml')
    assert first == dict(passed=2848, failed=6, errors=0, skipped=0), first
    assert recovered_first == dict(passed=0, failed=686, errors=0, skipped=0), recovered_first
    full, ids = tests(OUT / 'shipping-full-suite-complete.xml')
    assert full == dict(passed=61598, failed=0, errors=0, skipped=0), full
    old_counts, old_ids = tests(OUT.parent / 'c2a-r29/full-suite-complete.xml')
    assert old_counts['passed'] == 58058 and not old_ids - ids
    assert sum((ids - old_ids).values()) == 3540
    completion = read(OUT / 'shipping-full-suite-completion.json')
    assert completion['source_sha256'] == source_hash and completion['collected_ids_exact']
    assert not any(completion['returncodes'].values()) and completion['counts'] == full
    assert sum(n for (file, name), n in ids.items() if file == 'dealroom_sign.tests.test_placement_r13'
               and name.startswith('test_l2_separate_own_company_line_preserves_scoring[')) == 40

    families, group_details, totals = {}, {}, {b: Counter() for b in BASES}
    codes = read(OUT / 'shipping-inherited/returncodes.json')
    assert len(codes) == 27 and not any(codes.values()), codes
    inherited_total, workers = 0, 0
    for family in codes:
        summary = read(OUT / 'shipping-inherited' / (family + '-summary.json'))
        assert summary['source_sha256']['r30'] == source_hash
        assert summary['external_http_calls'] == 0 and summary['archive_results_exact']
        data = read(OUT / 'shipping-inherited' / (family + '-cases.json.gz'))
        counts, comparisons = Counter(), {b: Counter() for b in BASES}
        for row in data['cases']:
            results = {v: data['outcomes'][row['results'][v]] for v in (*BASES, 'r30')}
            states = {v: 'w' if row['raw_wrong'][v] else
                      {'placed': 'c', 'needs_sender': 'n', 'bare': 'b'}[results[v]['status']]
                      for v in results}
            assert states['r30'] != 'w', (family, row['case'])
            detail = group_details.setdefault(family + '/' + row['group'],
                dict(cases=0, counts=Counter(), comparisons={b: Counter() for b in BASES}))
            detail['cases'] += 1
            for v, state in states.items():
                counts[v + '_' + state] += 1
                detail['counts'][v + '_' + state] += 1
            for base in BASES:
                compare(comparisons[base], states[base], states['r30'])
                compare(totals[base], states[base], states['r30'])
                compare(detail['comparisons'][base], states[base], states['r30'])
            assert versionless(results['r29']) == versionless(results['r30']), (family, row['case'])
        families['inherited/' + family] = dict(cases=len(data['cases']), counts=counts, comparisons=comparisons)
        inherited_total += len(data['cases'])
        workers += summary['worker_evaluations']
        if family == 'historical':
            golden = summary['groups']['Seven goldens']
            assert golden['cases'] == 7 and golden['r30_golden_diffs'] == golden['r30_native_diffs'] == 0
    assert inherited_total == 82450 and workers == 245, (inherited_total, workers)

    matrix_codes = read(OUT / 'shipping-returncodes.json')
    assert len(matrix_codes) == 6 and not any(matrix_codes.values())
    review_codes = read(OUT / 'review-completion.json')['returncodes']
    assert len(review_codes) == 8 and not any(review_codes.values())
    review_families = [('shipping-' + f, f) for f in matrix_codes]
    review_families += [(('rechecked-review-' if f in {'extended', 'r27'} else 'shipping-review-') + f, f)
                        for f in review_codes]
    review_families += [('shipping-' + f, f) for f in ('ordinary_offsets', 'stray')]
    retained = Counter()
    for prefix, family in review_families:
        summary = read(OUT / (prefix + '-summary.json'))
        hashes = summary['source_sha256']
        assert (hashes['r30'] if isinstance(hashes, dict) else hashes) == source_hash
        assert summary['external_http_calls'] == 0
        rows = read(OUT / (prefix + '-cases.json.gz'))
        counts, comparisons = Counter(), {b: Counter() for b in BASES}
        recoveries = 0
        for row in rows:
            states, results = row['states'], row['results']
            if family == 'date':
                assert versionless(results['r30']) == versionless(results['r28']) == versionless(results['r21'])
            for v in (*BASES, 'r30'):
                counts[v + '_' + states[v]] += 1
            assert row['model_calls']['r29'] == row['model_calls']['r30']
            for base in BASES:
                compare(comparisons[base], states[base], states['r30'])
                compare(totals[base], states[base], states['r30'])
                assert not (states[base] in {'n', 'b', 'c'} and states['r30'] == 'w'), (family, row['axes'])
            if states['r29'] == 'n' and states['r30'] == 'c':
                assert family == 'date' and states['r28'] == 'c'
                assert versionless(results['r30']) == versionless(results['r28'])
                recoveries += 1
            else:
                assert versionless(results['r30']) == versionless(results['r29']), (family, row['axes'])
            if states['r30'] == 'w':
                assert family in {'notices', 'r27', 'recitals', 'stacks', 'stray'}
                assert states['r29'] == states['r28'] == 'w'
                retained[family] += 1
        if family == 'date':
            assert len(rows) == 2844 and recoveries == 686 and counts['r30_w'] == 0
        if family in {'hidden', 'two_columns', 'no_rule', 'geometry', 'ruleless_name', 'variants'}:
            assert counts['r30_w'] == 0
        families['review/' + family] = dict(cases=len(rows), counts=counts, comparisons=comparisons,
                                            correct_M1_recoveries=recoveries)
    assert all(c['n_to_W'] == c['c_to_w'] == 0 for c in totals.values())
    assert totals['r29']['n_to_p'] == 686
    assert totals['r28']['n_to_p'] == totals['r21']['n_to_p'] == 0
    exact_workers = read(OUT / 'shipping-exact-workers.json')
    assert exact_workers['cases'] == 21 and exact_workers['wrong'] == 0
    assert exact_workers['source_sha256'] == source_hash
    oversized = [str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and p.stat().st_size >= 20_000_000]
    assert not oversized, oversized

    write('source-provenance.json', provenance)
    write('extraction-verification.json', dict(bash_commands=len(commands), heredoc_bodies=body_count,
          write_payloads=len(writes), byte_exact=True, transcript_sha256=extraction['transcript_sha256']))
    write('family-comparison.json', families)
    write('group-comparison.json', group_details)
    write('vs-live.json', dict(totals=totals, retained_policy_flags=retained,
          inherited_cells=inherited_total, review_cells=sum(v['cases'] for k, v in families.items() if k.startswith('review/'))))
    write('preservation-summary.json', dict(inventoried_files=len(initial), unchanged=len(initial)-1,
          changed=changed, prior_test_ids_preserved=58058, new_test_ids=3540,
          tests_frozen_since_failing_first=True, oversized_evidence=oversized))
    write('release-bars.json', dict(rc=0, head=head, version='c2a.30', source_sha256=source_hash,
          failing_first=first, recoveries_failing_first=recovered_first, full_suite=full,
          inherited_raw_wrong=0, h1_raw_wrong=0, m1_raw_wrong=0, r27_700_raw_wrong=0,
          M1_recovered=686, comparisons=totals, seven_goldens_exact_except_analysis_version=True,
          worker_evaluations=workers+6+21, preserved=True, blockers=[]))
    print(json.dumps(dict(full_suite=full, comparisons=totals, families=len(families), preserved=len(initial)-1), indent=2))


if __name__ == '__main__':
    main()
