import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";
import { BreadcrumbProvider } from "./BreadcrumbProvider";
import { SidebarProvider, useSidebar } from "./SidebarProvider";
import { cn } from "../../lib/utils";
import { UserProvider } from "../../contexts/UserProvider";
import { UploadProgressIndicator } from "../documents/UploadProgressIndicator";
import { useLanguageSync } from "../../hooks/useLanguageSync";
import { applyLayoutParam, useLayoutMode } from "../../lib/layoutMode";

function SidebarLayout() {
  const { isCollapsed } = useSidebar();
  return (
    <div
      className={cn(
        "grid h-screen w-full transition-all",
        isCollapsed
          ? "md:grid-cols-[4rem_1fr]"
          : "md:grid-cols-[16rem_1fr]"
      )}
    >
      <Sidebar />
      <div className="grid grid-rows-[auto_1fr] overflow-hidden">
        <Header />
        <main className="overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
      <UploadProgressIndicator />
    </div>
  );
}

// Prototype: Sign-style top bar. <main> stays the scroll container (pages rely on it), so the
// header's scroll hairline listens to <main> instead of window, matching Sign's scrollY > 5 rule.
function TopBarLayout() {
  const [scrolled, setScrolled] = useState(false);
  return (
    <div className="grid h-screen w-full grid-cols-[minmax(0,1fr)] grid-rows-[auto_1fr] overflow-hidden">
      <TopBar scrolled={scrolled} />
      <main className="overflow-auto" onScroll={(e) => setScrolled(e.currentTarget.scrollTop > 5)}>
        {/* Pages bring their own container + p-4/md:p-6, so md:px-2 puts content on Sign's 32px gutter. */}
        <div className="mx-auto w-full max-w-screen-xl pb-8 pt-2 md:px-2 md:pb-12 md:pt-4">
          <Header variant="inline" />
          <Outlet />
        </div>
      </main>
      <UploadProgressIndicator />
    </div>
  );
}

function Layout() {
  useLanguageSync();
  const { search } = useLocation();
  useEffect(() => applyLayoutParam(search), [search]);
  const mode = useLayoutMode();
  return mode === "topbar" ? <TopBarLayout /> : <SidebarLayout />;
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
