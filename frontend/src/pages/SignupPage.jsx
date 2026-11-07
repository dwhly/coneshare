import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { authService } from '../services/authService'
import { extractApiErrorMessage } from '../lib/apiErrors'
import { useBranding } from '../contexts/BrandingProvider'
import { Button } from '../components/ui/Button'
import { APP_DISPLAY_VERSION } from '../lib/constants'
import { LanguagePicker } from '../components/common/LanguagePicker'

export function SignupPage() {
  const { t } = useTranslation()
  const { brandName, brandLogoUrl, brandWebsiteUrl, termsUrl, privacyPolicyUrl } = useBranding()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    document.title = `${t('auth.createAccount')} - ${brandName}`;
  }, [brandName, t]);

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      await authService.requestSignup({ email, password, name })
      setSubmitted(true)
    } catch (err) {
      setError(extractApiErrorMessage(err, t('auth.signupFailed')))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center">
          {brandLogoUrl ? (
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-card p-2 shadow-sm border border-border">
              <img
                src={brandLogoUrl}
                alt={`${brandName} logo`}
                className="h-12 w-12 object-contain"
              />
            </div>
          ) : null}
          <h2 className="text-center text-3xl font-extrabold text-foreground">
            {t('auth.createAccount')}
          </h2>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            {t('auth.signUpSubtitle')}
          </p>
        </div>

        {submitted ? (
          <div className="rounded-md border border-success-border bg-success-subtle p-4 text-sm text-success">
            {t('auth.verificationSent')}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div className="space-y-4 rounded-md shadow-sm">
              <div>
                <label htmlFor="name" className="sr-only">
                  {t('auth.name')}
                </label>
                <input
                  id="name"
                  type="text"
                  autoComplete="name"
                  className="relative block w-full appearance-none rounded-md border border-input px-3 py-2 text-foreground placeholder-muted-foreground focus:z-10 focus:border-ring focus:outline-none focus:ring-ring sm:text-sm"
                  placeholder={t('auth.name')}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="email" className="sr-only">
                  {t('auth.email')}
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="relative block w-full appearance-none rounded-md border border-input px-3 py-2 text-foreground placeholder-muted-foreground focus:z-10 focus:border-ring focus:outline-none focus:ring-ring sm:text-sm"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="password" className="sr-only">
                  {t('auth.password')}
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  className="relative block w-full appearance-none rounded-md border border-input px-3 py-2 text-foreground placeholder-muted-foreground focus:z-10 focus:border-ring focus:outline-none focus:ring-ring sm:text-sm"
                  placeholder={t('auth.createPasswordPlaceholder')}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            {error && (
              <p className="text-sm text-danger">{error}</p>
            )}

            <div>
              <Button
                type="submit"
                size="lg"
                disabled={isLoading}
                className="w-full active:scale-[0.98] transition-transform"
              >
                {isLoading ? t('auth.submitting') : t('auth.signUp')}
              </Button>
            </div>
          </form>
        )}

        <p className="text-center text-sm text-muted-foreground">
          {t('auth.alreadyHaveAccount')}{' '}
          <Link className="font-medium text-brand hover:underline" to="/login">
            {t('auth.signIn')}
          </Link>
        </p>
      </div>

      {/* Footer Links */}
      <div className="mt-auto pt-8 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <a
            href={brandWebsiteUrl || "https://www.coneshare.com/about"}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-muted-foreground transition-colors"
          >
            {t('auth.aboutBrand', { brandName: brandName || 'Coneshare' })}
          </a>
          <span className="text-muted-foreground/70">&bull;</span>
          <a
            href={termsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-muted-foreground transition-colors"
          >
            {t('auth.terms')}
          </a>
          <span className="text-muted-foreground/70">&bull;</span>
          <a
            href={privacyPolicyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-muted-foreground transition-colors"
          >
            {t('auth.privacy')}
          </a>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground/80">
          <span>
            {t('viewer.poweredBy')}{' '}<a href="https://github.com/coneshare/coneshare" target="_blank" rel="noopener noreferrer" className="text-foreground hover:text-foreground font-semibold underline transition-colors">Coneshare</a>
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
      </div>
    </div>
  )
}
