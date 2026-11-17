import { useState } from 'react';
import { Folder, ArrowLeft, Check, CloudDownload } from 'lucide-react';
import api from '../../services/api';
import { Card, StatusPill, SelectMenu, errorText } from './shell';
import { FileTypeIcon } from '../documents/FileTypeIcon';

export function ImportReview({ review, choices, onChange, onConfirm, busy, excluded = [], onExcludedChange,
  destinations = {}, onDestinationsChange, onTemplateChange }) {
  const definitions = review.slot_definitions || {};
  const files = review.nodes.filter(n => n.type === 'file');
  const included = files.filter(f => !excluded.includes(f.id));
  const assigned = included.map(f => choices[f.id]).filter(Boolean);
  const missing = Object.values(definitions).filter(s => !assigned.includes(s.id));
  const duplicate = new Set(assigned).size !== assigned.length;
  const folders = review.nodes.filter(n => n.type === 'folder');
  const folderOptions = [...review.roots, ...folders].map(f => ({ value: `folder:${f.id}`, label: [f.folder_path, f.name].filter(Boolean).join(' / ') }));

  function move(file, value) {
    onChange({ ...choices, [file.id]: value.startsWith('slot:') ? value.slice(5) : '' });
    const next = { ...destinations };
    if (value.startsWith('folder:')) next[file.id] = value.slice(7);
    else delete next[file.id];
    onDestinationsChange?.(next);
  }
  function row(file) {
    const omitted = excluded.includes(file.id);
    const placement = choices[file.id] ? `slot:${choices[file.id]}` : destinations[file.id] ? `folder:${destinations[file.id]}` : '';
    return <div key={file.id} draggable={!omitted && !busy} onDragStart={e => e.dataTransfer.setData('text/plain', file.id)} className="flex flex-wrap items-center gap-3 border-t border-gray-100 py-4">
      <FileTypeIcon type={file.final_type || (file.mimeType === 'application/vnd.google-apps.document' ? 'pdf' : file.mimeType === 'application/pdf' ? 'pdf' : file.name)} />
      <div className="flex-1 min-w-0 basis-48"><strong className="text-sm break-words">{file.final_name || file.name}</strong><p className="text-xs text-muted-foreground mt-1">{file.import_description || file.folder_path || 'Top level'}</p></div>
      {!omitted && <div className="w-full sm:w-60"><span className="block text-xs text-muted-foreground mb-1">Move to…</span><SelectMenu label={`Move ${file.name} to`} disabled={busy} value={placement} placeholder="Move to…" onChange={value => move(file, value)} options={[
        { value: '', label: 'Keep in its Drive folder' }, ...folderOptions,
        ...(review.template ? Object.values(definitions).map(s => ({ value: `slot:${s.id}`, label: `Checklist · ${s.name}` })) : []),
      ]} /></div>}
      <button className="dr-btn" disabled={busy} aria-label={`${omitted ? 'Include' : 'Exclude'} ${file.name}`} onClick={() => onExcludedChange?.(omitted ? excluded.filter(id => id !== file.id) : [...excluded, file.id])}>{omitted ? 'Include' : 'Exclude'}</button>
    </div>;
  }
  function childrenOf(id) {
    return review.nodes.filter(n => (n.type === 'file' ? destinations[n.id] || n.parent_id : n.parent_id) === id);
  }
  function count(id) {
    return childrenOf(id).reduce((total, node) => total + (node.type === 'folder' ? count(node.id) : Number(!excluded.includes(node.id))), 0);
  }
  function folderTree(folder) {
    const children = childrenOf(folder.id);
    const total = count(folder.id);
    return <div key={folder.id} role="group" aria-label={folder.name} className="min-w-0">
      <div className="flex items-center gap-2 py-3"><Folder className="h-5 w-5 text-muted-foreground shrink-0" /><h3 className="font-medium text-sm break-words">{folder.name}</h3><span className="text-xs text-muted-foreground whitespace-nowrap">{total} {total === 1 ? 'file' : 'files'}</span></div>
      <div className="border-l border-gray-200 pl-3 sm:pl-5">{children.filter(n => n.type === 'folder').map(folderTree)}{children.filter(n => n.type === 'file' && !excluded.includes(n.id)).map(row)}</div>
    </div>;
  }
  return <div className="space-y-5">
    <div><h2 className="text-xl font-semibold">Review your import</h2><p className="text-sm text-muted-foreground mt-2">{included.length} files selected from {review.roots.map(r => r.name).join(', ')}. Nothing is in the room until you confirm.</p>
      <button className="dr-btn mt-3" disabled={busy} onClick={() => onTemplateChange?.(review.template ? '' : 'series_a')}>{review.template ? 'Keep my Drive folders instead' : 'Match to a Series A checklist instead'}</button>
    </div>
    {review.template ? <>
      <Card title={`Matched · ${included.filter(f => choices[f.id]).length}`} subtitle="Check the placements. Drag a file to a missing slot, or choose Move to…">{included.filter(f => choices[f.id]).map(row)}</Card>
      <Card title={`Unsure · ${included.filter(f => !choices[f.id]).length}`} subtitle="These stay in their Drive folders unless you choose another folder or slot.">{included.filter(f => !choices[f.id]).map(row)}{included.every(f => choices[f.id]) && <p className="text-sm text-muted-foreground">Everything has a place.</p>}</Card>
      <Card title={`Missing · ${missing.length}`} subtitle="You can add these later. Visitors never see empty slots."><div className="grid sm:grid-cols-2 gap-3">{missing.map(slot => <div key={slot.id} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); const id = e.dataTransfer.getData('text/plain'); if (!busy && included.some(f => f.id === id)) onChange({ ...choices, [id]: slot.id }); }} className="rounded-xl border border-dashed border-gray-300 p-4 text-sm"><StatusPill tone="warning">Missing</StatusPill><p className="font-medium mt-2">{slot.name}</p></div>)}</div></Card>
    </> : <Card title="Your Drive folders" subtitle="Review the files in each folder. Move or exclude anything before importing.">{review.roots.map(folderTree)}</Card>}
    {excluded.length > 0 && <Card title={`Excluded · ${excluded.length}`} subtitle="These files will stay out of the room.">{files.filter(f => excluded.includes(f.id)).map(row)}</Card>}
    {review.skipped?.length > 0 && <Card title={`Skipped · ${review.skipped.length}`} subtitle="These items cannot be imported.">{review.skipped.map(file => <div key={file.id} className="py-3 border-t text-sm"><strong>{file.name}</strong><p className="text-muted-foreground mt-1">{file.skip_reason}</p></div>)}</Card>}
    <div className="sticky bottom-0 z-10 rounded-xl border bg-card p-4 shadow-sm flex flex-wrap items-center justify-between gap-3" aria-label="Import confirmation">
      <p className="text-sm text-muted-foreground">{included.length} selected · {excluded.length} excluded · {review.skipped?.length || 0} skipped</p>
      {duplicate && <p role="alert" className="text-sm text-amber-700">Two files share a slot. Choose a different slot or keep one in its Drive folder.</p>}
      <button className="dr-btn dr-btn--primary" disabled={busy || duplicate || !included.length} onClick={onConfirm}><Check />{busy ? 'Importing files…' : `Confirm and import ${included.length} ${included.length === 1 ? 'file' : 'files'}`}</button>
    </div>
  </div>;
}

export default function DriveImport({ roomId, definitions, onImported, onClose, onBusyChange }) {
  const [links, setLinks] = useState('');
  const [template, setTemplate] = useState('');
  const [review, setReview] = useState(null);
  const [choices, setChoices] = useState({});
  const [excluded, setExcluded] = useState([]);
  const [destinations, setDestinations] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function run(fn) {
    setBusy(true); onBusyChange?.(true); setError('');
    try { await fn(); } catch (e) { setError(errorText(e)); }
    finally { setBusy(false); onBusyChange?.(false); }
  }
  async function read(nextTemplate, preserve = false) {
    const { data } = await api.post(`/dealroom/rooms/${roomId}/drive-review/`, { links: links.split(/\s+/).filter(Boolean), template: nextTemplate });
    setReview(data); setTemplate(nextTemplate);
    setChoices(Object.fromEntries(data.matched.filter(f => !preserve || !destinations[f.id]).map(f => [f.id, f.slot])));
    const ids = new Set(data.nodes.filter(n => n.type === 'file').map(n => n.id));
    setExcluded(preserve ? excluded.filter(id => ids.has(id)) : []);
    setDestinations(preserve ? Object.fromEntries(Object.entries(destinations).filter(([id]) => ids.has(id))) : {});
  }
  return <div className="space-y-5">
    <button className="dr-btn" disabled={busy} onClick={() => review ? setReview(null) : onClose()}><ArrowLeft />{review ? 'Change folders' : 'Back to room'}</button>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {review ? <ImportReview review={{ ...review, slot_definitions: definitions }} choices={choices} onChange={setChoices} excluded={excluded} onExcludedChange={setExcluded} destinations={destinations} onDestinationsChange={setDestinations} onTemplateChange={next => run(() => read(next, true))} busy={busy} onConfirm={() => run(async () => { await api.post(`/dealroom/rooms/${roomId}/drive-import/`, { ticket: review.ticket, choices, excluded, destinations }); onImported(); })} /> :
      <Card title="Start from Google Drive" subtitle="Bring your whole folder tree into the room, including folders inside folders.">
        <form onSubmit={e => { e.preventDefault(); run(() => read(template)); }} className="space-y-5">
          <div className="dr-field"><label htmlFor="drive-links">Drive folder links · one per line</label><textarea id="drive-links" className="dr-input min-h-32" required value={links} onChange={e => setLinks(e.target.value)} placeholder="https://drive.google.com/drive/folders/…" /></div>
          <div className="dr-field"><span className="dr-label">Room structure</span><SelectMenu label="Room structure" value={template} onChange={setTemplate} options={[{ value: '', label: 'Keep my Drive folders' }, { value: 'series_a', label: 'Match to Series A checklist' }]} /></div>
          <p className="text-sm text-muted-foreground">You review every placement before importing. Matching uses file names, folder paths and file types. Your files are never sent to an AI provider.</p>
          <p className="text-xs text-muted-foreground">This prototype reads the folder snapshot prepared for this server. Live Google sign-in is not connected yet.</p>
          <button className="dr-btn dr-btn--primary" disabled={busy}><CloudDownload />{busy ? 'Reading folders…' : 'Read folders'}</button>
        </form>
      </Card>}
  </div>;
}
