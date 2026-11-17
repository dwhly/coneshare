"""Document-wide unnamed roles cannot select a domain-matching affiliate."""
from itertools import product
from unittest.mock import Mock

import pytest

from dealroom_sign import placement
from dealroom_sign.tests.placement_r21_review_cases import (
    ROLE_WORDS, cross_page_cases, layout_pages, matrix_cases, pages_pdf, wrong_fields,
)
from dealroom_sign.tests.test_placement import no_network  # noqa: F401
from dealroom_sign.tests.test_placement_r14 import in_process
from dealroom_sign.tests.test_placement_r17 import signers


def check(pages, both, allowed, worker=False):
    pdf, model = pages_pdf(pages), Mock()
    result = in_process(placement, pdf, signers(both), model)
    assert not wrong_fields(result, allowed), result
    assert result['status'] in {'placed', 'needs_sender'}, result
    if result['status'] == 'needs_sender':
        assert result['fields'] == []
    if worker:
        assert placement.place(pdf, signers(both), model_client=model) == result
    model.assert_not_called()
    return result


@pytest.mark.parametrize('args,pages,both,allowed', list(cross_page_cases()))
def test_document_wide_unnamed_party(args, pages, both, allowed):
    check(pages, both, allowed)


@pytest.mark.parametrize('args,pages,both,allowed', list(matrix_cases()))
def test_review_layout_matrix(args, pages, both, allowed):
    check(pages, both, allowed)


@pytest.mark.parametrize('layout,both,extra', product(
    ('same', 'guarantor', 'split'), (False, True), ('placeholders', 'printed')))
def test_recipient_heading_and_own_printed_name(layout, both, extra):
    pages, allowed = layout_pages(layout, extra=extra)
    result = check(pages, both, allowed, worker=True)
    if extra == 'printed':
        assert result['status'] == 'placed', result


@pytest.mark.parametrize('word,plural,leading', product(ROLE_WORDS, (False, True), ('', 'THE ')))
def test_party_role_words_are_not_printed_people(word, plural, leading):
    if plural:
        word = word[:-1] + 'ies' if word.endswith('y') else word + 's'
    text = leading + word.upper()
    assert placement.person_text(text) == ''
    pages, allowed = layout_pages(heading=text)
    check(pages, False, allowed)


@pytest.mark.parametrize('text', ['THE RECIPIENT SELLER', 'BUYERS SELLERS',
                                'THE EMPLOYERS EMPLOYEES', 'THE PARTIES'])
def test_combined_party_roles_are_not_people(text):
    assert placement.person_text(text) == ''


@pytest.mark.parametrize('text', ['Pat Smith', 'Chris Jones', 'Recipient Jones', 'The Smith'])
def test_role_vocabulary_does_not_erase_person_names(text):
    assert placement.person_text(text) == text


@pytest.mark.parametrize('recital', ['address', 'hereinafter'])
def test_descriptive_role_definition_maps_legal_entity(recital):
    pages, _ = layout_pages(recital=recital, heading='RECIPIENT:')
    _, _, roles = placement.extract(pages_pdf(pages))
    assert placement.tokens(roles['recipient']) == ['harbor', 'light', 'analytics', 'inc']
