"""Run the preserved r21 harnesses with the manager's narrow alias correction.

The existing generators, oracles, variants and evidence remain unchanged.
New output uses an r21b prefix; only B-2's resolved-heading check changes.
"""
import os
from pathlib import Path
import runpy
import subprocess
import sys

import variants


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
original_variants = variants.variants
DUPLICATE_ROLE_GUARD = '''                    # A named role still needs one unclaimed signing block.
                    # Two blocks for its company leave the role assignment
                    # unresolved unless a printed person distinguishes them.
                    if named and party_role_text(other.heading):
                        for peer in blocks:
                            if (peer is other or witness_block(peer)
                                    or printed_names(peer, blocks)):
                                continue
                            peer_heading = roles.get(peer.heading.rstrip(': ').lower(), peer.heading)
                            peer_heading = (behalf_parts(peer_heading) or ('', peer_heading))[1]
                            if similarity(other_heading, peer_heading):
                                return value
'''


def corrected_variants(source):
    sources = original_variants(source)
    for name in ('b2', 'role_def', 'r21'):
        sources[name] = variants.replace_once(
            sources[name],
            '                    named = (not party_role_text(other.heading)\n',
            '                    named = (not party_role_text(other_heading)\n')
        anchor = '                    if not named and sum(not witness_block(b) for b in blocks) >= 3:\n'
        sources[name] = variants.replace_once(sources[name], anchor, DUPLICATE_ROLE_GUARD + anchor)
    assert sources['r21'] == (ROOT / 'backend/dealroom_sign/placement.py').read_text()
    return sources


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    part = sys.argv[1]
    assert part in {'historical', 'review', 'layouts', 'reviewer'}
    variants.variants = corrected_variants
    baseline = subprocess.check_output([
        'git', 'show', 'e0ed35e7:backend/dealroom_sign/placement.py'], cwd=ROOT).decode()
    corrected_variants(baseline)
    os.environ['R21_RUN_PREFIX'] = 'r21b-final-reviewer-' if part == 'reviewer' else 'r21b-final-'
    script = ('check_evidence.py' if part in {'historical', 'review'} else
              'check_reviewer_matrix.py' if part == 'reviewer' else 'check_layouts.py')
    sys.argv = [str(OUT / script), part]
    runpy.run_path(str(OUT / script), run_name='__main__')
