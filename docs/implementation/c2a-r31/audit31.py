"""Audit final-source runs, exact case coverage, transitions, and preservation."""
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
BASES = ('r29', 'r28', 'r21')
PRODUCT = 'backend/dealroom_sign/placement.py'


def read(p):
    if str(p).endswith('.gz'):
        with gzip.open(p, 'rt') as stream:
            return json.load(stream)
    return json.loads(p.read_text())


def write(name, data):
    (OUT/name).write_text(json.dumps(data, indent=2)+'\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def versionless(r):
    return {k: v for k, v in r.items() if k != 'analysis_version'}


def test_counts(p):
    counts = Counter(dict.fromkeys(('passed', 'failed', 'errors', 'skipped'), 0))
    ids = Counter()
    for case in ET.parse(p).getroot().iter('testcase'):
        status = ('failed' if case.find('failure') is not None else
                  'errors' if case.find('error') is not None else
                  'skipped' if case.find('skipped') is not None else 'passed')
        counts[status] += 1
        ids[(case.get('classname'), case.get('name'))] += 1
    return counts, ids


def compare(c, before, after):
    c[before + '_to_' + after] += 1
    c['n_to_p'] += before in {'n', 'b'} and after in {'c', 'w'}
    c['n_to_W'] += before in {'n', 'b'} and after == 'w'
    c['c_to_w'] += before == 'c' and after == 'w'


def main():
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    assert head == '9a9196bf370edefef0f4b825450bd1b4841f3248'
    source_hash = sha(ROOT/PRODUCT)
    assert source_hash == sha(OUT/'shipping-source.py.txt')
    assert b"VERSION = 'c2a.31'" in (ROOT/PRODUCT).read_bytes()
    provenance = {}
    for v, commit in dict(r30=head, r29='0aa3cbbb1331b9416649bfcbdef14ed788cf7684',
                         r28='3e3f33de3f06742b13b4d8a85c7cbf48e7538598',
                         r21='afb9aa6e71a28f3989c9896e0318912a11572891').items():
        data = subprocess.check_output(['git','show',commit+':'+PRODUCT], cwd=ROOT)
        assert data == (OUT/(v+'-source.py.txt')).read_bytes()
        provenance[v] = dict(commit=commit, sha256=hashlib.sha256(data).hexdigest())

    extraction = read(OUT/'extraction-provenance.json')
    transcript = Path(extraction['transcript'])
    assert sha(transcript) == extraction['sha256']
    commands, writes = [], []
    for line in transcript.read_text().splitlines():
        message = json.loads(line).get('message', {})
        if not isinstance(message, dict) or not isinstance(message.get('content'), list):
            continue
        for content in message['content']:
            if not isinstance(content, dict) or content.get('type') != 'tool_use':
                continue
            if content['name'] == 'Bash': commands.append(content['input']['command'])
            if content['name'] == 'Write': writes.append(content['input'])
    fixtures = ROOT/'backend/dealroom_sign/tests/fixtures/r31'
    bodies = 0
    for i, command in enumerate(commands, 1):
        assert command.encode() == (fixtures/f'reviewer-r30-call{i}.command.txt').read_bytes()
        for j, match in enumerate(re.finditer(r"<<\s*['\"]?(\w+)['\"]?[^\n]*\n(.*?)\n\1(?:\n|$)", command, re.S), 1):
            assert (match[2]+'\n').encode() == (fixtures/f'reviewer-r30-call{i}-body{j}.txt').read_bytes()
            bodies += 1
    for item in writes:
        assert item['content'].encode() == (fixtures/('reviewer-r30-'+Path(item['file_path']).name+'.txt')).read_bytes()
    for file in ('failing-first-hashes.json', 'frozen-tests-hashes.json'):
        for path, digest in read(OUT/file).items():
            assert sha(ROOT/path) == digest, path
    initial = read(OUT/'starting-hashes.json')
    changed = [p for p, h in initial.items() if not (ROOT/p).is_file() or sha(ROOT/p) != h]
    assert changed == [PRODUCT], changed
    assert not subprocess.check_output(['git','diff','--cached'], cwd=ROOT)
    subprocess.run(['git','diff','--check'], cwd=ROOT, check=True)

    first = {name: test_counts(OUT/(name+'.xml'))[0] for name in
             ('failing-first', 'ownership-failing-first', 'unclaimed-failing-first', 'recital-failing-first')}
    assert first['failing-first'] == dict(passed=15400, failed=3068, errors=0, skipped=0), first
    assert first['ownership-failing-first'] == dict(passed=4, failed=14, errors=0, skipped=0)
    assert first['unclaimed-failing-first'] == dict(passed=0, failed=2, errors=0, skipped=0)
    assert first['recital-failing-first'] == dict(passed=1, failed=1, errors=0, skipped=0)
    full, ids = test_counts(OUT/'shipping-full-suite-complete.xml')
    old, old_ids = test_counts(OUT.parent/'c2a-r30/shipping-full-suite-complete.xml')
    assert full == dict(passed=80088, failed=0, errors=0, skipped=0), full
    assert old['passed'] == 61598 and not old_ids-ids
    assert sum((ids-old_ids).values()) == 18490
    assert sum(n for (file,name),n in ids.items() if file=='dealroom_sign.tests.test_placement_r13'
               and name.startswith('test_l2_separate_own_company_line_preserves_scoring[')) == 40
    completion = read(OUT/'shipping-full-suite-completion.json')
    assert completion['source_sha256'] == source_hash and completion['collected_ids_exact']
    assert not any(completion['returncodes'].values()) and completion['counts'] == full

    totals = {b: Counter() for b in BASES}
    families, groups, recoveries = {}, {}, []
    def account(family, case, states, results, policy=False, group=None):
        entry = families.setdefault(family, dict(cases=0, raw_counts=Counter(),
                                                comparisons={b:Counter() for b in BASES}, policy_controls=0))
        entry['cases'] += 1
        for v in (*BASES,'r31'):
            entry['raw_counts'][v+'_'+states[v]] += 1
        if states['r31']=='w':
            assert policy and states['r29']==states['r28']=='w', (family,case)
            assert versionless(results['r31']) == versionless(results['r29']), (family,case)
            entry['policy_controls'] += 1
        for b in BASES:
            compare(entry['comparisons'][b],states[b],states['r31'])
            compare(totals[b],states[b],states['r31'])
            assert not (states[b] in {'n','b','c'} and states['r31']=='w'), (family,case,b)
        if states['r29'] in {'n','b'} and states['r31']=='c':
            assert family=='review/date' and states['r28']=='c', (family,case)
            assert versionless(results['r31'])==versionless(results['r28']), (family,case)
            recoveries.append(dict(family=family,case=case,correct=True,result=results['r31']))
        else:
            assert versionless(results['r31'])==versionless(results['r29']), (family,case)
        if group:
            entry = groups.setdefault(family+'/'+group,dict(cases=0,comparisons={b:Counter() for b in BASES}))
            entry['cases'] += 1
            for b in BASES: compare(entry['comparisons'][b],states[b],states['r31'])

    codes = read(OUT/'shipping-inherited/returncodes.json')
    assert len(codes)==27 and not any(codes.values()), codes
    workers, inherited = 0, 0
    for family in codes:
        summary=read(OUT/'shipping-inherited'/(family+'-summary.json'))
        assert summary['source_sha256']['r31']==source_hash
        assert summary['external_http_calls']==0 and summary['archive_results_exact']
        data=read(OUT/'shipping-inherited'/(family+'-cases.json.gz'))
        for row in data['cases']:
            results={v:data['outcomes'][row['results'][v]] for v in (*BASES,'r31')}
            states={v:'w' if row['raw_wrong'][v] else {'placed':'c','needs_sender':'n','bare':'b'}[results[v]['status']]
                    for v in results}
            assert states['r31']!='w'
            account('inherited/'+family,row['case'],states,results,group=row['group'])
        inherited+=len(data['cases']);workers+=summary['worker_evaluations']
        if family=='historical':
            g=summary['groups']['Seven goldens']
            assert g['cases']==7 and g['r31_golden_diffs']==g['r31_native_diffs']==0
    assert inherited==82450 and workers==245
    codes=read(OUT/'shipping-matrix-returncodes.json')
    assert len(codes)==9 and not any(codes.values()), codes
    review=read(OUT/'rechecked-review-returncodes.json')
    assert len(review)==8 and not any(review.values()), review
    prefixes=[('shipping-'+f,f) for f in (*codes,'date')]+[('rechecked-review-'+f,f) for f in review]
    for prefix,family in prefixes:
        summary=read(OUT/(prefix+'-summary.json'))
        h=summary['source_sha256']; assert (h['r31'] if isinstance(h,dict) else h)==source_hash
        assert summary['external_http_calls']==0
        rows=read(OUT/(prefix+'-cases.json.gz'))
        for row in rows:
            assert row['model_calls']['r31']==row['model_calls']['r29']
            account('review/'+family,dict(index=row['index'],axes=row['axes']),row['states'],row['results'],
                    policy=row.get('retained_policy_control',family=='stray'))
        if family in {'plain','swap'}: assert len(rows)==9216
        if family=='date': assert len(rows)==2844
        if family=='variants': assert len(rows)==700
        if family in {'plain','swap','date','hidden','two_columns','no_rule','geometry','ruleless_name','variants'}:
            assert families['review/'+family]['raw_counts']['r31_w']==0
    assert len(recoveries)==686
    assert totals['r29']['n_to_p']==686
    assert totals['r28']['n_to_p']==totals['r21']['n_to_p']==0
    assert all(t['n_to_W']==t['c_to_w']==0 for t in totals.values())
    exact=read(OUT/'shipping-exact-workers.json')
    assert exact['cases']==21 and exact['wrong']==0 and exact['source_sha256']==source_hash
    oversized=[str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and p.stat().st_size>=20_000_000]
    assert not oversized, oversized
    write('source-provenance.json',provenance)
    write('extraction-verification.json',dict(commands=len(commands),heredoc_bodies=bodies,write_payloads=len(writes),
          copied_generators=len(read(OUT/'copied-generator-provenance.json')),byte_exact=True,transcript_sha256=extraction['sha256']))
    write('family-comparison.json',families);write('group-comparison.json',groups)
    with gzip.open(OUT/'every-n-to-p.json.gz','wt') as stream:json.dump(recoveries,stream)
    write('vs-live.json',totals)
    write('preservation-summary.json',dict(inventoried=len(initial),unchanged=len(initial)-1,changed=changed,
          existing_test_ids_preserved=61598,new_test_ids=18490,failing_first_tests_unchanged=True,oversized_evidence=oversized))
    write('release-bars.json',dict(rc=0,head=head,version='c2a.31',source_sha256=source_hash,failing_first=first,
          full_suite=full,M1_recovered=686,b1_wrong=0,h1_wrong=0,r27_700_wrong=0,inherited_wrong=0,
          inherited_cells=inherited,comparisons=totals,seven_goldens_exact_except_analysis_version=True,
          policy_controls=sum(f['policy_controls'] for f in families.values()),blockers=[]))
    print(json.dumps(dict(full_suite=full,comparisons=totals,preserved=len(initial)-1),indent=2))

if __name__=='__main__':main()
