import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export function SettingsTabs() {
  const { t } = useTranslation();

  const tabs = [
    { to: '/settings', label: t('settings.profile'), end: true },
    { to: '/settings/password', label: t('settings.password') },
    { to: '/settings/integrations', label: t('settings.cloudStorage') },
    { to: '/settings/api-keys', label: t('settings.mcpAndKeys') },
  ];

  return (
    <div className="border-b border-border mb-6">
      <nav className="-mb-px flex space-x-8" aria-label="Tabs">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `border-b-2 py-4 px-1 text-sm font-medium transition-colors ${
                isActive
                  ? 'border-foreground font-semibold text-foreground'
                  : 'border-transparent text-muted-foreground hover:border-input hover:text-foreground '
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
