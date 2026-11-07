import { useState } from 'react';
import { toast } from 'sonner';
import { Mail, Info, ArrowRight, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { requestShareLinkAccess, confirmShareLinkEmailAccess } from '../../services/api';
import { getLocalizedErrorMessage } from '../../utils/errorTranslator';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { GateLayout } from './GateLayout';

export function EmailForm({
  slug,
  onSuccess,
  publicMeta = null,
  requiresConfirmation = false,
  emailToConfirm = '',
  token = '',
}) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  // AmForge: full name is captured with the email and burned into the watermark.
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasSubmitted, setHasSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const name = fullName.trim();
      const response = name
        ? await requestShareLinkAccess(slug, email, name)
        : await requestShareLinkAccess(slug, email);
      toast.success(getLocalizedErrorMessage(response.data.message));

      if (response.data.verification_required) {
        setHasSubmitted(true);
      } else {
        onSuccess();
      }
    } catch {
      // Error handled by global interceptor
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    setIsLoading(true);
    try {
      const response = await confirmShareLinkEmailAccess(slug, token);
      toast.success(getLocalizedErrorMessage(response.data.message));
      onSuccess();
    } catch {
      // Error handled by global interceptor
    } finally {
      setIsLoading(false);
    }
  };

  if (requiresConfirmation && emailToConfirm) {
    return (
      <GateLayout publicMeta={publicMeta} maxWidth="max-w-md">
        <div className="space-y-4 pt-1">
          <p className="text-left text-xs sm:text-sm text-muted-foreground">
            {t('viewer.verifyingAccessAs')}{' '}
            <strong className="break-all text-foreground font-mono">{emailToConfirm}</strong>.
          </p>

          {/* Scanner-Safe Protected Box */}
          <div className="rounded-xl border border-info-border bg-info-subtle/60 p-3.5 space-y-3">
            <div className="flex items-start gap-2.5">
              <div className="w-5 h-5 rounded-full bg-info text-info-foreground flex items-center justify-center shrink-0 mt-0.5 text-[10px] font-bold">
                ✓
              </div>
              <div>
                <p className="text-xs font-semibold text-info">
                  {t('viewer.scannerProtectedTitle', { defaultValue: 'Security Scanner Protected' })}
                </p>
                <p className="text-[11px] text-info/90 leading-normal mt-0.5">
                  {t('viewer.scannerProtectedDesc', {
                    defaultValue:
                      'Enterprise email firewalls often pre-click links. Click below to manually validate session as a human viewer.',
                  })}
                </p>
              </div>
            </div>

            <Button
              onClick={handleConfirm}
              size="lg"
              className="w-full flex items-center justify-center gap-2 active:scale-[0.98] transition-transform bg-primary hover:bg-black text-primary-foreground"
              disabled={isLoading}
            >
              <span>{isLoading ? t('viewer.verifying') : t('viewer.continue', { defaultValue: 'Continue' })}</span>
              {!isLoading && <ArrowRight className="h-4 w-4 shrink-0" />}
            </Button>
          </div>
        </div>
      </GateLayout>
    );
  }

  if (hasSubmitted) {
    return (
      <GateLayout publicMeta={publicMeta} maxWidth="max-w-md" showAccessOwnerCard={false}>
        <div className="text-center py-4 space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-info-subtle text-info">
            <Mail className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">
              {t('viewer.checkYourEmail')}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed max-w-xs mx-auto">
              {t('viewer.emailSentNotice')}{' '}
              <strong className="text-foreground font-mono">{email}</strong>.{' '}
              {t('viewer.clickLinkNotice')}
            </p>
          </div>
          <div className="pt-2">
            <button
              type="button"
              onClick={() => {
                setIsLoading(false);
                setHasSubmitted(false);
              }}
              className="text-xs font-semibold text-brand hover:underline"
            >
              {t('viewer.useDifferentEmail')}
            </button>
          </div>
        </div>
      </GateLayout>
    );
  }

  return (
    <GateLayout publicMeta={publicMeta} maxWidth="max-w-md">
      <div className="space-y-4 pt-1">
        <div>
          <h2 className="text-base font-semibold text-foreground tracking-tight">
            {t('viewer.identifyToView', { defaultValue: 'Identify to view secured files' })}
          </h2>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            {t('viewer.emailVerificationSubtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="space-y-1.5">
            <Label htmlFor="full-name" className="block text-xs font-medium text-foreground">
              {t('amforge.viewer.fullName', { defaultValue: 'Full name' })}
            </Label>
            <div className="relative">
              <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="full-name"
                name="name"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="pl-10"
                placeholder={t('amforge.viewer.fullNamePlaceholder', { defaultValue: 'Jane Doe' })}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email" className="block text-xs font-medium text-foreground">
              {t('auth.email')}
            </Label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="email"
                name="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10"
                placeholder="you@company.com"
                autoFocus
              />
            </div>
          </div>

          {/* Watermark Notice Box */}
          <div className="p-2.5 rounded-lg bg-muted border border-border/70 text-[11px] text-muted-foreground leading-normal flex items-start gap-2">
            <Info className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
            <span>
              {t('amforge.viewer.watermarkNotice', {
                defaultValue: 'Your name, organisation and email are watermarked on every page and copy, and access is logged.',
              })}
            </span>
          </div>

          <div className="pt-1">
            <Button
              type="submit"
              size="lg"
              className="w-full flex items-center justify-center gap-2 active:scale-[0.98] transition-all bg-primary hover:bg-black text-primary-foreground"
              disabled={isLoading}
            >
              <span>{isLoading ? t('auth.submitting') : t('viewer.continue')}</span>
              {!isLoading && <ArrowRight className="h-4 w-4 shrink-0" />}
            </Button>
          </div>
        </form>
      </div>
    </GateLayout>
  );
}
