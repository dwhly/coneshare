import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authService } from "../services/authService";
import { isSafeUrl } from "../lib/utils";

const BrandingContext = createContext(null);

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState({
    brandName: "Dealroom",
    brandLogoUrl: "/brand-mark.svg",
    brandWebsiteUrl: "",
    termsUrl: "https://www.coneshare.com/terms",
    privacyPolicyUrl: "https://www.coneshare.com/privacy-policy",
  });
  const [isLoading, setIsLoading] = useState(true);

  const fetchBranding = useCallback(async () => {
    try {
      const data = await authService.getPublicSettings();
      const brand = await fetch('/api/v1/dealroom/brand/').then(r => r.json());
      data.brand_name = brand.name;
      data.brand_logo_url = brand.logo;
      // Fleet design system: a tenant may override BRAND slots only (DESIGN.md §2). brand.yaml's `primary`
      // is the tenant accent, so it becomes --brand (links/focus); the primary button stays ink.
      // Text, surface, radius and status keys are ignored.
      // The tenant gives one (light-mode) accent, so it is scoped to light; dark keeps the token's dark brand.
      const ignored = [];
      const slots = [];
      Object.entries(brand.tokens || {}).forEach(([key, value]) => {
        const slot = key === "primary" ? "brand" : key;
        if (/^brand(-|$)/.test(slot) && /^[\d.]+ [\d.]+% [\d.]+%$/.test(String(value).trim())) slots.push(`--${slot}: ${String(value).trim()};`);
        else ignored.push(key);
      });
      let tenantStyle = document.getElementById("fds-tenant-brand");
      if (!tenantStyle) {
        tenantStyle = document.createElement("style");
        tenantStyle.id = "fds-tenant-brand";
        document.head.appendChild(tenantStyle);
      }
      tenantStyle.textContent = slots.length ? `:root:not([data-theme="dark"]) { ${slots.join(" ")} }` : "";
      if (ignored.length) console.warn(`[fds] tenant tokens ignored (brand slots only): ${ignored.join(", ")}`);
      data.sign_url = brand.sign_url;
      const websiteUrl = data?.brand_website_url;
      const terms = data?.terms_url;
      const privacy = data?.privacy_policy_url;

      setBranding({
        brandName: data?.brand_name || "Dealroom",
        brandLogoUrl: data?.brand_logo_url || "/brand-mark.svg",
        brandWebsiteUrl: (websiteUrl && isSafeUrl(websiteUrl)) ? websiteUrl : "",
        termsUrl: (terms && isSafeUrl(terms)) ? terms : "https://www.coneshare.com/terms",
        privacyPolicyUrl: (privacy && isSafeUrl(privacy)) ? privacy : "https://www.coneshare.com/privacy-policy",
        signUrl: (data?.sign_url && isSafeUrl(data.sign_url)) ? data.sign_url : "",
      });
    } catch (error) {
      console.error("Failed to fetch public settings/branding:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBranding();
  }, [fetchBranding]);

  useEffect(() => {
    const faviconElement = document.querySelector("link[rel~='icon']");
    if (faviconElement) {
      faviconElement.href = branding.brandLogoUrl || "/brand-mark.svg";
    }
  }, [branding.brandLogoUrl]);

  const value = {
    ...branding,
    isLoading,
    refetchBranding: fetchBranding,
  };

  return (
    <BrandingContext.Provider value={value}>
      {children}
    </BrandingContext.Provider>
  );
}

export function useBranding() {
  const context = useContext(BrandingContext);
  if (context === null) {
    return {
      brandName: "Dealroom",
      brandLogoUrl: "/brand-mark.svg",
      brandWebsiteUrl: "",
      termsUrl: "https://www.coneshare.com/terms",
      privacyPolicyUrl: "https://www.coneshare.com/privacy-policy",
      isLoading: false,
      refetchBranding: async () => {},
    };
  }
  return context;
}
