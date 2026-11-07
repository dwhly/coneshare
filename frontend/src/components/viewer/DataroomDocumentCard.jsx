import { useTranslation } from 'react-i18next';
import { MessageCircle, Download, Eye, Lock } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import { formatBytes } from '../../lib/formatters';
import { FileTypeIcon, getDocumentBadgeStyle } from '../documents/FileTypeIcon';
import { Button } from '../ui/Button';

export function DataroomDocumentCard({
  item,
  index = null,
  showIndex = false,
  onItemClick,
  onDownloadClick,
  onQnaClick,
  qnaEnabled = true,
}) {
  const { t } = useTranslation();
  const indexLabel = index !== null ? `#${String(index).padStart(2, '0')}` : null;
  const isVideo = item.document_type === 'video' || item.type === 'video';

  return (
    <article
      data-testid={`document-card-${item.id}`}
      className="flex flex-col justify-between p-4 rounded-xl bg-card border border-border/60 shadow-2xs hover:shadow-xs hover:border-input transition-all gap-4"
    >
      <div className="flex items-start gap-3 min-w-0">
        {showIndex && indexLabel && (
          <span className="font-mono text-xs text-muted-foreground shrink-0 mt-0.5">
            {indexLabel}
          </span>
        )}
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${getDocumentBadgeStyle(item.document_type)}`}>
          <FileTypeIcon type={item.document_type} className="h-5 w-5 shrink-0" palette="viewer" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h4
              onClick={() => onItemClick(item)}
              className="text-sm font-medium text-foreground truncate hover:text-primary transition-colors cursor-pointer"
              title={item.name || item.document_name}
            >
              {item.name || item.document_name}
            </h4>
            {item.document_type && (
              <span className="px-1.5 py-0.5 rounded bg-muted font-mono text-[10px] text-muted-foreground uppercase">
                {item.document_type}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1 flex-wrap">
            {typeof item.file_size === 'number' && (
              <span>{formatBytes(item.file_size)}</span>
            )}
            {item.updated_at && (
              <>
                <span>•</span>
                <span>{formatRelativeTime(item.updated_at)}</span>
              </>
            )}
            {item.enable_watermark && (
              <>
                <span>•</span>
                <span className="inline-flex items-center gap-0.5 text-muted-foreground">
                  <Lock className="h-3 w-3" />
                  <span>{t('viewer.watermarked', { defaultValue: 'Watermarked' })}</span>
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 shrink-0 pt-1">
        {qnaEnabled && onQnaClick && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            title={t('qna.askQuestion', { defaultValue: 'Ask question' })}
            onClick={() => onQnaClick(item)}
          >
            <MessageCircle className="h-4 w-4" />
          </Button>
        )}
        {item.allow_download && onDownloadClick && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
            title={t('viewer.download', { defaultValue: 'Download' })}
            onClick={() => onDownloadClick(item)}
          >
            <Download className="h-4 w-4" />
          </Button>
        )}
        <Button
          size="sm"
          className="h-8 px-3 text-xs font-medium gap-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs transition-all"
          onClick={() => onItemClick(item)}
        >
          <Eye className="h-3.5 w-3.5" />
          <span>{isVideo ? t('viewer.watchVideo', { defaultValue: 'Watch Video' }) : t('viewer.viewDocument', { defaultValue: 'View Document' })}</span>
        </Button>
      </div>
    </article>
  );
}
