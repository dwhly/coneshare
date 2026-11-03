import { ChevronsLeft, ChevronsRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSidebar } from "./SidebarProvider";
import { Button } from "../ui/Button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/Tooltip";

import { useBranding } from "../../contexts/BrandingProvider";
import { AmforgeLogo, AmforgeMark } from "./AmforgeLogo";

function SidebarHeader() {
  const { t } = useTranslation();
  const { isCollapsed, toggleSidebar } = useSidebar();
  const { brandName, brandWebsiteUrl } = useBranding();

  // AmForge shell: the app chrome always shows the AmForge mark/wordmark; the product name lives in
  // the product switcher (Header). Per-dataroom/org branding still applies to visitor-facing pages.
  const logoContent = isCollapsed ? (
    <AmforgeMark className="h-6 w-6" />
  ) : (
    <AmforgeLogo className="h-6 w-auto text-foreground" />
  );

  return (
    <div className="flex h-14 items-center border-b px-4">
      {brandWebsiteUrl ? (
        <a
          href={brandWebsiteUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-1 items-center gap-2 font-semibold"
          aria-label={`${brandName} Home`}
        >
          {logoContent}
        </a>
      ) : (
        <Link
          to="/"
          className="flex flex-1 items-center gap-2 font-semibold"
          aria-label={`${brandName} Home`}
        >
          {logoContent}
        </Link>
      )}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className="h-8 w-8"
            >
              {isCollapsed ? (
                <ChevronsRight className="h-5 w-5" />
              ) : (
                <ChevronsLeft className="h-5 w-5" />
              )}
              <span className="sr-only">{t('nav.toggleSidebar')}</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p>{t('nav.pressToToggleSidebar')}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
export default SidebarHeader;
