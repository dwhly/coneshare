// AmForge: organisation / email access grants for a share link.
// Rendered inside LinkSheet; reuses the sheet's existing Switch/Input/Select/Button primitives.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import {
  addShareLinkAccessGrant,
  createViewerOrganisation,
  getShareLinkAccessGrants,
  getViewerOrganisations,
  removeShareLinkAccessGrant,
} from '../../services/amforgeApi';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Select } from '../ui/Select';
import { Switch } from '../ui/Switch';

const listOf = (res) => (Array.isArray(res?.data) ? res.data : res?.data?.results || []);

/**
 * Applies grants queued while creating a link (no link id yet).
 */
export async function applyPendingGrants(linkId, pendingGrants) {
  for (const grant of pendingGrants || []) {
    await addShareLinkAccessGrant(linkId, grant.viewer_organisation
      ? { viewer_organisation: grant.viewer_organisation }
      : { email: grant.email });
  }
}

export function AccessGrantsSection({
  isOpen,
  linkId,
  restrictToGrants,
  onRestrictToGrantsChange,
  pendingGrants,
  onPendingGrantsChange,
}) {
  const { t } = useTranslation();
  const [organisations, setOrganisations] = useState([]);
  const [grants, setGrants] = useState([]);
  const [selectedOrgId, setSelectedOrgId] = useState('');
  const [email, setEmail] = useState('');
  const [showNewOrg, setShowNewOrg] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgDomains, setNewOrgDomains] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    getViewerOrganisations().then((res) => setOrganisations(listOf(res))).catch(() => {});
    if (linkId) {
      getShareLinkAccessGrants(linkId).then((res) => setGrants(listOf(res))).catch(() => {});
    } else {
      setGrants([]);
    }
  }, [isOpen, linkId]);

  const orgById = Object.fromEntries(organisations.map((o) => [o.id, o]));
  const shownGrants = linkId
    ? grants
    : (pendingGrants || []).map((g, i) => ({
        id: `pending-${i}`,
        viewer_organisation: g.viewer_organisation || null,
        viewer_organisation_name: g.viewer_organisation ? orgById[g.viewer_organisation]?.name : null,
        viewer_organisation_domains: g.viewer_organisation ? orgById[g.viewer_organisation]?.email_domains : [],
        email: g.email || '',
      }));

  const addGrant = async (payload) => {
    if (!linkId) {
      const exists = (pendingGrants || []).some(
        (g) => (payload.viewer_organisation && g.viewer_organisation === payload.viewer_organisation)
          || (payload.email && g.email === payload.email),
      );
      if (!exists) onPendingGrantsChange([...(pendingGrants || []), payload]);
      return true;
    }
    setBusy(true);
    try {
      const res = await addShareLinkAccessGrant(linkId, payload);
      setGrants((prev) => [...prev, res.data]);
      return true;
    } catch {
      return false;
    } finally {
      setBusy(false);
    }
  };

  const removeGrant = async (grant) => {
    if (!linkId) {
      const idx = Number(String(grant.id).replace('pending-', ''));
      onPendingGrantsChange((pendingGrants || []).filter((_, i) => i !== idx));
      return;
    }
    setBusy(true);
    try {
      await removeShareLinkAccessGrant(linkId, grant.id);
      setGrants((prev) => prev.filter((g) => g.id !== grant.id));
    } finally {
      setBusy(false);
    }
  };

  const handleAddOrg = async () => {
    if (!selectedOrgId) return;
    if (await addGrant({ viewer_organisation: selectedOrgId })) setSelectedOrgId('');
  };

  const handleAddEmail = async () => {
    const value = email.trim().toLowerCase();
    if (!value || !value.includes('@')) return;
    if (await addGrant({ email: value })) setEmail('');
  };

  const handleCreateOrg = async () => {
    const name = newOrgName.trim();
    const domains = newOrgDomains.split(/[\s,;]+/).map((d) => d.trim()).filter(Boolean);
    if (!name || domains.length === 0) return;
    setBusy(true);
    try {
      const res = await createViewerOrganisation({ name, email_domains: domains });
      setOrganisations((prev) => [...prev, res.data].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedOrgId(res.data.id);
      setNewOrgName('');
      setNewOrgDomains('');
      setShowNewOrg(false);
      toast.success(t('amforge.grants.orgCreated', { name: res.data.name }));
    } catch {
      // global interceptor shows the error
    } finally {
      setBusy(false);
    }
  };

  const grantedOrgIds = new Set(shownGrants.map((g) => g.viewer_organisation).filter(Boolean));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label htmlFor="restrict-to-grants" className="flex flex-col space-y-1">
          <span>{t('amforge.grants.restrict')}</span>
          <span className="text-sm font-normal text-muted-foreground">
            {t('amforge.grants.restrictSubtitle')}
          </span>
        </Label>
        <Switch
          id="restrict-to-grants"
          checked={restrictToGrants}
          onCheckedChange={onRestrictToGrantsChange}
        />
      </div>
      {restrictToGrants && (
        <div className="space-y-4 rounded-md border bg-gray-50 p-4 dark:bg-gray-800/50">
          {shownGrants.length === 0 ? (
            <p className="text-sm text-muted-foreground">{t('amforge.grants.empty')}</p>
          ) : (
            <ul className="space-y-2" data-testid="access-grant-list">
              {shownGrants.map((grant) => (
                <li key={grant.id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="min-w-0 truncate">
                    {grant.viewer_organisation ? (
                      <>
                        <span className="font-medium">{grant.viewer_organisation_name}</span>
                        <span className="text-muted-foreground">
                          {' '}
                          ({(grant.viewer_organisation_domains || []).map((d) => `@${d}`).join(', ')})
                        </span>
                      </>
                    ) : (
                      <span>{grant.email}</span>
                    )}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0"
                    onClick={() => removeGrant(grant)}
                    disabled={busy}
                    aria-label={t('amforge.grants.remove')}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}

          <div className="space-y-2">
            <Label htmlFor="grant-org">{t('amforge.grants.organisation')}</Label>
            <div className="flex gap-2">
              <Select
                id="grant-org"
                value={selectedOrgId}
                onChange={(e) => setSelectedOrgId(e.target.value)}
              >
                <option value="">{t('amforge.grants.selectOrganisation')}</option>
                {organisations.filter((o) => !grantedOrgIds.has(o.id)).map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name} ({(o.email_domains || []).join(', ')})
                  </option>
                ))}
              </Select>
              <Button type="button" variant="outline" onClick={handleAddOrg} disabled={busy || !selectedOrgId}>
                {t('amforge.grants.add')}
              </Button>
            </div>
            {!showNewOrg ? (
              <button
                type="button"
                className="text-sm text-muted-foreground underline-offset-4 hover:underline"
                onClick={() => setShowNewOrg(true)}
              >
                {t('amforge.grants.newOrganisation')}
              </button>
            ) : (
              <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <Input
                  id="new-org-name"
                  value={newOrgName}
                  onChange={(e) => setNewOrgName(e.target.value)}
                  placeholder={t('amforge.grants.orgNamePlaceholder')}
                />
                <Input
                  id="new-org-domains"
                  value={newOrgDomains}
                  onChange={(e) => setNewOrgDomains(e.target.value)}
                  placeholder={t('amforge.grants.orgDomainsPlaceholder')}
                />
                <Button type="button" variant="outline" onClick={handleCreateOrg} disabled={busy}>
                  {t('amforge.grants.create')}
                </Button>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="grant-email">{t('amforge.grants.person')}</Label>
            <div className="flex gap-2">
              <Input
                id="grant-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddEmail();
                  }
                }}
                placeholder="name@company.com"
              />
              <Button type="button" variant="outline" onClick={handleAddEmail} disabled={busy || !email.trim()}>
                {t('amforge.grants.add')}
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">{t('amforge.grants.verificationNote')}</p>
        </div>
      )}
    </div>
  );
}
