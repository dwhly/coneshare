"""Measured-only proposals; none is imported by production or its tests."""


def replace_once(source, before, after):
    assert source.count(before) == 1, before
    return source.replace(before, after)


def candidates(source):
    # Keep the original direct recital grammar first. The additional grammar
    # permits bounded descriptive text after a legal company suffix.
    anchor = "                for match in ROLE_DEF.finditer(opening):"
    role = replace_once(source, anchor,
                        "                for match in (*ROLE_DEF.finditer(opening), *ROLE_DESCRIPTION.finditer(opening)):")
    role = replace_once(role, "STOP = {", r'''ROLE_DESCRIPTION = re.compile(
    r'(?:\b(?:between|and|by|with)\s+)'
    r'([A-Z][\w&.,\' -]{2,120}?\b(?:Inc\.?|INC\.?|LLC|Ltd\.?|LTD\.?|Corp\.?|Corporation|Co\.?))'
    r'(?:,\s*[^()]{0,400})?\s*\((?:hereinafter\s+)?(?:the\s+)?'
    r'["“\']([A-Z][A-Za-z ]{2,30})["”\']\)', re.M)
STOP = {''')

    # Only the shared-heading flag is bypassed. Earlier geometric, mixed-company
    # and raw-name vetoes remain set, and score still requires an exact name.
    l1 = replace_once(source,
                     "        if (block.line.page in unresolved_heading_pages\n",
                     "        printed, ambiguous = printed_name_evidence(block, blocks)\n"
                     "        if (block.line.page in unresolved_heading_pages and not (printed and not ambiguous)\n")

    # Use original scores before redaction; another named party must be
    # identified by some supplied signer. This can only remove domain credit.
    m1 = replace_once(source,
                     '    # Every score needs the original role labels, before output redaction.\n',
                     '''    original_scores = {id(block): list(block.scores) for block in blocks}
    for block in blocks:
        parties = [other for other in blocks
                   if other.line.page == block.line.page and not witness_block(other)]
        if len(parties) < 3 or printed_names(block, blocks):
            continue
        for index, signer in enumerate(signers):
            if signer.get('company') or block.scores[index] < 4:
                continue
            domain = signer['email'].split('@')[-1].split('.')[0].lower()
            for other in parties:
                if other is block or any(v >= 4 for v in original_scores[id(other)]):
                    continue
                heading = roles.get(other.heading.rstrip(': ').lower(), other.heading)
                heading = (behalf_parts(heading) or ('', heading))[1]
                named = (company_text(heading) and any(t not in STOP for t in tokens(heading))
                         or person_text(heading))
                if named and not similarity(domain, heading):
                    block.scores[index] = 0
                    break
    # Every score needs the original role labels, before output redaction.
''')
    return {'role_def': role, 'l1': l1, 'm1': m1}
