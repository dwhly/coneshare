import { useEffect, useState } from "react";
import { toast } from "sonner";
import api from "../../services/api";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/Dialog";
import { Dropzone, SelectMenu, errorText } from "../../components/dealroom/shell";
import { Checkbox } from "../../components/ui/Checkbox";

/** One dialog frame for every "create" action (page actions open these; no permanently-open inline forms). */
function FormDialog({ open, onOpenChange, title, description, submitLabel, busy, error, onSubmit, children, disabled }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[560px] gap-0 rounded-lg p-6">
        <DialogTitle className="mb-1 text-lg font-semibold leading-7">{title}</DialogTitle>
        {description && <DialogDescription className="mb-5 text-sm text-muted-foreground">{description}</DialogDescription>}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
        >
          {children}
          {error && (
            <p role="alert" className="fds-callout fds-callout--danger mt-2 text-sm">
              {error}
            </p>
          )}
          <div className="dr-dialog__foot">
            <button type="button" className="dr-btn" onClick={() => onOpenChange(false)}>
              Cancel
            </button>
            <button type="submit" className="dr-btn dr-btn--primary" disabled={busy || disabled}>
              {busy ? "Working…" : submitLabel}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function useDialogState(open) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (open) setError("");
  }, [open]);
  async function run(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      return true;
    } catch (e) {
      setError(errorText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, error, run };
}

export function CreateRoomDialog({ open, onOpenChange, onCreated }) {
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("series_a");
  const [drive, setDrive] = useState(false);
  const { busy, error, run } = useDialogState(open);
  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Create room"
      description="Start with a deal checklist, or bring the folders you already have in Google Drive."
      submitLabel="Create room"
      busy={busy}
      error={error}
      disabled={!name.trim()}
      onSubmit={async () => {
        let created;
        if (await run(async () => { created = (await api.post("/dealroom/rooms/", { name: name.trim() })).data; await api.patch(`/dealroom/rooms/${created.id}/outline/`, { ...(template ? { template } : {}), require_nda: true }); })) {
          toast.success("Room created");
          setName("");
          onOpenChange(false);
          onCreated?.({ ...created, startDrive: drive });
        }
      }}
    >
      <div className="dr-field">
        <label htmlFor="room-name">Room name</label>
        <input id="room-name" className="dr-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Harbor Light Analytics · Series A" autoFocus required />
      </div>
      <div className="dr-field"><span className="dr-label">Start with</span><SelectMenu label="Room template" value={template} onChange={setTemplate} options={[{ value: 'series_a', label: 'Series A · 8 folders and a checklist' }, { value: '', label: 'My own folders' }]} /></div>
      <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={drive} onChange={e => { setDrive(e.target.checked); if (e.target.checked) setTemplate(''); }} />Start from Google Drive</label>
    </FormDialog>
  );
}

/** IDNA check in plain words: only international domains need a confirmation (homograph safety). */
export function domainCheck(domain) {
  const d = domain.trim().toLowerCase();
  let alabel = "";
  try {
    if (/^[^\s/:?#@]+\.[^\s/:?#@]+$/.test(d)) alabel = new URL(`https://${d}`).hostname;
  } catch {
    alabel = "";
  }
  return { domain: d, alabel, valid: Boolean(alabel), international: Boolean(alabel) && alabel !== d };
}

export function AddOrganisationDialog({ open, onOpenChange, onCreated }) {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const { busy, error, run } = useDialogState(open);
  const check = domainCheck(domain);
  useEffect(() => setConfirmed(false), [domain]);
  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Add organisation"
      description="Everyone with an email at this domain can be granted access to a room in one step."
      submitLabel="Add organisation"
      busy={busy}
      error={error}
      disabled={!name.trim() || !check.valid || (check.international && !confirmed)}
      onSubmit={async () => {
        if (
          await run(() =>
            api.post("/dealroom/orgs/", { name: name.trim(), email_domains: [check.domain], confirm_domains: true })
          )
        ) {
          toast.success("Organisation added");
          setName("");
          setDomain("");
          onOpenChange(false);
          onCreated?.();
        }
      }}
    >
      <div className="dr-field">
        <label htmlFor="org-name">Organisation name</label>
        <input id="org-name" className="dr-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Capital" required />
      </div>
      <div className="dr-field">
        <label htmlFor="org-domain">Email domain</label>
        <input id="org-domain" className="dr-input" value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="acme.com" required />
        {domain && !check.valid && <p className="dr-hint">Enter a domain like acme.com.</p>}
      </div>
      {check.international && (
        <div className="fds-callout fds-callout--warning mb-4 text-sm">
          <p className="m-0">
            This domain uses international characters. Email systems will see it as{" "}
            <span className="font-mono">{check.alabel}</span>.
          </p>
          <label className="mt-2 flex items-center gap-2 font-medium">
            <Checkbox checked={confirmed} onCheckedChange={(v) => setConfirmed(v === true)} aria-label="This is the right domain" />
            This is the right domain
          </label>
        </div>
      )}
    </FormDialog>
  );
}

export function GrantAccessDialog({ open, onOpenChange, roomId, orgs, onGranted, onAddOrganisation }) {
  const [mode, setMode] = useState("person");
  const [email, setEmail] = useState("");
  const [orgId, setOrgId] = useState("");
  const { busy, error, run } = useDialogState(open);
  const orgOptions = (orgs || []).filter((o) => !o.archived_at).map((o) => ({ value: o.id, label: `${o.name} · ${(o.email_domains || []).join(", ")}` }));
  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Grant access"
      description="People you grant verify their email, sign the room's NDA if one is set, then see watermarked copies."
      submitLabel="Grant access"
      busy={busy}
      error={error}
      disabled={mode === "person" ? !email.trim() : !orgId}
      onSubmit={async () => {
        const body = mode === "person" ? { room: roomId, email: email.trim() } : { room: roomId, viewer_organisation: orgId };
        if (await run(() => api.post("/dealroom/grants/", body))) {
          toast.success("Access granted");
          setEmail("");
          setOrgId("");
          onOpenChange(false);
          onGranted?.();
        }
      }}
    >
      <div className="dr-field">
        <span className="dr-label" id="grant-mode-label">Grant to</span>
        <div className="fds-seg self-start" role="group" aria-labelledby="grant-mode-label">
          <button type="button" aria-pressed={mode === "person"} onClick={() => setMode("person")}>
            A person
          </button>
          <button type="button" aria-pressed={mode === "org"} onClick={() => setMode("org")}>
            An organisation
          </button>
        </div>
      </div>
      {mode === "person" ? (
        <div className="dr-field">
          <label htmlFor="grant-email">Email address</label>
          <input id="grant-email" aria-label="Member email" className="dr-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" />
        </div>
      ) : (
        <div className="dr-field">
          <label htmlFor="grant-org">Organisation</label>
          {orgOptions.length ? (
            <SelectMenu id="grant-org" label="Organisation" value={orgId} onChange={setOrgId} options={orgOptions} placeholder="Choose an organisation" />
          ) : (
            <p className="dr-hint">No organisations yet.</p>
          )}
          {onAddOrganisation && (
            <button type="button" className="self-start text-sm font-medium text-brand hover:underline" onClick={onAddOrganisation}>
              Add organisation
            </button>
          )}
        </div>
      )}
    </FormDialog>
  );
}

export function UploadDialog({ open, onOpenChange, roomId, onUploaded }) {
  const [file, setFile] = useState(null);
  const { busy, error, run } = useDialogState(open);
  useEffect(() => {
    if (!open) setFile(null);
  }, [open]);
  return (
    <FormDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Upload document"
      description="Visitors only ever see per-person watermarked copies."
      submitLabel="Upload"
      busy={busy}
      error={error}
      disabled={!file}
      onSubmit={async () => {
        const data = new FormData();
        data.append("file", file);
        let uploaded;
        if (await run(async () => { uploaded = (await api.post(`/dealroom/rooms/${roomId}/upload/`, data, { headers: { "Content-Type": "multipart/form-data" } })).data; })) {
          toast.success(`${file.name} uploaded`);
          onOpenChange(false);
          onUploaded?.(uploaded);
        }
      }}
    >
      <Dropzone accept=".pdf,.docx,.pptx,.xlsx" file={file} onFile={setFile} hint="PDF, Word, PowerPoint or Excel" />
    </FormDialog>
  );
}
