import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink, FileSignature, Upload, UserPlus } from "lucide-react";
import { toast } from "sonner";
import api from "../../services/api";
import { usePageTitle } from "../../hooks/usePageTitle";
import {
  Card,
  CopyField,
  EmptyState,
  IdentityChip,
  PageHead,
  RowMenu,
  StatusPill,
  TimeCell,
  formatBytes,
  formatDate,
  humanEvent,
  errorText,
} from "../../components/dealroom/shell";
import { AddOrganisationDialog, GrantAccessDialog, UploadDialog } from "./dialogs";
import { items, loadRoomDetail, useLoader } from "./data";

function grantStatus(g) {
  if (g.revoked_at) return ["neutral", "Revoked"];
  if (g.expires_at && new Date(g.expires_at) < new Date()) return ["neutral", "Expired"];
  if (g.expires_at && new Date(g.expires_at) - Date.now() < 7 * 864e5) return ["warning", "Expiring"];
  if (g.member?.verified_at) return ["success", "Verified"];
  return ["info", "Invited"];
}

/** Room detail (§3 detail page): page head + stacked outline cards. */
export default function RoomDetailPage() {
  const { dataroomId } = useParams();
  const { data, error, loading, reload } = useLoader(() => loadRoomDetail(dataroomId), [dataroomId]);
  const activity = useLoader(async () => items((await api.get("/dealroom/activity/")).data).filter((a) => a.room_id === dataroomId).slice(0, 6), [dataroomId]);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [grantOpen, setGrantOpen] = useState(false);
  const [orgOpen, setOrgOpen] = useState(false);
  const room = data?.room;
  usePageTitle(room?.name || "Room");
  const entry = room ? `${window.location.origin}${room.entry_url}` : "";

  async function revoke(g) {
    try {
      await api.delete(`/dealroom/grants/${g.id}/`);
      toast.success("Access revoked");
      reload();
    } catch (e) {
      toast.error(errorText(e));
    }
  }

  return (
    <div className="dr-container">
      <PageHead
        crumbs={[{ label: "Rooms", to: "/datarooms" }, { label: room?.name || "Room" }]}
        title={room?.name || (loading ? "Loading…" : "Room")}
        subtitle="Visitors verify their email, sign the NDA, then view watermarked copies."
        actions={
          room && (
            <>
              <button type="button" className="dr-btn" onClick={() => setGrantOpen(true)}>
                <UserPlus aria-hidden="true" />
                Grant access
              </button>
              <button type="button" className="dr-btn dr-btn--primary" onClick={() => setUploadOpen(true)}>
                <Upload aria-hidden="true" />
                Upload document
              </button>
            </>
          )
        }
      />
      {error && (
        <p role="alert" className="fds-callout fds-callout--danger dr-notice text-sm">
          {errorText(error)}
        </p>
      )}
      {room && (
        <div className="dr-stack">
          <Card
            title="Visitor link"
            subtitle="Send this link to the people you grant. It only opens for verified, granted emails."
            action={
              <a className="dr-btn" href={room.entry_url} target="_blank" rel="noreferrer">
                <ExternalLink aria-hidden="true" />
                Open visitor page
              </a>
            }
          >
            <CopyField value={entry} />
          </Card>

          <Card
            flush
            title="Documents"
            action={
              <a className="dr-btn" href={`/signing/?room=${room.id}`}>
                <FileSignature aria-hidden="true" />
                Send for signature
              </a>
            }
          >
            {data.documents.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  action={
                    <button type="button" className="dr-btn dr-btn--primary" onClick={() => setUploadOpen(true)}>
                      <Upload aria-hidden="true" />
                      Upload document
                    </button>
                  }
                >
                  No documents in this room yet.
                </EmptyState>
              </div>
            ) : (
              <div className="dr-table-wrap">
                <table className="dr-table">
                  <thead>
                    <tr>
                      <th scope="col">Name</th>
                      <th scope="col">Type</th>
                      <th scope="col" className="dr-num">Size</th>
                      <th scope="col" className="dr-num">Views</th>
                      <th scope="col" className="dr-num">Added</th>
                      <th scope="col" className="dr-actions">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.documents.map((d) => (
                      <tr key={d.id}>
                        <td className="dr-strong">{d.name}</td>
                        <td>{String(d.document_type || "file").toUpperCase()}</td>
                        <td className="dr-num">{formatBytes(d.file_size)}</td>
                        <td className="dr-num">{d.dataroom_view_count ?? 0}</td>
                        <td className="dr-num">{formatDate(d.created_at)}</td>
                        <td className="dr-actions">
                          <RowMenu
                            label={`Actions for ${d.name}`}
                            items={[
                              { label: "Open document", onSelect: () => window.location.assign(`/documents/${d.document_id}`) },
                              { label: "Send for signature", onSelect: () => window.location.assign(`/signing/?room=${room.id}`) },
                            ]}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card
            flush
            title="People with access"
            action={
              <button type="button" className="dr-btn" onClick={() => setGrantOpen(true)}>
                <UserPlus aria-hidden="true" />
                Grant access
              </button>
            }
          >
            {data.grants.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  action={
                    <button type="button" className="dr-btn dr-btn--primary" onClick={() => setGrantOpen(true)}>
                      <UserPlus aria-hidden="true" />
                      Grant access
                    </button>
                  }
                >
                  Nobody has access yet.
                </EmptyState>
              </div>
            ) : (
              <div className="dr-table-wrap">
                <table className="dr-table">
                  <thead>
                    <tr>
                      <th scope="col">Person or organisation</th>
                      <th scope="col">Status</th>
                      <th scope="col" className="dr-num">Verified</th>
                      <th scope="col" className="dr-actions">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.grants.slice(0, 12).map((g) => {
                      const [tone, word] = grantStatus(g);
                      return (
                        <tr key={g.id}>
                          <td>
                            {g.email ? (
                              <>
                                <span className="dr-strong">{g.member?.name || g.email}</span>
                                {g.member?.name && <span className="dr-sub">{g.email}</span>}
                              </>
                            ) : (
                              <IdentityChip name={g.org_name} />
                            )}
                          </td>
                          <td>
                            <StatusPill tone={tone}>{word}</StatusPill>
                          </td>
                          <td className="dr-num">{formatDate(g.member?.verified_at)}</td>
                          <td className="dr-actions">
                            {!g.revoked_at && (
                              <RowMenu label={`Actions for ${g.email || g.org_name}`} items={[{ label: "Revoke access", danger: true, onSelect: () => revoke(g) }]} />
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {data.grants.length > 12 && <div className="dr-more dr-muted text-sm">{data.grants.length - 12} more</div>}
              </div>
            )}
          </Card>

          <Card
            flush
            title="Recent activity"
            action={
              <Link className="dr-btn" to={`/activity?room=${room.id}`}>
                View all
              </Link>
            }
          >
            <div className="dr-table-wrap">
              <table className="dr-table">
                <tbody>
                  {(activity.data || []).length === 0 && (
                    <tr>
                      <td className="dr-muted">No activity yet.</td>
                    </tr>
                  )}
                  {(activity.data || []).map((a) => (
                    <tr key={a.id}>
                      <td className="dr-strong">{humanEvent(a.event_type)}</td>
                      <td className="dr-muted">{a.data?.name || a.data?.email || a.actor_kind}</td>
                      <td className="dr-num dr-muted">
                        <TimeCell value={a.created_at} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
      {room && (
        <>
          <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} roomId={room.id} onUploaded={reload} />
          <GrantAccessDialog
            open={grantOpen}
            onOpenChange={setGrantOpen}
            roomId={room.id}
            orgs={data.orgs}
            onGranted={reload}
            onAddOrganisation={() => {
              setGrantOpen(false);
              setOrgOpen(true);
            }}
          />
          <AddOrganisationDialog
            open={orgOpen}
            onOpenChange={setOrgOpen}
            onCreated={() => {
              reload();
              setGrantOpen(true);
            }}
          />
        </>
      )}
    </div>
  );
}
