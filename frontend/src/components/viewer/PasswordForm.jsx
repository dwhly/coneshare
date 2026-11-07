import { useState } from 'react';
import { toast } from 'sonner';
import { Lock, ArrowRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { verifyShareLinkPassword } from '../../services/api';
import { Button } from '../ui/Button';
import { Label } from '../ui/Label';
import { PasswordInput } from '../ui/PasswordInput';
import { GateLayout } from './GateLayout';

export function PasswordForm({ slug, onSuccess, publicMeta = null }) {
  const { t } = useTranslation();
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await verifyShareLinkPassword(slug, password);
      toast.success(t('viewer.accessGrantedLoading', { defaultValue: 'Access granted. Loading document...' }));
      onSuccess();
    } catch {
      // Error handled by global interceptor
      setIsLoading(false);
    }
  };

  return (
    <GateLayout publicMeta={publicMeta} maxWidth="max-w-md">
      <div className="space-y-4 pt-1">
        <div>
          <h2 className="text-lg font-semibold text-foreground tracking-tight">
            {t('viewer.enterPassword', { defaultValue: 'Enter Access Password' })}
          </h2>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            {t('viewer.passwordSubtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="space-y-1.5">
            <Label htmlFor="password" className="block text-xs font-medium text-foreground">
              {t('auth.password')}
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground z-10 pointer-events-none" />
              <PasswordInput
                id="password"
                name="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pl-10 font-mono tracking-wider"
                placeholder={t('viewer.enterPassword', { defaultValue: 'Enter Password' })}
                autoFocus
              />
            </div>
          </div>

          <div className="pt-1">
            <Button
              type="submit"
              size="lg"
              className="w-full flex items-center justify-center gap-2 active:scale-[0.98] transition-all bg-primary hover:bg-black text-primary-foreground"
              disabled={isLoading}
            >
              <span>{isLoading ? t('viewer.verifying') : t('viewer.continue', { defaultValue: 'Continue' })}</span>
              {!isLoading && <ArrowRight className="h-4 w-4 shrink-0" />}
            </Button>
          </div>
        </form>
      </div>
    </GateLayout>
  );
}
