import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Check,
  Folder,
  GripVertical,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Button } from '../ui/Button';
import { FileTypeIcon, getDocumentBadgeStyle } from '../documents/FileTypeIcon';
import { formatBytes } from '../../lib/formatters';
import { formatRelativeTime } from '../../utils/formatters';

function moveItem(list, from, to) {
  if (to < 0 || to >= list.length) return list;
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

function sortAlphabeticalChronological(list) {
  return [...list].sort((a, b) => {
    const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
    if (aTime !== bTime) return aTime - bTime;
    return String(a.name || a.id).localeCompare(String(b.name || b.id));
  });
}

function ReorderRow({
  item,
  index,
  total,
  isSaving,
  onDragStart,
  onDrop,
  onMoveUp,
  onMoveDown,
}) {
  const { t } = useTranslation();
  const isFirst = index === 0;
  const isLast = index === total - 1;
  const isFolder = item.type === 'folder';
  const docType = item.document_type || item.type;

  return (
    <li
      draggable={!isSaving}
      onDragStart={onDragStart}
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      className="group flex items-center justify-between px-3 py-2.5 bg-muted/70 hover:bg-accent border border-border/80 rounded-xl transition duration-150 gap-2"
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <button
          type="button"
          className="cursor-grab active:cursor-grabbing text-muted-foreground group-hover:text-muted-foreground p-0.5"
          title={t('datarooms.dragToReorder')}
          tabIndex={-1}
        >
          <GripVertical className="h-4 w-4" />
        </button>
        <span className="font-mono text-xs font-semibold text-muted-foreground bg-card border border-border/80 px-2 py-0.5 rounded shadow-xs shrink-0">
          {String(index + 1).padStart(2, '0')}
        </span>
        {isFolder ? (
          <div className="w-7 h-7 rounded-lg bg-warning-subtle/70 border border-warning-border flex items-center justify-center text-warning shrink-0">
            <Folder className="w-4 h-4 fill-warning/20" />
          </div>
        ) : (
          <div className={`w-7 h-7 rounded-lg border flex items-center justify-center shrink-0 ${getDocumentBadgeStyle(docType)}`}>
            <FileTypeIcon type={docType} className="h-4 w-4 shrink-0" palette="viewer" />
          </div>
        )}
        <div className="truncate min-w-0 flex-1">
          {isFolder ? (
            <div className="flex items-baseline gap-2 truncate">
              <span className="text-sm font-medium text-foreground truncate">
                {item.name}
              </span>
              <span className="text-[11px] text-muted-foreground font-normal shrink-0 hidden md:inline">
                {t('datarooms.cardPosition', { position: index + 1 })}
              </span>
            </div>
          ) : (
            <>
              <span className="text-sm font-medium text-foreground truncate block">
                {item.name}
              </span>
              {(typeof item.file_size === 'number' || item.updated_at) && (
                <span className="text-[11px] text-muted-foreground font-normal flex items-center gap-1.5 mt-0.5">
                  {typeof item.file_size === 'number' && <span>{formatBytes(item.file_size)}</span>}
                  {typeof item.file_size === 'number' && item.updated_at && <span>•</span>}
                  {item.updated_at && <span>{formatRelativeTime(item.updated_at)}</span>}
                </span>
              )}
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="h-7 w-7 rounded-lg border border-border bg-card text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent"
          disabled={isFirst || isSaving}
          onClick={onMoveUp}
          aria-label={t('datarooms.moveItemUp', { name: item.name })}
        >
          <ArrowUp className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="h-7 w-7 rounded-lg border border-border bg-card text-muted-foreground disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent"
          disabled={isLast || isSaving}
          onClick={onMoveDown}
          aria-label={t('datarooms.moveItemDown', { name: item.name })}
        >
          <ArrowDown className="h-3.5 w-3.5" />
        </Button>
      </div>
    </li>
  );
}

export function DataroomReorderItemsDialog({
  isOpen,
  onOpenChange,
  items = [],
  onConfirm,
  currentFolderName = null,
}) {
  const { t } = useTranslation();
  const [orderedFolders, setOrderedFolders] = useState([]);
  const [orderedDocs, setOrderedDocs] = useState([]);
  const [dragFolderIndex, setDragFolderIndex] = useState(null);
  const [dragDocIndex, setDragDocIndex] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const prevOpenRef = useRef(false);

  useEffect(() => {
    if (isOpen && !prevOpenRef.current) {
      setOrderedFolders(items.filter((item) => item.type === 'folder'));
      setOrderedDocs(items.filter((item) => item.type !== 'folder'));
      setDragFolderIndex(null);
      setDragDocIndex(null);
    }
    prevOpenRef.current = isOpen;
  }, [isOpen, items]);

  const titleScope = useMemo(
    () => (currentFolderName ? t('datarooms.reorderScopeFolder', { name: currentFolderName }) : t('datarooms.reorderScopeRoot')),
    [currentFolderName, t]
  );

  const handleFolderDrop = (targetIndex) => {
    if (dragFolderIndex === null || dragFolderIndex === targetIndex) return;
    setOrderedFolders((prev) => moveItem(prev, dragFolderIndex, targetIndex));
    setDragFolderIndex(null);
  };

  const handleDocDrop = (targetIndex) => {
    if (dragDocIndex === null || dragDocIndex === targetIndex) return;
    setOrderedDocs((prev) => moveItem(prev, dragDocIndex, targetIndex));
    setDragDocIndex(null);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onConfirm([...orderedFolders, ...orderedDocs]);
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetOrder = () => {
    const rawFolders = items.filter((item) => item.type === 'folder');
    const rawDocs = items.filter((item) => item.type !== 'folder');
    setOrderedFolders(sortAlphabeticalChronological(rawFolders));
    setOrderedDocs(sortAlphabeticalChronological(rawDocs));
  };

  const hasFolders = orderedFolders.length > 0;
  const hasDocs = orderedDocs.length > 0;
  const hasItems = hasFolders || hasDocs;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => {
      if (!isSaving) {
        onOpenChange(open);
      }
    }}>
      <DialogContent className="sm:max-w-2xl max-h-[88vh] flex flex-col p-6">
        <DialogHeader className="pb-3 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-muted text-foreground flex items-center justify-center border border-border/60 shrink-0">
              <ArrowUpDown className="w-4 h-4" />
            </div>
            <div className="space-y-0.5 min-w-0">
              <DialogTitle>{t('datarooms.reorderItemsTitle')}</DialogTitle>
              <DialogDescription>
                {t('datarooms.reorderDescription', { scope: titleScope })}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto max-h-[60vh] py-3 px-0.5 space-y-6">
          {!hasItems ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              {t('datarooms.noItemsToReorder')}
            </div>
          ) : (
            <>
              {hasFolders && (
                <section aria-labelledby="reorder-folders-heading">
                  <div className="flex items-center justify-between mb-2.5 px-0.5">
                    <div className="flex items-center gap-2">
                      <h3
                        id="reorder-folders-heading"
                        className="text-xs font-bold tracking-wider uppercase text-foreground"
                      >
                        {t('datarooms.foldersOrder')}
                      </h3>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-muted text-muted-foreground border border-border">
                        {t('datarooms.countFolders', { count: orderedFolders.length })}
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground font-normal hidden sm:inline">
                      {t('datarooms.foldersOrderHint')}
                    </span>
                  </div>

                  <ul
                    className="space-y-2"
                    aria-label={t('datarooms.foldersListAria')}
                  >
                    {orderedFolders.map((folder, index) => (
                      <ReorderRow
                        key={`folder-${folder.id}`}
                        item={folder}
                        index={index}
                        total={orderedFolders.length}
                        isSaving={isSaving}
                        onDragStart={() => !isSaving && setDragFolderIndex(index)}
                        onDrop={() => !isSaving && handleFolderDrop(index)}
                        onMoveUp={() => setOrderedFolders((prev) => moveItem(prev, index, index - 1))}
                        onMoveDown={() => setOrderedFolders((prev) => moveItem(prev, index, index + 1))}
                      />
                    ))}
                  </ul>
                </section>
              )}

              {hasFolders && hasDocs && (
                <div className="border-t border-border/90 my-4" />
              )}

              {hasDocs && (
                <section aria-labelledby="reorder-documents-heading">
                  <div className="flex items-center justify-between mb-2.5 px-0.5">
                    <div className="flex items-center gap-2">
                      <h3
                        id="reorder-documents-heading"
                        className="text-xs font-bold tracking-wider uppercase text-foreground"
                      >
                        {t('datarooms.documentsOrder')}
                      </h3>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-muted text-muted-foreground border border-border">
                        {t('datarooms.countDocuments', { count: orderedDocs.length })}
                      </span>
                    </div>
                  </div>

                  <ul
                    className="space-y-2"
                    aria-label={t('datarooms.documentsListAria')}
                  >
                    {orderedDocs.map((doc, index) => (
                      <ReorderRow
                        key={`doc-${doc.id}`}
                        item={doc}
                        index={index}
                        total={orderedDocs.length}
                        isSaving={isSaving}
                        onDragStart={() => !isSaving && setDragDocIndex(index)}
                        onDrop={() => !isSaving && handleDocDrop(index)}
                        onMoveUp={() => setOrderedDocs((prev) => moveItem(prev, index, index - 1))}
                        onMoveDown={() => setOrderedDocs((prev) => moveItem(prev, index, index + 1))}
                      />
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>

        <DialogFooter className="flex items-center justify-between pt-3 border-t border-border">
          <Button
            type="button"
            variant="ghost"
            className="mr-auto inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
            onClick={() => {
              if (!isSaving) {
                handleResetOrder();
              }
            }}
            disabled={isSaving || !hasItems}
          >
            <RotateCcw className="h-3.5 w-3.5 text-muted-foreground" />
            {t('datarooms.resetOrder')}
          </Button>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (!isSaving) {
                  onOpenChange(false);
                }
              }}
              disabled={isSaving}
            >
              {t('common.cancel')}
            </Button>
            <Button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !hasItems}
              className="inline-flex items-center gap-1.5"
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  {t('common.saving')}
                </>
              ) : (
                <>
                  <Check className="mr-1.5 h-4 w-4" />
                  {t('datarooms.saveOrder')}
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

