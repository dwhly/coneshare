import { useTranslation } from 'react-i18next';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { Edit, MoreHorizontal, Share2, Trash2, UploadCloud, Download, Copy } from 'lucide-react';
import { Button } from '../ui/Button';

export function ActionsDropdown({
  item,
  type,
  onRename,
  onDelete,
  onShare,
  onRequestFiles,
  onOpenChange,
  onDownload,
  onCopy,
  deleteLabel,
}) {
  const { t } = useTranslation();

  return (
    <DropdownMenu.Root onOpenChange={onOpenChange}>
      <DropdownMenu.Trigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-full"
          onClick={(e) => {
            // Prevent card's link navigation when clicking the trigger
            e.preventDefault();
            e.stopPropagation();
          }}
          aria-label={`Actions for ${item.name}`}
        >
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="z-[9999] w-48 origin-top-right rounded-md bg-card p-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
          sideOffset={5}
          align="end"
          // Prevent focus from returning to trigger, which can re-trigger card navigation.
          onCloseAutoFocus={(e) => e.preventDefault()}
        >
          <DropdownMenu.Item
            onSelect={(e) => {
              e.stopPropagation();
              onRename(item);
            }}
            className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
          >
            <Edit className="h-4 w-4" aria-hidden="true" />
            <span>{t('documents.rename')}</span>
          </DropdownMenu.Item>

          {type === 'document' && onCopy && (
            <DropdownMenu.Item
              onSelect={(e) => {
                e.stopPropagation();
                onCopy(item);
              }}
              className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
            >
              <Copy className="h-4 w-4" aria-hidden="true" />
              <span>{t('documents.copy')}</span>
            </DropdownMenu.Item>
          )}

          {type === 'document' && onShare && (
             <DropdownMenu.Item
              onSelect={(e) => {
                e.stopPropagation();
                onShare(item);
              }}
              className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
             >
              <Share2 className="h-4 w-4" aria-hidden="true" />
              <span>{t('documents.getLink')}</span>
            </DropdownMenu.Item>
          )}

          {type === 'document' && onDownload && (
            <DropdownMenu.Item
              onSelect={(e) => {
                e.stopPropagation();
                onDownload(item);
              }}
              className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              <span>{t('documents.download')}</span>
            </DropdownMenu.Item>
          )}

          {type === 'folder' && onRequestFiles && (
            <DropdownMenu.Item
              onSelect={(e) => {
                e.stopPropagation();
                onRequestFiles(item);
              }}
              className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-foreground hover:bg-accent focus:bg-muted focus:outline-none"
            >
              <UploadCloud className="h-4 w-4" aria-hidden="true" />
              <span>{t('documents.requestFiles')}</span>
            </DropdownMenu.Item>
          )}

          <DropdownMenu.Separator className="my-1 h-px bg-border" />
          
          <DropdownMenu.Item
            onSelect={(e) => {
              e.stopPropagation();
              onDelete(item);
            }}
            className="flex w-full cursor-pointer items-center gap-x-2 rounded-sm px-3 py-1.5 text-sm text-danger hover:bg-danger-subtle focus:bg-danger-subtle focus:text-danger focus:outline-none"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            <span>{deleteLabel || t('common.delete')}</span>
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
