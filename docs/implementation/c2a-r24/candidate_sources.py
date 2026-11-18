"""Exact reviewer cand and cand3, plus the conditional cross-page competitor."""
import ast
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PRODUCT = 'backend/dealroom_sign/placement.py'


def sources():
    r21, r23 = [subprocess.check_output(['git', 'show', sha + ':' + PRODUCT], cwd=ROOT).decode()
                for sha in ('afb9aa6e', 'e2bbb758')]
    node = next(n for n in ast.parse(r21).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'ROLE_DESCRIPTION' for t in n.targets))
    wide = ast.get_source_segment(r21, node).replace('ROLE_DESCRIPTION =', 'ROLE_DESCRIPTION_WIDE =', 1)
    cand = r23.replace('STOP = {', '# Preserve r21 as a co-contributor: a bounded parse may start inside a party.\n' + wide + '\nSTOP = {', 1)
    cand = cand.replace('descriptions = ROLE_DESCRIPTION.finditer(opening)',
                        'descriptions = (*ROLE_DESCRIPTION.finditer(opening),\n'
                        '                                *ROLE_DESCRIPTION_WIDE.finditer(opening))', 1)
    page_filter = '                if other.line.page != block.line.page:\n                    continue\n'
    assert cand.count(page_filter) == 1
    cand3 = cand.replace(page_filter, '')
    narrow = cand.replace('        # Company-only identity must be unique on the page. Every matching\n'
                          '        # heading competes, even when a veto or geometry removes its score.\n'
                          '        if not value:\n',
                          '        # Matching headings compete on the page even if their score is vetoed.\n'
                          '        # An unaccounted party role also leaves cross-page ownership unresolved.\n'
                          '        if not value:\n'
                          '            unresolved_role = any(\n'
                          "                party_role_text(label['text']) and not accounted_label(label['text'], roles)\n"
                          '                for candidate in blocks for label in candidate.raw_labels)\n', 1)
    narrow = narrow.replace(page_filter, '                if other.line.page != block.line.page and not unresolved_role:\n                    continue\n')
    narrow = narrow.replace("VERSION = 'c2a.23'", "VERSION = 'c2a.24'")
    return dict(r21=r21, r23=r23, cand=cand, cand3=cand3, r24=narrow)
