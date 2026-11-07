import { FileCode, FileIcon, FileImageIcon, FileQuestion, FileSpreadsheet, FileTextIcon, FolderIcon, FileVideo } from "lucide-react";

function normalizeType(type) {
  if (!type) return "unknown";
  const raw = String(type).trim().toLowerCase();
  if (raw === "folder") return "folder";
  if (raw === "pdf" || raw.endsWith(".pdf")) return "pdf";
  if (raw === "image" || ["jpg", "jpeg", "png", "gif", "svg", "webp", "bmp"].includes(raw) || /\.(jpg|jpeg|png|gif|svg|webp|bmp)$/i.test(raw)) return "image";
  if (
    raw === "video" ||
    ["mov", "mp4", "avi", "webm", "m3u8", "mkv"].includes(raw) ||
    /\.(mov|mp4|avi|webm|m3u8|mkv)$/i.test(raw)
  ) return "video";
  if (
    raw === "markdown" ||
    raw === "md" ||
    ["md", "markdown"].includes(raw) ||
    /\.(md|markdown)$/i.test(raw) ||
    raw === "text/markdown" ||
    raw === "text/x-markdown"
  ) {
    return "markdown";
  }
  if (
    raw === "spreadsheet" ||
    raw === "sheet" ||
    ["xlsx", "xls", "csv", "tsv"].includes(raw) ||
    /\.(xlsx|xls|csv|tsv)$/i.test(raw) ||
    raw === "text/csv" ||
    raw.includes("spreadsheet") ||
    raw.includes("excel")
  ) {
    return "spreadsheet";
  }
  if (
    raw === "document" ||
    raw === "doc" ||
    raw === "docx" ||
    /\.(doc|docx|txt|rtf|odt)$/i.test(raw)
  ) return "document";
  return "unknown";
}

export function FileTypeIcon({ type, className = "h-5 w-5", palette = "default" }) {
  const normalized = normalizeType(type);

  // Fleet design system: file type = IDENTITY, so icons take a tag hue (never a status colour);
  // folders/unknown stay neutral or follow the room's own palette.
  const TYPE_TAG = {
    pdf: "hsl(var(--tag-2))",
    document: "hsl(var(--tag-3))",
    spreadsheet: "hsl(var(--tag-4))",
    image: "hsl(var(--tag-5))",
    video: "hsl(var(--tag-1))",
    markdown: "hsl(var(--tag-6))",
  };
  const paletteVars = {
    viewer: { ...TYPE_TAG, folder: "var(--viewer-accent)", unknown: "var(--viewer-secondary)" },
    dataroom: { ...TYPE_TAG, folder: "var(--dataroom-secondary)", unknown: "var(--dataroom-secondary)" },
    default: { ...TYPE_TAG, folder: "hsl(var(--muted-foreground))", unknown: "hsl(var(--muted-foreground))" },
  };

  const colors = paletteVars[palette] || paletteVars.default;
  const style = { color: colors[normalized] || colors.unknown };

  if (normalized === "folder") {
    return <FolderIcon data-testid="file-type-icon-folder" className={className} style={style} />;
  }
  if (normalized === "pdf") {
    return <FileTextIcon data-testid="file-type-icon-pdf" className={className} style={style} />;
  }
  if (normalized === "spreadsheet") {
    return <FileSpreadsheet data-testid="file-type-icon-spreadsheet" className={className} style={style} />;
  }
  if (normalized === "image") {
    return <FileImageIcon data-testid="file-type-icon-image" className={className} style={style} />;
  }
  if (normalized === "document") {
    return <FileIcon data-testid="file-type-icon-document" className={className} style={style} />;
  }
  if (normalized === "video") {
    return <FileVideo data-testid="file-type-icon-video" className={className} style={style} />;
  }
  if (normalized === "markdown") {
    return <FileCode data-testid="file-type-icon-markdown" className={className} style={style} />;
  }
  return <FileQuestion data-testid="file-type-icon-unknown" className={className} style={style} />;
}

// eslint-disable-next-line react-refresh/only-export-components
export function getDocumentBadgeStyle() {
  // Identity, not status: every file tile is the same neutral chip; the icon inside carries the tag hue.
  return 'bg-secondary text-secondary-foreground border-border';
}
