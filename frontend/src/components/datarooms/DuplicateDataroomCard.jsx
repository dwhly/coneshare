// AmForge: "Duplicate room" action for the dataroom settings tab.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Copy, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { duplicateDataroom } from '../../services/amforgeApi';
import { Button } from '../ui/Button';
import { Switch } from '../ui/Switch';

export function DuplicateDataroomCard({ dataroom }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [includeLinks, setIncludeLinks] = useState(true);
  const [isDuplicating, setIsDuplicating] = useState(false);

  const handleDuplicate = async () => {
    setIsDuplicating(true);
    try {
      const res = await duplicateDataroom(dataroom.id, { include_share_links: includeLinks });
      const copy = res.data?.dataroom;
      toast.success(t('amforge.duplicate.success', {
        name: copy?.name,
        documents: res.data?.document_count ?? 0,
        folders: res.data?.folder_count ?? 0,
      }));
      if (copy?.id) navigate(`/datarooms/${copy.id}`);
    } catch {
      // Error toast handled by interceptor
    } finally {
      setIsDuplicating(false);
    }
  };

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t('amforge.duplicate.title')}</h3>
      </div>
      <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">{t('amforge.duplicate.notice')}</p>
      <div className="flex items-center justify-between rounded border border-gray-200 p-3 dark:border-gray-700">
        <div>
          <p className="text-sm font-medium">{t('amforge.duplicate.includeLinks')}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{t('amforge.duplicate.includeLinksHelp')}</p>
        </div>
        <Switch
          checked={includeLinks}
          onCheckedChange={setIncludeLinks}
          aria-label={t('amforge.duplicate.includeLinks')}
        />
      </div>
      <div className="mt-3">
        <Button type="button" variant="outline" size="sm" onClick={handleDuplicate} disabled={isDuplicating}>
          {isDuplicating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Copy className="mr-2 h-4 w-4" />}
          {t('amforge.duplicate.button')}
        </Button>
      </div>
    </div>
  );
}
