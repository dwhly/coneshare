import { useTranslation } from 'react-i18next';
import { useBranding } from '../../contexts/BrandingProvider';
import { LanguagePicker } from '../common/LanguagePicker';
import { cn, isSafeUrl } from '../../lib/utils';
import { AccessOwnerCard } from './AccessOwnerCard';

export function GateLayout({
  children,
  publicMeta = null,
  maxWidth = 'max-w-md',
  showAccessOwnerCard = true,
  cardClassName = '',
  badgeText = null,
}) {
  const { t } = useTranslation();
  const { brandName, brandLogoUrl, brandWebsiteUrl, termsUrl, privacyPolicyUrl } = useBranding();

  const displayBrandName = brandName || 'Coneshare';
  const rawLogoUrl = publicMeta?.resolved_brand_logo_url || brandLogoUrl;
  const resolvedLogoUrl = rawLogoUrl && isSafeUrl(rawLogoUrl) ? rawLogoUrl : null;

  return (
    <div className="min-h-screen bg-muted text-foreground flex flex-col justify-between relative selection:bg-primary selection:text-white">
      {/* Radial Dot Grid Pattern Header Overlay */}
      <div className="absolute inset-x-0 top-0 h-96 pointer-events-none gate-dot-pattern [mask-image:radial-gradient(ellipse_60%_70%_at_50%_0%,#000_70%,transparent_100%)]" />

      {/* Top Minimal Utility Bar */}
      <header className="relative z-10 w-full px-6 py-4 flex items-center justify-between border-b border-border/60 bg-background/70 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          {resolvedLogoUrl ? (
            <img
              src={resolvedLogoUrl}
              alt=""
              aria-hidden="true"
              className="h-7 w-7 object-contain rounded-md"
            />
          ) : (
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold text-xs shadow-sm">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
            </div>
          )}
          <span className="font-semibold text-sm tracking-tight text-foreground">
            {displayBrandName}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <LanguagePicker />
        </div>
      </header>

      {/* Main Center Gate Viewport */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 py-8 sm:py-12">
        <div className={cn('w-full', maxWidth)}>
          {/* Center Elevated Card */}
          <div
            className={cn(
              'bg-card rounded-2xl border border-border shadow-[0_4px_24px_-4px_rgba(15,23,42,0.06),0_1px_3px_rgba(15,23,42,0.04)] overflow-hidden',
              cardClassName
            )}
          >
            {/* Card Brand & Security Header */}
            <div className="p-6 pb-4 border-b border-border">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  {resolvedLogoUrl ? (
                    <img
                      src={resolvedLogoUrl}
                      alt={t('viewer.brandLogo', {
                        brandName: displayBrandName,
                        defaultValue: `${displayBrandName} Logo`,
                      })}
                      className="w-8 h-8 rounded-lg object-contain bg-card p-0.5 border border-border shadow-sm shrink-0"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-semibold text-sm shadow-sm ring-2 ring-border shrink-0">
                      {displayBrandName.slice(0, 1).toUpperCase()}
                    </div>
                  )}
                  <div className="min-w-0">
                    <span className="text-sm font-semibold text-foreground truncate block">
                      {displayBrandName}
                    </span>
                    <p className="text-[11px] text-muted-foreground truncate">
                      {t('viewer.secureFileShare', { defaultValue: 'Secure File Share' })}
                    </p>
                  </div>
                </div>
                {badgeText && (
                  <span className="font-mono text-[10px] tracking-wider uppercase font-semibold px-2 py-1 rounded-md bg-muted text-muted-foreground border border-border/80 shrink-0">
                    {badgeText}
                  </span>
                )}
              </div>
            </div>

            <div className="p-6 pt-5 space-y-5">
              {/* Shared Access Context Card */}
              {showAccessOwnerCard && publicMeta && (
                <AccessOwnerCard publicMeta={publicMeta} />
              )}

              {/* Core Gate Content */}
              {children}
            </div>
          </div>

          {/* Trust Badges & Footer Links Below Card */}
          <div className="mt-6 text-center space-y-3">
            <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground font-medium">
              <a
                href={brandWebsiteUrl || 'https://www.coneshare.com/about'}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors"
              >
                {t('auth.aboutBrand', { brandName: displayBrandName })}
              </a>
              <span>•</span>
              <a
                href={termsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors"
              >
                {t('auth.terms')}
              </a>
              <span>•</span>
              <a
                href={privacyPolicyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors"
              >
                {t('auth.privacy')}
              </a>
            </div>
            <div className="flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground">
              <span>
                {t('viewer.poweredBy')}{' '}
                <a
                  href="https://github.com/coneshare/coneshare"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-foreground hover:underline"
                >
                  Coneshare
                </a>
              </span>
            </div>
          </div>
        </div>
      </main>

      <footer className="h-4 pointer-events-none" />
    </div>
  );
}
