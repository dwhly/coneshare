import { useEffect } from "react";

export const PRODUCT_TITLE = "Fleet Dealroom";

/** One title rule for every page: "<page> · Fleet Dealroom" (fixes the stale "Sign In - AmForge" after login). */
export function pageTitle(page) {
  return page ? `${page} · ${PRODUCT_TITLE}` : PRODUCT_TITLE;
}

export function usePageTitle(page) {
  useEffect(() => {
    document.title = pageTitle(page);
  }, [page]);
}
