import { useEffect, useState } from 'react';
import api from '../services/api';
import { hydrateLayoutMode } from '../lib/layoutMode';
import { useOptionalBreadcrumb } from '../components/layout/BreadcrumbProvider';

// Fleet design system: page title in foreground, cards = outline edges, primary = ink, secondary = outline,
// selected room = --selected role, links = brand, mono for data (URLs, payloads, timestamps) only.
const input = 'h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const button = 'inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background';
const secondary = 'inline-flex h-10 items-center rounded-md border border-input bg-background px-4 text-sm font-semibold text-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const card = 'rounded-lg border border-border bg-card p-card';
const roomFromPath = () => (window.location.pathname.match(/^\/datarooms\/([^/]+)/) || [])[1] || '';

export default function DealroomConsole() {
  const [rooms,setRooms]=useState([]), [approvals,setApprovals]=useState([]), [orgs,setOrgs]=useState([]), [activity,setActivity]=useState([]);
  const [roomId,setRoomId]=useState(roomFromPath), [roomName,setRoomName]=useState(''), [orgName,setOrgName]=useState(''), [domain,setDomain]=useState(''), [email,setEmail]=useState(''), [error,setError]=useState('');
  const [orgId,setOrgId]=useState('');
  const { setBreadcrumbData } = useOptionalBreadcrumb();
  let alabel = '';
  try { if (/^[^\s/:?#@]+$/.test(domain.trim())) alabel = new URL(`https://${domain.trim()}`).hostname; } catch { /* invalid domain stays unconfirmed */ }
  const items=data=>data.results||data;
  async function refresh(){
    const [r,a,o,e]=await Promise.all(['rooms','approvals','orgs','activity'].map(x=>api.get(`/dealroom/${x}/`)));
    setRooms(items(r.data));setApprovals(items(a.data));setOrgs(items(o.data));setActivity(items(e.data));setRoomId(id=>id||items(r.data)[0]?.id||'');
  }
  useEffect(()=>{hydrateLayoutMode();refresh().catch(e=>setError(JSON.stringify(e.response?.data||e.message)))},[]);
  const selected = rooms.find(r=>r.id===roomId);
  const fromPath = roomFromPath();
  useEffect(()=>{ setBreadcrumbData(selected && fromPath ? { type: 'dataroom', dataroomName: selected.name } : null); },[selected, fromPath, setBreadcrumbData]);
  function selectRoom(id){ setRoomId(id); window.history.replaceState(window.history.state, '', `/datarooms/${id}`); }
  async function act(fn){try{setError('');await fn();await refresh()}catch(e){setError(JSON.stringify(e.response?.data||e.message))}}
  const pending = approvals.filter(a=>a.status==='pending_approval');
  return <div className="mx-auto max-w-6xl px-6 py-8 space-y-8">
    <div><p className="text-sm font-medium text-muted-foreground">Rooms</p><h1 className="text-3xl font-semibold tracking-tight text-foreground mt-1">Your deal rooms</h1><p className="text-muted-foreground mt-2">Manage access, review agent requests, and follow the activity trail.</p></div>
    {error&&<p role="alert" className="rounded-lg border border-danger-border bg-danger-subtle p-4 text-sm text-danger">{error}</p>}
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">{rooms.map(r=>{const on=r.id===roomId;return <article key={r.id} aria-current={on?'true':undefined} className={`${card} ${on?'border-selected-border bg-selected':''}`}>
      <div className="flex items-start justify-between gap-3"><span className="text-xs font-medium text-muted-foreground">Data room</span>{on?<span className="inline-flex items-center rounded-pill border border-border bg-background px-2 py-0.5 text-xs font-semibold text-foreground">Selected</span>:<button type="button" className="text-sm font-medium text-brand hover:underline" onClick={()=>selectRoom(r.id)}>Manage</button>}</div>
      <h2 className="text-xl font-semibold text-foreground my-2">{r.name}</h2>
      <a className="text-sm font-medium text-brand hover:underline" href={r.entry_url}>Open recipient entry →</a>
      <p className="font-mono text-xs text-muted-foreground mt-2 break-all">{window.location.origin}{r.entry_url}</p></article>})}</div>
    <section className={`${card} space-y-5`}><div><h2 className="font-semibold text-lg text-foreground">Room access</h2><p className="text-sm text-muted-foreground mt-1">{selected?<>Granting and uploading to <span className="font-medium text-foreground">{selected.name}</span>.</>:'Create a room to start granting access.'}</p></div>
      <form className="flex flex-wrap gap-3" onSubmit={e=>{e.preventDefault();act(()=>api.post('/dealroom/rooms/',{name:roomName}))}}><input aria-label="New room name" className={input} placeholder="New room name" value={roomName} onChange={e=>setRoomName(e.target.value)} required/><button className={button}>Create room</button></form>
      <form className="flex flex-wrap gap-3" onSubmit={e=>{e.preventDefault();act(()=>api.post('/dealroom/orgs/',{name:orgName,email_domains:[domain],confirm_domains:true}))}}><input aria-label="Organization name" className={input} placeholder="Organization name" value={orgName} onChange={e=>setOrgName(e.target.value)} required/><input aria-label="Organization domain" className={input} placeholder="acme.test" value={domain} onChange={e=>setDomain(e.target.value)} required/><label className="text-xs text-muted-foreground flex items-center gap-2"><input key={domain} type="checkbox" className="accent-primary" required disabled={!alabel}/>I confirm Unicode: {domain.trim().toLowerCase() || "—"} · A-label: {alabel || "—"}</label><button className={button}>Add recipient organization</button></form>
      <form className="flex flex-wrap gap-3" onSubmit={e=>{e.preventDefault();act(()=>api.post('/dealroom/grants/',{room:roomId,...(email?{email}:{viewer_organisation:orgId})}))}}><select aria-label="Room" className={input} value={roomId} onChange={e=>selectRoom(e.target.value)}>{rooms.map(r=><option value={r.id} key={r.id}>{r.name}</option>)}</select><select aria-label="Recipient organization" className={input} value={orgId} onChange={e=>setOrgId(e.target.value)}><option value="">Choose organization</option>{orgs.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select><span className="self-center text-sm text-muted-foreground">or</span><input aria-label="Member email" className={input} type="email" placeholder="Named member email" value={email} onChange={e=>setEmail(e.target.value)}/><button className={button}>Grant view access</button></form>
      <label className="block text-sm font-medium text-foreground">Upload a PDF or Office file to the selected room<input className="block mt-2 text-sm text-muted-foreground file:mr-3 file:h-9 file:rounded-md file:border file:border-input file:bg-background file:px-3 file:text-sm file:font-semibold file:text-foreground" type="file" accept=".pdf,.docx,.pptx,.xlsx" onChange={e=>{const data=new FormData();data.append('file',e.target.files[0]);act(()=>api.post(`/dealroom/rooms/${roomId}/upload/`,data,{headers:{'Content-Type':'multipart/form-data'}}))}}/></label>
    </section>
    <section className={card}><h2 className="text-lg font-semibold text-foreground mb-4">Pending access approvals</h2>{pending.length===0&&<p className="text-sm text-muted-foreground">No requests waiting for review.</p>}{pending.map(a=><article key={a.id} className="border-t border-border py-4 space-y-2"><div className="flex items-center gap-2"><p className="font-medium text-foreground">{a.operation_id}</p><span className="inline-flex items-center rounded-pill border border-warning-border bg-warning-subtle px-2 py-0.5 text-xs font-semibold text-warning">Needs review</span></div><p className="text-sm text-muted-foreground break-all">Target: {a.method} {a.path}</p><h3 className="text-sm font-medium text-foreground">Current state</h3><pre className="font-mono text-xs whitespace-pre-wrap bg-muted border border-border p-3 rounded-md">{JSON.stringify(a.current_state,null,2)}</pre><h3 className="text-sm font-medium text-foreground">Proposed changes</h3><pre className="font-mono text-xs whitespace-pre-wrap break-all bg-muted border border-border p-3 rounded-md">{JSON.stringify(a.payload,null,2)}</pre><div className="flex gap-3 pt-1"><button className={button} onClick={()=>act(()=>api.post(`/dealroom/approvals/${a.id}/approve/`))}>Approve access</button><button className={secondary} onClick={()=>act(()=>api.post(`/dealroom/approvals/${a.id}/reject/`))}>Reject</button></div></article>)}</section>
    <section><h2 className="text-lg font-semibold text-foreground mb-3">Recent activity</h2><div className="divide-y divide-border rounded-lg border border-border bg-card">{activity.length===0&&<p className="p-4 text-sm text-muted-foreground">No activity yet.</p>}{activity.slice(0,15).map(a=><div key={a.id} className="px-4 py-3 flex flex-wrap items-center gap-4 text-sm"><span className="font-medium text-foreground">{a.event_type.replace(/_/g,' ')}</span><span className="inline-flex items-center rounded-pill border border-border bg-secondary px-2 py-0.5 text-xs font-medium text-secondary-foreground">{a.actor_kind}</span><time dateTime={a.created_at} className="ml-auto font-mono text-xs text-muted-foreground">{new Date(a.created_at).toLocaleString()}</time></div>)}</div></section>
  </div>
}
