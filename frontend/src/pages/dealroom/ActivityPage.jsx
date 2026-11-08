import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../../services/api";
import { usePageTitle } from "../../hooks/usePageTitle";
import { EmptyState, FilterButton, IdentityChip, PageHead, SearchInput, SelectMenu, TableFooter, TimeCell, humanEvent, errorText, usePaged } from "../../components/dealroom/shell";
import { items, useLoader } from "./data";

const ACTORS = [
  { id: "all", label: "All" },
  { id: "recipient", label: "Visitors" },
  { id: "human", label: "Staff" },
  { id: "agent", label: "Agents" },
];
const actorGroup = (kind) => (kind === "recipient" || kind === "member" || kind === "viewer" ? "recipient" : kind === "agent" || kind === "api_key" ? "agent" : "human");
const actorWord = { recipient: "Visitor", human: "Staff", agent: "Agent" };
const MAX_PAGES = 20;

/** Activity (§3 list page): who did what, when, in which room. */
export default function ActivityPage() {
  usePageTitle("Activity");
  const [params, setParams] = useSearchParams();
  const room = params.get("room") || "";
  const [q, setQ] = useState("");
  const [actor, setActor] = useState("all");
  const { data, error, loading } = useLoader(async () => {
    const [act, rooms] = await Promise.all([api.get("/dealroom/activity/"), api.get("/dealroom/rooms/")]);
    // The API pages by cursor (50 a page, no count): read up to MAX_PAGES so the footer can say "of N".
    let rows = items(act.data);
    let next = act.data?.next || null;
    for (let i = 1; next && i < MAX_PAGES; i++) {
      const url = new URL(next, window.location.origin);
      const r = await api.get(`/dealroom/activity/${url.search}`);
      rows = rows.concat(items(r.data));
      next = r.data?.next || null;
    }
    return { rows, more: Boolean(next), rooms: items(rooms.data) };
  }, []);
  const roomName = useMemo(() => Object.fromEntries((data?.rooms || []).map((r) => [r.id, r.name])), [data]);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (data?.rows || []).filter(
      (a) =>
        (!room || a.room_id === room) &&
        (actor === "all" || actorGroup(a.actor_kind) === actor) &&
        (!needle || `${a.event_type} ${a.data?.name || ""} ${a.data?.email || ""}`.toLowerCase().includes(needle))
    );
  }, [data, q, actor, room]);
  const paged = usePaged(rows, undefined, `${q}|${actor}|${room}`);

  const roomOptions = [{ value: "all", label: "All rooms" }, ...(data?.rooms || []).map((r) => ({ value: r.id, label: r.name }))];

  return (
    <div className="dr-container">
      <PageHead title="Activity" subtitle="Every visit, signature and access change, newest first." />
      {error && (
        <p role="alert" className="fds-callout fds-callout--danger dr-notice text-sm">
          {errorText(error)}
        </p>
      )}
      <div className="dr-filterbar">
        <SearchInput value={q} onChange={setQ} placeholder="Search activity" />
        {ACTORS.map((a) => (
          <FilterButton key={a.id} pressed={actor === a.id} onClick={() => setActor(a.id)}>
            {a.label}
          </FilterButton>
        ))}
        <div className="ml-auto w-64">
          <SelectMenu
            label="Room"
            value={room || "all"}
            onChange={(v) => setParams(v && v !== "all" ? { room: v } : {})}
            options={roomOptions}
            placeholder="All rooms"
          />
        </div>
      </div>
      {!loading && rows.length === 0 ? (
        <EmptyState>No activity matches.</EmptyState>
      ) : (
        <div className="dr-table-wrap">
          <table className="dr-table">
            <thead>
              <tr>
                <th scope="col">Event</th>
                <th scope="col">Who</th>
                <th scope="col">Room</th>
                <th scope="col" className="dr-num">When</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={4} className="dr-muted">
                    Loading activity…
                  </td>
                </tr>
              )}
              {paged.shown.map((a) => {
                const group = actorGroup(a.actor_kind);
                const who = a.data?.name || a.data?.email;
                return (
                  <tr key={a.id}>
                    <td className="dr-strong">{humanEvent(a.event_type)}</td>
                    <td>
                      {who ? (
                        <>
                          <span>{who}</span>
                          {a.data?.name && a.data?.email && <span className="dr-sub">{a.data.email}</span>}
                        </>
                      ) : (
                        <IdentityChip name={group}>{actorWord[group]}</IdentityChip>
                      )}
                    </td>
                    <td className="dr-muted">{roomName[a.room_id] || "—"}</td>
                    <td className="dr-num dr-muted">
                      <TimeCell value={a.created_at} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!loading && <TableFooter paged={paged} noun="event" more={Boolean(data?.more) && !q && actor === "all" && !room} />}
        </div>
      )}
    </div>
  );
}
