import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useUser } from "../../contexts/UserProvider";
import { AccountMenu, FleetLockup, ThemeToggle, useSignaturesUrl } from "./FleetChrome";

/**
 * Fleet Dealroom staff header (docs/design/dealroom-shell.md §1; same spec as Sign's chief/fleet-header.tsx and the
 * Django _fleet_header.html): background surface, 1px bottom border, 56px, 24px padding. Lockup → Rooms | Signatures
 * tabs → flexible space → account menu (the person) → Theme last. No search box, no icon buttons.
 */
export default function TopBar() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { user, handleLogout } = useUser();
  const signaturesUrl = useSignaturesUrl();
  const roomsActive = !pathname.startsWith("/settings") && !pathname.startsWith("/admin");

  return (
    <header className="fds-header dr-header" data-testid="app-header-container">
      <FleetLockup as={Link} to="/datarooms" className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
      <nav className="fds-nav" aria-label={t("nav.products", "Dealroom apps")}>
        <Link to="/datarooms" aria-current={roomsActive ? "page" : undefined}>
          {t("nav.rooms", "Rooms")}
        </Link>
        <a href={signaturesUrl || undefined} aria-disabled={signaturesUrl ? undefined : "true"}>
          {t("nav.signatures", "Signatures")}
        </a>
      </nav>
      <div className="fds-header__utils">
        <AccountMenu user={user} onSignOut={handleLogout} />
        <ThemeToggle />
      </div>
    </header>
  );
}
