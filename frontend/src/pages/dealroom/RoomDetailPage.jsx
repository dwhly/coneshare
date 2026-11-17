import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { ArrowDown, ArrowUp, CloudDownload, ExternalLink, Folder, Pin, Plus, RefreshCw, Upload, UserPlus, X } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../services/api';
import { usePageTitle } from '../../hooks/usePageTitle';
import { Card, CopyField, EmptyState, PageHead, RowMenu, SelectMenu, StatusPill, errorText } from '../../components/dealroom/shell';
import { FileTypeIcon } from '../../components/documents/FileTypeIcon';
import DriveImport from '../../components/dealroom/DriveImport';
import { Progress } from '../../components/ui/Progress';
import { UploadDialog } from './dialogs';
import { loadRoomDetail, useLoader } from './data';

export default function RoomDetailPage() {
  const { dataroomId } = useParams();
  const [search, setSearch] = useSearchParams();
  const detail = useLoader(() => loadRoomDetail(dataroomId), [dataroomId]);
  const outline = useLoader(async () => (await api.get(`/dealroom/rooms/${dataroomId}/outline/`)).data, [dataroomId]);
  const [tab, setTab] = useState('Documents');
  const [importing, setImporting] = useState(search.get('drive') === '1');
  const [importBusy, setImportBusy] = useState(false);
  const [checkedAt, setCheckedAt] = useState(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [targetSlot, setTargetSlot] = useState('');
  const [updates, setUpdates] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const room = detail.data?.room;
  const state = outline.data?.groups ? outline.data : { groups: [], documents: [], slots: {}, start_here: [], not_needed: [], needs_you: [] };
  const documents = state.documents.length ? state.documents : (detail.data?.documents || []);
  usePageTitle(room?.name || 'Room');
  async function run(fn) { setBusy(true); setError(''); try { await fn(); } catch (e) { setError(errorText(e)); } finally { setBusy(false); } }
  async function refresh() { await Promise.all([detail.reload(), outline.reload()]); }
  async function save(patch) { await api.patch(`/dealroom/rooms/${dataroomId}/outline/`, patch); await outline.reload(); }
  const toggleStart = id => run(() => save({ start_here: state.start_here.includes(id) ? state.start_here.filter(i => i !== id) : [...state.start_here, id] }));
  const place = (slot, id) => run(() => save({ slots: { ...Object.fromEntries(Object.entries(state.slots).filter(([, v]) => v !== id)), [slot]: id } }));
  const defs = state.slot_definitions || {};
  const missing = state.missing_slots || Object.values(defs).filter(s => !state.slots[s.id] && !state.not_needed.includes(s.id));
  const needsYouCount = state.needs_you_count ?? state.needs_you.length;
  const hasDrive = state.drive_roots?.length > 0 || documents.some(doc => doc.source);
  const lastChecked = checkedAt || state.drive_checked_at;
  function reorderStart(index, delta) {
    const ids = [...state.start_here];
    [ids[index], ids[index + delta]] = [ids[index + delta], ids[index]];
    run(() => save({ start_here: ids }));
  }
  const actionUpload = slot => { setTargetSlot(slot || ''); setUploadOpen(true); };
  function docRow(doc, index) {
    return <div key={doc.id} draggable onDragStart={e => e.dataTransfer.setData('text/plain', doc.id)} className="flex items-center gap-3 py-3 border-t border-gray-100">
      <span className="text-xs text-muted-foreground font-mono w-8">{index}</span><FileTypeIcon type={doc.name} />
      <div className="flex-1 min-w-0"><a className="text-sm font-medium hover:underline" href={`/documents/${doc.document_id}`}>{doc.name}</a>{doc.folder_path && <p className="text-xs text-muted-foreground">{doc.folder_path}</p>}{doc.source && <p className="text-xs text-muted-foreground mt-1">Drive snapshot · {new Date(doc.source.modifiedTime).toLocaleDateString()}{/^https:\/\/(?:drive|docs)\.google\.com\//.test(doc.source.webViewLink) && <> · <a href={doc.source.webViewLink} target="_blank" rel="noreferrer" className="underline">Source</a></>}</p>}</div>
      <button className="dr-btn" title={`${state.start_here.includes(doc.id) ? 'Unpin' : 'Pin'} ${doc.name}`} aria-label={`${state.start_here.includes(doc.id) ? 'Unpin' : 'Pin'} ${doc.name}`} onClick={() => toggleStart(doc.id)}><Pin className={state.start_here.includes(doc.id) ? 'fill-current' : ''} /></button>
    </div>;
  }
  return <div className="dr-container pb-12">
    <PageHead crumbs={[{ label: 'Rooms', to: '/datarooms' }, { label: room?.name || 'Room' }]} title={room?.name || 'Loading…'} subtitle="Your outline, your note, your investors." actions={room && <><a href={room.entry_url} target="_blank" rel="noreferrer" className="dr-btn"><ExternalLink />Visitor link</a><button disabled={importBusy} className={`dr-btn ${documents.length > 0 && !importing && !importBusy ? 'dr-btn--primary' : ''}`} onClick={() => { setImporting(false); setTab('Investors'); }}><UserPlus />Invite investors</button><RowMenu label="Room actions" items={[{ label: 'Close room', onSelect: () => { setImporting(false); setTab('Settings'); }, disabled: importBusy }]} /></>} />
    {(error || detail.error || outline.error) && <p role="alert" className="text-sm text-red-700 mb-4">{error || errorText(detail.error || outline.error)}</p>}
    {room && <>
      <div className="dr-subnav mb-6" style={{ padding: 0 }}><nav aria-label="Room sections" className="overflow-x-auto">{['Documents', 'Investors', 'Needs you', 'Settings'].map(t => <button key={t} disabled={importBusy} onClick={() => { setTab(t); setImporting(false); }} aria-current={(importing ? 'Documents' : tab) === t ? 'page' : undefined}>{t}{t === 'Needs you' && needsYouCount > 0 && <StatusPill>{needsYouCount}</StatusPill>}</button>)}</nav></div>
      {importing ? <DriveImport onBusyChange={setImportBusy} roomId={room.id} definitions={defs} onClose={() => setImporting(false)} onImported={() => { setImporting(false); setSearch({}); refresh(); toast.success('Files imported'); }} /> : tab === 'Documents' ? <div className="grid lg:grid-cols-[minmax(0,1fr)_320px] gap-6">
        <div className="space-y-5">
          <Card title={state.template ? `${Object.keys(state.slots).length} of ${Object.keys(defs).length - state.not_needed.length} usual documents in` : `${documents.length} documents in your room`} subtitle={state.template ? `${missing.length} missing${missing.length ? ': ' + missing.map(slot => slot.name).join(', ') : ''}. Visitors never see empty slots.` : 'Keep your folders, or start with a Series A checklist.'}>
            <div className="flex flex-wrap gap-2"><button className="dr-btn dr-btn--primary" onClick={() => actionUpload()}><Upload />Add files</button><button className="dr-btn" onClick={() => setImporting(true)}><CloudDownload />Start from Google Drive</button>{!state.template && <button className="dr-btn" onClick={() => run(() => save({ template: 'series_a' }))}>Use Series A checklist</button>}</div>
            {state.template && <Progress className="h-2 mt-5" value={100 * Object.keys(state.slots).length / Math.max(1, Object.keys(defs).length - state.not_needed.length)} aria-label="Checklist completeness" />}
          </Card>
          {state.template ? state.groups.map((group, g) => <Card key={group.id} title={`${String(g + 1).padStart(2, '0')} ${group.name}`} action={<Folder className="w-5 h-5 text-muted-foreground" />}>
            {group.slots.map(([id, name], n) => { const doc = documents.find(d => d.id === state.slots[id]); return doc ? docRow(doc, `${g + 1}.${n + 1}`) : <div key={id} className="border-t border-dashed py-4 flex flex-wrap items-center gap-3" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); const docId = e.dataTransfer.getData('text/plain'); if (documents.some(d => d.id === docId)) place(id, docId); }}><span className="text-xs font-mono text-muted-foreground">{g + 1}.{n + 1}</span><span className="flex-1 text-sm">{name}<span className="block text-xs text-muted-foreground mt-1">{state.not_needed.includes(id) ? 'Not needed for this deal' : 'Missing · drop a room file here or add a file'}</span></span><button className="dr-btn" onClick={() => run(() => save({ not_needed: state.not_needed.includes(id) ? state.not_needed.filter(k => k !== id) : [...state.not_needed, id] }))}>{state.not_needed.includes(id) ? 'Restore' : 'Not needed'}</button><button className="dr-btn" aria-label={`Add file for ${name}`} onClick={() => actionUpload(id)}><Plus />Add file</button>{documents.length > 0 && <div className="w-full"><SelectMenu label={`File for ${name}`} value="" placeholder="Choose an existing room file" options={documents.map(d => ({ value: d.id, label: d.name }))} onChange={docId => place(id, docId)} /></div>}</div>; })}
          </Card>) : (detail.data?.folders || []).map((folder, n) => <Card key={folder.id} title={`${String(n + 1).padStart(2, '0')} ${folder.name}`}>{documents.filter(d => (d.folder_id || d.folder) === folder.id).map((d, i) => docRow(d, `${n + 1}.${i + 1}`))}</Card>)}
          <Card title={state.template ? 'Also in this room' : 'Documents'} subtitle={state.template ? 'Files outside the checklist keep their Drive folders.' : undefined}>{documents.filter(d => state.template ? !Object.values(state.slots).includes(d.id) : !(d.folder_id || d.folder)).map((d, n) => docRow(d, String(n + 1).padStart(2, '0')))}{!documents.length && <EmptyState>Add your first files or import a Drive folder.</EmptyState>}</Card>
        </div>
        <aside className="space-y-5">
          <Card title="Google Drive" subtitle="Updates stay private until you publish each new version.">{hasDrive && <p className="text-xs text-muted-foreground mb-3">{lastChecked ? `Last checked ${new Date(lastChecked).toLocaleString()}` : 'Not checked yet'}</p>}<button disabled={busy || !hasDrive} className="dr-btn w-full" onClick={() => run(async () => { const { data } = await api.get(`/dealroom/rooms/${room.id}/drive-updates/`); setUpdates(data.updates); setCheckedAt(data.checked_at); })}><RefreshCw />Check Drive for updates</button>{updates && <div className="mt-4 text-sm space-y-4">{!updates.length && <p>No changes since the last import.</p>}{updates.map(u => <div key={u.item_id}><p className="font-medium">{u.name}</p><p className="text-xs text-muted-foreground">Changed {new Date(u.modifiedTime).toLocaleString()}</p><button className="dr-btn mt-2" disabled={busy} onClick={() => run(async () => { await api.post(`/dealroom/rooms/${room.id}/drive-updates/`, { item_id: u.item_id, modifiedTime: u.modifiedTime }); setUpdates(updates.filter(x => x.item_id !== u.item_id)); await refresh(); })}>Publish new version</button></div>)}</div>}</Card>
          <NoteCard note={state.note || ''} onSave={note => run(() => save({ note }))} />
          <Card title="What investors see first" subtitle="Pin documents in the outline, then set their order here.">{state.start_here.map((id, n) => {
            const name = documents.find(d => d.id === id)?.name || 'Document';
            return <div key={id} className="flex items-center gap-2 py-3 border-t text-sm"><span className="font-mono">{n + 1}</span><span className="flex-1 min-w-0 break-words">{name}</span>
              <div className="flex gap-1"><button className="dr-btn" title={`Move ${name} up`} aria-label={`Move ${name} up`} disabled={!n || busy} onClick={() => reorderStart(n, -1)}><ArrowUp /></button>
              <button className="dr-btn" title={`Move ${name} down`} aria-label={`Move ${name} down`} disabled={n === state.start_here.length - 1 || busy} onClick={() => reorderStart(n, 1)}><ArrowDown /></button>
              <button className="dr-btn" title={`Remove ${name} from start here`} aria-label={`Remove ${name} from start here`} disabled={busy} onClick={() => toggleStart(id)}><X /></button></div></div>;
          })}</Card>
          <Card title="Room rules"><ul className="text-sm space-y-3"><li>NDA in Sign {state.nda_configured ? <StatusPill tone="success">Ready</StatusPill> : <button className="underline" onClick={() => setTab('Settings')}>Set up NDA</button>}</li><li>Their name on every page</li><li>Downloads off · copies by request</li><li>Full room · named people only</li></ul></Card>

        </aside>
      </div> : tab === 'Investors' ? <Investors roomId={room.id} state={state} onRefresh={refresh} run={run} busy={busy} /> : tab === 'Needs you' ? <NeedsYou state={state} roomId={room.id} run={run} reload={outline.reload} /> : <RoomSettings room={room} state={state} run={run} refresh={refresh} />}
      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} roomId={room.id} onUploaded={async item => { if (targetSlot && item?.id) await save({ slots: { ...state.slots, [targetSlot]: item.id } }); refresh(); }} />
    </>}
  </div>;
}

function NoteCard({ note, onSave }) {
  const [draft, setDraft] = useState(null);
  return <Card title="Your welcome note" subtitle="You can write a personal note for each firm when inviting."><textarea aria-label="Welcome note" className="dr-input min-h-28" value={draft ?? note} onChange={e => setDraft(e.target.value)} placeholder="Thanks for taking a look. Start with the model; I’m around this week to walk through it." /><button className="dr-btn mt-3" onClick={() => onSave(draft ?? note)}>Save note</button></Card>;
}

function Investors({ roomId, state, onRefresh, run, busy }) {
  const [emails, setEmails] = useState(''); const [notes, setNotes] = useState({}); const [sent, setSent] = useState([]);
  const people = [...new Set(emails.split(/[\s,;]+/).filter(e => e.includes('@')))];
  const firms = [...new Set(people.map(e => e.split('@')[1]))];
  return <div className="max-w-3xl space-y-5"><Card title="Invite by firm" subtitle="Each person gets a personal link by email. No account, no password. The same link works when they return."><div className="dr-field"><label htmlFor="invite-emails">Email addresses</label><textarea id="invite-emails" className="dr-input min-h-24" value={emails} onChange={e => setEmails(e.target.value)} placeholder="maya@northwind.vc, leo@northwind.vc" /></div>{firms.map(f => <div key={f} className="rounded-xl border p-4 mb-4"><strong className="text-sm">{f}</strong><p className="text-xs text-muted-foreground my-2">{people.filter(e => e.endsWith('@' + f)).join(', ')} · Just these people</p><textarea className="dr-input" aria-label={`Note for ${f}`} value={notes[f] ?? state.note ?? ''} onChange={e => setNotes({ ...notes, [f]: e.target.value })} placeholder="A personal note for this firm" /></div>)}<p className="text-sm text-muted-foreground mb-4">Full room. NDA in Sign. Every page watermarked. Downloads off. Answers private to the asking firm.</p><button className="dr-btn dr-btn--primary" disabled={!people.length || busy} onClick={() => run(async () => { setSent((await api.post(`/dealroom/rooms/${roomId}/invite/`, { emails: people, notes })).data.invitations); await onRefresh(); })}><UserPlus />{busy ? 'Sending…' : 'Send personal invitations'}</button></Card>{sent.map(p => <Card key={p.email} title={p.email} subtitle="Personal invitation sent"><CopyField value={`${window.location.origin}${p.url}`} label={`Link for ${p.email}`} /></Card>)}<Card title="Invited people">{(state.invitations || []).map((p, n) => <div key={`${p.email}-${n}`} className="py-3 border-t text-sm"><strong>{p.firm}</strong><p className="text-muted-foreground">{p.email}</p><p className="mt-2">{p.note}</p></div>)}{!state.invitations?.length && <EmptyState>No investors invited yet.</EmptyState>}</Card></div>;
}

function NeedsYou({ state, roomId, run, reload }) {
  const [answer, setAnswer] = useState({}); const [faq, setFaq] = useState({});
  return <Card title="Needs you" subtitle="Questions and copy requests, in one place." action={<a className="dr-btn" href={`/activity?room=${roomId}`}>All room activity</a>}>{!state.needs_you.length && <EmptyState>You’re all caught up.</EmptyState>}{state.needs_you.map(q => <div key={q.id} className="py-5 border-t space-y-3"><div className="flex flex-wrap gap-2 items-center"><strong className="text-sm">{q.firm}</strong><StatusPill>{q.kind === 'copy' ? 'Copy requested' : 'Question'}</StatusPill></div><p className="text-sm">{q.text}</p><p className="text-xs text-muted-foreground">{q.document} · page {q.page} · {q.email}</p><textarea aria-label={`Reply to ${q.email}`} className="dr-input" placeholder="Write an answer" value={answer[q.id] || ''} onChange={e => setAnswer({ ...answer, [q.id]: e.target.value })} /><label className="text-sm flex gap-2"><input type="checkbox" checked={faq[q.id] || false} onChange={e => setFaq({ ...faq, [q.id]: e.target.checked })} />Also publish to all firms</label><p className="text-xs text-muted-foreground">{q.kind === 'copy' ? 'A reply does not release a file. Copies remain disabled.' : 'Private to this firm by default. Your answer appears in their room.'}</p><button className="dr-btn dr-btn--primary" disabled={!answer[q.id]?.trim()} onClick={() => run(async () => { await api.post(`/dealroom/rooms/${roomId}/answer/`, { id: q.id, text: answer[q.id], faq: faq[q.id] || false }); await reload(); })}>Send answer</button></div>)}</Card>;
}

function RoomSettings({ room, state, run, refresh }) {
  const [nda, setNda] = useState(''); const [expires, setExpires] = useState('');
  return <div className="max-w-3xl space-y-5"><Card title="NDA in Sign" subtitle="Choose the room’s NDA PDF. This uses the existing Sign consent and signed-copy delivery."><SelectMenu label="NDA PDF" value={nda} onChange={setNda} options={state.documents.filter(d => d.name.toLowerCase().endsWith('.pdf')).map(d => ({ value: d.id, label: d.name }))} placeholder="Choose your NDA" /><p className="text-xs text-muted-foreground mt-3">Prototype signature placement: lower left on the last page. Use a demo NDA with a clear signature area there.</p><button className="dr-btn mt-4" disabled={!nda} onClick={() => run(async () => { const d = state.documents.find(d => d.id === nda); await api.put(`/dealroom-sign/nda-policy/${room.id}/`, { version_id: d.version_id, enabled: true, fields: [{ type: 'SIGNATURE', page: d.page_count || 1, positionX: 10, positionY: 70, width: 30, height: 10 }] }); await refresh(); toast.success('NDA gate ready'); })}>Use this NDA</button>{state.nda_configured && <p className="text-sm mt-3">NDA gate is ready. Sign credentials must be configured for the room owner.</p>}</Card><Card title="Close the room" subtitle="Visitors keep the NDA and any copies already issued. Closing prevents further room access."><label className="dr-field">Close on<input type="date" className="dr-input" value={expires} onChange={e => setExpires(e.target.value)} /></label><div className="flex flex-wrap gap-3"><button className="dr-btn" disabled={!expires} onClick={() => run(async () => { await api.patch(`/dealroom/rooms/${room.id}/policy/`, { expires_at: `${expires}T23:59:59Z` }); await refresh(); toast.success('Closing date saved'); })}>Set closing date</button><button className="dr-btn" onClick={() => run(async () => { await api.patch(`/dealroom/rooms/${room.id}/policy/`, { status: state.policy?.status === 'archived' ? 'active' : 'archived', ...(state.policy?.status === 'archived' ? { expires_at: null } : {}) }); await refresh(); })}>{state.policy?.status === 'archived' ? 'Reopen room' : 'Close room now'}</button></div><p className="text-sm text-muted-foreground mt-4">{state.policy?.status === 'archived' ? 'Room closed' : state.policy?.expires_at ? `Closes ${new Date(state.policy.expires_at).toLocaleDateString()}` : 'Room open · no closing date set'}</p></Card></div>;
}
