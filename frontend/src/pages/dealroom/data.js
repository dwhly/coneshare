import { useCallback, useEffect, useState } from "react";
import api from "../../services/api";

const items = (data) => (data && data.results) || data || [];

/** Rooms joined with Coneshare's dataroom rows (created/storage) and their grants (via the entry link). */
export async function loadRooms() {
  const [rooms, datarooms, links, grants] = await Promise.all([
    api.get("/dealroom/rooms/"),
    api.get("/datarooms/").catch(() => ({ data: [] })),
    api.get("/dealroom/share-links/").catch(() => ({ data: [] })),
    api.get("/dealroom/grants/").catch(() => ({ data: [] })),
  ]);
  const meta = Object.fromEntries(items(datarooms.data).map((d) => [d.id, d]));
  const linkRoom = Object.fromEntries(items(links.data).map((l) => [l.id, l.dataroom]));
  const active = items(grants.data).filter((g) => !g.revoked_at);
  return items(rooms.data).map((r) => ({
    ...r,
    created_at: meta[r.id]?.created_at,
    updated_at: meta[r.id]?.updated_at,
    storage_used_bytes: meta[r.id]?.storage_used_bytes,
    people: active.filter((g) => linkRoom[g.share_link] === r.id).length,
  }));
}

export async function loadRoomDetail(id) {
  const [room, detail, links, grants, members, orgs] = await Promise.all([
    api.get(`/dealroom/rooms/${id}/`),
    // content=full: every folder and document at any depth (the default returns the root level only, which would hide
    // everything filed under a folder, e.g. signed copies under Executed/Agreements/...). Review r1 [2].
    api.get(`/datarooms/${id}/`, { params: { content: "full" } }).catch(() => ({ data: { items: [] } })),
    api.get("/dealroom/share-links/").catch(() => ({ data: [] })),
    api.get("/dealroom/grants/").catch(() => ({ data: [] })),
    api.get("/dealroom/members/").catch(() => ({ data: [] })),
    api.get("/dealroom/orgs/").catch(() => ({ data: [] })),
  ]);
  const linkIds = new Set(items(links.data).filter((l) => l.dataroom === id).map((l) => l.id));
  const people = Object.fromEntries(items(members.data).map((m) => [String(m.email).toLowerCase(), m]));
  const orgList = items(orgs.data);
  const orgName = Object.fromEntries(orgList.map((o) => [o.id, o.name]));
  const grantRows = items(grants.data)
    .filter((g) => linkIds.has(g.share_link))
    .map((g) => ({
      ...g,
      member: g.email ? people[String(g.email).toLowerCase()] : null,
      org_name: g.viewer_organisation ? orgName[g.viewer_organisation] || "Organisation" : "",
    }))
    .reverse();
  const all = detail.data?.items || [];
  const folders = all.filter((i) => i.type === "folder");
  return {
    room: room.data,
    created_at: detail.data?.created_at,
    documents: withFolderPaths(all.filter((i) => i.type === "document"), folders),
    folders,
    grants: grantRows,
    orgs: orgList,
  };
}

/** Each document gets `folder_path` ("Executed / Agreements", "" at the root); root documents first, then by path. */
export function withFolderPaths(documents, folders) {
  const path = Object.fromEntries(
    folders.map((f) => [String(f.id), [...(f.ancestors || []).map((a) => a.name), f.name].join(" / ")]),
  );
  // Array.prototype.sort is stable, so the server's order holds within a folder.
  return documents
    .map((d) => ({ ...d, folder_path: d.folder ? path[String(d.folder)] || "" : "" }))
    .sort((a, b) => a.folder_path.localeCompare(b.folder_path));
}

export function useLoader(loader, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const reload = useCallback(async () => {
    try {
      const data = await loader();
      setState({ data, error: null, loading: false });
    } catch (error) {
      setState((s) => ({ ...s, error, loading: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => {
    reload();
  }, [reload]);
  return { ...state, reload };
}

export { items };
