import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronDown, LogOut, Settings } from "lucide-react";
import { useBranding } from "../../contexts/BrandingProvider";
import { getAvatarInitial } from "../../utils/formatters";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/DropdownMenu";

/**
 * Fleet design system chrome shared by every staff surface (DESIGN.md §6, §8):
 *  - FleetLockup: "Fleet | Dealroom" (.fds-lockup from components.css; same geometry in every fleet product)
 *  - ThemeToggle: the Theme icon button (fds v0.10), always LAST at the far right of the header (theme.js draws it)
 *  - AccountMenu / DealroomSubnav: the shared shell (fleet-dealroom docs/design/dealroom-shell.md §1-§2); geometry in
 *    /dealroom/shell.css, which the Django glue pages link too.
 */
export function FleetMark(props) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M12 2.5 16.2 10.4 12 8.6 7.8 10.4Z" />
      <path d="M6 10.5 10.2 18.4 6 16.6 1.8 18.4Z" opacity=".8" />
      <path d="M18 10.5 22.2 18.4 18 16.6 13.8 18.4Z" opacity=".8" />
    </svg>
  );
}

export function FleetLockup({ as: Comp = "a", product = "Dealroom", className = "", ...props }) {
  return (
    <Comp className={`fds-lockup ${className}`} aria-label={`Fleet ${product}`} {...props}>
      <FleetMark className="fds-lockup__mark" />
      <span className="fds-lockup__family">Fleet</span>
      <span className="fds-lockup__rule" aria-hidden="true" />
      <span className="fds-lockup__product">{product}</span>
    </Comp>
  );
}

export function ThemeToggle({ className = "" }) {
  // fds v0.10 theme.js draws the sun / moon / sun-moon icon into this empty button and sets title + aria-label
  // ("Theme: auto (light)") on load and on every click. React renders no children, so it never fights theme.js.
  useEffect(() => {
    window.fdsTheme?.apply();
  }, []);
  return (
    <button
      type="button"
      className={`fds-btn ${className}`}
      data-fds-theme-toggle
      aria-label="Theme"
      title="Theme"
      suppressHydrationWarning
    />
  );
}

/** Sign's staff inbox (the "Signatures" tab). The backend reports Sign's public URL with the brand. */
export function useSignaturesUrl() {
  const { signUrl } = useBranding();
  return signUrl ? `${signUrl.replace(/\/$/, "")}/inbox` : "";
}

/** A person's display name; never the email as the label (falls back to the email's local part, title-cased). */
export function displayName(user) {
  if (user?.name && user.name.trim()) return user.name.trim();
  const local = String(user?.email || "").split("@")[0];
  return local ? local.split(/[._-]+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(" ") : "Account";
}

/** Account menu = the person (§1): 28px neutral initials avatar + name + chevron; menu = email, Settings, Sign out. */
export function AccountMenu({ user, onSignOut, settingsHref = "/settings" }) {
  if (!user) return <span className="dr-account" aria-hidden="true"><span className="dr-avatar" /></span>;
  const name = displayName(user);
  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <button type="button" className="dr-account" data-testid="menu-switcher" aria-label={`Account: ${name}`}>
          <span className="dr-avatar" aria-hidden="true">{getAvatarInitial(user.name, user.email)}</span>
          <span className="dr-account__name">{name}</span>
          <ChevronDown className="dr-account__chevron" aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="dr-menu__label">{user.email}</div>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to={settingsHref}><Settings className="mr-2 h-4 w-4" aria-hidden="true" />Settings</Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={onSignOut}>
          <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Rooms section pages (§2): Rooms · Activity · Approvals. */
export const ROOMS_TABS = [
  { to: "/datarooms", label: "Rooms", match: (p) => p === "/" || p.startsWith("/datarooms") || p.startsWith("/signing") },
  { to: "/activity", label: "Activity", match: (p) => p.startsWith("/activity") },
  { to: "/approvals", label: "Approvals", match: (p) => p.startsWith("/approvals") },
];
export const isRoomsSection = (p) => ROOMS_TABS.some((t) => t.match(p));

export function DealroomSubnav() {
  const { pathname } = useLocation();
  return (
    <div className="dr-subnav">
      <nav aria-label="Rooms">
        {ROOMS_TABS.map((t) => (
          <Link key={t.to} to={t.to} aria-current={t.match(pathname) ? "page" : undefined}>
            {t.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
