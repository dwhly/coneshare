import { useEffect } from "react";
import { useBranding } from "../../contexts/BrandingProvider";

/**
 * Fleet design system chrome shared by every staff surface (DESIGN.md §6, §8):
 *  - FleetLockup: "Fleet | Dealroom" (.fds-lockup from components.css; same geometry in every fleet product)
 *  - ThemeToggle: the labelled Theme button, always LAST at the far right of the header (theme.js wires it)
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
  // theme.js rewrites the label ("Theme: auto|light|dark") on load and on every click.
  useEffect(() => {
    window.fdsTheme?.apply();
  }, []);
  return (
    <button type="button" className={`fds-btn ${className}`} data-fds-theme-toggle suppressHydrationWarning>
      Theme
    </button>
  );
}

/** Sign's staff inbox (the "Signatures" tab). The backend reports Sign's public URL with the brand. */
export function useSignaturesUrl() {
  const { signUrl } = useBranding();
  return signUrl ? `${signUrl.replace(/\/$/, "")}/inbox` : "";
}
