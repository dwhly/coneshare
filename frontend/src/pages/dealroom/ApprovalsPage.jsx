import { useMemo, useState } from "react";
import { toast } from "sonner";
import api from "../../services/api";
import { usePageTitle } from "../../hooks/usePageTitle";
import { Details, EmptyState, FilterButton, PageHead, SearchInput, StatusPill, TableFooter, formatDate, humanEvent, errorText, usePaged } from "../../components/dealroom/shell";
import { items, useLoader } from "./data";

const VERBS = { create: "Create", partial_update: "Change", update: "Change", destroy: "Remove" };
/** "dealroom_GrantViewSet_partial_update_patch" → "Change grant"; plain ids are sentence-cased. */
export function requestTitle(a) {
  if (a.operation_id === "dealroom_sign_SigningEnvelopeViewSet_create_post") return "Send for signature";
  const m = /^dealroom(?:_sign)?_([A-Za-z]+?)(?:ViewSet|View)_(.+?)_(get|post|put|patch|delete)$/.exec(a.operation_id || "");
  if (!m) return humanEvent(a.operation_id);
  const resource = m[1].replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
  const verb = VERBS[m[2]] || humanEvent(m[2]);
  return `${verb} ${resource}`;
}

function summary(a, rooms) {
  const p = a.payload || {};
  const bits = [];
  if (Array.isArray(p.recipients)) bits.push(p.recipients.map((r) => (r.name ? `${r.name} (${r.email})` : r.email)).join(", "));
  if (p.email) bits.push(p.email);
  const room = p.room_id || p.room;
  if (room && rooms[room]) bits.push(rooms[room]);
  return bits.filter(Boolean).join(" · ");
}

export function approvalState(a, now = Date.now()) {
  if (a.status === "pending_approval") {
    if (a.expires_at && new Date(a.expires_at).getTime() < now) return ["neutral", "Expired", false];
    if (a.expires_at && new Date(a.expires_at).getTime() - now < 864e5) return ["warning", "Expiring", true];
    return ["info", "Pending", true];
  }
  if (/reject|denied|declin/.test(a.status)) return ["danger", "Rejected", false];
  if (/fail|error/.test(a.status)) return ["danger", "Failed", false];
  if (/approv|execut|done|complete/.test(a.status)) return ["success", "Approved", false];
  if (/expir/.test(a.status)) return ["neutral", "Expired", false];
  return ["neutral", humanEvent(a.status), false];
}

/** Approvals (§3 list page): agent requests waiting for a human. Raw payloads sit behind "Details". */
export default function ApprovalsPage() {
  usePageTitle("Approvals");
  const [q, setQ] = useState("");
  const [show, setShow] = useState("pending");
  const { data, error, loading, reload } = useLoader(async () => {
    const [ap, rooms] = await Promise.all([api.get("/dealroom/approvals/"), api.get("/dealroom/rooms/").catch(() => ({ data: [] }))]);
    return { rows: items(ap.data), rooms: Object.fromEntries(items(rooms.data).map((r) => [r.id, r.name])) };
  }, []);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (data?.rows || []).filter(
      (a) =>
        (show === "all" || approvalState(a)[2]) &&
        (!needle || `${requestTitle(a)} ${JSON.stringify(a.payload)}`.toLowerCase().includes(needle))
    );
  }, [data, q, show]);
  const paged = usePaged(rows, undefined, `${q}|${show}`);

  async function decide(a, action) {
    try {
      await api.post(`/dealroom/approvals/${a.id}/${action}/`);
      toast.success(action === "approve" ? "Request approved" : "Request rejected");
      reload();
    } catch (e) {
      toast.error(errorText(e));
    }
  }

  return (
    <div className="dr-container">
      <PageHead title="Approvals" subtitle="Agent requests wait here until a person approves them." />
      {error && (
        <p role="alert" className="fds-callout fds-callout--danger dr-notice text-sm">
          {errorText(error)}
        </p>
      )}
      <div className="dr-filterbar">
        <SearchInput value={q} onChange={setQ} placeholder="Search requests" />
        <FilterButton pressed={show === "pending"} onClick={() => setShow("pending")}>
          Waiting
        </FilterButton>
        <FilterButton pressed={show === "all"} onClick={() => setShow("all")}>
          All
        </FilterButton>
      </div>
      {!loading && rows.length === 0 ? (
        <EmptyState>{show === "pending" ? "No requests are waiting for you." : "No requests match."}</EmptyState>
      ) : (
        <div className="dr-table-wrap">
          <table className="dr-table dr-table--top">
            <thead>
              <tr>
                <th scope="col">Request</th>
                <th scope="col">Status</th>
                <th scope="col" className="dr-num">Requested</th>
                <th scope="col" className="dr-actions">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={4} className="dr-muted">
                    Loading requests…
                  </td>
                </tr>
              )}
              {paged.shown.map((a) => {
                const [tone, word, open] = approvalState(a);
                const sum = summary(a, data.rooms);
                return (
                  <tr key={a.id}>
                    <td>
                      <span className="dr-strong">{requestTitle(a)}</span>
                      {sum && <span className="dr-sub">{sum}</span>}
                      <Details>
                        <p className="dr-hint mt-2">Target: {a.method} {a.path}</p>
                        <p className="dr-hint mt-2">Current state</p>
                        {a.current_state && Object.keys(a.current_state).length ? <pre>{JSON.stringify(a.current_state, null, 2)}</pre> : <p className="dr-hint">Nothing yet — this request creates something new.</p>}
                        <p className="dr-hint mt-2">Proposed changes</p>
                        <pre>{JSON.stringify(a.payload, null, 2)}</pre>
                      </Details>
                    </td>
                    <td>
                      <StatusPill tone={tone}>{word}</StatusPill>
                    </td>
                    <td className="dr-num dr-muted">
                      <time dateTime={a.created_at}>{formatDate(a.created_at)}</time>
                    </td>
                    <td className="dr-actions">
                      {open && (
                        <div className="flex justify-end gap-2">
                          <button type="button" className="dr-btn dr-btn--sm" onClick={() => decide(a, "reject")}>
                            Reject
                          </button>
                          <button type="button" className="dr-btn dr-btn--sm dr-btn--primary" onClick={() => decide(a, "approve")}>
                            Approve
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!loading && <TableFooter paged={paged} noun="request" />}
        </div>
      )}
    </div>
  );
}
