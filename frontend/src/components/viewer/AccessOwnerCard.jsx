import { useTranslation } from 'react-i18next';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/Avatar';
import { FileText, Folder } from 'lucide-react';
import { cn } from '../../lib/utils';

function getInitials(name = '') {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  if (parts.length === 1) return parts[0].slice(0, 1).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function AccessOwnerCard({ publicMeta, className }) {
  const { t } = useTranslation();
  if (!publicMeta) return null;

  const {
    owner_name: ownerName,
    owner_email_masked: ownerEmailMasked,
    owner_avatar_url: ownerAvatarUrl,
    target_type: targetType,
    target_name: targetName,
  } = publicMeta;

  const isDataroom = targetType === 'dataroom';
  const fallbackOwner = t('viewer.documentOwner', { defaultValue: 'Document Owner' });

  return (
    <div
      className={cn(
        'rounded-xl bg-muted border border-border/80 p-3.5 space-y-2.5 text-xs',
        className
      )}
    >
      {/* Sender Row */}
      <div className="flex items-center justify-between pb-2.5 border-b border-border/70">
        <div className="flex items-center gap-2 min-w-0">
          <Avatar className="h-6 w-6 ring-1 ring-border shrink-0">
            <AvatarImage src={ownerAvatarUrl || ''} alt={ownerName || fallbackOwner} />
            <AvatarFallback className="text-[10px] bg-gradient-to-tr from-info to-tag-1 text-white font-medium">
              {getInitials(ownerName || fallbackOwner)}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex items-center gap-1.5 truncate">
            <span className="font-medium text-foreground truncate">
              {ownerName || fallbackOwner}
            </span>
            {ownerEmailMasked && (
              <span className="text-muted-foreground font-mono text-[11px] truncate">
                <span>(</span>{ownerEmailMasked}<span>)</span>
              </span>
            )}
          </div>
        </div>
        <span className="text-[10px] uppercase font-semibold tracking-wider text-muted-foreground shrink-0 ml-2">
          {t('viewer.invitedYouTo', { defaultValue: 'INVITED YOU TO' })}
        </span>
      </div>

      {/* Target Resource Row */}
      <div className="flex items-center justify-between pt-0.5">
        <div className="flex items-center gap-2.5 min-w-0 pr-2">
          <div className="w-7 h-7 rounded-md bg-card border border-border flex items-center justify-center text-info shrink-0 shadow-xs">
            {isDataroom ? <Folder className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
          </div>
          <div className="truncate min-w-0">
            <p
              className="font-semibold text-foreground truncate text-[13px]"
              title={targetName}
            >
              {targetName || t('viewer.untitledLink', { defaultValue: 'Untitled Link' })}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {isDataroom
                ? t('viewer.dataroom', { defaultValue: 'Dataroom' })
                : t('viewer.document', { defaultValue: 'Document' })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
