"""Attributable fictional NDA for the seeded Maya/Northwind visitor."""
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas


def nda_bytes():
    output = BytesIO()
    pdf = Canvas(output, pagesize=(612, 792), invariant=True)
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(48, 720, 'Mutual Non-Disclosure Agreement')
    pdf.setFont('Helvetica', 11)
    lines = [
        'Harbor Light Analytics and Northwind Ventures',
        'Fictional demonstration only.', '',
        '1. Purpose. The parties wish to explore a potential investment.',
        '2. Confidential information includes non-public materials shared for that purpose.',
        '3. Each party will protect the information and use it only for that purpose.',
        '4. Public, previously known and independently developed information is excluded.',
        '5. These obligations continue for two years after disclosure.',
    ]
    for n, line in enumerate(lines):
        pdf.drawString(48, 674 - n * 26, line)
    pdf.showPage()
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(72, 720, 'Signatures')
    for company, name, y in [('Harbor Light Analytics', 'Dan Whaley, CEO', 620),
                              ('Northwind Ventures LLC', 'Maya Chen, Partner', 440)]:
        pdf.setFont('Helvetica-Bold', 13)
        pdf.drawString(72, y, company)
        pdf.line(72, y - 64, 288, y - 64)
        pdf.setFont('Helvetica', 11)
        pdf.drawString(72, y - 76, 'Name / title: ' + name)
        pdf.drawString(331.2, y - 76, 'Date: ____________')
    pdf.save()
    return output.getvalue()


if __name__ == '__main__':
    (Path(__file__).parent / 'drive/harbor-light/nda.pdf').write_bytes(nda_bytes())
