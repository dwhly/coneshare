import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useBranding } from '../contexts/BrandingProvider';
import { isSafeUrl } from '../lib/utils';
import RoomVisitor from '../components/dealroom/RoomVisitor';

export default function DealroomRecipient() {
  const { slug } = useParams();
  const fallbackBrand = useBranding();
  const [invitation, setInvitation] = useState(null);
  const brand = invitation?.brand ? { ...fallbackBrand, brandName: invitation.brand.name, brandLogoUrl: isSafeUrl(invitation.brand.logo) ? invitation.brand.logo : fallbackBrand.brandLogoUrl } : fallbackBrand;
  const identity = <div className="flex items-center gap-3"><img src={brand.brandLogoUrl} alt="" className="w-9 h-9 object-contain" /><strong className="text-xl">{brand.brandName}</strong><span className="text-muted-foreground">Dealroom</span></div>;
  const [csrf, setCsrf] = useState('');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [params] = useState(() => new URLSearchParams(window.location.hash.slice(1)));
  useEffect(() => { window.history.replaceState({}, '', window.location.pathname); }, []);
  const [challenge, setChallenge] = useState(params.get('challenge') || '');
  const [room, setRoom] = useState(null);
  const [nda, setNda] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const base = `/api/v1/dealroom/recipient/${encodeURIComponent(slug)}`;
  async function loadRoom() {
    const response = await fetch(`${base}/room/`, { credentials: 'same-origin' });
    const data = await response.json();
    if (response.ok) { setRoom(data); setNda(null); }
    else if (data.code === 'nda_required' || data.code === 'nda_not_configured') setNda(data);

  }
  useEffect(() => {
    fetch(`${base}/challenge/`, { credentials: 'same-origin', headers: params.get('personal') ? { 'X-Room-Invitation': params.get('personal') } : {} }).then(r => r.json()).then(data => { setCsrf(data.csrf_token); setInvitation(data); }).catch(() => setError('Could not load your invitation. Please reload to try again.'));
    if (!params.get('personal')) loadRoom();
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
  async function personal() {
    setBusy(true); setError('');
    try {
      const response = await fetch(`${base}/personal/`, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: JSON.stringify({ token: params.get('personal') }) });
      if (!response.ok) { const d = await response.json(); throw new Error(d.detail || 'This personal link is no longer available.'); }
      await loadRoom();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function signNda() {
    setBusy(true); setError('');
    try {
      const url = `/api/v1/dealroom-sign/nda/${nda.room_id}/`;
      const options = { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrf } };
      let response = await fetch(url, options);
      if (!response.ok) { const d = await response.json(); throw new Error(d.detail || JSON.stringify(d)); }
      response = await fetch(url, { credentials: 'same-origin' });
      const status = await response.json();
      if (status.accepted) return await loadRoom();
      if (!status.can_enter) { setError('Your NDA is being prepared. Choose Review and sign again in a moment.'); return; }
      response = await fetch(`${url}enter/`, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Signing is not ready.');
      const destination = new URL(data.signing_url, window.location.origin);
      if (!['https:', 'http:'].includes(destination.protocol)) throw new Error('Invalid signing address.');
      window.location.assign(destination.href);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  if (nda) return <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6"><section className="max-w-lg rounded-xl border bg-white p-8 space-y-5">{identity}<h1 className="text-2xl font-semibold">Before you enter</h1><p className="text-sm text-muted-foreground">Review and sign the NDA. A signed copy will be emailed to you, then you can open the room.</p>{nda.code === 'nda_not_configured' ? <p>The host is preparing the NDA. Please come back shortly.</p> : <button className="dr-btn dr-btn--primary" disabled={busy} onClick={signNda}>{busy ? 'Preparing…' : 'Review and sign'}</button>}<button className="dr-btn" onClick={loadRoom}>I’ve signed · open the room</button>{error && <p role="alert" className="text-sm text-red-700">{error}</p>}</section></main>;
  if (!room && params.get('personal')) return <main className="min-h-screen bg-gray-50 flex items-center justify-center p-6"><section className="max-w-md rounded-xl border bg-white p-8 space-y-5">{identity}<h1 className="text-2xl font-semibold">{invitation?.sender_name ? `${invitation.sender_name} invited you` : 'You’re invited'}</h1><p className="text-sm text-muted-foreground">First, review and sign the NDA. You’ll receive a signed copy by email, then see your host’s note and documents. No account needed.</p><button className="dr-btn dr-btn--primary" disabled={busy || !csrf} onClick={personal}>{busy ? 'Opening…' : 'Review the NDA'}</button>{error && <p role="alert" className="text-sm text-red-700">{error}</p>}</section></main>;
  if (!room) return <main className="min-h-screen bg-muted flex flex-col items-center justify-center p-6">
    <form onSubmit={submit} className="w-full max-w-md rounded-xl border bg-card p-8 shadow-sm space-y-5">
      {identity}
      <div><h1 className="text-2xl font-semibold">{challenge ? 'Check your email' : 'Enter your deal room'}</h1><p className="text-sm text-muted-foreground mt-2">{challenge ? 'Enter the six-digit code, or confirm the link you opened. Your code expires after ten minutes.' : 'Verify your email to access confidential documents.'}</p></div>
      {!challenge && <><label className="block text-sm">Your name<input required className="mt-1 w-full border rounded-md p-3" value={name} onChange={e=>setName(e.target.value)} autoComplete="name" /></label><label className="block text-sm">Email address<input required type="email" className="mt-1 w-full border rounded-md p-3" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="email" /></label></>}
      {challenge && !params.get('token') && <label className="block text-sm">Verification code<input required inputMode="numeric" pattern="[0-9]{6}" maxLength={6} className="mt-1 w-full border rounded-md p-3 text-xl tracking-widest" value={code} onChange={e=>setCode(e.target.value)} autoComplete="one-time-code" /></label>}
      {error && <p role="alert" className="text-danger text-sm">{error}</p>}
      <button disabled={busy} className="w-full rounded-md bg-primary text-primary-foreground p-3 font-medium">{busy ? 'Please wait…' : challenge ? 'Confirm access' : 'Send verification code'}</button>
      {challenge && <button type="button" className="text-sm text-muted-foreground" onClick={()=>{setChallenge('');setError('')}}>Use another email or request a new code</button>}
      <p className="text-xs text-muted-foreground">Every copy is personalized. Access can be revoked by the room owner.</p>
    </form>
  </main>;
  return <RoomVisitor room={room} brand={brand} onRequest={async body => {
    const response = await fetch(`${base}/requests/`, { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: JSON.stringify(body) });
    if (!response.ok) { const data = await response.json(); throw new Error(data.detail || 'Could not send. Reload to check your access.'); }
    return response.json();
  }} />;
}
