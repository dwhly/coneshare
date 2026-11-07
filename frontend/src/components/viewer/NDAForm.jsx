import { useState } from 'react';
import { toast } from 'sonner';
import { ShieldAlert, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { acceptShareLinkNda } from '../../services/api';
import { getLocalizedErrorMessage } from '../../utils/errorTranslator';
import { Button } from '../ui/Button';
import { GateLayout } from './GateLayout';
import { useBranding } from '../../contexts/BrandingProvider';
import { cn } from '../../lib/utils';

export function NDAForm({ slug, onSuccess, publicMeta = null }) {
  const { t } = useTranslation();
  const { brandWebsiteUrl } = useBranding();
  const [agreed, setAgreed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const hasNdaText = Boolean(publicMeta?.nda_text && publicMeta.nda_text.trim());
  const ndaText = hasNdaText
    ? publicMeta.nda_text
    : t('viewer.ndaTermsUnavailable', {
        defaultValue: 'No Non-Disclosure Agreement terms are currently available.',
      });

  const versionString = publicMeta?.nda_version
    ? String(publicMeta.nda_version).startsWith('v')
      ? publicMeta.nda_version
      : `v${publicMeta.nda_version}`
    : null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!hasNdaText) {
      return;
    }
    if (!agreed) {
      toast.error(t('viewer.mustAgreeNda'));
      return;
    }

    setIsLoading(true);
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const viewSessionId = searchParams.get('view_session_id');

      const response = await acceptShareLinkNda(slug, {
        view_session_id: viewSessionId,
      });

      toast.success(getLocalizedErrorMessage(response.data?.message || 'NDA accepted successfully.'));
      onSuccess(response.data?.view_session_id);
    } catch (err) {
      toast.error(getLocalizedErrorMessage(err, 'viewer.ndaAcceptFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <GateLayout publicMeta={publicMeta} maxWidth="max-w-lg">
      <div className="space-y-4 pt-1">
        {/* NDA Warning Banner */}
        <div className="flex items-start gap-2.5 rounded-lg bg-info-subtle/90 p-3 text-xs text-info border border-info-border">
          <ShieldAlert className="h-4 w-4 shrink-0 text-info mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-[11px] block uppercase tracking-wider text-info">
              {t('viewer.ndaRequired')}
            </span>
            {t('viewer.ndaNotice')}
          </div>
        </div>

        {/* Legal Agreement Viewer Box */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-medium text-muted-foreground px-0.5">
            <span>
              {versionString
                ? t('viewer.confidentialityAgreementWithVersion', {
                    version: versionString,
                    defaultValue: `Confidentiality Agreement (${versionString})`,
                  })
                : t('viewer.confidentialityAgreement', {
                    defaultValue: 'Confidentiality & Non-Disclosure Agreement',
                  })}
            </span>
          </div>
          <div
            className={cn(
              'max-h-52 overflow-y-auto overflow-x-hidden rounded-xl border border-border bg-muted p-4 text-xs leading-relaxed shadow-inner nda-scroll whitespace-pre-line break-words',
              hasNdaText
                ? 'text-foreground '
                : 'text-warning italic bg-warning-subtle/40 border-warning-border '
            )}
          >
            {ndaText}
          </div>
        </div>

        {/* Agreement Checkbox & Primary CTA */}
        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <label
            className={cn(
              'flex items-start gap-3 select-none group',
              hasNdaText ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'
            )}
          >
            <input
              type="checkbox"
              className="mt-0.5 h-4 w-4 rounded border-input text-info focus:ring-ring cursor-pointer disabled:cursor-not-allowed"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              disabled={isLoading || !hasNdaText}
            />
            <span className="text-xs text-muted-foreground group-hover:text-foreground transition-colors leading-normal">
              {t('viewer.ndaAgreeCheckbox')}
            </span>
          </label>

          <div className="pt-1">
            <Button
              type="submit"
              size="lg"
              className="w-full flex items-center justify-center gap-2 active:scale-[0.98] transition-all bg-primary hover:bg-black text-primary-foreground"
              disabled={isLoading || !agreed || !hasNdaText}
            >
              <span>{isLoading ? t('viewer.processing') : t('viewer.acceptAndView')}</span>
              {!isLoading && <ArrowRight className="h-4 w-4 shrink-0" />}
            </Button>
          </div>
        </form>

        <div className="text-center pt-1">
          <a
            href={brandWebsiteUrl || 'https://www.coneshare.com'}
            className="text-[11px] text-muted-foreground hover:text-muted-foreground transition-colors"
          >
            {t('viewer.declineNda', { defaultValue: 'Decline and leave' })}
          </a>
        </div>
      </div>
    </GateLayout>
  );
}
