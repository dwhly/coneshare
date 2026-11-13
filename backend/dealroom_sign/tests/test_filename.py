from dealroom_sign.client import pdf_filename


def test_signed_file_is_named_after_the_agreement():
    assert pdf_filename('Advisor agreement - Jimmy (Nov 13 1746)') == 'Advisor agreement - Jimmy (Nov 13 1746).pdf'


def test_unsafe_characters_and_extension():
    assert pdf_filename('NDA: Acme/Beta <v2>.PDF') == 'NDA Acme Beta v2.pdf'
    assert pdf_filename('  ') == 'document.pdf'
    assert pdf_filename(None) == 'document.pdf'
    assert len(pdf_filename('x' * 400)) == 124
