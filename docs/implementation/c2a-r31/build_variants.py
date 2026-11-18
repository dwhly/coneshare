"""Build review suggestion and peer-guard variants without modifying r30."""
from pathlib import Path

OUT = Path(__file__).resolve().parent
source = (OUT/'r30-source.py.txt').read_text()
source = source.replace("VERSION = 'c2a.30'", "VERSION = 'c2a.31'")
source = source.replace('    printed_name_blocked: bool = False\n',
    '    printed_name_blocked: bool = False\n    extended_date_names: list = field(default_factory=list, repr=False)\n')
source = source.replace('''            if date.y < y0 - band:
                return True
''', '''            if date.y < y0 - band:
                return True
            block.extended_date_names.append((names, own_party))
''')
source = source.replace('''    for block in blocks:
        block.scores = [score(s, block, roles, blocks) for s in signers]
''', '''    for block in blocks:
        if not extended_date_names_owned(block, blocks, roles, signers):
            block.printed_name_blocked = True
        block.scores = [score(s, block, roles, blocks) for s in signers]
''')
helper = '''def extended_date_names_owned(block, blocks, roles, signers):
    """Require party ownership before a name can cross the 22-point Date band."""
    for names, own_party in getattr(block, 'extended_date_names', ()):
        matched = [s for s in signers if tokens(s.get('name', '')) in names]
        if not own_party or not matched:
            return False
        for signer in matched:
            domain = signer['email'].split('@')[-1].split('.')[0].lower()
            company = signer.get('company') or (domain if domain not in GENERIC_DOMAINS else '')
            if not similarity(company, ' '.join(own_party)):
                return False
            # PEER_GUARD
    return True


'''
source = source.replace('def prepare_blocks(blocks, roles, signers):', helper+'def prepare_blocks(blocks, roles, signers):')
(OUT/'suggestion-source.py.txt').write_text(source)
peer = '''for other in blocks:
                if other is block or other.line.page != block.line.page or witness_block(other):
                    continue
                printed = printed_names(other, blocks)
                if printed:
                    if any(name in printed for name in names):
                        return False
                    continue
                heading = (behalf_parts(other.heading) or ('', other.heading))[1]
                key = heading.rstrip(': ').lower()
                heading = roles.get(key, roles.get(key.removeprefix('the '), heading))
                if not company_text(heading) or similarity(company, heading):
                    return False
            if any(not printed or any(name in printed for name in names)
                   for printed in block.unclaimed_signing_peers):
                return False'''
source = source.replace('# PEER_GUARD',peer)
(OUT/'guarded-source.py.txt').write_text(source)
