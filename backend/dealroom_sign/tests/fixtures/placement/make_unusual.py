"""Reproducible fictional unusual-label golden (no document body goes to the model)."""
from pathlib import Path
from reportlab.pdfgen import canvas

out = Path(__file__).with_name('unusual.pdf')
c = canvas.Canvas(str(out), pagesize=(612, 792), invariant=True)
c.drawString(72, 720, 'PRIVATE BODY SENTINEL: commercial terms are not model input.')
c.drawString(72, 400, 'Lee Harbor, Harbor Light Analytics')
c.drawString(72, 350, 'Hand of the covenanting party:')
c.line(245, 348, 465, 348)
c.drawString(72, 310, 'Date:')
c.line(112, 308, 265, 308)
c.save()
