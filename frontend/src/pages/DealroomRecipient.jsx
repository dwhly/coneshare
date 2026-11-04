import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useBranding } from '../contexts/BrandingProvider';

export default function DealroomRecipient() {
  const { slug } = useParams();
  const brand = useBranding();
  const [csrf, setCsrf] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [params] = useState(() => new URLSearchParams(window.location.hash.slice(1)));
  useEffect(() => { window.history.replaceState({}, '', window.location.pathname); }, []);
  const [challenge, setChallenge] = useState(params.get('challenge') || '');
  const [room, setRoom] = useState(null);
  const [selected, setSelected] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const base = `/api/v1/dealroom/recipient/${encodeURIComponent(slug)}`;
  async function loadRoom() {
    const response = await fetch(`${base}/room/`, { credentials: 'same-origin' });
    if (response.ok) setRoom(await response.json());
  }
  useEffect(() => {
    fetch(`${base}/challenge/`, { credentials: 'same-origin' }).then(r => r.json()).then(data => setCsrf(data.csrf_token));
    loadRoom();
  }, [slug]);
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const payload = challenge ? { challenge_id: challenge, ...(code ? {code} : {token: params.get('token') || ''}) } : {email, name};
      const response = await fetch(`${base}/${challenge ? 'confirm' : 'challenge'}/`, { method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json', 'X-CSRFToken':csrf}, body:JSON.stringify(payload) });
      const result = await response.json();
      if (!response.ok || result.status === 'refused') throw new Error(result.message || result.detail || JSON.stringify(result));
      if (result.challenge_id) setChallenge(result.challenge_id);
      if (result.status === 'verified') { window.history.replaceState({}, '', `/view/${slug}`); await loadRoom(); }
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  if (!room) return <main className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
    <form onSubmit={submit} className="w-full max-w-md rounded-xl border bg-white p-8 shadow-sm space-y-5">
      <div className="flex items-center gap-3"><img src={brand.brandLogoUrl} alt="" className="w-9 h-9"/><strong className="text-xl">{brand.brandName}</strong><span className="text-slate-500">Send</span></div>
      <div><h1 className="text-2xl font-semibold">{challenge ? 'Check your email' : 'Enter your deal room'}</h1><p className="text-sm text-slate-500 mt-2">{challenge ? 'Enter the six-digit code, or confirm the link you opened. Your code expires after ten minutes.' : 'Verify your email to access confidential documents.'}</p></div>
      {!challenge && <><label className="block text-sm">Your name<input required className="mt-1 w-full border rounded-md p-3" value={name} onChange={e=>setName(e.target.value)} autoComplete="name" /></label><label className="block text-sm">Email address<input required type="email" className="mt-1 w-full border rounded-md p-3" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" /></label></>}
      {challenge && !params.get('token') && <label className="block text-sm">Verification code<input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} className="mt-1 w-full border rounded-md p-3 text-xl tracking-widest" value={code} onChange={e=>setCode(e.target.value)} autoComplete="one-time-code" /></label>}
      {error && <p role="alert" className="text-red-700 text-sm">{error}</p>}
      <button disabled={busy} className="w-full rounded-md bg-primary text-primary-foreground p-3 font-medium">{busy ? 'Please wait…' : challenge ? 'Confirm access' : 'Send verification code'}</button>
      {challenge && <button type="button" className="text-sm text-slate-600" onClick={()=>{setChallenge('');setError('')}}>Use another email or request a new code</button>}
      <p className="text-xs text-slate-400">Every copy is personalized. Access can be revoked by the room owner.</p>
    </form>
  </main>;
  const file = selected || room.files[0];
  return <main className="min-h-screen bg-slate-50">
    <header className="bg-white border-b px-6 py-4 flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-3"><img src={brand.brandLogoUrl} alt="" className="w-8 h-8"/><strong>{brand.brandName}</strong><span className="text-slate-300">/</span><h1 className="font-medium">{room.name}</h1></div><div className="text-sm text-slate-600">{room.member.name} · {room.member.org} · {room.member.email}</div></header>
    <div className="max-w-screen-2xl mx-auto grid md:grid-cols-[260px_1fr] gap-6 p-6">
      <aside className="bg-white border rounded-xl p-4 self-start"><h2 className="text-xs tracking-wider font-semibold text-slate-500 uppercase mb-4">Documents</h2>{room.folders.map(folder=><section key={folder.id} className="mb-5"><h3 className="font-medium text-sm mb-2">{folder.name}</h3>{room.files.filter(f=>f.folder_id===folder.id).map(f=><button key={f.id} onClick={()=>{setSelected(f);setPage(1)}} className={`text-left w-full p-2 rounded-md text-sm ${f.id===file?.id?'bg-slate-100 font-medium':'text-slate-500'}`}>{f.name}</button>)}</section>)}{room.files.filter(f=>!f.folder_id).map(f=><button key={f.id} onClick={()=>{setSelected(f);setPage(1)}} className="block py-2 text-sm">{f.name}</button>)}</aside>
      <section>{file ? <><div className="flex flex-wrap gap-3 items-center justify-between mb-4"><h2 className="font-semibold">{file.name}</h2><div className="flex items-center gap-3 text-sm"><button disabled={page===1} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page} of {file.page_count}</span><button disabled={page>=file.page_count} onClick={()=>setPage(p=>p+1)}>Next</button>{file.download_level!=='none' ? <a className="rounded-md border bg-white px-3 py-2" href={file.download_url}>Download watermarked PDF</a> : <span className="text-slate-400">View only</span>}</div></div><img className="mx-auto w-full max-w-[920px] bg-white border shadow-sm" src={file.page_url.replace('/render-page/1/', `/render-page/${page}/`)} alt={`Personalized page ${page} of ${file.name}`} onError={()=>setError('This page is not ready or access has been revoked. Reload to check access.')} />{error && <p role="alert" className="text-red-700 mt-4">{error}</p>}</> : <p>No documents are available yet.</p>}</section>
    </div>
  </main>;
}
