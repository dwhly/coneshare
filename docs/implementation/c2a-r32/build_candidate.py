"""Create the widened-band-only candidate from the preserved r31 source."""
from pathlib import Path

OUT = Path(__file__).resolve().parent
source = (OUT / 'r31-source.py.txt').read_text()
source = source.replace("VERSION = 'c2a.31'", "VERSION = 'c2a.32'")
source = source.replace("            block.unclaimed_date_rule = any(\n", "            # Match extraction's 110-point floor for unlabelled signing rules;\n            # header rules above that floor are not unclaimed signing stacks.\n            block.unclaimed_date_rule = any(\n")
a = '''    for names, own_party in getattr(block, 'extended_date_names', ()):
'''
b = '''    def company_key(value):
        # Keep word boundaries and substantive words (including digits). Only
        # trailing legal suffixes fold; a domain is not an explicit company.
        parts = re.findall(r"[^\\W_]+(?:['’-][^\\W_]+)*", value.casefold())
        legal = {'inc', 'incorporated', 'llc', 'llp', 'ltd', 'limited', 'co',
                 'corp', 'corporation', 'company', 'gmbh', 'plc'}
        while parts and parts[-1] in legal:
            parts.pop()
        return tuple(parts)

    def heading_company(heading):
        heading = (behalf_parts(heading) or ('', heading))[1]
        key = heading.rstrip(': ').lower()
        return roles.get(key, roles.get(key.removeprefix('the '), heading))

    for names, own_party in getattr(block, 'extended_date_names', ()):
'''
assert source.count(a) == 1
source = source.replace(a, b)
a = '''            if not similarity(company, ' '.join(own_party)):
                return False
            mapped = {tuple(t for t in tokens(party) if t not in STOP)
                      for party in roles.values() if company_text(party)}
            if any(party != own_party and similarity(company, ' '.join(party))
                   for party in mapped):
                return False
'''
b = '''            explicit = company_key(signer.get('company') or '')
            heading = heading_company(block.heading)
            own_key = company_key(heading)
            mapped = {company_key(party): party for party in roles.values()
                      if company_text(party)}
            exact = bool(explicit and explicit == own_key)
            recital_owned = own_key in mapped and (
                explicit == own_key if explicit else similarity(company, mapped[own_key]))
            if not (exact or recital_owned):
                return False
            if any(party != own_key and similarity(company, value)
                   for party, value in mapped.items()):
                return False
'''
assert source.count(a) == 1
source = source.replace(a, b)
a = '''                if other is block or other.line.page != block.line.page or witness_block(other):
                    continue
                printed = printed_names(other, blocks)
'''
b = '''                if other is block or witness_block(other):
                    continue
                printed = printed_names(other, blocks)
                if other.line.page != block.line.page:
                    # A direct company heading is stronger than a mapped role;
                    # exact words are stronger than the general domain hint.
                    # Only unclaimed ruled blocks compete across pages here.
                    other_heading = heading_company(other.heading)
                    direct = (behalf_parts(block.heading) or ('', block.heading))[1]
                    other_exact = company_key(company) == company_key(other_heading)
                    own_exact = company_key(company) == company_key(direct)
                    if (not printed and other.line.kind == 'drawn'
                            and company_text(other_heading)
                            and similarity(company, other_heading)
                            and (other_exact and not own_exact
                                 or not similarity(company, direct))):
                        return False
                    continue
'''
assert source.count(a) == 1
source = source.replace(a, b)
(OUT / 'candidate-source.py.txt').write_text(source)
