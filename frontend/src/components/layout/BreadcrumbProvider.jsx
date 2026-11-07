import { createContext, useContext, useState } from "react";

const BreadcrumbContext = createContext();

export function BreadcrumbProvider({ children }) {
  const [breadcrumbData, setBreadcrumbData] = useState(null);

  return (
    <BreadcrumbContext.Provider value={{ breadcrumbData, setBreadcrumbData }}>
      {children}
    </BreadcrumbContext.Provider>
  );
}

export function useBreadcrumb() {
  const context = useContext(BreadcrumbContext);
  if (context === undefined) {
    throw new Error("useBreadcrumb must be used within a BreadcrumbProvider");
  }
  return context;
}

/** Same context, but a no-op outside the provider (pages rendered standalone in tests). */
export function useOptionalBreadcrumb() {
  return useContext(BreadcrumbContext) || { breadcrumbData: null, setBreadcrumbData: () => {} };
}
