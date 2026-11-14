import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Copy, Check, ExternalLink, ShieldAlert, Terminal, FileCode } from "lucide-react";
import { Button } from "../ui/Button";

export function McpSetupGuide({ rawKey = null }) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState("claude_desktop");
  const [mode, setMode] = useState("cli"); // "cli" or "json"
  const [copied, setCopied] = useState(false);

  const activeKey = rawKey || "cs_live_YOUR_KEY_HERE";

  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "https://app.coneshare.com";
  const mcpUrl = `${origin}/mcp/sse`;

  const copyToClipboard = (text) => {
    if (!navigator.clipboard) {
      toast.error(t("settings.settingsUpdateFailed"));
      return;
    }
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(true);
        toast.success(t("common.success"));
        setTimeout(() => setCopied(false), 2000);
      })
      .catch((err) => {
        console.error("Clipboard copy failed:", err);
        toast.error(t("settings.settingsUpdateFailed"));
      });
  };

  const jsonConfig = JSON.stringify(
    {
      mcpServers: {
        coneshare: {
          url: mcpUrl,
          headers: {
            Authorization: `Bearer ${activeKey}`,
          },
        },
      },
    },
    null,
    2
  );

  const getCliCommand = (clientId) => {
    if (clientId === "claude_code") {
      return `claude mcp add --transport sse coneshare ${mcpUrl} --header "Authorization: Bearer ${activeKey}"`;
    }
    return `${clientId} mcp add coneshare --url ${mcpUrl} --header "Authorization: Bearer ${activeKey}"`;
  };

  const agentTabs = [
    {
      id: "claude_desktop",
      label: t("settings.mcpTabClaudeDesktop", "Claude Desktop"),
      hasCli: false,
      path: "macOS: ~/Library/Application Support/Claude/claude_desktop_config.json\nWindows: %APPDATA%\\Claude\\claude_desktop_config.json",
    },
    {
      id: "claude_code",
      label: t("settings.mcpTabClaudeCode", "Claude Code"),
      hasCli: true,
      cliCmd: getCliCommand("claude_code"),
      path: "~/.claude.json or project .mcp.json",
    },
    {
      id: "agy",
      label: t("settings.mcpTabAgy", "Antigravity CLI (agy)"),
      hasCli: false,
      path: "~/.gemini/config/mcp_config.json or .agents/mcp_config.json",
    },
    {
      id: "cursor",
      label: t("settings.mcpTabCursor", "Cursor"),
      hasCli: false,
      path: "~/.cursor/mcp.json or project .cursor/mcp.json",
    },
    {
      id: "vscode",
      label: t("settings.mcpTabVsCode", "VS Code"),
      hasCli: false,
      path: ".vscode/mcp.json",
    },
    {
      id: "codex",
      label: t("settings.mcpTabCodex", "Codex"),
      hasCli: false,
      path: "~/.codex/config.json or codex.json",
    },
  ];

  const currentAgent = agentTabs.find((a) => a.id === activeTab) || agentTabs[0];
  const isCliActive = currentAgent.hasCli && mode === "cli";
  const displayContent = isCliActive ? currentAgent.cliCmd : jsonConfig;

  return (
    <div className="space-y-4 text-sm text-foreground">
      <p className="pt-1 text-muted-foreground">
        {t("settings.mcpSetupGuideSubtitle", "Select your AI tool below to get pre-configured settings to connect to the Remote MCP Server.")}
      </p>

      {/* Agent Selector Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-border pb-2">
        {agentTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => {
              setActiveTab(tab.id);
              setCopied(false);
              if (!tab.hasCli) setMode("json");
            }}
            className={`px-3 py-1.5 rounded-md font-medium text-xs transition-colors ${
              activeTab === tab.id
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-muted text-muted-foreground hover:bg-accent "
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Mode Switcher (CLI vs JSON) for CLI-supported agents */}
      {currentAgent.hasCli && (
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-muted-foreground font-medium">{t("settings.mcpConfigMode", "Configuration Mode")}:</span>
          <div className="flex items-center gap-1 bg-muted p-0.5 rounded-lg border border-border">
            <button
              type="button"
              onClick={() => {
                setMode("cli");
                setCopied(false);
              }}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "cli"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground "
              }`}
            >
              <Terminal className="h-3.5 w-3.5" />
              {t("settings.mcpModeCli", "1-Line CLI Command")}
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("json");
                setCopied(false);
              }}
              className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "json"
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground "
              }`}
            >
              <FileCode className="h-3.5 w-3.5" />
              {t("settings.mcpModeJson", "JSON File Config")}
            </button>
          </div>
        </div>
      )}

      {/* Target Path / Info Line */}
      <div className="text-xs text-muted-foreground font-mono">
        <span className="font-semibold">{t("settings.mcpConfigLocation", "Target File / Location")}:</span>{" "}
        {currentAgent.path}
      </div>

      {/* Code Snippet Box */}
      <div className="relative group">
        <pre className="p-3 bg-muted text-foreground rounded-lg font-mono text-xs overflow-x-auto border border-border leading-relaxed">
          {displayContent}
        </pre>
        <Button
          size="sm"
          variant="outline"
          aria-label={t("common.copy", "Copy configuration")}
          onClick={() => copyToClipboard(displayContent)}
          className="absolute top-2 right-2 bg-background text-foreground border-input hover:bg-accent"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
        </Button>
      </div>

      {/* Permissions Tier Warning */}
      <div className="flex items-start gap-2 p-3 bg-warning-subtle text-warning rounded-lg border border-warning-border text-xs">
        <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
        <span>
          {t(
            "settings.mcpTierTip",
            "Tip: Make sure your API key has Read & Write or Full Access if your AI agent needs to upload files or generate share links."
          )}
        </span>
      </div>

      {/* Skill Integration Footer */}
      <div className="pt-2 border-t border-border text-xs">
        <a
          href="https://www.coneshare.com/agents"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-primary hover:underline font-medium"
        >
          <span>
            {t("settings.mcpSkillInstall", "Install the coneshare-it skill for automated uploading, link sharing, and dataroom workflows.")}
          </span>
          <ExternalLink className="h-3 w-3 shrink-0 opacity-70" />
        </a>
      </div>
    </div>
  );
}
