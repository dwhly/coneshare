import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, FileDown, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { formatBytes } from '../../lib/formatters';
import { getLocalizedErrorMessage } from '../../utils/errorTranslator';
import { FileTypeIcon } from './FileTypeIcon';

import { isPreviewPending, isPreviewFailed } from '../../utils/previewState';

export function PreviewStatePanel({
  documentData,
  allowDownload = true,
  downloadUrl = null,
  className = '',
  onRetry = null,
  title: customTitle = null,
  message: customMessage = null,
}) {
  const { t } = useTranslation();
  const isFailed = isPreviewFailed(documentData);
  const isPending = isPreviewPending(documentData);
  const title = customTitle || (isFailed ? t('viewer.previewUnavailable') : t('viewer.preparingPreview'));
  const message = customMessage || (isFailed
    ? getLocalizedErrorMessage(documentData?.render_error || documentData?.render_message, 'viewer.previewCouldNotBeGenerated')
    : t('viewer.preparingPreviewNotice'));
  const href = downloadUrl || documentData?.download_url;

  const [showStuckRetry, setShowStuckRetry] = useState(false);

  // Both isPending and preview_status are listed as deps intentionally:
  // the timer must reset whenever the status string changes (even between
  // two pending states), not just when the boolean flips.
  useEffect(() => {
    setShowStuckRetry(false);
    if (!isPending) {
      return;
    }
    const timer = setTimeout(() => {
      setShowStuckRetry(true);
    }, 60000); // Show retry if stuck for > 60s
    return () => clearTimeout(timer);
  }, [isPending, documentData?.preview_status]);

  return (
    <div className={`flex h-full min-h-80 items-center justify-center p-4 ${className}`}>
      <div className="w-full max-w-xl rounded-2xl bg-card border border-border/80 p-8 sm:p-10 text-center shadow-xl shadow-foreground/50">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl">
          {isPending ? (
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-info-subtle text-info ring-8 ring-ring">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : isFailed ? (
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-warning-subtle text-warning ring-8 ring-warning-border">
              <AlertTriangle className="h-8 w-8" />
            </div>
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted text-muted-foreground ring-8 ring-border/60">
              <FileDown className="h-8 w-8" />
            </div>
          )}
        </div>

        <h1
          className="text-xl sm:text-2xl font-bold tracking-tight text-foreground truncate"
          title={documentData?.name || title}
        >
          {title}
        </h1>

        <p className="mt-2 text-sm text-muted-foreground leading-relaxed max-w-sm mx-auto">
          {message}
        </p>

        {isPending && (
          <div className="mx-auto my-5 h-1.5 w-48 overflow-hidden rounded-full bg-info-subtle/70">
            <div className="h-full w-2/5 animate-pulse rounded-full bg-info" />
          </div>
        )}

        {(documentData?.name || documentData?.file_size) && (
          <div className="my-6 flex items-center gap-3.5 rounded-xl border border-border/80 bg-muted/80 p-3.5 text-left">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-border/80 bg-card shadow-sm">
              <FileTypeIcon
                type={documentData?.type || documentData?.preview_mode || 'document'}
                className="h-6 w-6"
              />
            </div>
            <div className="min-w-0 flex-1">
              {documentData?.name && (
                <p className="truncate text-sm font-semibold text-foreground" title={documentData.name}>
                  {documentData.name}
                </p>
              )}
              {documentData?.file_size ? (
                <p className="text-xs font-medium text-muted-foreground">
                  {formatBytes(documentData.file_size)}
                </p>
              ) : null}
            </div>
          </div>
        )}

        {onRetry && (isFailed || (isPending && showStuckRetry)) && (
          <div className="mb-6 rounded-xl border border-warning-border bg-warning-subtle/70 p-3 text-xs sm:text-sm text-warning">
            <span>{t('viewer.havingTroubleViewing')}{' '}</span>
            <button
              type="button"
              onClick={onRetry}
              className="font-semibold text-brand hover:text-brand hover:underline focus:outline-none"
            >
              {t('viewer.retryGeneration')}
            </button>
          </div>
        )}

        {allowDownload && href ? (
          <Button asChild size="lg" className="w-full h-11 rounded-xl font-medium gap-2 shadow-sm">
            <a href={href} download={documentData?.name}>
              <FileDown className="h-4 w-4" />
              <span>{t('viewer.download')}</span>
            </a>
          </Button>
        ) : (
          <div>
            <Button size="lg" className="w-full h-11 rounded-xl font-medium gap-2" disabled>
              <FileDown className="h-4 w-4" />
              <span>{t('viewer.download')}</span>
            </Button>
            {!allowDownload && (
              <p className="mt-2.5 text-xs text-muted-foreground">
                {t('viewer.downloadDisabledNotice')}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
