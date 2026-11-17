import { useEffect, useRef, useState } from 'react';
import { Check, ChevronLeft, ChevronRight, Grip, Plus, Trash2, Upload } from 'lucide-react';
import api from '../../services/api';
import { usePdfDocument } from '../../hooks/usePdfDocument';
import { PdfPage } from '../documents/PdfPage';
import { Card, SelectMenu, StatusPill, errorText } from './shell';

const TYPES = { SIGNATURE: 'Signature', NAME: 'Name', TEXT: 'Company', DATE: 'Date', INITIALS: 'Initials' };
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

export function NdaPlacement({ policy, onConfirm, busy }) {
  const [fields, setFields] = useState(() => (policy.confirmed ? policy.fields : policy.suggestions || []).map(f => ({ ...f })));
  const [page, setPage] = useState(fields[0]?.page || 1);
  const [selected, setSelected] = useState(0);
  const [changed, setChanged] = useState(false);
  const [container, setContainer] = useState(null);
  const [width, setWidth] = useState(612);
  const pageRef = useRef(null);
  const gesture = useRef(null);
  const { pdfDoc, numPages, pageDimensions, loading, error } = usePdfDocument(policy.pdf_url);
  const dimensions = pageDimensions[page - 1] || { width: 612, height: 792 };
  useEffect(() => {
    if (!container) return;
    const measure = () => setWidth(container.clientWidth || 612);
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(measure); observer.observe(container);
    return () => observer.disconnect();
  }, [container]);
  function update(index, patch) {
    setChanged(true);
    setFields(current => current.map((f, i) => i === index ? { ...f, ...patch } : f));
  }
  function begin(e, index, resize) {
    if (busy) return;
    e.preventDefault(); e.stopPropagation(); setSelected(index);
    const rect = pageRef.current.getBoundingClientRect();
    gesture.current = { index, resize, field: fields[index], x: e.clientX, y: e.clientY, rect };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }
  function move(e) {
    const g = gesture.current;
    if (!g || !g.rect.width || !g.rect.height) return;
    const dx = (e.clientX - g.x) / g.rect.width * 100;
    const dy = (e.clientY - g.y) / g.rect.height * 100;
    const f = g.field;
    update(g.index, g.resize ? { width: clamp(f.width + dx, 1, 100 - f.positionX), height: clamp(f.height + dy, 1, 100 - f.positionY) }
      : { positionX: clamp(f.positionX + dx, 0, 100 - f.width), positionY: clamp(f.positionY + dy, 0, 100 - f.height) });
  }
  function key(e, index, resize = false) {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) return;
    e.preventDefault(); const f = fields[index]; const step = e.shiftKey ? 1 : 0.25;
    const dx = e.key === 'ArrowLeft' ? -step : e.key === 'ArrowRight' ? step : 0;
    const dy = e.key === 'ArrowUp' ? -step : e.key === 'ArrowDown' ? step : 0;
    update(index, resize ? { width: clamp(f.width + dx, 1, 100 - f.positionX), height: clamp(f.height + dy, 1, 100 - f.positionY) }
      : { positionX: clamp(f.positionX + dx, 0, 100 - f.width), positionY: clamp(f.positionY + dy, 0, 100 - f.height) });
  }
  return <section aria-label="NDA field placement" className="space-y-4 max-w-4xl mx-auto scroll-mt-20">
    <div className="flex flex-wrap gap-3 items-center justify-between"><div><h3 className="font-semibold text-lg">Place the visitor’s fields</h3><p className="text-sm text-muted-foreground mt-1">{policy.name}</p></div><StatusPill tone="warning">{changed ? 'Edited — check' : 'Suggested — check'}</StatusPill></div>
    <p className="text-sm text-muted-foreground">Check the blank recipient block. Drag a box to move it, or drag its corner to resize. Arrow keys also work. These positions apply to every visitor after you confirm.</p>
    {!fields.length && <p role="status" className="text-sm">No clear blank recipient block was found. Add fields below and place them on the page.</p>}
    <div className="flex flex-wrap gap-2" aria-label="Field palette">{Object.entries(TYPES).map(([type, label]) => <button key={type} className="dr-btn" disabled={busy} aria-label={`Add ${label}`} onClick={() => { setFields([...fields, { type, page, positionX: 20, positionY: 40, width: 35, height: 4, identifier: 0 }]); setSelected(fields.length); setChanged(true); }}><Plus />{label}</button>)}</div>
    <div className="grid lg:grid-cols-[minmax(0,1fr)_220px] gap-5 items-start">
      <div className="min-w-0">
        <div className="flex items-center justify-between mb-3"><button className="dr-btn" aria-label="Previous NDA page" disabled={page <= 1 || busy} onClick={() => setPage(page - 1)}><ChevronLeft /></button><span className="text-sm">Page {page} of {numPages || 1}</span><button className="dr-btn" aria-label="Next NDA page" disabled={page >= numPages || busy} onClick={() => setPage(page + 1)}><ChevronRight /></button></div>
        {loading && <p role="status">Loading NDA…</p>}{error && <p role="alert" className="text-sm text-red-700">Couldn’t load the NDA. Reload the page to try again.</p>}
        <div ref={setContainer} className="w-full max-w-[480px] mx-auto bg-muted rounded-lg">
          <div ref={pageRef} data-testid="nda-page" className="relative mx-auto bg-white" style={{ aspectRatio: `${dimensions.width} / ${dimensions.height}`, containerType: 'inline-size' }}>
            <PdfPage pdfDoc={pdfDoc} pageNumber={page} scale={width / dimensions.width} dimensions={dimensions} scrollContainer={container} />
            {fields.map((f, i) => f.page === page && <div key={i} className={`absolute border-2 ${selected === i ? 'border-blue-600 bg-blue-100/60' : 'border-amber-600 bg-amber-100/50'}`} style={{ left: `${f.positionX}%`, top: `${f.positionY}%`, width: `${f.width}%`, height: `${f.height}%` }}>
              <button className="absolute inset-0 w-full h-full text-left leading-none font-medium overflow-hidden touch-none cursor-move px-1 text-gray-900" style={{ fontSize: 'clamp(6px, 1.8cqw, 12px)' }} disabled={busy} aria-label={`Move ${TYPES[f.type]} field ${i + 1}`} onFocus={() => setSelected(i)} onPointerDown={e => begin(e, i, false)} onPointerMove={move} onPointerUp={() => { gesture.current = null; }} onPointerCancel={() => { gesture.current = null; }} onKeyDown={e => key(e, i)}>{i + 1}. {TYPES[f.type]}</button>
              <button className="absolute -bottom-2 -right-2 w-5 h-5 rounded bg-white border border-blue-600 touch-none cursor-se-resize flex items-center justify-center" disabled={busy} title={`Resize ${TYPES[f.type]} field ${i + 1}`} aria-label={`Resize ${TYPES[f.type]} field ${i + 1}`} onPointerDown={e => begin(e, i, true)} onPointerMove={move} onPointerUp={() => { gesture.current = null; }} onPointerCancel={() => { gesture.current = null; }} onKeyDown={e => key(e, i, true)}><Grip className="w-3 h-3" /></button>
            </div>)}
          </div>
        </div>
      </div>
      <div className="space-y-3"><h4 className="font-medium text-sm">Visitor fields · {fields.length}</h4><p className="text-xs text-muted-foreground">Name and company use invitation details when known. The visitor can edit them.</p>{fields.map((f, i) => <div key={i} className={`border rounded-lg p-3 ${selected === i ? 'border-blue-500' : ''}`}><div className="flex items-center gap-2"><button className="text-sm font-medium flex-1 text-left" onClick={() => { setSelected(i); setPage(f.page); }}>{i + 1}. {TYPES[f.type]}<span className="block font-normal text-xs text-muted-foreground">Page {f.page}</span></button><button className="dr-btn" disabled={busy} title={`Delete ${TYPES[f.type]} field ${i + 1}`} aria-label={`Delete ${TYPES[f.type]} field ${i + 1}`} onClick={() => { setFields(fields.filter((_, n) => n !== i)); setChanged(true); }}><Trash2 /></button></div></div>)}</div>
    </div>
    <div className="sticky bottom-0 z-10 border-t bg-white py-4 flex flex-wrap gap-3 items-center justify-between"><p className="text-xs text-muted-foreground">Check every box before sharing.</p><button className="dr-btn dr-btn--primary" disabled={busy || Boolean(error) || loading || !fields.some(f => f.type === 'SIGNATURE')} onClick={() => onConfirm(fields)}><Check />{busy ? 'Saving…' : 'Use these positions'}</button></div>
  </section>;
}

export default function EntryNda({ roomId, documents = [], onRefresh }) {
  const [policy, setPolicy] = useState(null);
  const [chosen, setChosen] = useState('');
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const base = `/dealroom/rooms/${roomId}/entry-nda/`;
  useEffect(() => { let live = true; api.get(base).then(({ data }) => { if (live) setPolicy(data); }).catch(e => { if (live) setError(errorText(e)); }); return () => { live = false; }; }, [base]);
  async function run(fn) { setBusy(true); setError(''); try { await fn(); } catch (e) { setError(errorText(e)); } finally { setBusy(false); } }
  return <Card title="Entry NDA" subtitle="A separate agreement for visitors entering this room. Place its fields once, then every visitor signs in the same places.">
    <div className="space-y-5">
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-[auto_minmax(0,1fr)_auto] items-end">
        <label className="dr-btn cursor-pointer w-fit"><Upload />Upload PDF<input aria-label="Upload entry NDA PDF" className="sr-only" type="file" accept="application/pdf,.pdf" disabled={busy} onChange={e => { const file = e.target.files[0]; e.target.value = ''; if (file) run(async () => { const form = new FormData(); form.append('file', file); const { data } = await api.post(base, form); setPolicy(data); setEditing(false); await onRefresh(); }); }} /></label>
        <div className="min-w-0"><SelectMenu label="Or choose a room PDF" value={chosen} onChange={setChosen} options={documents.filter(d => d.name.toLowerCase().endsWith('.pdf')).map(d => ({ value: d.id, label: d.name }))} placeholder="Choose a document" /></div>
        <button className="dr-btn" disabled={!chosen || busy} onClick={() => run(async () => { const doc = documents.find(d => d.id === chosen); await api.put(`/dealroom-sign/nda-policy/${roomId}/`, { version_id: doc.version_id, enabled: true }); setPolicy((await api.get(base)).data); setEditing(false); await onRefresh(); })}>Use this PDF</button>
      </div>
      <p className="text-xs text-muted-foreground">Changing the PDF clears its field confirmation. Uploaded entry NDAs stay separate from room content.</p>
      {policy?.confirmed && !editing ? <div className="rounded-xl border p-5 space-y-3"><StatusPill tone="success">Positions confirmed</StatusPill><p className="font-medium text-sm">{policy.name}</p><p className="text-sm text-muted-foreground">{policy.fields.length} fields ready for every visitor. You can now share the room.</p><button className="dr-btn" onClick={() => setEditing(true)}>Edit positions</button></div> : policy?.source_version_id ? <NdaPlacement key={`${policy.source_version_id}:${policy.revision}`} policy={policy} busy={busy} onConfirm={fields => run(async () => { const { data } = await api.put(`/dealroom-sign/nda-policy/${roomId}/`, { version_id: policy.source_version_id, revision: policy.revision, enabled: true, fields, confirm: true }); setPolicy(data); setEditing(false); await onRefresh(); })} /> : <p className="text-sm text-muted-foreground">Upload or choose a PDF to place the NDA fields.</p>}
    </div>
  </Card>;
}
