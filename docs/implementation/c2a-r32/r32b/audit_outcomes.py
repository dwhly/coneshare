"""Audit preserved r32 matrices and freshly execute every changed live outcome."""
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET

OUT = Path(__file__).resolve().parent
EVIDENCE = OUT.parent
ROOT = EVIDENCE.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
sys.dont_write_bytecode = True
sys.path[:0] = [str(EVIDENCE), str(ROOT / 'backend')]
import measure32
from dealroom_sign.tests.test_placement import EXPECTED, FIXTURES, model_answer


def read(path):
    with (gzip.open(path, 'rt') if str(path).endswith('.gz') else path.open()) as stream:
        return json.load(stream)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def versionless(result):
    return {k: v for k, v in result.items() if k != 'analysis_version'}


def main():
    for key in ('OPENROUTER_API_KEY', 'PLACE_MODEL'):
        os.environ.pop(key, None)
    source_hash = sha(ROOT / PRODUCT)
    assert source_hash == sha(EVIDENCE / 'shipping-source.py.txt')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    provenance = read(EVIDENCE / 'source-provenance.json')
    assert head == provenance['r32']['head']
    for version in ('r29', 'r31'):
        original = subprocess.check_output(['git', 'show', provenance[version]['commit'] + ':' + PRODUCT], cwd=ROOT)
        assert original == (EVIDENCE / (version + '-source.py.txt')).read_bytes()
    assert provenance['r32']['sha256'] == source_hash

    families = {}
    changed = defaultdict(dict)
    flags = []

    def compare(family, index, axes, results, states, calls):
        counts = families.setdefault(family, Counter())
        counts['cells'] += 1
        for version in ('r29', 'r32'):
            counts[version + '_wrong'] += states[version] == 'w'
            counts[version + '_placed'] += bool(results[version]['fields'])
            counts[version + '_model_calls'] += calls[version]
        before, after = states['r29'], states['r32']
        counts['n_to_p'] += before == 'n' and after == 'c'
        counts['n_to_W'] += before == 'n' and after == 'w'
        counts['c_to_w'] += before == 'c' and after == 'w'
        counts['c_to_hold'] += before == 'c' and after == 'n'
        differs = versionless(results['r29']) != versionless(results['r32'])
        counts['changed_output'] += differs
        assert calls['r29'] == calls['r32'], (family, index, 'model calls')
        if differs:
            # This includes any changed w->w, w->n, or c->c, not just n->p.
            assert after != 'w', (family, index, 'changed outcome is wrong')
            changed[family][index] = dict(index=index, axes=axes, results=results,
                                         states=states, model_calls=calls)
        if after == 'w':
            counts['wrong_unchanged_from_live'] += not differs
            assert not differs, (family, index, 'oracle flag changed')
            flags.append(dict(family=family, index=index, axes=axes,
                              unchanged_from_live=True))

    for pattern, count in [('shipping-*-cases.json.gz', 18), ('rechecked-review-*-cases.json.gz', 8)]:
        paths = sorted(EVIDENCE.glob(pattern))
        assert len(paths) == count
        for path in paths:
            stem = path.name.removesuffix('-cases.json.gz')
            family = ('review/' + stem.removeprefix('shipping-') if stem.startswith('shipping-')
                      else 'prior/' + stem.removeprefix('rechecked-review-'))
            summary = read(path.with_name(stem + '-summary.json'))
            digest = summary['source_sha256']
            assert (digest.get('r32') if isinstance(digest, dict) else digest) == source_hash
            assert summary['external_http_calls'] == 0
            rows = read(path)
            assert len(rows) == summary['cases']
            for row in rows:
                compare(family, row['index'], row['axes'], row['results'], row['states'], row['model_calls'])
    inherited = sorted((EVIDENCE / 'shipping-inherited').glob('*-cases.json.gz'))
    assert len(inherited) == 27
    archived_goldens = {}
    for path in inherited:
        part = path.name.removesuffix('-cases.json.gz')
        data = read(path)
        summary = read(path.with_name(part + '-summary.json'))
        live = read(EVIDENCE.parent / 'c2a-r29/verified' / path.name)
        live_summary = read(EVIDENCE.parent / 'c2a-r29/verified' / (part + '-summary.json'))
        assert live_summary['source_sha256']['r29'] == provenance['r29']['sha256']
        live_rows = {(r['group'], r['case']): r for r in live['cases']}
        assert len(data['cases']) == summary['cases'] == len(live_rows)
        assert summary['source_sha256']['r32'] == source_hash and summary['external_http_calls'] == 0
        for index, row in enumerate(data['cases']):
            results = {v: data['outcomes'][row['results'][v]] for v in ('r29', 'r32')}
            old = live_rows[(row['group'], row['case'])]
            assert results['r29'] == live['outcomes'][old['results']['r29']]
            states = {v: 'w' if row['raw_wrong'][v] else 'c' if results[v]['fields'] else 'n' for v in results}
            compare('inherited/' + part, index, dict(group=row['group'], case=row['case']),
                    results, states, row['model_calls'])
            if row['group'] == 'Seven goldens':
                assert versionless(results['r32']) == versionless(results['r29'])
                archived_goldens[row['case']] = results
    assert families == read(EVIDENCE / 'family-comparison.json')
    assert len(archived_goldens) == 7
    assert all(not c['c_to_w'] and not c['n_to_W'] for c in families.values())
    totals, measurement = Counter(), Counter()
    for name, counts in families.items():
        (measurement if 'narrow_affiliate' in name else totals).update(counts)
    assert totals['r32_wrong'] == totals['wrong_unchanged_from_live'] == 876
    assert totals['changed_output'] == 2166
    write('family-comparison.json', families)
    write('unchanged-raw-flags.json', flags)
    print('Archived audit:', totals['cells'], 'release cells;', measurement['cells'], 'measurement cells', flush=True)

    recoveries = read(ROOT / 'backend/dealroom_sign/tests/fixtures/r30/date-first-recoveries.json')
    dates = {r['index']: r for r in read(EVIDENCE / 'shipping-date-cases.json.gz')}
    held = {int(i) for i in recoveries if dates[int(i)]['axes']['recital'] == 'none'
            and dates[int(i)]['axes']['signer'] in {'domain', 'both'}}
    retained = set(map(int, recoveries)) - held
    assert len(held) == 200 and len(retained) == 486
    old_failures = [case for case in ET.parse(EVIDENCE / 'shipping-full-suite-complete.xml').getroot().iter('testcase')
                    if case.find('failure') is not None]
    assert len(old_failures) == 200
    assert all(c.get('classname') == 'dealroom_sign.tests.test_placement_r30_recoveries' for c in old_failures)
    assert {int(c.get('name').split('[', 1)[1].split('-', 1)[0]) for c in old_failures} == held

    selected = {family: dict(rows) for family, rows in changed.items()}
    assert all(name.startswith('review/') for name in selected), selected.keys()
    selected['review/date'].update({i: dates[i] for i in held})
    fresh_rows = []
    http = Mock(side_effect=AssertionError('External HTTP forbidden'))
    goldens = {}
    with ExitStack() as stack:
        modules = {v: measure32.module('r32b_' + v, (EVIDENCE / (v + '-source.py.txt')).read_text()
                                      if v == 'r29' else (ROOT / PRODUCT).read_text()) for v in ('r29', 'r32')}
        for module in modules.values():
            extract = lru_cache(maxsize=12)(module.extract)
            stack.enter_context(patch.object(module, 'extract', lambda pdf, deadline=None, fn=extract: copy.deepcopy(fn(pdf))))
        stack.enter_context(patch('httpx.Client.send', http))
        render = lru_cache(maxsize=12)(lambda pages: measure32.r29.pdf(json.loads(pages)))
        for family, wanted in selected.items():
            seen = set()
            for index, (axes, pages, people, allowed) in enumerate(measure32.cells(family.removeprefix('review/'))):
                if index not in wanted:
                    continue
                archived = wanted[index]
                assert json.loads(json.dumps(axes)) == archived['axes'], (family, index, axes, archived['axes'])
                pdf = pages if isinstance(pages, bytes) else render(json.dumps(pages))
                results = {}
                for version, module in modules.items():
                    model = Mock()
                    result = measure32.in_process(module, pdf, people, model)
                    assert result == archived['results'][version], (family, index, version, 'fresh output differs')
                    assert model.call_count == archived['model_calls'][version]
                    assert not measure32.r29.rc.wrong_fields(result, allowed), (family, index, version)
                    results[version] = result
                if family == 'review/date':
                    if index in held:
                        assert results['r32']['status'] == 'needs_sender' and results['r32']['fields'] == []
                    else:
                        assert index in retained and results['r32']['status'] == 'placed'
                        assert versionless(results['r32']) == versionless(recoveries[str(index)])
                fresh_rows.append(dict(family=family, index=index, axes=axes,
                                       changed_from_live=index in changed[family], strict_wrong=False,
                                       fresh_matches_archive=True, results=results))
                seen.add(index)
            assert seen == set(wanted)
            print('Fresh', family, len(seen), flush=True)
        expected_goldens = read(EVIDENCE.parent / 'c2a-r13/placements.json')
        for name, metadata in EXPECTED['fixtures'].items():
            pdf = (FIXTURES / (name + '.pdf')).read_bytes()
            people = metadata['signers']
            results = {}
            for version, module in modules.items():
                model = Mock(side_effect=model_answer)
                result = measure32.in_process(module, pdf, people, model)
                assert model.call_count == int(name == 'unusual')
                assert result == archived_goldens[name][version]
                assert versionless(result) == versionless(expected_goldens[name])
                for person in people:
                    assert module.to_native_fields(result, person['email']) == module.to_native_fields(expected_goldens[name], person['email'])
                results[version] = result
            goldens[name] = dict(exact_except_analysis_version=True, native_fields_exact=True, results=results)
        http.assert_not_called()
    assert len(fresh_rows) == 2366 and len(goldens) == 7
    assert sum(r['changed_from_live'] for r in fresh_rows) == 2166
    assert sha(ROOT / PRODUCT) == source_hash
    with gzip.open(OUT / 'fresh-outcomes.json.gz', 'wt') as stream:
        json.dump(fresh_rows, stream)
    write('goldens.json', goldens)
    write('recovery-audit.json', dict(total=686, held=200, retained_exact=486,
          hold_indices=sorted(held), retained_indices=sorted(retained),
          hold_indices_equal_original_200_failures=True, strict_wrong=0, fresh_execution=True))
    write('outcome-audit.json', dict(head=head, source_sha256=source_hash,
          production_unchanged_since_r32=True, release=totals, measurement_only=measurement,
          fresh_changed_cells=2166, fresh_authorised_holds=200, fresh_goldens=7,
          strict_wrong_on_every_changed_outcome=0, external_http_calls=0,
          model_calls_equal_live=True, all_family_transitions_safe=True))
    print('Outcome audit complete: 2166 fresh changed cells; 200 fresh holds; seven exact goldens.', flush=True)


if __name__ == '__main__':
    main()
