import { useState } from 'react';
import { Folder, ArrowLeft, Check, CloudDownload } from 'lucide-react';
import api from '../../services/api';
import { Card, StatusPill, SelectMenu, errorText } from './shell';
import { FileTypeIcon } from '../documents/FileTypeIcon';

export function ImportReview({ review, choices, onChange, onConfirm, busy }) {
  const definitions = review.slot_definitions || {};
  const files = review.nodes.filter(n => n.type === 'file');
  const assigned = Object.values(choices).filter(Boolean);
  const missing = Object.values(definitions).filter(s => !assigned.includes(s.id));
  const duplicate = new Set(assigned).size !== assigned.length;
  function row(file) {
    return <div key={file.id} draggable onDragStart={e => e.dataTransfer.setData('text/plain', file.id)} className="flex flex-wrap items-center gap-3 border-t border-gray-100 py-4">
      <FileTypeIcon type={file.mimeType === 'application/vnd.google-apps.document' ? 'pdf' : file.mimeType} />
      <div className="flex-1 min-w-48"><strong className="text-sm">{file.name}</strong><p className="text-xs text-muted-foreground mt-1">{file.folder_path || 'Top level'} · {file.mimeType?.startsWith('application/vnd.google-apps.') ? 'Fixed exported snapshot' : 'Original file'}</p></div>
      {review.template && <div className="w-full sm:w-60"><SelectMenu label={`Place ${file.name}`} value={choices[file.id] || ''} onChange={slot => onChange({ ...choices, [file.id]: slot })} options={[{ value: '', label: 'Keep in its Drive folder' }, ...Object.values(definitions).map(s => ({ value: s.id, label: s.name }))]} /></div>}
    </div>;
  }
  return <div className="space-y-5">
    <div><h2 className="text-xl font-semibold">Review your import</h2><p className="text-sm text-muted-foreground mt-2">{files.length} files from {review.roots.map(r => r.name).join(', ')}. Nothing is in the room until you confirm.</p></div>
    {review.template ? <>
      <Card title={`Matched · ${files.filter(f => choices[f.id]).length}`} subtitle="Check the placements. Drag a file to a missing slot, or choose a slot from its menu.">{files.filter(f => choices[f.id]).map(row)}</Card>
      <Card title={`Unsure · ${files.filter(f => !choices[f.id]).length}`} subtitle="These stay in their Drive folders unless you choose a slot.">{files.filter(f => !choices[f.id]).map(row)}{files.every(f => choices[f.id]) && <p className="text-sm text-muted-foreground">Everything has a place.</p>}</Card>
      <Card title={`Missing · ${missing.length}`} subtitle="You can add these later. Visitors never see empty slots."><div className="grid sm:grid-cols-2 gap-3">{missing.map(slot => <div key={slot.id} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); const id = e.dataTransfer.getData('text/plain'); if (files.some(f => f.id === id)) onChange({ ...choices, [id]: slot.id }); }} className="rounded-xl border border-dashed border-gray-300 p-4 text-sm"><StatusPill tone="warning">Missing</StatusPill><p className="font-medium mt-2">{slot.name}</p></div>)}</div></Card>
    </> : <Card title="Your Drive folders, kept as they are" subtitle="Docs become PDFs, Sheets become Excel files, Slides become PowerPoint files.">{review.nodes.filter(n => n.type === 'folder').map(f => <p key={f.id} className="flex gap-2 text-sm font-medium py-2"><Folder className="h-4 w-4" />{[f.folder_path, f.name].filter(Boolean).join(' / ')}</p>)}{files.map(row)}</Card>}
    {duplicate && <p role="alert" className="text-sm text-amber-700">Two files share a slot. Choose a different slot or keep one in its Drive folder.</p>}
    <button className="dr-btn dr-btn--primary" disabled={busy || duplicate} onClick={onConfirm}><Check />{busy ? 'Importing files…' : `Confirm and import ${files.length} files`}</button>
  </div>;
}

export default function DriveImport({ roomId, definitions, onImported, onClose }) {
  const [links, setLinks] = useState('');
  const [template, setTemplate] = useState('');
  const [review, setReview] = useState(null);
  const [choices, setChoices] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function run(fn) { setBusy(true); setError(''); try { await fn(); } catch (e) { setError(errorText(e)); } finally { setBusy(false); } }
  return <div className="space-y-5">
    <button className="dr-btn" onClick={() => review ? setReview(null) : onClose()}><ArrowLeft />{review ? 'Change folders' : 'Back to room'}</button>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {review ? <ImportReview review={{ ...review, slot_definitions: definitions }} choices={choices} onChange={setChoices} busy={busy} onConfirm={() => run(async () => { await api.post(`/dealroom/rooms/${roomId}/drive-import/`, { ticket: review.ticket, choices }); onImported(); })} /> :
      <Card title="Start from Google Drive" subtitle="Bring your whole folder tree into the room, including folders inside folders.">
        <form onSubmit={e => { e.preventDefault(); run(async () => { const { data } = await api.post(`/dealroom/rooms/${roomId}/drive-review/`, { links: links.split(/\s+/).filter(Boolean), template }); setReview(data); setChoices(Object.fromEntries(data.matched.map(f => [f.id, f.slot]))); }); }} className="space-y-5">
          <div className="dr-field"><label htmlFor="drive-links">Drive folder links · one per line</label><textarea id="drive-links" className="dr-input min-h-32" required value={links} onChange={e => setLinks(e.target.value)} placeholder="https://drive.google.com/drive/folders/…" /></div>
          <div className="dr-field"><span className="dr-label">Room structure</span><SelectMenu label="Room structure" value={template} onChange={setTemplate} options={[{ value: '', label: 'Keep my Drive folders' }, { value: 'series_a', label: 'Match to Series A checklist' }]} /></div>
          <p className="text-sm text-muted-foreground">You review every placement before importing. Matching uses file names, folder paths and file types. Your files are never sent to an AI provider.</p>
          <p className="text-xs text-muted-foreground">This prototype reads the folder snapshot prepared for this server. Live Google sign-in is not connected yet.</p>
          <button className="dr-btn dr-btn--primary" disabled={busy}><CloudDownload />{busy ? 'Reading folders…' : 'Read folders'}</button>
        </form>
      </Card>}
  </div>;
}
