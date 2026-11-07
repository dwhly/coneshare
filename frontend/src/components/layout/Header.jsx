import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Breadcrumbs } from "../documents/Breadcrumbs";
import { useBreadcrumb } from "./BreadcrumbProvider";
import { useNavItems } from "./SidebarContent";
import { DataroomBreadcrumbs } from "../datarooms/DataroomBreadcrumbs";
import { ThemeToggle, useSignaturesUrl } from "./FleetChrome";

function Header({ variant = "bar" }) {
  const { t } = useTranslation();
  const { breadcrumbData } = useBreadcrumb();
  const { pathname } = useLocation();
  const navItems = useNavItems();
  const signaturesUrl = useSignaturesUrl();

  // Find the current nav item. Reverse to match more specific paths first (e.g., /documents before /)
  const currentNavItem = navItems.slice()
    .reverse()
    .find((item) => pathname.startsWith(item.href));
  let title = currentNavItem ? currentNavItem.label : "";

  if (pathname.startsWith('/admin')) {
    title = t('nav.adminPanel', 'Admin Panel');
  }

  const renderBreadcrumbs = () => {
    if (!breadcrumbData) {
      return <h1 className="text-lg font-semibold">{title}</h1>;
    }

    // Check for an explicit type property for more robust routing
    if (breadcrumbData.type === 'dataroom') {
      return (
        <DataroomBreadcrumbs
          dataroomName={breadcrumbData.dataroomName}
          currentFolder={breadcrumbData.folder}
          onNavigate={breadcrumbData.onNavigate}
        />
      );
    }

    if (breadcrumbData.type === 'fileRequest') {
      return (
        <nav className="flex" aria-label="Breadcrumb">
          <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-base font-medium text-muted-foreground">
            <li>
              <Link to="/file-requests" className="hover:text-foreground">
                {t('nav.fileRequests', 'File Requests')}
              </Link>
            </li>
            <li className="flex items-center">
              <span className="select-none px-1 text-muted-foreground">/</span>
              <span className="font-semibold text-foreground">{breadcrumbData.fileRequestName}</span>
            </li>
          </ol>
        </nav>
      );
    }

    // Default to documents breadcrumbs
    return <Breadcrumbs currentFolder={breadcrumbData} />;
  };

  // Top-bar layout: the title/breadcrumbs become the first row of the page container (no bar chrome).
  // List pages skip the plain title (the active nav link and the page H1 already name the section).
  if (variant === "inline") {
    if (!breadcrumbData) return null;
    return <div className="flex min-h-8 items-center px-4 pt-2 md:px-6">{renderBreadcrumbs()}</div>;
  }

  return (
    <header className="fds-header gap-6 px-6">
      <nav className="fds-nav hidden md:flex" aria-label={t("nav.products", "Dealroom apps")}>
        <Link to="/datarooms" aria-current="page">{t("nav.rooms", "Rooms")}</Link>
        <a href={signaturesUrl || undefined}>{t("nav.signatures", "Signatures")}</a>
      </nav>
      <div className="hidden h-6 w-px bg-border md:block" aria-hidden="true" />
      {renderBreadcrumbs()}
      <div className="fds-header__utils">
        <ThemeToggle />
      </div>
    </header>
  );
}

export default Header;
