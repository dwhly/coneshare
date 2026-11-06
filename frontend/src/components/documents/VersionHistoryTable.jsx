import { useTranslation } from 'react-i18next';
import { formatBytes } from '../../lib/formatters';
import { formatDate } from '../../utils/formatters';
import { Eye, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';
import { Pagination } from '../ui/Pagination';
import { Skeleton } from '../ui/Skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/Table';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/Tooltip';

export function VersionHistoryTable({
  versions,
  totalCount,
  loading,
  currentPage,
  onPageChange,
  pageSize = 10,
  onPreviewVersion,
  onPromoteVersion,
}) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div>
        <h2 className="text-xl font-semibold">{t('documents.versions')}</h2>
        <div className="mt-4 space-y-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <div>
        <h2 className="text-xl font-semibold">{t('documents.versions')}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{t('documents.noVersions')}</p>
      </div>
    );
  }

  const totalPages = pageSize > 0 ? Math.ceil(totalCount / pageSize) : 0;

  const getSourceDisplay = (version) => {
    const cloudImport = version.cloud_import;
    if (cloudImport) {
      return t('documents.importedFrom', { provider: cloudImport.provider_display || cloudImport.provider });
    }
    return t('documents.manualUpload');
  };

  const getStatusBadge = (version) => {
    const badges = [];

    // Render status badge
    if (version.render_status === 'failed') {
      badges.push(
        <Tooltip key="failed">
          <TooltipTrigger asChild>
            <span className="inline-flex cursor-help items-center rounded-full bg-danger-subtle px-2 py-1 text-xs font-medium text-danger ring-1 ring-inset ring-danger/10">
              {t('documents.errorStatus')}
            </span>
          </TooltipTrigger>
          {version.render_error && (
            <TooltipContent>
              <p className="max-w-xs text-xs">{version.render_error}</p>
            </TooltipContent>
          )}
        </Tooltip>
      );
    } else if (version.render_status === 'processing' || version.render_status === 'queued') {
      badges.push(
        <span key="processing" className="inline-flex items-center rounded-full bg-info-subtle px-2 py-1 text-xs font-medium text-info ring-1 ring-inset ring-ring">
          {t('documents.processingStatus')}
        </span>
      );
    } else if (version.render_status === 'ready') {
      badges.push(
        <span key="ready" className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-xs font-medium text-foreground ring-1 ring-inset ring-foreground/20">
          {t('documents.readyStatus')}
        </span>
      );
    } else {
      // Fallback for other statuses like 'not_generated'
      const statusLabel = version.render_status
        ? version.render_status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
        : 'Unknown';
      badges.push(
        <span key="other" className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-xs font-medium text-muted-foreground ring-1 ring-inset ring-foreground/10">
          {statusLabel}
        </span>
      );
    }

    return (
      <div className="flex flex-col gap-1 items-start">
        <div className="flex flex-wrap gap-1.5">
          {badges}
        </div>
        {version.render_status === 'failed' && version.render_error && (
          <span className="text-xs text-danger max-w-[200px] truncate" title={version.render_error}>
            {version.render_error}
          </span>
        )}
      </div>
    );
  };

  return (
    <TooltipProvider>
      <div>
        <h2 className="text-xl font-semibold">{t('documents.versions')}</h2>
        <div className="mt-4 overflow-hidden rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('documents.versionColumn')}</TableHead>
                <TableHead>{t('documents.uploadDateColumn')}</TableHead>
                <TableHead>{t('documents.sourceColumn')}</TableHead>
                <TableHead>{t('documents.fileSizeColumn')}</TableHead>
                <TableHead>{t('documents.statusColumn')}</TableHead>
                <TableHead className="text-right">{t('common.actions')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versions.map((version) => (
                <TableRow key={version.id}>
                  <TableCell className="font-semibold">
                    <div className="flex items-center gap-2">
                      <span>v{version.version_number}</span>
                      {version.file_name && (
                        <span className="text-xs font-normal text-gray-500 truncate max-w-[180px]" title={version.file_name}>
                          ({version.file_name})
                        </span>
                      )}
                      {version.is_primary && (
                        <span className="inline-flex items-center rounded-full bg-success-subtle px-2 py-0.5 text-xs font-medium text-success ring-1 ring-inset ring-success/20">
                          {t('documents.activeStatus')}
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {formatDate(version.created_at, 'PP p')}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{getSourceDisplay(version)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {version.file_size != null ? formatBytes(version.file_size) : '—'}
                  </TableCell>
                  <TableCell>{getStatusBadge(version)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onPreviewVersion(version)}
                        className="inline-flex items-center gap-1"
                        title={t('viewer.preview')}
                      >
                        <Eye className="h-4 w-4" />
                        <span>{t('viewer.preview')}</span>
                      </Button>
                      {!version.is_primary && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onPromoteVersion(version)}
                          className="inline-flex items-center gap-1 border-info-border text-info hover:bg-info-subtle hover:text-info"
                          title={t('documents.restore')}
                        >
                          <RefreshCw className="h-4 w-4" />
                          <span>{t('documents.restore')}</span>
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {totalPages > 1 && (
          <Pagination
            totalPages={totalPages}
            currentPage={currentPage}
            onPageChange={onPageChange}
          />
        )}
      </div>
    </TooltipProvider>
  );
}
