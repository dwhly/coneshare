"""Rebuild the fictional Harbor Light snapshot. No company data or network access."""
import json
from io import BytesIO
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from openpyxl import Workbook

ROOT = Path(__file__).parent / 'drive' / 'harbor-light'
ROOT.mkdir(parents=True, exist_ok=True)
PDF = 'application/pdf'
SHEET = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
DOC = 'application/vnd.google-apps.document'
GSHEET = 'application/vnd.google-apps.spreadsheet'
nodes = []
for id, name in [('company', '01 Company'), ('financials', 'Financials'), ('legal', 'Legal'), ('product', 'Product')]:
    nodes.append(dict(id=id, name=name, mimeType='application/vnd.google-apps.folder', parents=['harbor-light'], modifiedTime='2026-11-17T09:00:00Z', webViewLink=f'https://drive.google.com/drive/folders/{id}', path=None, exportedMimeType=None))
for id, title, parent, mime in [
    ('overview', 'Company overview', 'company', DOC),
    ('deck', 'Pitch deck.pdf', 'company', PDF),
    ('model', 'Financial model FY26-FY29', 'financials', GSHEET),
    ('pnl', 'Monthly P&L 2026.xlsx', 'financials', SHEET),
    ('incorporation', 'Certificate of incorporation.pdf', 'legal', PDF),
    ('cap', 'Cap table', 'legal', GSHEET),
    ('nda', 'Mutual NDA.pdf', 'legal', PDF),
    ('roadmap', 'Product roadmap 2027', 'product', DOC),
    ('security', 'Security overview.pdf', 'product', PDF),
    ('customers', 'Customer list - top 10', 'harbor-light', GSHEET),
    ('notes', 'Notes for investors - draft', 'harbor-light', DOC),
    ('board', 'Board deck Q3 2026.pdf', 'harbor-light', PDF),
]:
    sheet = mime in (GSHEET, SHEET)
    path = f'{id}.xlsx' if sheet else f'{id}.pdf'
    if sheet:
        workbook = Workbook()
        ws = workbook.active
        ws.title = 'Fictional example'
        ws.append([title, 'FY26', 'FY27', 'FY28', 'FY29'])
        ws.append(['Revenue ($m)', 4.1, 9.8, 18.6, 31.2])
        ws.append(['Gross margin', .61, .64, .68, .72])
        ws.append(['Fictional demo data only'])
        workbook.save(ROOT / path)
    else:
        out = BytesIO()
        canvas = Canvas(out, pagesize=(612, 792), invariant=True)
        for p in range(6 if id == 'deck' else 2 if id == 'nda' else 1):
            canvas.setFont('Helvetica-Bold', 24)
            canvas.drawString(48, 720, 'Harbor Light Analytics')
            canvas.setFont('Helvetica', 16)
            canvas.drawString(48, 680, title)
            canvas.setFont('Helvetica', 11)
            for n, line in enumerate(['Series A - fictional demonstration', 'Prepared for an investor conversation.', 'No real company information appears in this document.', '', f'Page {p + 1}']):
                canvas.drawString(48, 620 - 22 * n, line)
            canvas.showPage()
        canvas.save()
        (ROOT / path).write_bytes(out.getvalue())
    nodes.append(dict(id=id, name=title, mimeType=mime, parents=[parent], modifiedTime='2026-11-17T09:00:00Z', webViewLink=f'https://drive.google.com/file/d/{id}/view', path=path, exportedMimeType=SHEET if sheet else PDF))
(ROOT / 'manifest.json').write_text(json.dumps(dict(root_id='harbor-light', root_name='TEST (fictional) Harbor Light Analytics - Series A data room', taken_at='2026-11-17T09:00:00Z', nodes=nodes), indent=2) + '\n')
