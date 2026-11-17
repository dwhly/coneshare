import { useEffect, useState } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, Download, Folder, MessageSquare } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '../ui/Dialog';
import { FileTypeIcon } from '../documents/FileTypeIcon';
import { Card, StatusPill } from './shell';
import { ThemeToggle } from '../layout/FleetChrome';
import { PersonalNda } from './SignedNda';

export function VisitorReader({ file, files, member, onBack, onSelect, onRequest, initialPage = 1, onProgress = () => {} }) {
  const [page, setPage] = useState(initialPage);
  const [sheet, setSheet] = useState('');
  const [drafts, setDrafts] = useState({});
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [fit, setFit] = useState(true);
  useEffect(() => { setPage(initialPage); setError(''); setSent(false); }, [file.id, initialPage]);
  const draftKey = `${file.id}:${page}:${sheet}`;
  const draft = drafts[draftKey] || '';
  const next = files[files.findIndex(f => f.id === file.id) + 1];
  function turn(p) { setPage(p); onProgress(file.id, p); setError(''); }
  return <section className="min-h-screen bg-gray-50 pb-24" aria-label="Document reader">
    <div className="sticky top-0 z-10 bg-white border-b px-4 sm:px-6 py-3 flex items-center gap-3">
      <button className="dr-btn" aria-label="Back to room" onClick={onBack}><ArrowLeft /></button>
      <div className="flex-1 min-w-0"><h1 className="text-sm sm:text-base font-semibold break-words">{file.name}</h1><p className="text-xs text-muted-foreground mt-1">Page {page} of {file.page_count}</p></div>
      <details className="relative text-sm"><summary className="dr-btn cursor-pointer" aria-label="Reader options">More</summary><div className="absolute right-0 mt-2 rounded-xl border bg-white p-4 shadow-sm w-52"><label className="flex gap-2"><input type="checkbox" checked={fit} onChange={e => setFit(e.target.checked)} />Fit width</label><label className="block mt-3">Go to page<input className="dr-input mt-1" type="number" min="1" max={file.page_count} value={page} onChange={e => { const p = Number(e.target.value); if (p >= 1 && p <= file.page_count) turn(p); }} /></label></div></details>
    </div>
    <div className="overflow-x-auto p-2 sm:p-6">
      <img className={`${fit ? 'w-full' : 'min-w-[1100px]'} mx-auto bg-white border shadow-sm`} src={file.page_url.replace('/render-page/1/', `/render-page/${page}/`)} alt={`Watermarked page ${page} of ${file.name}`} onError={() => setError('This preview is still being prepared, or access has changed. Try again shortly.')} />
      <p className="text-xs text-center text-muted-foreground my-3">{member.name} · {member.org} · {member.email}<br />Every copy you open is watermarked with your company and individual details. The sender can see what you open.</p>
      {error && <p role="alert" className="text-sm text-red-700 text-center my-4">{error}</p>}
      <div className="flex gap-4 items-center justify-center my-6"><button className="dr-btn" disabled={page <= 1} onClick={() => turn(page - 1)}><ChevronLeft />Previous page</button><span className="text-sm">{page} / {file.page_count}</span><button className="dr-btn" disabled={page >= file.page_count} onClick={() => turn(page + 1)}>Next page<ChevronRight /></button></div>
      {next && <button className="block w-full text-left rounded-xl border bg-white p-5" onClick={() => onSelect(next)}><span className="text-xs text-muted-foreground">Next document</span><strong className="block text-sm mt-1">{next.name}</strong></button>}
    </div>
    <div className="fixed bottom-0 inset-x-0 z-20 bg-white border-t p-3 flex gap-3 justify-center pb-[max(12px,env(safe-area-inset-bottom))]">
      <button className="dr-btn flex-1 max-w-xs" onClick={() => { setSheet('question'); setSent(false); }}><MessageSquare />Ask</button><button className="dr-btn flex-1 max-w-xs" onClick={() => { setSheet('copy'); setSent(false); }}><Download />Get a copy</button>
    </div>
    <Dialog open={Boolean(sheet)} onOpenChange={open => { if (!open) setSheet(''); }}><DialogContent className="max-w-lg rounded-xl">
      <DialogTitle>{sheet === 'question' ? `Ask about page ${page}` : 'Get a copy'}</DialogTitle><DialogDescription>{file.name}</DialogDescription>
      {sent ? <p role="status" className="text-sm py-6">{sheet === 'question' ? 'Question sent. Your answer will appear in this room.' : 'Copy requested. The sender will review it; no file has been released.'}</p> : <form className="space-y-4" onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { await onRequest({ item_id: file.id, kind: sheet, page, text: draft || 'Please email me a watermarked copy.' }); setSent(true); setDrafts({ ...drafts, [draftKey]: '' }); } catch (e) { setError(e.message); } finally { setBusy(false); } }}>
        {sheet === 'copy' && <p className="text-sm">Downloads are off. Ask for a watermarked PDF by email to {member.email}, or explain why you need the original.</p>}
        <textarea className="dr-input min-h-32" aria-label={sheet === 'question' ? 'Your question' : 'Copy request'} value={draft} onChange={e => setDrafts({ ...drafts, [draftKey]: e.target.value })} placeholder={sheet === 'question' ? 'What would you like to know?' : 'Please email me a watermarked copy.'} required={sheet === 'question'} />
        <p className="text-xs text-muted-foreground">Only the sender’s team and your firm see this. Closing keeps your draft.</p>
        <button disabled={busy} className="dr-btn dr-btn--primary">{busy ? 'Sending…' : sheet === 'question' ? 'Send question' : 'Request a copy'}</button>
      </form>}
    </DialogContent></Dialog>
  </section>;
}

export default function RoomVisitor({ room, brand, onRequest, base }) {
  const key = `room-visit:${room.id}:${room.member.email}`;
  const [previous] = useState(() => { try { return JSON.parse(localStorage.getItem(key)) || {}; } catch { return {}; } });
  const [file, setFile] = useState(null);
  const [page, setPage] = useState(1);

  const [query, setQuery] = useState('');
  const [showAnswers, setShowAnswers] = useState(false);
  useEffect(() => { localStorage.setItem(key, JSON.stringify({ ...previous, at: new Date().toISOString() })); }, [key, previous]);
  const progress = (id, p) => { localStorage.setItem(key, JSON.stringify({ at: new Date().toISOString(), file: id, page: p })); };
  function open(f, p = 1) { setFile(f); setPage(p); progress(f.id, p); }
  const changes = previous.at ? room.files.filter(f => f.published_at > previous.at) : [];
  const ordered = [...(room.start_here || []).map(id => room.files.find(f => f.id === id)).filter(Boolean), ...room.files.filter(f => !(room.start_here || []).includes(f.id))];
  if (file) return <VisitorReader file={file} files={ordered} member={room.member} onBack={() => setFile(null)} onSelect={open} initialPage={page} onProgress={progress} onRequest={onRequest} />;
  function fileRow(f, badge) {
    const spreadsheet = /\.(xlsx?|csv|ods)$/i.test(f.name);
    const count = spreadsheet ? f.sheet_count : f.page_count;
    const unit = spreadsheet ? 'sheet' : 'page';
    return <button key={f.id} className="w-full text-left flex items-center gap-3 rounded-lg px-3 py-3 hover:bg-gray-50" onClick={() => open(f)}><FileTypeIcon type={f.name} /><span className="flex-1 min-w-0"><strong className="block text-sm break-words">{f.name}</strong>{count > 0 && <span className="text-xs text-muted-foreground">{count} {unit}{count === 1 ? '' : 's'}</span>}</span>{badge && <StatusPill tone="info">{badge}</StatusPill>}<ChevronRight className="w-4 h-4 shrink-0" /></button>;
  }
  function folderSection(parent = '', ancestors = []) {
    return room.folders.filter(f => (f.parent_id || '') === parent && !ancestors.includes(f.id)).map(f =>
      <details key={f.id} open aria-label={f.name} className={ancestors.length ? 'pl-3 sm:pl-4' : 'rounded-xl border px-3 py-2 sm:px-4'}>
        <summary className="cursor-pointer text-sm font-semibold py-2"><Folder className="inline h-4 w-4 mr-2" />{f.name}</summary>
        <div>
          {room.files.filter(file => file.folder_id === f.id).map(file => fileRow(file))}
          {folderSection(f.id, [...ancestors, f.id])}
        </div>
      </details>);
  }
  return <main className="min-h-screen bg-white pb-12">
    <header className="border-b px-5 py-4 flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><img className="h-8 w-8" src={brand.brandLogoUrl} alt="" /><strong>{brand.brandName}</strong><span className="text-muted-foreground">| Dealroom</span></div><div className="flex items-center gap-3"><span className="text-xs text-muted-foreground">{room.member.name} · {room.member.org}</span><ThemeToggle /></div></header>
    <div className="max-w-6xl mx-auto px-5 sm:px-8 pt-8 space-y-7">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">{room.nda_signed && <StatusPill tone="success">NDA signed</StatusPill>}<p className="text-sm text-muted-foreground">Documents you open are watermarked with your company and individual details. Your signed NDA is yours, unwatermarked.</p></div>
      <div><p className="text-xs uppercase tracking-wider text-muted-foreground mb-2">Prepared for {room.member.org || room.member.name}</p><h1 className="text-3xl font-bold tracking-tight">{room.name}</h1></div>
      {room.note && <div className="rounded-2xl border border-gray-200 bg-gray-50/40 p-6 shadow-sm"><p className="text-base leading-7 whitespace-pre-wrap">{room.note}</p><p className="text-xs text-muted-foreground mt-3">A note from your host</p></div>}
      {previous.at && <Card title={`Welcome back, ${room.member.name.split(' ')[0]}`} subtitle="What changed since you were here"><div className="space-y-3">{changes.map(f => fileRow(f, f.version_number > 1 ? 'Updated' : 'Added'))}{!changes.length && <p className="text-sm text-muted-foreground">You’re up to date. No new documents since your last visit.</p>}{room.answers?.length > 0 && <button className="dr-btn" onClick={() => setShowAnswers(!showAnswers)}>Read the answers from the team</button>}{room.files.some(f => f.id === previous.file) && <button className="dr-btn" onClick={() => open(room.files.find(f => f.id === previous.file), previous.page || 1)}>Pick up where you stopped · page {previous.page || 1}</button>}</div></Card>}

      {!query && (room.start_here || []).length > 0 && <section><h2 className="text-xl font-semibold mb-4">Start here</h2><div className="grid md:grid-cols-2 gap-1 rounded-xl border p-2">{room.start_here.map(id => room.files.find(f => f.id === id)).filter(Boolean).map(f => fileRow(f))}</div></section>}
      <section><div className="flex flex-wrap gap-4 items-center justify-between mb-4"><h2 className="text-xl font-semibold">All documents · {room.files.length}</h2><input className="dr-input sm:max-w-xs" aria-label="Search documents" placeholder="Search documents" value={query} onChange={e => setQuery(e.target.value)} /></div>
        <div className="space-y-3">
          {!query && folderSection()}
          {query ? room.files.filter(f => f.name.toLowerCase().includes(query.toLowerCase())).map(f => fileRow(f)) : room.files.some(f => !f.folder_id) && <section aria-label="Other documents" className="rounded-xl border px-3 py-2 sm:px-4"><h3 className="text-sm font-semibold py-2 pl-4"><Folder className="inline h-4 w-4 mr-2" />Other documents</h3>{room.files.filter(f => !f.folder_id).map(f => fileRow(f))}</section>}
        </div>
      </section>
      {room.answers?.length > 0 && <section><button className="dr-btn" onClick={() => setShowAnswers(!showAnswers)}>Answers from the team · {room.answers.length}</button>{showAnswers && room.answers.map(a => <div key={a.id} className="rounded-xl border p-5 mt-3"><StatusPill>{a.faq ? 'Room FAQ' : 'Private to your firm'}</StatusPill><p className="text-sm mt-3 whitespace-pre-wrap">{a.text}</p></div>)}</section>}
      {room.signed_nda?.signed && <PersonalNda initial={room.signed_nda} base={base} />}
    </div>
  </main>;
}
