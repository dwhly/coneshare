import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { Folder, MessageCircle, ChevronRight, ChevronDown, ChevronUp, MoreHorizontal, Eye, Download as DownloadIcon } from 'lucide-react';
import { formatRelativeTime } from '../../utils/formatters';
import { Button } from '../ui/Button';

export function DataroomFolderGrid({
  folders = [],
  onFolderClick,
  onDownloadClick,
  onQnaClick,
  qnaEnabled = true,
  showIndex = true,
  maxInitialCount = 6,
  showEmpty = false,
  emptyMessage,
}) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  if (!folders || folders.length === 0) {
    if (!showEmpty) {
      return null;
    }

    return (
      <section aria-label={t('documents.folders', { defaultValue: 'Folders' })} className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs uppercase tracking-wider font-semibold text-foreground">
            {t('documents.folders', { defaultValue: 'Folders' })} (0)
          </span>
        </div>

        <div className="rounded-xl border border-border/60 bg-card p-6 flex flex-col items-center justify-center text-center shadow-2xs">
          <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-2">
            <Folder className="h-4 w-4" />
          </div>
          <p className="text-xs font-medium text-muted-foreground">
            {emptyMessage || t('viewer.noFolders', { defaultValue: 'No folders in this directory' })}
          </p>
        </div>
      </section>
    );
  }

  const displayedFolders = isExpanded ? folders : folders.slice(0, maxInitialCount);

  return (
    <section aria-label={t('documents.folders', { defaultValue: 'Folders' })} className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-wider font-semibold text-foreground">
            {t('documents.folders', { defaultValue: 'Folders' })} ({folders.length})
          </span>
          {folders.length > maxInitialCount && !isExpanded && (
            <span className="px-1.5 py-0.5 rounded bg-muted font-mono text-[11px] text-muted-foreground hidden sm:inline">
              {t('common.showingCount', { count: maxInitialCount, defaultValue: `Showing ${maxInitialCount}` })}
            </span>
          )}
        </div>
        {folders.length > maxInitialCount && (
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <span>
              {isExpanded
                ? t('common.showLess', { defaultValue: 'Show less' })
                : t('common.showAllFolders', { count: folders.length, defaultValue: `Show all ${folders.length} folders` })}
            </span>
            {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {displayedFolders.map((folder, idx) => {
          const indexLabel = String(idx + 1).padStart(2, '0');
          return (
            <div
              key={folder.id}
              onClick={() => onFolderClick?.(folder)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.target !== e.currentTarget) return;
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onFolderClick?.(folder);
                }
              }}
              data-testid={`folder-card-${folder.id}`}
              className="group rounded-xl bg-card p-3.5 shadow-2xs hover:shadow-xs hover:border-input hover:bg-accent transition-all flex flex-col justify-between cursor-pointer border border-border/60"
            >
              {/* Top Row: Icon, Folder Name, and Actions */}
              <div className="flex items-center justify-between gap-2 min-w-0">
                <div className="flex items-center gap-2.5 min-w-0 flex-1 pr-1">
                  {showIndex && (
                    <span className="font-mono text-[11px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded shrink-0 self-center">
                      {indexLabel}
                    </span>
                  )}
                  <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0 text-muted-foreground group-hover:text-foreground group-hover:bg-accent/70 transition-colors">
                    <Folder className="h-4 w-4" />
                  </div>
                  <span
                    className="text-sm font-medium text-foreground truncate block group-hover:text-primary transition-colors flex-1"
                    title={folder.name}
                  >
                    {folder.name}
                  </span>
                </div>

                {/* Quick Actions: Q&A + 3-dots Menu */}
                <div className="flex items-center gap-1 shrink-0 opacity-80 sm:opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
                  {qnaEnabled && onQnaClick && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-accent/60"
                      title={t('qna.folderQna', { defaultValue: 'Folder Q&A' })}
                      onClick={(e) => {
                        e.stopPropagation();
                        onQnaClick?.(folder);
                      }}
                    >
                      <MessageCircle className="h-3.5 w-3.5" />
                    </Button>
                  )}
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-foreground hover:bg-accent/60"
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                        aria-label={t('common.actionsFor', { name: folder.name, defaultValue: `Actions for ${folder.name}` })}
                      >
                        <MoreHorizontal className="h-3.5 w-3.5" />
                      </Button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Portal>
                      <DropdownMenu.Content
                        className="z-[9999] w-40 origin-top-right rounded-md bg-card p-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
                        sideOffset={5}
                        align="end"
                        onCloseAutoFocus={(e) => e.preventDefault()}
                      >
                        <DropdownMenu.Item
                          onSelect={(e) => {
                            e.stopPropagation();
                            onFolderClick?.(folder);
                          }}
                          className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
                        >
                          <Eye className="h-4 w-4" aria-hidden="true" />
                          <span>{t('viewer.view')}</span>
                        </DropdownMenu.Item>
                        {folder.allow_download && onDownloadClick && (
                          <DropdownMenu.Item
                            onSelect={(e) => {
                              e.stopPropagation();
                              onDownloadClick(folder);
                            }}
                            className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
                          >
                            <DownloadIcon className="h-4 w-4" aria-hidden="true" />
                            <span>{t('viewer.download')}</span>
                          </DropdownMenu.Item>
                        )}
                        {qnaEnabled && onQnaClick && (
                          <DropdownMenu.Item
                            onSelect={(e) => {
                              e.stopPropagation();
                              onQnaClick?.(folder);
                            }}
                            className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
                          >
                            <MessageCircle className="h-4 w-4" aria-hidden="true" />
                            <span>{t('qna.title', { defaultValue: 'Q&A' })}</span>
                          </DropdownMenu.Item>
                        )}
                      </DropdownMenu.Content>
                    </DropdownMenu.Portal>
                  </DropdownMenu.Root>
                </div>
              </div>

              {/* Divider & Bottom Row: Update Time + Right Arrow */}
              <div className="pt-2.5 mt-2.5 border-t border-border flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
                <div className="truncate min-w-0">
                  {folder.updated_at ? (
                    <span className="font-normal truncate block">
                      {t('common.updated', { defaultValue: 'Updated' })} {formatRelativeTime(folder.updated_at)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground/70">—</span>
                  )}
                </div>
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-foreground group-hover:translate-x-0.5 transition-all shrink-0" />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
