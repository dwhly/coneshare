import { BookOpen, ChevronsUpDown, CircleUserRound, KeyRound, LogOut, Shield, Cloud, Lock, Sparkles, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/Avatar";
import { Button } from "../ui/Button";
import { Progress } from "../ui/Progress";
import { Skeleton } from "../ui/Skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/DropdownMenu";
import { useSidebar } from "./SidebarProvider";
import { cn } from "../../lib/utils";
import { useUser } from "../../contexts/UserProvider";
import { getAvatarInitial } from "../../utils/formatters";
import { formatBytes } from "../../lib/formatters";
import { APP_DISPLAY_VERSION } from "../../lib/constants";
import { setLayoutMode, useLayoutMode } from "../../lib/layoutMode";

/** Prototype: "Layout: Sidebar | Top bar", same Tabs-primitive treatment as the product switcher. */
function LayoutToggle() {
  const { t } = useTranslation();
  const mode = useLayoutMode();
  const options = [
    { id: "sidebar", label: t("nav.layoutSidebar", "Sidebar") },
    { id: "topbar", label: t("nav.layoutTopbar", "Top bar") },
  ];
  return (
    <div className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm">
      <span className="text-muted-foreground">{t("nav.layout", "Layout")}</span>
      <div
        role="radiogroup"
        aria-label={t("nav.layout", "Layout")}
        className="inline-flex h-7 items-center rounded-md bg-muted p-0.5 text-muted-foreground"
      >
        {options.map((o) => (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={mode === o.id}
            onClick={() => setLayoutMode(o.id)}
            className={cn(
              "inline-flex h-6 items-center rounded-sm px-2 text-xs font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              mode === o.id ? "bg-background text-foreground shadow-sm" : "hover:text-foreground"
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Top-bar only: the sidebar footer's quota + version, moved into the account menu. */
function QuotaAndVersion({ user }) {
  const { t } = useTranslation();
  const quotaMB = user?.file_size_quota_mb || 0;
  const usageBytes = user?.total_document_size || 0;
  const quotaBytes = quotaMB * 1024 * 1024;
  const usagePercentage = quotaMB > 0 ? (usageBytes / quotaBytes) * 100 : 0;
  return (
    <div className="space-y-2 px-2 py-1.5 text-xs">
      <div className="flex justify-between font-medium text-muted-foreground">
        <span>{t("nav.usedQuota", { size: formatBytes(usageBytes) })}</span>
        <span>{quotaMB > 0 ? formatBytes(quotaBytes, 0) : t("nav.unlimited")}</span>
      </div>
      <Progress value={usagePercentage} className="h-2" />
      {APP_DISPLAY_VERSION && <div className="text-muted-foreground">{`ver-${APP_DISPLAY_VERSION}`}</div>}
    </div>
  );
}

function NavUser({ variant = "sidebar" }) {
  const { t } = useTranslation();
  const { isCollapsed } = useSidebar();
  const navigate = useNavigate();
  const { user, handleLogout } = useUser();
  const isTopbar = variant === "topbar";

  if (!user) {
    if (isTopbar) {
      return (
        <div className="flex h-12 items-center gap-2 md:px-2">
          <Skeleton className="h-10 w-10 shrink-0 rounded-full" />
          <div className="hidden gap-1.5 lg:grid">
            <Skeleton className="h-3.5 w-24" />
            <Skeleton className="h-2.5 w-32" />
          </div>
        </div>
      );
    }
    return (
      <div
        className={cn(
          "flex items-center gap-2 rounded-lg",
          isCollapsed ? "h-10 w-10 justify-center p-0" : "px-3 py-2"
        )}
      >
        <Skeleton className="h-8 w-8 rounded-full shrink-0" />
        <div className={cn("grid flex-1 gap-1.5", isCollapsed && "hidden")}>
          <Skeleton className="h-3.5 w-24" />
          <Skeleton className="h-2.5 w-32" />
        </div>
      </div>
    );
  }

  // Top bar trigger mirrors Sign's OrgMenuSwitcher (AvatarWithText: h-10 avatar, two-line label from lg, chevrons).
  const trigger = isTopbar ? (
    <button
      type="button"
      data-testid="menu-switcher"
      className="relative flex h-12 flex-row items-center px-0 py-2 ring-0 focus:outline-none focus-visible:ring-0 md:px-2"
    >
      <div className="flex w-full max-w-xs items-center gap-2">
        <Avatar className="h-10 w-10 border-2 border-solid border-white dark:border-border">
          <AvatarImage src={user.avatar_url || ""} alt={user.name || ""} />
          <AvatarFallback className="text-xs text-gray-400">{getAvatarInitial(user.name, user.email)}</AvatarFallback>
        </Avatar>
        <div className="hidden max-w-[8rem] flex-col truncate text-left text-sm font-normal lg:flex">
          <span className="truncate text-foreground">{user.name || user.email}</span>
          <span className="truncate text-xs text-muted-foreground">
            {user.role === "admin" ? t("nav.roleAdmin", "Admin") : t("nav.roleMember", "Member")}
          </span>
        </div>
        <ChevronsUpDown className="ml-auto h-4 w-4 text-muted-foreground" />
      </div>
    </button>
  ) : (
    <Button
      variant="ghost"
      className={cn(
        "w-full justify-start gap-2",
        isCollapsed ? "h-10 w-10 justify-center p-0" : "px-3"
      )}
    >
      <Avatar className="h-8 w-8">
        <AvatarImage src={user.avatar_url || ""} alt={user.name || ""} />
        <AvatarFallback>{getAvatarInitial(user.name, user.email)}</AvatarFallback>
      </Avatar>
      <div
        className={cn("grid flex-1 text-left", isCollapsed && "hidden")}
      >
        <span className="truncate text-sm font-semibold">{user.name || user.email}</span>
        <span className="truncate text-xs text-gray-500">
          {user.email}
        </span>
      </div>
      <ChevronsUpDown
        className={cn("ml-auto h-4 w-4", isCollapsed && "hidden")}
      />
    </Button>
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
      <DropdownMenuContent className={cn(isTopbar ? "w-64" : "w-56")} align="end" forceMount>
        <DropdownMenuGroup>
          <DropdownMenuItem onSelect={() => navigate("/settings")}>
            <CircleUserRound className="mr-2 h-4 w-4" />
            <span>{t('settings.profile')}</span>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => navigate("/settings/password")}>
            <Lock className="mr-2 h-4 w-4" />
            <span>{t('settings.changePassword')}</span>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => navigate("/settings/integrations")}>
            <Cloud className="mr-2 h-4 w-4" />
            <span>{t('settings.cloudStorage')}</span>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={() => navigate("/settings/api-keys")}>
            <Sparkles className="mr-2 h-4 w-4" />
            <span>{t('settings.mcpAndKeys')}</span>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        {isTopbar && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate("/trash")}>
              <Trash2 className="mr-2 h-4 w-4" />
              <span>{t('nav.trash')}</span>
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => window.open("/api/schema/swagger/", "_blank", "noopener,noreferrer")}>
              <BookOpen className="mr-2 h-4 w-4" />
              <span>{t('nav.apiDocs')}</span>
            </DropdownMenuItem>
          </>
        )}
        {user?.role == 'admin' && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => navigate("/admin/settings")}>
              <Shield className="mr-2 h-4 w-4" />
              <span>{t('settings.adminPanel')}</span>
            </DropdownMenuItem>
          </>
        )}
        {isTopbar && (
          <>
            <DropdownMenuSeparator />
            <QuotaAndVersion user={user} />
          </>
        )}
        <DropdownMenuSeparator />
        <LayoutToggle />
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          <span>{t('auth.logout')}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default NavUser;
