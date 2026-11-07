import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authService } from '../services/authService'
import { APP_DISPLAY_VERSION } from '../lib/constants'
import { Button } from '../components/ui/Button'
import { useBranding } from '../contexts/BrandingProvider'
import { LanguagePicker } from '../components/common/LanguagePicker'
import { FleetLockup, ThemeToggle } from '../components/layout/FleetChrome'
import { pageTitle } from '../hooks/usePageTitle'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useTranslation()
  const { brandName, brandWebsiteUrl, termsUrl, privacyPolicyUrl } = useBranding()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [showSignupLink, setShowSignupLink] = useState(false)

  useEffect(() => {
    let mounted = true

    const loadPublicSettings = async () => {
      try {
        const data = await authService.getPublicSettings()
        if (mounted) setShowSignupLink(Boolean(data?.enable_public_signup))
      } catch (_err) {
        if (mounted) setShowSignupLink(false)
      }
    }

    loadPublicSettings()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    document.title = pageTitle(t('auth.signIn'));
  }, [t])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      await authService.login(email, password)
      const fromLocation = location.state?.from
      const rawFrom = typeof fromLocation === 'string'
        ? fromLocation
        : fromLocation?.pathname
          ? `${fromLocation.pathname}${fromLocation.search || ''}${fromLocation.hash || ''}`
          : '/'
      const from =
        rawFrom.startsWith('/') && !rawFrom.startsWith('//') && !rawFrom.startsWith('/login')
          ? rawFrom
          : '/'
      navigate(from, { replace: true })
    } catch (err) {
      setError('auth.invalidCredentials')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="fds-header dr-header">
        <FleetLockup href="/login" />
        <div className="fds-header__utils">
          <ThemeToggle />
        </div>
      </header>
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-card shadow-sm">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {t('auth.signIn')}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {t('auth.welcomeBack', { brandName: 'Fleet Dealroom' })}
          </p>
        </div>
        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium text-foreground">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                {t('auth.password')}
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                className="block w-full rounded-md border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <p className="rounded-md border border-danger-border bg-danger-subtle px-3 py-2 text-sm text-danger">{t(error)}</p>
          )}

          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? t('auth.signingIn') : t('auth.signIn')}
          </Button>
        </form>
        {showSignupLink && (
          <p className="mt-6 text-sm text-muted-foreground">
            {t('auth.newTo', { brandName })}{' '}
            <Link className="font-medium text-brand underline-offset-2 hover:underline" to="/signup">
              {t('auth.signUp')}
            </Link>
          </p>
        )}

      </div>
      </main>

      {/* Footer Links */}
      <footer className="flex flex-col items-center justify-center gap-2 pb-8 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <a
            href={brandWebsiteUrl || "https://www.coneshare.com/about"}
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            {t('auth.aboutBrand', { brandName: brandName || 'Coneshare' })}
          </a>
          <span className="text-muted-foreground/70">&bull;</span>
          <a
            href={termsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            {t('auth.terms')}
          </a>
          <span className="text-muted-foreground/70">&bull;</span>
          <a
            href={privacyPolicyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            {t('auth.privacy')}
          </a>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/80">
          <span>
            {t('viewer.poweredBy')}{' '}<a href="https://github.com/coneshare/coneshare" target="_blank" rel="noopener noreferrer" className="font-medium text-brand underline underline-offset-2">Coneshare</a>
          </span>
          {APP_DISPLAY_VERSION && (
            <>
              <span className="text-muted-foreground/70 select-none">&bull;</span>
              <span>{`ver-${APP_DISPLAY_VERSION}`}</span>
            </>
          )}
          <span className="text-muted-foreground/70 select-none">&bull;</span>
          <LanguagePicker />
        </div>
      </footer>
    </div>
  )
}

export default LoginPage
