import { useState, useEffect, useCallback, useRef } from 'react';
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
import { AddFolderDialog } from './AddFolderDialog';
import {
  Folder as FolderIcon,
  ChevronRight,
  Home,
  FolderPlus,
  ArrowRight,
  Loader2,
  AlertCircle,
  RotateCw,
} from 'lucide-react';

function Breadcrumbs({ currentFolder, onNavigate }) {
  const { t } = useTranslation();

  return (
    <nav className="flex flex-wrap items-center gap-1.5 text-xs font-medium text-muted-foreground min-w-0" aria-label="Breadcrumb">
      <button
        type="button"
        onClick={() => onNavigate(null)}
        className="flex items-center gap-1 hover:text-foreground flex-shrink-0"
      >
        <Home className="h-3.5 w-3.5" />
        <span>{t('datarooms.home')}</span>
      </button>
      {currentFolder?.ancestors?.map((ancestor) => (
        <div key={ancestor.id} className="flex items-center gap-1.5 min-w-0">
          <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
          <button
            type="button"
            onClick={() => onNavigate(ancestor.id, ancestor.name)}
            className="truncate max-w-[120px] sm:max-w-[160px] hover:text-foreground"
            title={ancestor.name}
          >
            {ancestor.name}
          </button>
        </div>
      ))}
      {currentFolder && (
        <div className="flex items-center gap-1.5 min-w-0">
          <ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
          <span
            className="font-semibold text-foreground truncate max-w-[140px] sm:max-w-[200px]"
            title={currentFolder.name}
          >
            {currentFolder.name}
          </span>
        </div>
      )}
    </nav>
  );
}

export function MoveDestinationDialog({
  isOpen,
  onOpenChange,
  onConfirm,
  onFetchContents,
  onCreateFolder,
  sourceFolderId = undefined,
  selectedFolderIds = [],
  selectedCount = 0,
  title,
  description,
  confirmAriaLabel,
}) {
  const { t } = useTranslation();
  const [currentFolderId, setCurrentFolderId] = useState(null);
  const [currentFolderInfo, setCurrentFolderInfo] = useState(null);
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isAddFolderOpen, setIsAddFolderOpen] = useState(false);
  const [selectedDestination, setSelectedDestination] = useState({ id: null });
  const requestIdRef = useRef(0);

  const fetchData = useCallback(async (folderId) => {
    const requestId = ++requestIdRef.current;
    setLoading(true);
    setFetchError(false);
    try {
      const result = await onFetchContents(folderId);

      // Ignore stale responses from earlier navigation requests
      if (requestId !== requestIdRef.current) return;

      if (folderId && result?.currentFolder) {
        setCurrentFolderInfo({
          id: result.currentFolder.id,
          name: result.currentFolder.name,
          ancestors: result.currentFolder.ancestors || [],
        });
      } else {
        setCurrentFolderInfo(null);
      }

      setFolders(result?.subFolders || []);
    } catch (error) {
      if (requestId === requestIdRef.current) {
        console.error('Failed to fetch destination folder contents:', error);
        setFetchError(true);
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [onFetchContents]);

  useEffect(() => {
    if (isOpen) {
      setCurrentFolderId(null);
      setCurrentFolderInfo(null);
      setSelectedDestination({ id: null });
      fetchData(null);
    }
  }, [isOpen, fetchData]);

  const handleNavigate = (folderId, folderName = null) => {
    setCurrentFolderId(folderId);
    if (!folderId) {
      setSelectedDestination({ id: null });
    } else if (folderName) {
      setSelectedDestination({ id: folderId, name: folderName });
    }
    fetchData(folderId);
  };

  const handleConfirm = async () => {
    if (isConfirming || isMoveDisabled) return;
    setIsConfirming(true);
    try {
      await onConfirm(selectedDestination?.id ?? null);
    } catch (error) {
      console.error('Failed to confirm move:', error);
    } finally {
      setIsConfirming(false);
    }
  };

  const handleCreateFolder = async (name) => {
    try {
      const res = await onCreateFolder(name, currentFolderId || null);
      await fetchData(currentFolderId);
      // Handles both direct response { id, name } and Axios response object { data: { id, name } }
      if (res?.id) {
        setSelectedDestination({ id: res.id, name: res.name });
      } else if (res?.data?.id) {
        setSelectedDestination({ id: res.data.id, name: res.data.name });
      }
    } catch (error) {
      console.error('Failed to create folder in destination:', error);
    } finally {
      setIsAddFolderOpen(false);
    }
  };

  const isCurrentDirectory = Boolean(
    sourceFolderId !== undefined &&
      selectedDestination &&
      (selectedDestination.id ?? null) === (sourceFolderId ?? null)
  );

  const isDestinationDisabled = Boolean(
    selectedDestination?.id && selectedFolderIds.includes(selectedDestination.id)
  );

  const isMoveDisabled =
    isConfirming || !selectedDestination || isDestinationDisabled || isCurrentDirectory;

  const dialogTitle = title || t('documents.moveTitle');
  const dialogDescription = description || t('documents.selectTargetFolder');

  return (
    <>
      <AddFolderDialog
        isOpen={isAddFolderOpen}
        onOpenChange={setIsAddFolderOpen}
        onConfirm={handleCreateFolder}
      />
      <Dialog
        open={isOpen}
        onOpenChange={(open) => {
          if (!isConfirming) {
            onOpenChange(open);
          }
        }}
      >
        <DialogContent className="sm:max-w-xl max-h-[88vh] flex flex-col p-6 overflow-hidden">
          <DialogHeader className="pb-3 border-b border-border">
            <div className="flex items-center space-x-2">
              <DialogTitle className="text-lg font-semibold text-foreground tracking-tight flex items-center space-x-2">
                <span>{dialogTitle}</span>
                {selectedCount > 0 && (
                  <span className="text-xs font-medium bg-muted text-muted-foreground py-0.5 px-2 rounded-full border border-border">
                    {t('documents.selectedCount', { count: selectedCount })}
                  </span>
                )}
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground mt-1">
              {dialogDescription}
            </DialogDescription>
          </DialogHeader>

          {/* Folder Tree Directory Listing */}
          <div className="py-3 flex-1 min-h-0">
            <div className="border border-border rounded-xl overflow-hidden bg-card shadow-xs flex flex-col h-full">
              {/* Root Level or Breadcrumb Header */}
              {!currentFolderId ? (
                <button
                  type="button"
                  aria-pressed={selectedDestination?.id === null}
                  onClick={() => setSelectedDestination({ id: null })}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 text-left border-b border-border transition-colors group ${
                    selectedDestination?.id === null
                      ? 'bg-foreground/5 '
                      : 'hover:bg-accent '
                  }`}
                >
                  <div className="flex items-center space-x-2.5 min-w-0">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      selectedDestination?.id === null
                        ? 'bg-border/80 text-foreground '
                        : 'bg-muted text-foreground '
                    }`}>
                      <Home className="w-4 h-4" strokeWidth={2} />
                    </div>
                    <span className="text-sm font-medium text-foreground truncate">
                      {t('datarooms.homeDirectory')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {selectedDestination?.id === null && (
                      isCurrentDirectory ? (
                        <span className="text-[10px] font-medium bg-muted text-muted-foreground rounded px-1.5 py-0.5 border border-border">
                          {t('datarooms.currentLocation')}
                        </span>
                      ) : (
                        <span className="text-[10px] font-medium bg-primary text-primary-foreground rounded px-1.5 py-0.5">
                          {t('common.selected')}
                        </span>
                      )
                    )}
                  </div>
                </button>
              ) : (
                <div className="px-3.5 py-2.5 bg-muted/70 border-b border-border">
                  <Breadcrumbs currentFolder={currentFolderInfo} onNavigate={handleNavigate} />
                </div>
              )}

              {/* Scrollable Subfolder List */}
              <div className="h-60 overflow-y-auto divide-y divide-border min-h-[160px]">
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
                      onClick={() => fetchData(currentFolderId)}
                      className="mt-1 text-xs inline-flex items-center gap-1.5"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                      <span>{t('common.retry')}</span>
                    </Button>
                  </div>
                ) : folders.length > 0 ? (
                  folders.map((folder) => {
                    const isSelected = selectedDestination?.id === folder.id;
                    const isFolderDisabled = selectedFolderIds.includes(folder.id);
                    const isCurrent = sourceFolderId !== undefined && (sourceFolderId ?? null) === folder.id;
                    const itemCount = folder.items_count ?? (Array.isArray(folder.items) ? folder.items.length : null);

                    return (
                      <div
                        key={folder.id}
                        className={`flex items-center justify-between px-3.5 py-2 transition-colors ${
                          isSelected
                            ? 'bg-foreground/5 '
                            : 'hover:bg-accent '
                        } ${isFolderDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <button
                          type="button"
                          disabled={isFolderDisabled}
                          aria-pressed={isSelected}
                          onClick={() => {
                            if (!isFolderDisabled) {
                              setSelectedDestination({ id: folder.id, name: folder.name });
                            }
                          }}
                          onDoubleClick={() => {
                            if (!isFolderDisabled) {
                              handleNavigate(folder.id, folder.name);
                            }
                          }}
                          className="flex items-center space-x-2.5 min-w-0 flex-1 text-left py-0.5 group disabled:cursor-not-allowed"
                        >
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                            isSelected
                              ? 'bg-border/80 text-foreground '
                              : 'bg-muted text-foreground '
                          }`}>
                            <FolderIcon className="w-4 h-4" strokeWidth={2} />
                          </div>
                          <span className={`text-sm truncate max-w-[260px] ${
                            isSelected
                              ? 'font-semibold text-foreground '
                              : 'font-medium text-foreground group-hover:text-foreground '
                          }`}>
                            {folder.name}
                          </span>
                        </button>
                        <div className="flex items-center space-x-2 shrink-0">
                          {itemCount !== null && (
                            <span className="text-[11px] text-muted-foreground font-normal">
                              {t('documents.itemCount', { count: itemCount })}
                            </span>
                          )}
                          {!isSelected && isCurrent && (
                            <span className="text-[10px] text-muted-foreground font-normal">
                              ({t('datarooms.currentLocation')})
                            </span>
                          )}
                          {isSelected && (
                            isCurrent ? (
                              <span className="text-[10px] font-medium bg-muted text-muted-foreground rounded px-1.5 py-0.5 border border-border">
                                {t('datarooms.currentLocation')}
                              </span>
                            ) : (
                              <span className="text-[10px] font-medium bg-primary text-primary-foreground rounded px-1.5 py-0.5">
                                {t('common.selected')}
                              </span>
                            )
                          )}
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            disabled={isFolderDisabled}
                            onClick={() => {
                              handleNavigate(folder.id, folder.name);
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
                  })
                ) : (
                  <div className="flex h-full items-center justify-center p-8 text-sm text-muted-foreground">
                    {t('documents.noSubfolders')}
                  </div>
                )}
              </div>
            </div>
          </div>

          <DialogFooter className="flex flex-row items-center justify-between sm:justify-between sm:space-x-0 w-[calc(100%+3rem)] py-3 bg-muted/70 border-t border-border mt-2 -mx-6 -mb-6 px-6">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsAddFolderOpen(true)}
              disabled={isConfirming}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-foreground"
            >
              <FolderPlus className="w-3.5 h-3.5 text-muted-foreground" />
              <span>{t('documents.createFolder')}</span>
            </Button>
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
                onClick={handleConfirm}
                disabled={isMoveDisabled}
                size="sm"
                aria-label={isConfirming ? t('common.moving') : (confirmAriaLabel || t('documents.move'))}
                title={
                  isCurrentDirectory
                    ? t('datarooms.alreadyInFolder')
                    : undefined
                }
                className="inline-flex items-center gap-1.5 text-xs font-medium"
              >
                {isConfirming ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>{t('common.moving')}</span>
                  </>
                ) : (
                  <>
                    <span>{t('datarooms.moveToFolder')}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
