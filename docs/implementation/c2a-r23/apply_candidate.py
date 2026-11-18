"""Apply only the review's measured cand plus the release version."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
p = ROOT / 'backend/dealroom_sign/placement.py'
s = p.read_text()
assert s == Path(__file__).with_name('baseline-placement.py.txt').read_text()
stop = """# A conjunction starts a new party only after a completed designation.
# Company names and descriptive phrases may themselves contain 'and'.
PARTY_JOIN_STOP = (
    r'(?!(?:(?<=Inc)|(?<=Inc\\.)|(?<=INC)|(?<=INC\\.)|(?<=LLC)|(?<=LLP)'
    r'|(?<=Ltd)|(?<=Ltd\\.)|(?<=LTD)|(?<=LTD\\.)|(?<=Corp)|(?<=Corp\\.)'
    r'|(?<=Co)|(?<=Co\\.)|(?<=CO)|(?<=CO\\.)|(?<=Corporation)|(?<=corporation)'
    r'|(?<=company)|(?<=partnership))\\s*,?\\s+and\\s+[A-Z])')
"""
s = s.replace('ROLE_DESCRIPTION = re.compile(', stop + 'ROLE_DESCRIPTION = re.compile(')
s = s.replace("    r'([A-Z](?:(?!,?\\s+and\\s+[A-Z])[\\w&.,\\' -]){2,120}?\\b(?:Inc\\.?|INC\\.?|LLC|Ltd\\.?|LTD\\.?|Corp\\.?|Corporation|Co\\.?))'", "    r'([A-Z](?:' + PARTY_JOIN_STOP + r'[\\w&.,\\' -]){2,120}?\\b(?:Inc\\.?|INC\\.?|LLC|Ltd\\.?|LTD\\.?|Corp\\.?|Corporation|Co\\.?))'")
s = s.replace("    r'(?:,\\s*(?:(?!,?\\s+and\\s+[A-Z])[^()]){0,400})?\\s*\\((?:hereinafter\\s+)?(?:the\\s+)?'", "    r'(?:,\\s*(?:' + PARTY_JOIN_STOP + r'[^()]){0,400})?\\s*\\((?:hereinafter\\s+)?(?:the\\s+)?'")
a = s.index('                # Both grammars may reach')
b = s.index('                for match in', a)
s = s[:a] + """                # A lazy direct definition can match a description's tail.
                # Let both grammars contribute; disagreement retains the hold.
                descriptions = ROLE_DESCRIPTION.finditer(opening)
""" + s[b:]
s = s.replace("VERSION = 'c2a.22'", "VERSION = 'c2a.23'")
assert s.count('PARTY_JOIN_STOP') == 3
assert 'defined_roles' not in s
assert '(?!,?\\s+and\\s+[A-Z])' not in s
p.write_text(s)
