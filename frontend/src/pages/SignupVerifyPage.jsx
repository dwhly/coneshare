import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authService } from '../services/authService'
import { extractApiErrorMessage } from '../lib/apiErrors'
import { useBranding } from '../contexts/BrandingProvider'

export function SignupVerifyPage() {
  const navigate = useNavigate()
  const { brandName, brandLogoUrl, brandWebsiteUrl, termsUrl, privacyPolicyUrl } = useBranding()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('loading')
  const [message, setMessage] = useState('Verifying your account...')

  useEffect(() => {
    document.title = `Email Verification - ${brandName}`;
  }, [brandName]);

  useEffect(() => {
    let mounted = true
    let redirectTimer = null
    const uid = searchParams.get('uid')
    const token = searchParams.get('token')

    if (!uid || !token) {
      if (mounted) {
        setStatus('error')
        setMessage('Invalid verification link.')
      }
      return () => {
        mounted = false
        if (redirectTimer) clearTimeout(redirectTimer)
      }
    }

    const run = async () => {
      try {
        await authService.verifySignup({ uid, token })
        if (!mounted) return
        setStatus('success')
        setMessage('Your account has been verified. Redirecting...')
        redirectTimer = setTimeout(() => {
          if (mounted) navigate('/')
        }, 1000)
      } catch (err) {
        if (!mounted) return
        setStatus('error')
        setMessage(extractApiErrorMessage(err, 'Verification failed.'))
      }
    }

    run()
    return () => {
      mounted = false
      if (redirectTimer) clearTimeout(redirectTimer)
    }
  }, [navigate, searchParams])

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md">
        <div className="rounded-md bg-card p-6 shadow">
          {brandLogoUrl ? (
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-card p-2 shadow-sm border border-border">
              <img
                src={brandLogoUrl}
                alt={`${brandName} logo`}
                className="h-12 w-12 object-contain"
              />
            </div>
          ) : null}
          <h1 className="text-2xl font-bold text-foreground">Email Verification</h1>
          <p className={`mt-3 text-sm ${status === 'error' ? 'text-danger ' : 'text-muted-foreground '}`}>
            {message}
          </p>
          {status === 'error' && (
            <p className="mt-4 text-sm">
              <Link className="font-medium text-brand hover:underline" to="/signup">
                Request a new verification email
              </Link>
            </p>
          )}
        </div>

        {/* Footer Links */}
        <div className="mt-8 flex flex-col items-center justify-center gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <a
              href={brandWebsiteUrl || "https://www.coneshare.com/about"}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-muted-foreground transition-colors"
            >
              {brandWebsiteUrl ? `About ${brandName}` : "About Coneshare"}
            </a>
            <span className="text-muted-foreground/70">&bull;</span>
            <a
              href={termsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-muted-foreground transition-colors"
            >
              Terms
            </a>
            <span className="text-muted-foreground/70">&bull;</span>
            <a
              href={privacyPolicyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-muted-foreground transition-colors"
            >
              Privacy Policy
            </a>
          </div>
          <div className="text-[11px] text-muted-foreground/80">
            Powered by <a href="https://github.com/coneshare/coneshare" target="_blank" rel="noopener noreferrer" className="text-foreground hover:text-foreground font-semibold underline transition-colors">Coneshare</a>
          </div>
        </div>
      </div>
    </div>
  )
}
