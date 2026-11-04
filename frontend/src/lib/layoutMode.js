import { useSyncExternalStore } from "react";

/**
 * Chief Dealroom layout prototype: one shared shell, two arrangements.
 *   "sidebar" (default) = Coneshare's native left sidebar
 *   "topbar"            = the AmForge/Documenso top bar (wordmark, switcher, nav, search, account)
 * `?layout=sidebar|topbar` on any URL sets it; it persists in localStorage under `dealroom-layout`.
 */
export const LAYOUT_STORAGE_KEY = "dealroom-layout";
export const LAYOUTS = ["sidebar", "topbar"];
const EVENT = "dealroom-layout-change";

function readStored() {
  try {
    const v = window.localStorage.getItem(LAYOUT_STORAGE_KEY);
    return LAYOUTS.includes(v) ? v : "topbar";
  } catch {
    return "topbar";
  }
}

export function setLayoutMode(mode) {
  if (!LAYOUTS.includes(mode)) return;
  try {
    window.localStorage.setItem(LAYOUT_STORAGE_KEY, mode);
  } catch {
    /* private mode: fall through, the event still updates this tab */
  }
  window.dispatchEvent(new Event(EVENT));
}

/** Apply `?layout=` from the current URL (called at boot and on navigation). */
export function applyLayoutParam(search = typeof window !== "undefined" ? window.location.search : "") {
  const v = new URLSearchParams(search).get("layout");
  if (LAYOUTS.includes(v)) setLayoutMode(v);
}

// Capture the param before any auth redirect drops it (e.g. /?layout=topbar -> /login).
if (typeof window !== "undefined") applyLayoutParam();

function subscribe(cb) {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}

export function useLayoutMode() {
  return useSyncExternalStore(subscribe, readStored, () => "topbar");
}
