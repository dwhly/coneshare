import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { MenuIcon, SearchIcon } from "lucide-react";
import { cn } from "../../lib/utils";
import { AmforgeLogo } from "./AmforgeLogo";
import { AmforgeProductSwitcher } from "./AmforgeProductSwitcher";
import { useNavItems } from "./SidebarContent";
import NavUser from "./NavUser";
import { TopBarSearch, TopBarSearchButton } from "./TopBarSearch";
import { Sheet, SheetContent, SheetTitle } from "../ui/Sheet";
import { useUser } from "../../contexts/UserProvider";

const isActive = (href, pathname) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

/**
 * Prototype top-bar shell for Send. Structure and classes follow Sign's app-header.tsx +
 * app-nav-desktop.tsx (h-16, max-w-screen-xl md:px-8 container, wordmark -> switcher -> inline nav ->
 * search -> account; the wordmark links to Dashboard) so send-topbar and sign-topbar read as one product. Trash, API docs, quota and
 * version (the sidebar footer) move into the account menu.
 */
export default function TopBar({ scrolled }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { handleLogout } = useUser();
  const navItems = useNavItems();
  // Like Sign, the wordmark is the way home (Dashboard); Trash moves to the account menu.
  const inline = navItems.filter((i) => i.href !== "/trash" && i.href !== "/");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-16 w-full items-center border-b border-b-transparent bg-background/95 backdrop-blur duration-200 supports-[backdrop-filter]:bg-background/60",
        scrolled && "border-b-border"
      )}
    >
      <div
        className="mx-auto flex w-full max-w-screen-xl items-center justify-between gap-x-4 px-4 md:justify-normal md:px-8"
        data-testid="app-header-container"
      >
        <Link
          to="/"
          className="hidden rounded-md ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 md:inline"
          aria-label="AmForge Home"
        >
          <AmforgeLogo className="h-6 w-auto text-foreground" />
        </Link>

        <AmforgeProductSwitcher current="send" className="ml-6 hidden md:inline-flex" />

        <div className="ml-8 hidden flex-1 items-center gap-x-12 md:flex md:justify-between">
          <div className="flex items-baseline gap-x-6">
            {inline.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  "whitespace-nowrap rounded-md font-medium leading-5 text-muted-foreground ring-offset-background hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:text-muted-foreground/60",
                  isActive(item.href, pathname) && "text-foreground dark:text-muted-foreground"
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>
          <TopBarSearchButton onClick={() => setIsSearchOpen(true)} />
        </div>

        <div className="md:ml-4">
          <NavUser variant="topbar" />
        </div>

        <div className="flex flex-row items-center space-x-4 md:hidden">
          <button type="button" onClick={() => setIsSearchOpen(true)} aria-label={t("nav.globalSearch", "Search")}>
            <SearchIcon className="h-6 w-6 text-muted-foreground" />
          </button>
          <button type="button" onClick={() => setIsMenuOpen(true)} aria-label={t("nav.menu", "Menu")}>
            <MenuIcon className="h-6 w-6 text-muted-foreground" />
          </button>
        </div>
      </div>

      <TopBarSearch open={isSearchOpen} onOpenChange={setIsSearchOpen} />

      <Sheet open={isMenuOpen} onOpenChange={setIsMenuOpen}>
        <SheetContent className="flex w-full max-w-[350px] flex-col">
          <SheetTitle className="sr-only">{t("nav.menu", "Menu")}</SheetTitle>
          <Link to="/" onClick={() => setIsMenuOpen(false)}>
            <AmforgeLogo product="send" className="h-6 w-auto text-foreground" />
          </Link>
          <AmforgeProductSwitcher current="send" className="mt-6 self-start" />
          <div className="mt-8 flex w-full flex-col items-start gap-y-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setIsMenuOpen(false)}
                className="flex items-center gap-2 text-2xl font-semibold text-foreground hover:text-foreground/80"
              >
                {item.label}
              </Link>
            ))}
            <button
              type="button"
              className="text-2xl font-semibold text-foreground hover:text-foreground/80"
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
