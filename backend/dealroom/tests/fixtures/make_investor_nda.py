"""Deterministic, fictional entry template, independent of the room's mutual NDA."""
from io import BytesIO
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas


def nda_bytes():
    output = BytesIO()
    pdf = Canvas(output, pagesize=(612, 792), invariant=True)
    pdf.setTitle('Investor NDA (fictional)')
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(48, 730, 'Investor Non-Disclosure Agreement')
    pdf.setFont('Helvetica', 11)
    for n, line in enumerate([
        'Fictional demonstration only. No real parties or legal effect.', '',
        'Harbor Light Analytics, Inc. (Discloser) and the recipient identified below',
        'wish to discuss a potential investment.', '',
        '1. Use. The recipient will use non-public information only to evaluate',
        '   this potential investment.',
        '2. Care. The recipient will protect the information with reasonable care',
        '   and share it only with advisers bound by confidentiality.',
        '3. Exclusions. Public, previously known and independently developed',
        '   information is excluded.',
        '4. Term. These obligations continue for two years after disclosure.',
    ]):
        pdf.drawString(48, 700 - n * 20, line)
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(48, 405, 'Discloser: Harbor Light Analytics, Inc.')
    pdf.setFont('Helvetica-Oblique', 16)
    pdf.drawString(48, 377, '/s/ Dan Whaley')
    pdf.setFont('Helvetica', 11)
    pdf.drawString(48, 358, 'Dan Whaley, CEO - pre-signed for this fictional demonstration')
    pdf.drawString(48, 340, 'Date: 17 November 2026')
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(48, 295, 'Recipient')
    pdf.setFont('Helvetica', 11)
    for label, y in [('Signature', 258), ('Name', 211), ('Company', 164), ('Date', 117)]:
        pdf.drawString(48, y, label + ':')
        pdf.line(125, y - 2, 490, y - 2)
    pdf.setFont('Helvetica', 9)
    pdf.drawString(48, 52, 'Fictional investor entry NDA | 1 / 1')
    pdf.save()
    return output.getvalue()


if __name__ == '__main__':
    Path(__file__).with_name('Investor NDA (fictional).pdf').write_bytes(nda_bytes())
