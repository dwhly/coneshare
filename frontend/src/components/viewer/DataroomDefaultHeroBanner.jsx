import { Clock, Globe, Lock, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatRelativeTime } from '../../utils/formatters';

export function DataroomDefaultHeroBanner({
  dataroomName = '',
  _dataroomId = '',
  description = '',
  updatedAt = null,
  isWatermarked = false,
  isNdaProtected = false,
  isRestricted = false,
  _hasViewSession = false,
}) {
  const { t } = useTranslation();

  return (
    <section
      data-testid="dataroom-default-hero"
      data-theme="dark"
      className="relative w-full rounded-2xl overflow-hidden bg-card text-foreground shadow-sm border border-border"
    >
      {/* Glow mesh graphic background with subtle radiant violet & sapphire contour gradients */}
      <div
        className="absolute inset-0 pointer-events-none opacity-60 mix-blend-screen"
        style={{
          backgroundImage: `
            radial-gradient(circle at 85% 15%, hsl(var(--brand) / 0.28) 0%, transparent 45%),
            radial-gradient(circle at 15% 85%, hsl(var(--tag-1) / 0.22) 0%, transparent 50%),
            radial-gradient(circle at 50% 50%, hsl(var(--info) / 0.12) 0%, transparent 60%)
          `,
        }}
      />
      {/* Subtle architectural dot grid pattern */}
      <div
        className="absolute inset-0 pointer-events-none opacity-15"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, hsl(var(--foreground) / 0.25) 1px, transparent 0)',
          backgroundSize: '20px 20px',
        }}
      />
      {/* Horizontal light dampening overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-card/95 via-card/80 to-transparent pointer-events-none" />

      {/* Banner Content */}
      <div className="relative z-10 p-5 sm:p-7 md:p-8 flex flex-col justify-between min-h-[180px] gap-4">
        {/* Top bar: Last Updated */}
        {updatedAt ? (
          <div className="flex items-center justify-end gap-1.5 text-muted-foreground text-xs font-medium">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{t('common.updated')} {formatRelativeTime(updatedAt)}</span>
          </div>
        ) : null}

        {/* Center Title & Description */}
        <div className="max-w-3xl my-auto py-2 sm:py-3">
          <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-foreground tracking-tight leading-tight">
            {dataroomName}
          </h2>
          {description && (
            <p className="text-xs sm:text-sm text-muted-foreground mt-2 leading-relaxed max-w-2xl">
              {description}
            </p>
          )}
        </div>

        {/* Bottom tags: Compliance & Protections */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 mt-1 border-t border-white/10">
          <div className="flex items-center gap-2 flex-wrap text-xs">
            {isRestricted ? (
              <span
                data-testid="hero-restricted-badge"
                className="px-2 py-0.5 rounded bg-white/10 text-foreground text-[10px] font-semibold tracking-wider uppercase"
              >
                {t('viewer.restrictedConfidential')}
              </span>
            ) : (
              <span
                data-testid="hero-public-access-badge"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/10 text-foreground text-[10px] font-semibold tracking-wider uppercase"
              >
                <Globe className="h-3 w-3 text-brand" />
                <span>{t('viewer.publicAccess')}</span>
              </span>
            )}
            {isWatermarked && (
              <span
                data-testid="hero-watermark-badge"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/10 text-white/90 border border-white/15 text-[10px] font-medium"
              >
                <Lock className="h-3 w-3 text-brand" />
                <span>{t('viewer.watermarked')}</span>
              </span>
            )}
            {isNdaProtected && (
              <span
                data-testid="hero-nda-badge"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/10 text-white/90 border border-white/15 text-[10px] font-medium"
              >
                <ShieldCheck className="h-3 w-3 text-success" />
                <span>{t('viewer.ndaActive')}</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
