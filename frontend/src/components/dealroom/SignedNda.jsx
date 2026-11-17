import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { isSafeUrl } from '../../lib/utils';

export function useSignedNda(base, initial = null) {
  const [copy, setCopy] = useState(initial);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!base || copy?.download_url) return;
    let alive = true;
    let timer;
    const controller = new AbortController();
    async function poll() {
      try {
        const response = await fetch(`${base}/signed-nda/`, { credentials: 'same-origin', signal: controller.signal });
        if (!response.ok) throw new Error('Could not check your signed copy. Verify your access or try again.');
        const data = await response.json();
        if (!alive) return;
        setCopy(data); setError('');
        if (!data.download_url) timer = setTimeout(poll, 2000);
      } catch (e) { if (alive) setError(e.message); }
    }
    poll();
    return () => { alive = false; controller.abort(); clearTimeout(timer); };
  }, [base, retry, Boolean(copy?.download_url)]);
  return { copy, error, retry: () => { setError(''); setRetry(n => n + 1); } };
}

export function SignedNdaDownload({ copy }) {
  return copy?.download_url && isSafeUrl(copy.download_url)
    ? <a className="dr-btn" href={copy.download_url}><Download className="h-4 w-4" />Download your signed NDA</a>
    : <button className="dr-btn" disabled>Preparing your copy…</button>;
}

export function SignedNdaConfirmation({ base, identity, onEnter }) {
  const { copy, error, retry } = useSignedNda(base);
  return <main className="min-h-screen bg-gray-50 flex items-center justify-center p-5 sm:p-8">
    <section className="w-full max-w-lg rounded-xl border bg-white p-6 sm:p-8 space-y-6">
      {identity}
      <div><h1 className="text-3xl font-semibold">{copy?.signed ? 'Your NDA is signed' : 'Confirming your signature…'}</h1>
        <p className="text-sm text-muted-foreground mt-3">{copy?.signed ? 'Thank you. Your host’s note and documents are waiting for you.' : 'We’re checking the signing confirmation. This page will update automatically.'}</p></div>
      <button className="dr-btn dr-btn--primary w-full min-h-14 text-base" disabled={!copy?.can_enter} onClick={onEnter}>Enter the data room</button>
      <SignedNdaDownload copy={copy} />
      {copy?.signed && <p className="text-sm break-words">A copy is also on its way to {copy.email}.</p>}
      {copy?.signed && !copy.can_enter && <p className="text-sm text-muted-foreground">{copy.state === 'done' ? 'Room access is unavailable. You can still download your signed NDA.' : 'Finishing your NDA. Room access will be ready when the sealed copy is confirmed.'}</p>}
      {error && <div role="alert" className="text-sm space-y-3"><p>{error}</p><button className="dr-btn" onClick={retry}>Try again</button></div>}
    </section>
  </main>;
}

export function PersonalNda({ initial, base }) {
  const { copy, error, retry } = useSignedNda(base, initial);
  if (!copy?.signed) return null;
  return <section className="border-t pt-7 space-y-3" aria-label="Your signed NDA">
    <h2 className="text-xl font-semibold">Your signed NDA</h2>
    {copy.signed_at && <p className="text-sm text-muted-foreground">Signed {new Date(copy.signed_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}</p>}
    <p className="text-sm text-muted-foreground">Your personal signed copy. Always available to download, without a watermark.</p>
    <SignedNdaDownload copy={copy} />
    {error && <div role="alert"><p className="text-sm">{error}</p><button className="dr-btn" onClick={retry}>Try again</button></div>}
  </section>;
}
