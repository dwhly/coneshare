import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { MenuIcon, SearchIcon } from "lucide-react";
import { useNavItems } from "./SidebarContent";
import NavUser from "./NavUser";
import { TopBarSearch, TopBarSearchButton } from "./TopBarSearch";
import { Sheet, SheetContent, SheetTitle } from "../ui/Sheet";
import { useUser } from "../../contexts/UserProvider";
import { FleetLockup, ThemeToggle, useSignaturesUrl } from "./FleetChrome";

/**
 * Fleet app header (fleet-design-system DESIGN.md §6, one spec in every product):
 * background surface + 1px bottom border; "Fleet | Dealroom" lockup on the left; product tabs
 * (Rooms = this app, selected with a foreground underline; Signatures = Sign's staff inbox);
 * utilities on the right with the labelled Theme toggle LAST at the far right.
 * Trash, API docs, quota and version live in the account menu.
 */
export default function TopBar() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { handleLogout } = useUser();
  const navItems = useNavItems();
  const signaturesUrl = useSignaturesUrl();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const roomsActive = !pathname.startsWith("/settings") && !pathname.startsWith("/admin");

  return (
    <header className="fds-header sticky top-0 z-30 w-full gap-6 md:px-8" data-testid="app-header-container">
      <FleetLockup as={Link} to="/" className="shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />

      <nav className="fds-nav hidden md:flex" aria-label={t("nav.products", "Dealroom apps")}>
        <Link to="/datarooms" aria-current={roomsActive ? "page" : undefined}>
          {t("nav.rooms", "Rooms")}
        </Link>
        <a href={signaturesUrl || undefined} aria-disabled={signaturesUrl ? undefined : "true"}>
          {t("nav.signatures", "Signatures")}
        </a>
      </nav>

      <div className="fds-header__utils">
        <TopBarSearchButton className="hidden md:inline-flex" onClick={() => setIsSearchOpen(true)} />
        <button type="button" className="fds-btn md:hidden" onClick={() => setIsSearchOpen(true)} aria-label={t("nav.globalSearch", "Search")}>
          <SearchIcon className="h-4 w-4" />
        </button>
        <button type="button" className="fds-btn md:hidden" onClick={() => setIsMenuOpen(true)} aria-label={t("nav.menu", "Menu")}>
          <MenuIcon className="h-4 w-4" />
        </button>
        <NavUser variant="topbar" />
        <ThemeToggle />
      </div>

      <TopBarSearch open={isSearchOpen} onOpenChange={setIsSearchOpen} />

      <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
        <SheetContent className="flex w-full max-w-[350px] flex-col">
          <SheetTitle className="sr-only">{t("nav.menu", "Menu")}</SheetTitle>
          <FleetLockup as={Link} to="/" onClick={() => setIsMenuOpen(false)} />
          <div className="mt-8 flex w-full flex-col items-start gap-y-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setIsMenuOpen(false)}
                className="flex items-center gap-2 text-xl font-semibold text-foreground hover:text-foreground/80"
              >
                {item.href === "/datarooms" ? t("nav.rooms", "Rooms") : item.label}
              </Link>
            ))}
            {signaturesUrl && (
              <a href={signaturesUrl} className="text-xl font-semibold text-foreground hover:text-foreground/80">
                {t("nav.signatures", "Signatures")}
              </a>
            )}
            <button
              type="button"
              className="text-xl font-semibold text-foreground hover:text-foreground/80"
              onClick={handleLogout}
            >
              {t("auth.logout")}
            </button>
          </div>
        </SheetContent>
      </Sheet>
    </header>
  );
}
