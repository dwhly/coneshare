import { useEffect, useState } from 'react';
import api from '../../services/api';
import { Card, SelectMenu, errorText } from './shell';

export default function WatermarkSettings({ roomStyle, onSave }) {
  const isRoom = Boolean(onSave);
  const [style, setStyle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    if (isRoom) return;
    let alive = true;
    api.get('/dealroom/workspace-settings/').then(r => { if (alive) setStyle(r.data.watermark_style); })
      .catch(e => { if (alive) setError(errorText(e)); });
    return () => { alive = false; };
  }, [isRoom]);
  async function change(value) {
    setBusy(true); setError(''); setSaved(false);
    try {
      if (isRoom) await onSave(value === 'default' ? null : value);
      else { const r = await api.patch('/dealroom/workspace-settings/', { watermark_style: value }); setStyle(r.data.watermark_style); }
      setSaved(true);
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  return <Card title={isRoom ? 'Room watermark style' : 'Workspace watermark style'} subtitle={isRoom ? 'Use the workspace default, or choose a style for this room.' : 'The default for every room, viewer page and downloaded watermarked PDF.'}>
    <SelectMenu label="Watermark style" value={isRoom ? roomStyle || 'default' : style} onChange={change} disabled={busy || (!isRoom && !style)}
      options={[...(isRoom ? [{ value: 'default', label: 'Workspace default' }] : []), { value: 'diagonal', label: 'Diagonal' }, { value: 'edge', label: 'Edge' }]} />
    <p className="text-sm text-muted-foreground mt-3">Diagonal places low-opacity text across the page. Edge uses one small line along the bottom.</p>
    <p className="text-xs text-muted-foreground mt-2">Both include company and individual details with the Copy ID.</p>
    {saved && <p role="status" className="text-sm mt-3">Watermark style saved.</p>}
    {error && <p role="alert" className="text-sm mt-3">{error}</p>}
  </Card>;
}
