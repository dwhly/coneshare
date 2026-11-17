import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Building2, Plus } from "lucide-react";
import { toast } from "sonner";
import { usePageTitle } from "../../hooks/usePageTitle";
import { EmptyState, FilterButton, PageHead, RowMenu, SearchInput, TableFooter, formatBytes, formatDate, errorText, usePaged } from "../../components/dealroom/shell";
import { AddOrganisationDialog, CreateRoomDialog } from "./dialogs";
import { loadRooms, useLoader } from "./data";

const FILTERS = [
  { id: "all", label: "All", test: () => true },
  { id: "shared", label: "Shared", test: (r) => r.people > 0 },
  { id: "unshared", label: "Not shared", test: (r) => !r.people },
];

/** Rooms list (§3 list page): page head + filter bar + bordered table; creation happens in dialogs. */
export default function RoomsPage() {
  usePageTitle("Rooms");
  const navigate = useNavigate();
  const { data: rooms, error, loading, reload } = useLoader(loadRooms, []);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [orgOpen, setOrgOpen] = useState(false);
  const shown = useMemo(() => {
    const f = FILTERS.find((x) => x.id === filter) || FILTERS[0];
    return (rooms || []).filter((r) => f.test(r) && r.name.toLowerCase().includes(q.trim().toLowerCase()));
  }, [rooms, q, filter]);
  const paged = usePaged(shown, undefined, `${q}|${filter}`);

  const copyLink = async (r) => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${r.entry_url}`);
      toast.success("Visitor link copied");
    } catch {
      toast.error("Could not copy the link");
    }
  };

  return (
    <div className="dr-container">
      <PageHead
        title="Rooms"
        subtitle="Your deal rooms, ready for the next conversation."
        actions={
          <>
            <button type="button" className="dr-btn" onClick={() => setOrgOpen(true)}>
              <Building2 aria-hidden="true" />
              Add organisation
            </button>
            <button type="button" className="dr-btn dr-btn--primary" onClick={() => setCreateOpen(true)}>
              <Plus aria-hidden="true" />
              Create room
            </button>
          </>
        }
      />
      {error && (
        <p role="alert" className="fds-callout fds-callout--danger dr-notice text-sm">
          {errorText(error)}
        </p>
      )}
      {!loading && rooms && rooms.length === 0 ? (
        <EmptyState
          action={
            <button type="button" className="dr-btn dr-btn--primary" onClick={() => setCreateOpen(true)}>
              <Plus aria-hidden="true" />
              Create room
            </button>
          }
        >
          No rooms yet. Create one to start sharing documents.
        </EmptyState>
      ) : (
        <>
          <div className="dr-filterbar">
            <SearchInput value={q} onChange={setQ} placeholder="Search rooms" />
            {FILTERS.map((f) => (
              <FilterButton key={f.id} pressed={filter === f.id} onClick={() => setFilter(f.id)}>
                {f.label}
              </FilterButton>
            ))}
          </div>
          <div className="dr-table-wrap">
            <table className="dr-table">
              <thead>
                <tr>
                  <th scope="col">Room</th>
                  <th scope="col" className="dr-num">People</th>
                  <th scope="col" className="dr-num">Storage</th>
                  <th scope="col" className="dr-num">Created</th>
                  <th scope="col" className="dr-actions">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={5} className="dr-muted">
                      Loading rooms…
                    </td>
                  </tr>
                )}
                {!loading && shown.length === 0 && (
                  <tr>
                    <td colSpan={5} className="dr-muted">
                      No rooms match.
                    </td>
                  </tr>
                )}
                {paged.shown.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link className="dr-rowlink" to={`/datarooms/${r.id}`}>
                        {r.name}
                      </Link>
                    </td>
                    <td className="dr-num">{r.people}</td>
                    <td className="dr-num">{formatBytes(r.storage_used_bytes)}</td>
                    <td className="dr-num">{formatDate(r.created_at)}</td>
                    <td className="dr-actions">
                      <RowMenu
                        label={`Actions for ${r.name}`}
                        items={[
                          { label: "Open room", onSelect: () => navigate(`/datarooms/${r.id}`) },
                          { label: "Copy visitor link", onSelect: () => copyLink(r) },
                          { label: "Open visitor page", href: r.entry_url, newTab: true },
                          { label: "Signing", onSelect: () => window.location.assign(`/signing/?room=${r.id}`) },
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && <TableFooter paged={paged} noun="room" />}
          </div>
        </>
      )}
      <CreateRoomDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={(room) => (room?.id ? navigate(`/datarooms/${room.id}${room.startDrive ? "?drive=1" : ""}`) : reload())} />
      <AddOrganisationDialog open={orgOpen} onOpenChange={setOrgOpen} />
    </div>
  );
}
