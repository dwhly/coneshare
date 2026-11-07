import { useTranslation } from 'react-i18next';
import { ChevronDown, Globe } from 'lucide-react';
import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu';
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from '../ui/DropdownMenu';
import { SUPPORTED_LANGUAGES } from '../../lib/constants';

// Maps a detected browser language (e.g. "nl-be", "zh-tw") to a supported code.
const baseOf = (code) => code.split('-')[0];

function resolveLanguage(rawLang) {
  const match =
    SUPPORTED_LANGUAGES.find((lang) => lang.code === rawLang) ||
    SUPPORTED_LANGUAGES.find((lang) => baseOf(lang.code) === baseOf(rawLang));
  return match ? match.code : rawLang;
}

// Styled language menu (Fleet Dealroom shell: no native <select> on staff pages).
export function LanguagePicker({ className = '' }) {
  const { i18n, t } = useTranslation();
  const currentLang = resolveLanguage((i18n.language || 'en').toLowerCase());
  const current = SUPPORTED_LANGUAGES.find((lang) => lang.code === currentLang);

  return (
    <div className={`inline-flex items-center text-xs text-muted-foreground ${className}`}>
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger
          aria-label={t('settings.language')}
          className="inline-flex items-center gap-1.5 rounded px-1 text-xs text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <Globe className="h-3.5 w-3.5" aria-hidden="true" />
          {current ? current.name : currentLang}
          <ChevronDown className="h-3 w-3" aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="center" className="max-h-72 overflow-auto">
          <DropdownMenuPrimitive.RadioGroup value={currentLang} onValueChange={(code) => i18n.changeLanguage(code)}>
            {SUPPORTED_LANGUAGES.map((lang) => (
              <DropdownMenuPrimitive.RadioItem
                key={lang.code}
                value={lang.code}
                className="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none focus:bg-accent data-[state=checked]:bg-selected data-[state=checked]:text-selected-foreground"
              >
                {lang.name}
              </DropdownMenuPrimitive.RadioItem>
            ))}
          </DropdownMenuPrimitive.RadioGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
