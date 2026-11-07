import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { FileTypeIcon, getDocumentBadgeStyle } from '../documents/FileTypeIcon';
import { formatBytes } from '../../lib/formatters';
import { formatRelativeTime } from '../../utils/formatters';
import { getFolderContents, getRootFolderContents } from '../../services/api';
import {
  ChevronRight,
  Folder as FolderIcon,
  Home,
  Search,
  RotateCw,
  AlertCircle,
  ArrowRight,
  Loader2,
} from 'lucide-react';

function Breadcrumbs({ path, onNavigate }) {
  const { t } = useTranslation();

  return (
    <nav className="flex items-center space-x-1.5 text-xs text-muted-foreground font-medium min-w-0" aria-label="Breadcrumb">
      <button
        type="button"
        onClick={() => onNavigate(null)}
        className="hover:text-foreground flex items-center space-x-1 transition-colors shrink-0"
      >
        <Home className="w-3.5 h-3.5 text-muted-foreground" />
        <span>{t('datarooms.home')}</span>
      </button>
      {path.map((folder, index) => {
        const isCurrent = index === path.length - 1;
        return (
          <div key={folder.id} className="flex items-center space-x-1.5 min-w-0">
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            {isCurrent ? (
              <span
                className="truncate max-w-[120px] sm:max-w-[160px] font-semibold text-foreground"
                aria-current="page"
                title={folder.name}
              >
                {folder.name}
              </span>
            ) : (
              <button
                type="button"
                onClick={() => onNavigate(folder.id)}
                className="truncate max-w-[120px] sm:max-w-[160px] text-muted-foreground hover:text-foreground transition-colors"
                title={folder.name}
              >
                {folder.name}
              </button>
            )}
          </div>
        );
      })}
    </nav>
  );
}

export function AddContentDialog({ isOpen, onOpenChange, onConfirm }) {
  const { t } = useTranslation();
  const [currentFolder, setCurrentFolder] = useState(null);
  const [folders, setFolders] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [selection, setSelection] = useState({ documents: [], folders: [] });
  const [isConfirming, setIsConfirming] = useState(false);
  const requestIdRef = useRef(0);
  const lastRequestedFolderIdRef = useRef(null);

  const fetchData = useCallback(async (folderId = null) => {
    lastRequestedFolderIdRef.current = folderId;
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setFetchError(false);
    try {
      const response = folderId
        ? await getFolderContents(folderId)
        : await getRootFolderContents();

      if (requestId !== requestIdRef.current) return;

      const { current_folder, sub_folders, documents } = response?.data || {};
      setCurrentFolder(current_folder || null);
      setFolders(sub_folders || []);
      setDocuments(documents || []);
    } catch (error) {
      if (requestId === requestIdRef.current) {
        console.error('Failed to fetch content:', error);
        setFetchError(true);
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setSelection({ documents: [], folders: [] });
      fetchData(null);
    }
  }, [isOpen, fetchData]);

  const handleNavigate = (folderId) => {
    setSearchQuery('');
    fetchData(folderId);
  };

  const handleItemSelect = (id, type) => {
    setSelection((prev) => {
      const list = prev[type] || [];
      const updated = list.includes(id)
        ? list.filter((itemId) => itemId !== id)
        : [...list, id];
      return { ...prev, [type]: updated };
    });
  };

  const handleClearSelection = () => {
    setSelection({ documents: [], folders: [] });
  };

  const handleConfirm = async () => {
    if (selection.documents.length === 0 && selection.folders.length === 0) {
      return;
    }
    if (isConfirming) return;
    setIsConfirming(true);
    try {
      await onConfirm({
        document_ids: selection.documents,
        folder_ids: selection.folders,
      });
    } catch (error) {
      console.error('Failed to add content to dataroom:', error);
    } finally {
      setIsConfirming(false);
    }
  };

  const filteredFolders = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return folders;
    return folders.filter((f) => f.name.toLowerCase().includes(q));
  }, [folders, searchQuery]);

  const filteredDocuments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((d) => d.name.toLowerCase().includes(q));
  }, [documents, searchQuery]);

  const breadcrumbPath = currentFolder ? [...(currentFolder.ancestors || []), currentFolder] : [];
  const selectedCount = selection.documents.length + selection.folders.length;
  const hasItems = folders.length > 0 || documents.length > 0;
  const hasFilteredItems = filteredFolders.length > 0 || filteredDocuments.length > 0;

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!isConfirming) {
          onOpenChange(open);
        }
      }}
    >
      <DialogContent className="sm:max-w-xl max-h-[88vh] flex flex-col p-0 gap-0 overflow-hidden">
        <DialogHeader className="px-6 pt-5 pb-4 shrink-0 sm:text-left">
          <div className="flex items-center space-x-2">
            <DialogTitle className="text-lg font-semibold text-foreground tracking-tight flex items-center space-x-2">
              <span>{t('datarooms.addContentTitle')}</span>
              {selectedCount > 0 && (
                <span className="text-xs font-medium bg-muted text-muted-foreground py-0.5 px-2 rounded-full border border-border">
                  {t('documents.selectedCount', { count: selectedCount })}
                </span>
              )}
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-muted-foreground mt-1">
            {t('datarooms.addContentDescription')}
          </DialogDescription>
        </DialogHeader>

        {/* Filter and Search Toolbar */}
        <div className="px-6 py-2.5 bg-muted/70 border-b border-border flex items-center justify-between gap-3 text-sm shrink-0">
          <Breadcrumbs path={breadcrumbPath} onNavigate={handleNavigate} />
          <div className="flex items-center space-x-2 shrink-0">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('datarooms.filterCurrentList')}
                className="w-36 sm:w-44 pl-7 pr-2.5 py-1 text-xs bg-card border border-border rounded-md text-foreground placeholder-muted-foreground focus:outline-none focus:border-ring focus:ring-1 focus:ring-ring shadow-xs"
              />
              <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-2 top-2 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Content File & Folder List */}
        <div className="px-4 py-2 flex-1 min-h-[220px] max-h-[380px] overflow-y-auto divide-y divide-border">
          {loading ? (
            <div className="p-3 space-y-2">
              <p className="sr-only">{t('documents.loadingFolders')}</p>
              <div className="h-10 bg-muted rounded-lg animate-pulse" />
              <div className="h-10 bg-muted rounded-lg animate-pulse" />
              <div className="h-10 bg-muted rounded-lg animate-pulse" />
            </div>
          ) : fetchError ? (
            <div className="flex flex-col h-full items-center justify-center p-8 text-center text-sm text-muted-foreground gap-2">
              <AlertCircle className="w-5 h-5 text-danger" />
              <span>{t('common.errorOccurred')}</span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fetchData(lastRequestedFolderIdRef.current)}
                className="mt-1 text-xs inline-flex items-center gap-1.5"
              >
                <RotateCw className="w-3.5 h-3.5" />
                <span>{t('common.retry')}</span>
              </Button>
            </div>
          ) : !hasItems ? (
            <div className="flex h-full items-center justify-center p-8 text-sm text-muted-foreground">
              {t('datarooms.folderEmpty')}
            </div>
          ) : !hasFilteredItems ? (
            <div className="flex h-full items-center justify-center p-8 text-sm text-muted-foreground">
              {t('viewer.noMatchingFiles')}
            </div>
          ) : (
            <div className="space-y-1">
              {/* Folder Rows */}
              {filteredFolders.map((folder) => {
                const isChecked = selection.folders.includes(folder.id);
                const itemCount = folder.items_count ?? (Array.isArray(folder.items) ? folder.items.length : null);

                return (
                  <div
                    key={folder.id}
                    onClick={(e) => {
                      if (e.target.closest('button') || e.target.closest('[role="checkbox"]')) return;
                      handleItemSelect(folder.id, 'folders');
                    }}
                    onDoubleClick={() => handleNavigate(folder.id)}
                    className={`group flex items-center justify-between py-2 px-2 rounded-lg transition-colors cursor-pointer select-none ${
                      isChecked
                        ? 'bg-muted/90 border border-border/80 '
                        : 'hover:bg-muted border border-transparent'
                    }`}
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1">
                      <Checkbox
                        id={`folder-${folder.id}`}
                        checked={isChecked}
                        onCheckedChange={() => handleItemSelect(folder.id, 'folders')}
                        aria-label={folder.name}
                      />
                      <div className="w-8 h-8 rounded-lg bg-muted text-muted-foreground flex items-center justify-center shrink-0">
                        <FolderIcon className="w-4 h-4" strokeWidth={2} />
                      </div>
                      <div className="truncate flex-1">
                        <p className={`text-sm truncate ${isChecked ? 'font-semibold text-foreground ' : 'font-medium text-foreground group-hover:text-foreground '}`}>
                          {folder.name}
                        </p>
                        {itemCount !== null && (
                          <p className="text-xs text-muted-foreground font-normal">
                            {t('documents.itemCount', { count: itemCount })}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 shrink-0 ml-4">
                      {folder.updated_at && (
                        <span className="text-xs text-muted-foreground font-normal hidden sm:inline">
                          {formatRelativeTime(folder.updated_at)}
                        </span>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleNavigate(folder.id);
                        }}
                        className="h-7 w-7 text-muted-foreground hover:text-foreground"
                        title={t('datarooms.openFolder', { name: folder.name })}
                        aria-label={t('datarooms.openFolder', { name: folder.name })}
                      >
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}

              {/* Document Rows */}
              {filteredDocuments.map((doc) => {
                const isChecked = selection.documents.includes(doc.id);
                const docType = doc.type || doc.name;

                return (
                  <div
                    key={doc.id}
                    onClick={(e) => {
                      if (e.target.closest('[role="checkbox"]')) return;
                      handleItemSelect(doc.id, 'documents');
                    }}
                    className={`group flex items-center justify-between py-2 px-2 rounded-lg transition-colors cursor-pointer select-none ${
                      isChecked
                        ? 'bg-muted/90 border border-border/80 '
                        : 'hover:bg-muted border border-transparent'
                    }`}
                  >
                    <div className="flex items-center space-x-3 min-w-0 flex-1">
                      <Checkbox
                        id={`doc-${doc.id}`}
                        checked={isChecked}
                        onCheckedChange={() => handleItemSelect(doc.id, 'documents')}
                        aria-label={doc.name}
                      />
                      <div className={`w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 ${getDocumentBadgeStyle(docType)}`}>
                        <FileTypeIcon type={docType} className="h-4 w-4 shrink-0" palette="viewer" />
                      </div>
                      <div className="truncate flex-1">
                        <p className={`text-sm truncate ${isChecked ? 'font-semibold text-foreground ' : 'font-medium text-foreground group-hover:text-foreground '}`}>
                          {doc.name}
                        </p>
                        {typeof doc.file_size === 'number' && (
                          <p className="text-xs text-muted-foreground font-normal">
                            {formatBytes(doc.file_size)}
                          </p>
                        )}
                      </div>
                    </div>
                    {doc.updated_at && (
                      <span className="text-xs text-muted-foreground shrink-0 ml-4 font-normal hidden sm:inline">
                        {formatRelativeTime(doc.updated_at)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="px-6 py-3 bg-muted/70 border-t border-border flex flex-row items-center justify-between sm:justify-between sm:space-x-0 shrink-0">
          <div className="flex items-center space-x-2">
            {selectedCount > 0 && (
              <button
                type="button"
                onClick={handleClearSelection}
                className="text-xs text-muted-foreground hover:text-foreground underline transition-colors"
              >
                {t('documents.clearSelection')}
              </button>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                if (!isConfirming) {
                  onOpenChange(false);
                }
              }}
              disabled={isConfirming}
              className="text-xs"
            >
              {t('common.cancel')}
            </Button>
            <Button
              size="sm"
              onClick={handleConfirm}
              disabled={isConfirming || selectedCount === 0}
              className="inline-flex items-center gap-1.5 text-xs font-medium"
            >
              {isConfirming ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{t('common.saving')}</span>
                </>
              ) : (
                <>
                  <span>{t('datarooms.addSelectedItems', { count: selectedCount })}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
