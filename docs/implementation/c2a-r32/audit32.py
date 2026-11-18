"""Audit raw oracle outcomes, exact coverage, source provenance and preservation."""
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


def read(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else path.open()) as stream:
        return json.load(stream)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def versionless(result):
    return {k: v for k, v in result.items() if k != 'analysis_version'}


def test_counts(path):
    counts = Counter(dict.fromkeys(('passed','failed','errors','skipped'),0))
    ids = Counter()
    failures = []
    for case in ET.parse(path).getroot().iter('testcase'):
        state = ('failed' if case.find('failure') is not None else 'errors' if case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed')
        counts[state] += 1
        node = (case.get('classname'), case.get('name'))
        ids[node] += 1
        if state != 'passed': failures.append(dict(classname=node[0], name=node[1], status=state))
    return counts, ids, failures


def main():
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert head == '8dd65f82ae560c8563d29f16a0b3d4fad936d9e2'
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(OUT / 'shipping-source.py.txt')
    provenance = {}
    for version, commit in [('r31',head),('r29','0aa3cbbb1331b9416649bfcbdef14ed788cf7684')]:
        source = subprocess.check_output(['git','show',commit+':'+PRODUCT],cwd=ROOT)
        assert source == (OUT / (version+'-source.py.txt')).read_bytes()
        provenance[version] = dict(commit=commit,sha256=hashlib.sha256(source).hexdigest())
    provenance['r32'] = dict(head=head,sha256=source_hash,uncommitted=True)
    write('source-provenance.json',provenance)
    extraction=read(OUT/'extraction-provenance.json')
    transcript=Path(extraction['transcript'])
    assert sha(transcript)==extraction['transcript_sha256']
    lines=transcript.read_text().splitlines()
    fixtures=ROOT/'backend/dealroom_sign/tests/fixtures/r32'
    for item in extraction['files']:
        target=fixtures/item['file']
        assert sha(target)==item['sha256']
        tools=[c for c in json.loads(lines[item['line']-1])['message']['content']
               if isinstance(c,dict) and c.get('type')=='tool_use']
        if item['kind'].startswith('Write content'):
            assert target.read_bytes()==tools[0]['input']['content'].encode()
        if item['kind'].startswith('Bash command'):
            assert target.read_bytes()==tools[0]['input']['command'].encode()
        if item['kind']=='exact heredoc body':
            command=tools[0]['input']['command']
            match=re.search(r"<<'(?P<tag>\w+)'\n(?P<body>[\s\S]*?)\n(?P=tag)(?:\n|$)",command)
            assert target.read_bytes()==(match['body']+'\n').encode()
    inherited_provenance=read(OUT/'inherited-generator-provenance.json')
    assert sha(ROOT/inherited_provenance['result'])==inherited_provenance['result_sha256']
    write('extraction-verification.json',dict(exact_payload_files=len(extraction['files']),additional_inherited_wrapper=1,
        commands=extraction['commands'],decoded_payload_bytes_exact=True,fixtures_unchanged=True))
    start = read(OUT/'starting-hashes.json')
    changes = [p for p,h in start.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    assert changes == [PRODUCT], changes
    frozen = read(OUT/'frozen-tests-hashes.json')
    for path,digest in frozen.items(): assert sha(ROOT/path)==digest,path
    for name in ('failing-first-hashes.json','ownership-failing-first-hashes.json','rules-failing-first-hashes.json'):
        for path,digest in read(OUT/name).items(): assert sha(ROOT/path)==digest,path
    assert not subprocess.check_output(['git','diff','--cached'],cwd=ROOT)
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    write('preservation-summary.json',dict(starting_files=len(start),unchanged=len(start)-len(changes),changed=changes,
        old_test_tree_files=sum(p.startswith('backend/dealroom_sign/tests/') for p in start),
        frozen_new_files=len(frozen),old_tests_fixtures_evidence_and_done_markers_unchanged=True,staged=False,head=head))
    # Only the widened-band predicate and VERSION differ semantically from r31.
    def unaffected(path):
        tree=ast.parse(path.read_text())
        tree.body=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='extended_date_names_owned')
                   and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))]
        return ast.dump(tree,include_attributes=False)
    assert unaffected(ROOT/PRODUCT)==unaffected(OUT/'r31-source.py.txt')
    write('structural-proof.json',dict(only_changed_function='extended_date_names_owned',other_changes=['VERSION','N-2 comment only'],outside_widened_band_semantically_unchanged=True))
    first={name:test_counts(OUT/(name+'.xml'))[0] for name in ('failing-first','ownership-failing-first','rules-failing-first')}
    counts,ids,failures=test_counts(OUT/'shipping-full-suite-complete.xml')
    old_counts,old_ids,_=test_counts(OUT.parent/'c2a-r31/shipping-full-suite-complete.xml')
    assert not old_ids-ids
    manifest=read(OUT/'shipping-full-suite-completion.json')
    assert counts==manifest['counts'] and manifest['collected_ids_exact']
    write('test-audit.json',dict(failing_first=first,full_suite=counts,old_tests_preserved=sum(old_ids.values()),new_tests=sum((ids-old_ids).values()),failures=failures))

    for filename,expected in [('shipping-matrix-returncodes.json',18),('rechecked-review-returncodes.json',8),
                              ('shipping-inherited/returncodes.json',27)]:
        codes=read(OUT/filename)
        assert len(codes)==expected and not any(codes.values()),(filename,codes)
    assert len(list(OUT.glob('shipping-*-cases.json.gz')))==18
    assert len(list(OUT.glob('rechecked-review-*-cases.json.gz')))==8
    assert len(list((OUT/'shipping-inherited').glob('*-cases.json.gz')))==27

    families={};recoveries=[];wrong_rows=[]
    def compare(family,index,axes,results,states,calls):
        c=families.setdefault(family,Counter())
        c['cells']+=1
        for version in ('r29','r32'):
            c[version+'_wrong']+=states[version]=='w'
            c[version+'_placed']+=bool(results[version]['fields'])
            c[version+'_model_calls']+=calls[version]
        before,after=states['r29'],states['r32']
        c['n_to_p']+=before=='n' and after=='c'
        c['n_to_W']+=before=='n' and after=='w'
        c['c_to_w']+=before=='c' and after=='w'
        c['c_to_hold']+=before=='c' and after=='n'
        c['changed_output']+=versionless(results['r29'])!=versionless(results['r32'])
        if before=='n' and after in {'c','w'}:
            recoveries.append(dict(family=family,index=index,axes=axes,correct=after=='c',result=results['r32']))
        if after=='w':
            same=versionless(results['r29'])==versionless(results['r32'])
            c['wrong_unchanged_from_live']+=same
            wrong_rows.append(dict(family=family,index=index,axes=axes,unchanged_from_live=same,result=results['r32']))
        assert calls['r29']==calls['r32'],(family,index,'model calls changed')
    for path in sorted(OUT.glob('shipping-*-cases.json.gz'))+sorted(OUT.glob('rechecked-review-*-cases.json.gz')):
        stem=path.name.removesuffix('-cases.json.gz')
        family=('review/'+stem.removeprefix('shipping-') if stem.startswith('shipping-') else 'prior/'+stem.removeprefix('rechecked-review-'))
        summary=read(path.with_name(stem+'-summary.json'))
        assert (summary['source_sha256'].get('r32') if isinstance(summary['source_sha256'],dict) else summary['source_sha256'])==source_hash
        assert summary['external_http_calls']==0
        rows=read(path);assert len(rows)==summary['cases']
        for row in rows: compare(family,row['index'],row['axes'],row['results'],row['states'],row['model_calls'])
    goldens={}
    for path in sorted((OUT/'shipping-inherited').glob('*-cases.json.gz')):
        part=path.name.removesuffix('-cases.json.gz')
        data=read(path);summary=read(path.with_name(part+'-summary.json'))
        assert summary['source_sha256']['r32']==source_hash and summary['external_http_calls']==0
        archived_summary=read(OUT.parent/'c2a-r29/verified'/(part+'-summary.json'))
        assert archived_summary['source_sha256']['r29']==provenance['r29']['sha256']
        for index,row in enumerate(data['cases']):
            results={v:data['outcomes'][row['results'][v]] for v in ('r29','r32')}
            states={v:'w' if row['raw_wrong'][v] else 'c' if results[v]['fields'] else 'n' for v in results}
            compare('inherited/'+part,index,dict(group=row['group'],case=row['case']),results,states,row['model_calls'])
            if row['group']=='Seven goldens':
                goldens[row['case']]=versionless(results['r32'])==versionless(results['r29'])
        assert len(data['cases'])==summary['cases']
        for group,c in summary['groups'].items():
            if group=='Seven goldens': assert c['r32_golden_diffs']==c['r32_native_diffs']==0
    assert len(goldens)==7 and all(goldens.values()),goldens
    write('golden-audit.json',dict(cases=goldens,exact_except_analysis_version=True,native_fields_exact=True))
    for filename,data in [('every-n-to-p.json.gz',recoveries),('every-strict-wrong.json.gz',wrong_rows)]:
        with gzip.open(OUT/filename,'wt') as stream: json.dump(data,stream)
    write('family-comparison.json',families)
    totals=Counter()
    measurement=Counter()
    for family,c in families.items():
        (measurement if 'narrow_affiliate' in family else totals).update(c)
    write('release-bars.json',dict(head=head,source_sha256=source_hash,full_suite=counts,totals=totals,measurement_only=measurement,
        zero_new_wrong=totals['n_to_W']==totals['c_to_w']==0,zero_absolute_wrong=totals['r32_wrong']==0,
        all_old_tests_preserved=True,seven_goldens_exact=True,
        coder_rc=int(bool(counts['failed'] or counts['errors'] or counts['skipped'] or totals['r32_wrong'] or totals['n_to_W'] or totals['c_to_w']))))
    sizes={str(p.relative_to(ROOT)):p.stat().st_size for p in OUT.rglob('*') if p.is_file()}
    assert all(size<20_000_000 for size in sizes.values()),sorted(sizes.items(),key=lambda x:x[1])[-5:]
    write('evidence-size-audit.json',dict(limit_bytes=20_000_000,largest=sorted(sizes.items(),key=lambda x:x[1],reverse=True)[:10]))
    print(json.dumps(dict(full_suite=counts,totals=totals,goldens=len(goldens),preserved=len(start)-1),indent=2))


if __name__=='__main__': main()
