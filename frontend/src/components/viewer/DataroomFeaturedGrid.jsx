import { useTranslation } from 'react-i18next';
import {
  Star,
  Folder,
  Eye,
  ChevronRight,
  Lock,
} from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import { formatBytes } from '../../lib/formatters';
import { FileTypeIcon, getDocumentBadgeStyle } from '../documents/FileTypeIcon';
import { Button } from '../ui/Button';

export function DataroomFeaturedGrid({
  items = [],
  onItemClick,
  onFolderClick,
}) {
  const { t } = useTranslation();

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <section aria-label={t('viewer.featuredResources', { defaultValue: 'Featured Resources' })} className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-wider font-semibold text-foreground flex items-center gap-1.5">
            <Star className="h-3.5 w-3.5 fill-warning text-warning" />
            {t('viewer.featuredResources', { defaultValue: 'Featured Resources' })} ({items.length})
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {items.map((item) => {
          const isFolder = item.isFolder || item.type === 'folder' || !item.document_type;
          const isVideo = item.document_type === 'video' || item.type === 'video';

          return (
            <div
              key={item.id}
              data-testid={`featured-card-${item.id}`}
              className="group rounded-xl border border-border/80 bg-card p-4 shadow-2xs hover:shadow-xs hover:border-input transition-all flex flex-col justify-between gap-3.5 relative"
            >
              {/* Top Row: File/Folder Icon on the left, File Type Badge on the right */}
              <div className="flex items-center justify-between gap-2">
                {isFolder ? (
                  <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center shrink-0 text-muted-foreground group-hover:text-foreground group-hover:bg-accent/70 transition-colors">
                    <Folder className="h-5 w-5" />
                  </div>
                ) : (
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${getDocumentBadgeStyle(item.document_type)}`}>
                    <FileTypeIcon type={item.document_type} className="h-5 w-5 shrink-0" palette="viewer" />
                  </div>
                )}

                <span className="px-2 py-0.5 rounded bg-muted font-mono text-[10px] font-semibold text-muted-foreground uppercase tracking-wide shrink-0">
                  {isFolder
                    ? t('documents.folders', { defaultValue: 'Folder' })
                    : item.document_type || 'FILE'}
                </span>
              </div>

              {/* Middle Identity Block: Name + Meta */}
              <div className="min-w-0 flex-1">
                <h4
                  onClick={() => (isFolder ? onFolderClick?.(item) : onItemClick?.(item))}
                  className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors cursor-pointer"
                  title={item.name}
                >
                  {item.name}
                </h4>
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground mt-1 flex-wrap">
                  {!isFolder && typeof item.file_size === 'number' && (
                    <span>{formatBytes(item.file_size)}</span>
                  )}
                  {item.updated_at && (
                    <>
                      {!isFolder && typeof item.file_size === 'number' && <span>•</span>}
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

              {/* Bottom Action Button */}
              <div className="pt-1">
                {isFolder ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-8 px-3 text-xs font-medium gap-1.5 rounded-lg border-border hover:bg-accent text-foreground shadow-2xs transition-all flex items-center justify-center"
                    onClick={() => onFolderClick?.(item)}
                  >
                    <span>{t('viewer.openFolder', { defaultValue: 'Open Folder' })}</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    className="w-full h-8 px-3 text-xs font-medium gap-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs transition-all flex items-center justify-center"
                    onClick={() => onItemClick?.(item)}
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>
                      {isVideo
                        ? t('viewer.watchVideo', { defaultValue: 'Watch Video' })
                        : t('viewer.viewDocument', { defaultValue: 'View Document' })}
                    </span>
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
