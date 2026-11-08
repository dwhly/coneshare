import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ChevronDown, ChevronLeft, ChevronRight, Copy, MoreHorizontal, Search, Upload } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/DropdownMenu";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";

/**
 * Fleet Dealroom page building blocks (docs/design/dealroom-shell.md §3). The geometry lives in
 * /dealroom/shell.css (shared with the Django glue pages), so React and server-rendered pages match.
 */

/** Breadcrumb (omit on top-level pages) → H1 24/600 → one-line subtitle; actions right-aligned on the H1 row. */
export function PageHead({ crumbs = [], title, subtitle, actions }) {
  return (
    <header className="dr-pagehead">
      {crumbs.length > 0 && (
        <nav aria-label="Breadcrumb">
          <ol className="dr-crumbs">
            {crumbs.map((c) => (
              <li key={c.label}>{c.to ? <Link to={c.to}>{c.label}</Link> : <span aria-current="page">{c.label}</span>}</li>
            ))}
          </ol>
        </nav>
      )}
      <div className="dr-pagehead__row">
        <h1>{title}</h1>
        {actions && <div className="dr-pagehead__actions">{actions}</div>}
      </div>
      {subtitle && <p className="dr-pagehead__sub">{subtitle}</p>}
    </header>
  );
}

export function Card({ title, subtitle, action, flush = false, children, ...props }) {
  return (
    <section className={`dr-card${flush ? " dr-card--flush" : ""}`} {...props}>
      {(title || action) && (
        <div className="dr-card__head">
          <div>
            {title && <h2 className="dr-card__title">{title}</h2>}
            {subtitle && <p className="dr-card__sub">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function EmptyState({ children, action }) {
  return (
    <div className="dr-empty">
      <p>{children}</p>
      {action}
    </div>
  );
}

export function SearchInput({ value, onChange, placeholder = "Search", label }) {
  return (
    <label className="dr-search">
      <Search aria-hidden="true" />
      <input
        className="dr-input"
        type="search"
        aria-label={label || placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

export function FilterButton({ pressed, onClick, children }) {
  return (
    <button type="button" className="dr-btn dr-filter" aria-pressed={pressed ? "true" : "false"} onClick={onClick}>
      {children}
    </button>
  );
}

const TONES = { neutral: "neutral", info: "info", success: "success", warning: "warning", danger: "danger" };
/** Status = bordered tinted pill with a word. */
export function StatusPill({ tone = "neutral", children }) {
  return <span className={`fds-pill fds-pill--${TONES[tone] || "neutral"}`}>{children}</span>;
}

/** Identity (people, orgs) = neutral chip with a tag-colour dot; the hue is a stable hash of the name. */
export function IdentityChip({ name, children }) {
  let h = 0;
  for (const ch of String(name || "")) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return (
    <span className="dr-chip" style={{ "--tag-dot": `var(--tag-${(h % 6) + 1})` }}>
      {children || name}
    </span>
  );
}

export function CopyField({ value, label = "Visitor link" }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      /* clipboard blocked (insecure context): the field stays selectable */
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <div className="dr-copy">
      <input className="dr-input" readOnly value={value} aria-label={label} onFocus={(e) => e.target.select()} />
      <button type="button" className="dr-btn" onClick={copy}>
        {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

/**
 * Styled select (Radix dropdown radio group; the app has no Radix Select dependency). Looks like a field,
 * opens a listbox-style menu, keyboard accessible. options: [{ value, label }].
 */
export function SelectMenu({ value, onChange, options, placeholder = "Choose…", label, id }) {
  const current = options.find((o) => o.value === value);
  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <button type="button" id={id} className="dr-select__trigger" aria-label={label}>
          <span className={current ? "" : "dr-muted"}>{current ? current.label : placeholder}</span>
          <ChevronDown aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-72 w-[var(--radix-dropdown-menu-trigger-width)] overflow-auto">
        <DropdownMenuPrimitive.RadioGroup value={value} onValueChange={onChange}>
          {options.map((o) => (
            <DropdownMenuPrimitive.RadioItem
              key={o.value}
              value={o.value}
              className="relative flex cursor-default select-none items-center gap-2 rounded-sm px-2 py-2 text-sm outline-none focus:bg-accent data-[state=checked]:bg-selected data-[state=checked]:text-selected-foreground"
            >
              <span className="flex-1 truncate">{o.label}</span>
              <DropdownMenuPrimitive.ItemIndicator>
                <Check className="h-4 w-4" aria-hidden="true" />
              </DropdownMenuPrimitive.ItemIndicator>
            </DropdownMenuPrimitive.RadioItem>
          ))}
        </DropdownMenuPrimitive.RadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Dashed dropzone with a "Choose file" outline button; the native file input is never shown. */
export function Dropzone({ accept, file, onFile, hint }) {
  const input = useRef(null);
  const [over, setOver] = useState(false);
  return (
    <div
      className="dr-dropzone"
      data-over={over ? "true" : "false"}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
      }}
    >
      <Upload aria-hidden="true" />
      <p>{file ? <span className="font-medium text-foreground">{file.name}</span> : "Drag a file here, or"}</p>
      <button type="button" className="dr-btn dr-btn--sm" onClick={() => input.current?.click()}>
        {file ? "Choose another file" : "Choose file"}
      </button>
      {hint && <p className="dr-hint">{hint}</p>}
      <input
        ref={input}
        type="file"
        hidden
        accept={accept}
        data-testid="dropzone-input"
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
      />
    </div>
  );
}

/** Raw evidence (payloads, ids) behind a "Details" disclosure. */
export function Details({ data, children, summary = "Details" }) {
  return (
    <details className="dr-details">
      <summary>{summary}</summary>
      {children}
      {data !== undefined && <pre>{typeof data === "string" ? data : JSON.stringify(data, null, 2)}</pre>}
    </details>
  );
}

/** Trailing ⋯ row menu. items: [{ label, onSelect, href, danger }]. */
export function RowMenu({ label = "Actions", items }) {
  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <button type="button" className="dr-btn dr-btn--icon" aria-label={label}>
          <MoreHorizontal aria-hidden="true" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {items.map((item) => (
          <DropdownMenuItem
            key={item.label}
            className={item.danger ? "text-danger focus:text-danger" : ""}
            onSelect={() => (item.href ? window.open(item.href, item.newTab ? "_blank" : "_self", "noopener") : item.onSelect?.())}
          >
            {item.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export const PAGE_SIZE = 10;

/** Client-side paging for a list table: resets to page 1 when the rows change shape (filters, search). */
export function usePaged(rows, pageSize = PAGE_SIZE, resetKey = "") {
  const [page, setPage] = useState(1);
  const total = rows ? rows.length : 0;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  useEffect(() => {
    setPage(1);
  }, [resetKey]);
  const current = Math.min(page, pages);
  const shown = useMemo(() => (rows || []).slice((current - 1) * pageSize, current * pageSize), [rows, current, pageSize]);
  return { shown, page: current, pages, total, pageSize, setPage };
}

/** "1 room" / "12 rooms" on one page; "Showing 1–10 of 47" + pager when there is more than one page. */
export function footerText(total, page, pageSize, noun, plural, more = false) {
  if (total <= pageSize && !more) return `${total} ${total === 1 ? noun : plural || `${noun}s`}`;
  const from = total ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(total, page * pageSize);
  return `Showing ${from}–${to} of ${total}${more ? "+" : ""}`;
}

/** Table footer (§7): on every list table, inside the table's border. */
export function TableFooter({ paged, noun, plural, more = false }) {
  const { total, page, pages, pageSize, setPage } = paged;
  return (
    <div className="dr-tfoot">
      <span>{footerText(total, page, pageSize, noun, plural, more)}</span>
      {pages > 1 && (
        <nav className="dr-pager" aria-label="Pages">
          <button type="button" className="dr-btn" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            <ChevronLeft aria-hidden="true" />
          </button>
          <span className="dr-pager__page">
            Page {page} of {pages}
          </span>
          <button type="button" className="dr-btn" aria-label="Next page" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            <ChevronRight aria-hidden="true" />
          </button>
        </nav>
      )}
    </div>
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** DESIGN.md §4 dates: "Nov 4" this year, "Nov 4, 2025" otherwise; withTime adds ", 14:05". */
export function formatDate(value, { withTime = false } = {}) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const sameYear = d.getFullYear() === new Date().getFullYear();
  let s = `${MONTHS[d.getMonth()]} ${d.getDate()}${sameYear ? "" : `, ${d.getFullYear()}`}`;
  if (withTime) s += `, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  return s;
}

/** "under 24 h → relative; absolute on hover" (DESIGN.md §4). */
export function TimeCell({ value }) {
  if (!value) return <span className="dr-muted">—</span>;
  const d = new Date(value);
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  const abs = formatDate(value, { withTime: true });
  let text = abs;
  if (mins >= 0 && mins < 60 * 24) text = mins < 1 ? "just now" : mins < 60 ? `${mins} min ago` : `${Math.round(mins / 60)} h ago`;
  return (
    <time dateTime={value} title={abs}>
      {text}
    </time>
  );
}

export function formatBytes(n) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

/** "document.viewed" / "grant_created" → "Document viewed" (sentence case). */
export function humanEvent(type) {
  const s = String(type || "").replace(/[._]+/g, " ").trim();
  return s ? s[0].toUpperCase() + s.slice(1) : "Event";
}

export function errorText(e) {
  const d = e?.response?.data;
  if (!d) return e?.message || "Something went wrong.";
  if (typeof d === "string") return d;
  if (d.detail) return String(d.detail);
  const first = Object.entries(d)[0];
  if (!first) return "Something went wrong.";
  const [key, val] = first;
  const msg = Array.isArray(val) ? val[0] : typeof val === "string" ? val : JSON.stringify(val);
  return key === "non_field_errors" ? msg : `${key.replace(/_/g, " ")}: ${msg}`;
}
