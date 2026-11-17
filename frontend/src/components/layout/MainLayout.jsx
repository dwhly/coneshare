import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import TopBar from "./TopBar";
import { BreadcrumbProvider } from "./BreadcrumbProvider";
import { SidebarProvider } from "./SidebarProvider";
import { UserProvider } from "../../contexts/UserProvider";
import { UploadProgressIndicator } from "../documents/UploadProgressIndicator";
import { useLanguageSync } from "../../hooks/useLanguageSync";
import { applyLayoutParam } from "../../lib/layoutMode";
import { DealroomSubnav, isRoomsSection } from "./FleetChrome";
import { useBreadcrumb } from "./BreadcrumbProvider";
import { pageTitle } from "../../hooks/usePageTitle";

const SECTION_TITLES = [
  ["/datarooms", "Rooms"],
  ["/activity", "Activity"],
  ["/approvals", "Approvals"],
  ["/documents", "Documents"],
  ["/file-requests", "File requests"],
  ["/analytics", "Analytics"],
  ["/automations", "Automations"],
  ["/trash", "Trash"],
  ["/settings", "Settings"],
  ["/admin", "Admin"],
];

/** "<room or section> · Fleet Dealroom" for every console page (the login page title used to stick). */
function useConsoleTitle() {
  const { pathname } = useLocation();
  const { breadcrumbData } = useBreadcrumb();
  const section = pathname === "/" ? "Rooms" : (SECTION_TITLES.find(([p]) => pathname.startsWith(p)) || [null, ""])[1];
  const room = pathname.startsWith("/datarooms/") && breadcrumbData?.type === "dataroom" ? breadcrumbData.dataroomName : "";
  // Rooms-section pages set their own "<page> · Fleet Dealroom" (parent effects run after children's).
  useEffect(() => {
    if (!isRoomsSection(pathname)) document.title = pageTitle(room || section);
  }, [pathname, room, section]);
}

// Fleet Dealroom shell (docs/design/dealroom-shell.md): the 56px app header, then for the Rooms section the
// sub-nav (Rooms · Activity · Approvals) and pages that bring their own 1200px .dr-container. Other pages (settings,
// admin, legacy Coneshare views) keep their own container. <main> stays the scroll container.
function TopBarLayout() {
  const { pathname } = useLocation();
  const rooms = isRoomsSection(pathname);
  return (
    <div className="grid h-screen w-full grid-cols-[minmax(0,1fr)] grid-rows-[auto_1fr] overflow-hidden bg-background">
      <TopBar />
      <main className="overflow-auto">
        {rooms ? (
          <>
            {!pathname.startsWith("/datarooms/") && <DealroomSubnav />}
            <Outlet />
          </>
        ) : (
          <div className="mx-auto w-full max-w-[1200px] pb-8 pt-2 md:pb-12 md:pt-4">
            <Header variant="inline" />
            <Outlet />
          </div>
        )}
      </main>
      <UploadProgressIndicator />
    </div>
  );
}

function Layout() {
  useLanguageSync();
  useConsoleTitle();
  const { search } = useLocation();
  useEffect(() => applyLayoutParam(search), [search]);
  // One shell for every staff page (spec §1): the sidebar arrangement is retired; ?layout= is ignored.
  return <TopBarLayout />;
}

function MainLayout() {
  return (
    <SidebarProvider>
      <UserProvider>
        <BreadcrumbProvider>
          <Layout />
        </BreadcrumbProvider>
      </UserProvider>
    </SidebarProvider>
  );
}

export default MainLayout;
