"""Audit r21b against both the r20 tracked tree and the incoming r21 candidate."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from r21b_replay import DUPLICATE_ROLE_GUARD


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PRODUCT = 'backend/dealroom_sign/placement.py'
TEST = 'backend/dealroom_sign/tests/test_placement_r20_boundaries.py'
RESULT = 'docs/implementation/c2a-r21/results-r21.md'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((OUT / name).read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')


def counts(name):
    statuses = Counter(passed=0, failed=0, errors=0, skipped=0)
    inventory = []
    for test in ET.parse(OUT / name).iter('testcase'):
        status = ('failed' if test.find('failure') is not None else
                  'errors' if test.find('error') is not None else
                  'skipped' if test.find('skipped') is not None else 'passed')
        statuses[status] += 1
        inventory.append(test.attrib['classname'] + '::' + test.attrib['name'])
    return dict(statuses), Counter(inventory)


def main():
    incoming = load('r21b-starting-state.json')
    tracked = load('starting-hashes.json')
    changed = [name for name, sha in incoming['hashes'].items()
               if not (ROOT / name).is_file() or digest(ROOT / name) != sha]
    tracked_changed = [name for name, sha in tracked.items()
                       if not (ROOT / name).is_file() or digest(ROOT / name) != sha]
    assert set(changed) <= {PRODUCT, TEST, RESULT}, changed
    assert set(tracked_changed) == {PRODUCT, TEST}, tracked_changed
    assert git('rev-parse', 'HEAD').strip() == incoming['head']
    assert git('ls-files', '-s') == incoming['index']
    before_test = git('show', incoming['head'] + ':' + TEST)
    original = "    assert placement.score(signer, target, {}, blocks) == (10 if control == 'printed_signer' else 4)\n"
    corrected = ("    assert placement.score(signer, target, {}, blocks) == (\n"
                 "        0 if control == 'different_page' else (10 if control == 'printed_signer' else 4))\n")
    assert before_test.count(original) == 1
    assert (ROOT / TEST).read_text() == before_test.replace(original, corrected)
    test_diff = git('diff', '--', TEST)
    (OUT / 'r21b-authorized-test.patch').write_text(test_diff)
    (OUT / 'r21b-production.patch').write_text(git('diff', '--', PRODUCT))
    source = (ROOT / PRODUCT).read_text()
    prior_source = (OUT / 'release-historical-r21.py.txt').read_text()
    assert prior_source.count('named = (not party_role_text(other.heading)') == 1
    expected_source = prior_source.replace('named = (not party_role_text(other.heading)',
                                            'named = (not party_role_text(other_heading)')
    anchor = '                    if not named and sum(not witness_block(b) for b in blocks) >= 3:\n'
    assert expected_source.count(anchor) == 1
    assert source == expected_source.replace(anchor, DUPLICATE_ROLE_GUARD + anchor)
    assert "VERSION = 'c2a.21'" in source
    source_hash = digest(ROOT / PRODUCT)
    preservation = {
        'incoming_files': len(incoming['hashes']), 'changed_since_r21': changed,
        'r20_tracked_files': len(tracked), 'changed_since_r20': tracked_changed,
        'all_other_hashes_match': True, 'authorized_test_diff_exact': True,
        'mapped_northwind_test_byte_identical': True,
        'head': incoming['head'], 'head_unchanged': True, 'index_unchanged': True,
        'production_sha256': source_hash,
        'r21_production_changes': ['classify resolved heading', 'hold duplicate named-role claims'],
    }
    write('r21b-preservation-summary.json', preservation)

    runs = {name: counts('r21b-' + name + '.xml')[0]
            for name in ('failing-first', 'targeted', 'duplicate-failing-first',
                         'alias-targeted', 'final-full-suite')}
    assert runs['alias-targeted'] == {'passed': 96, 'failed': 0, 'errors': 0, 'skipped': 0}
    assert runs['duplicate-failing-first'] == {'passed': 4, 'failed': 4, 'errors': 0, 'skipped': 0}
    aliases = load('r21b-final-alias-controls.json')
    assert aliases['source_sha256'] == source_hash and aliases['cases'] == 42
    assert aliases['failed'] == 0
    full, actual = counts('r21b-final-full-suite.xml')
    _, previous = counts('full-suite.xml')
    r20_ids = Counter(t.attrib['classname'] + '::' + t.attrib['name']
                      for t in ET.parse(OUT.parent / 'c2a-r20/full-suite.xml').iter('testcase'))
    assert not (previous - actual)
    additions = list((actual - previous).elements())
    assert len(additions) == 8 and all(
        name.startswith('dealroom_sign.tests.test_placement_r21b::') for name in additions)
    assert not (r20_ids - actual)
    assert full == {'passed': 23980, 'failed': 0, 'errors': 0, 'skipped': 0}, full
    write('r21b-test-runs-summary.json', runs)
    write('r21b-test-inventory-summary.json', {
        'r20': sum(r20_ids.values()), 'r21': sum(previous.values()),
        'r21b': sum(actual.values()), 'removed': [], 'added_since_r21': additions,
    })

    families, comparisons, total = {}, {}, 0
    for stem, prior in (('historical', 'release-historical'), ('review', 'release-review'),
                        ('layouts', 'release-layouts'), ('reviewer-layouts', 'reviewer-layouts')):
        summary = load('r21b-final-' + stem + '-summary.json')
        assert summary['source_sha256']['r21'] == source_hash
        assert summary['external_http_calls'] == 0
        total += summary['cases']
        families[stem] = summary['groups']
        assert all(g['r21_wrong'] == 0 for g in summary['groups'].values())
        current = load('r21b-final-' + stem + '-cases.json')
        old = load(prior + '-cases.json')
        old_rows = {(r['group'], r['case']): r for r in old['cases']}
        assert len(current['cases']) == len(old_rows)
        changed_rows = []
        for row in current['cases']:
            before = old_rows[(row['group'], row['case'])]
            before_result = old['outcomes'][before['results']['r21']]
            after_result = current['outcomes'][row['results']['r21']]
            if before_result != after_result:
                changed_rows.append({'group': row['group'], 'case': row['case'],
                                     'before_status': before_result['status'],
                                     'after_status': after_result['status']})
        comparisons[stem] = {'cases': summary['cases'], 'changed_results': changed_rows}
    assert total == 40924, total
    golden = families['historical']['Seven goldens']
    assert golden['r21_golden_diffs'] == golden['r21_native_diffs'] == 0
    assert families['review']['Competition']['r21_raw_wrong'] == 96
    assert families['review']['Q4 M1 ambiguity']['r21_raw_wrong'] == 6
    matrix = load('r21b-final-reviewer-layouts-summary.json')
    assert matrix['cases'] == 5280
    cross = matrix['cross_page_1800_subset']
    assert cross['cases'] == 1800 and cross['r21_wrong'] == 0
    write('r21b-family-comparison.json', comparisons)
    bars = {'qualified': True, 'full_suite': full, 'replay_inputs': total,
            'wrong': 0, 'goldens': 7, 'golden_diffs': 0, 'native_golden_diffs': 0,
            'matrix': 5280, 'cross_page_subset': cross, 'external_http_calls': 0,
            'preservation': preservation}
    write('r21b-release-bars.json', bars)
    print(json.dumps(bars, indent=2))


if __name__ == '__main__':
    main()
