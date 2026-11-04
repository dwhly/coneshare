import { useEffect, useMemo, useState } from "react";
import { Search, LayoutGrid } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { Dialog, DialogContent, DialogTitle } from "../ui/Dialog";
import { getDatarooms } from "../../services/api";
import { useNavItems } from "./SidebarContent";
import { cn } from "../../lib/utils";

/**
 * Prototype top-bar search. Same trigger treatment as Sign's AppNavDesktop search (outline button,
 * "Search", ⌘+K chip). Coneshare has no global search API, so this is a jump-to palette over the
 * app's pages and the user's data rooms (client-side filter).
 */
export function TopBarSearch({ open, onOpenChange }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const navItems = useNavItems();
  const [query, setQuery] = useState("");
  const [rooms, setRooms] = useState([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActive(0);
    Promise.resolve()
      .then(() => getDatarooms({}))
      .then((res) => setRooms(Array.isArray(res?.data) ? res.data : res?.data?.results || []))
      .catch(() => setRooms([]));
  }, [open]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const pages = navItems.map((i) => ({ key: `p${i.href}`, group: "pages", label: i.label, icon: i.icon, href: i.href }));
    const roomItems = rooms.map((r) => ({ key: `r${r.id}`, group: "rooms", label: r.name, icon: LayoutGrid, href: `/datarooms/${r.id}` }));
    const all = [...pages, ...roomItems];
    return q ? all.filter((i) => (i.label || "").toLowerCase().includes(q)) : all;
  }, [query, navItems, rooms]);

  const go = (item) => {
    if (!item) return;
    onOpenChange(false);
    navigate(item.href);
  };

  const onInputKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    if (e.key === "Enter") { e.preventDefault(); go(results[active]); }
  };

  const groups = [
    { id: "pages", label: t("nav.searchPages", "Pages") },
    { id: "rooms", label: t("nav.datarooms") },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[20%] max-w-lg translate-y-0 gap-0 overflow-hidden p-0 data-[state=open]:slide-in-from-top-[20%]">
        <DialogTitle className="sr-only">{t("nav.globalSearch", "Search")}</DialogTitle>
        <div className="flex items-center border-b px-3">
          <Search className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActive(0); }}
            onKeyDown={onInputKey}
            placeholder={t("nav.searchPlaceholder", "Type a command or search...")}
            className="flex h-11 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>
        <div className="max-h-[300px] overflow-y-auto p-1">
          {results.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">{t("nav.searchEmpty", "No results found.")}</p>
          )}
          {groups.map((g) => {
            const items = results.filter((r) => r.group === g.id);
            if (!items.length) return null;
            return (
              <div key={g.id} className="py-1">
                <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">{g.label}</div>
                {items.map((item) => {
                  const idx = results.indexOf(item);
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onMouseEnter={() => setActive(idx)}
                      onClick={() => go(item)}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm",
                        idx === active && "bg-accent text-accent-foreground"
                      )}
                    >
                      <item.icon className="h-4 w-4 text-muted-foreground" />
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function TopBarSearchButton({ onClick }) {
  const { t } = useTranslation();
  const [modifierKey, setModifierKey] = useState("Ctrl");
  useEffect(() => {
    setModifierKey(/Macintosh|Mac\s+OS\s+X/i.test(navigator.userAgent) ? "⌘" : "Ctrl");
  }, []);
  return (
    <Button
      variant="outline"
      className="flex w-full max-w-96 items-center justify-between rounded-lg text-muted-foreground"
      onClick={onClick}
    >
      <div className="flex items-center">
        <Search className="mr-2 h-5 w-5" />
        {t("nav.globalSearch", "Search")}
      </div>
      <div>
        <div className="flex items-center rounded-md bg-muted px-1.5 py-0.5 text-xs tracking-wider text-muted-foreground">
          {modifierKey}+K
        </div>
      </div>
    </Button>
  );
}
