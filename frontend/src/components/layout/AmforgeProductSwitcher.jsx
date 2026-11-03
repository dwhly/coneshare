import { cn } from "../../lib/utils";

/**
 * AmForge product switcher (shared shell). Same markup as Sign's amforge-product-switcher.tsx and
 * amforge-ui/shell/ProductSwitcher.reference.jsx. Treatment = the Tabs primitive (TabsList /
 * TabsTrigger) at compact size, rendered as links because switching products is navigation.
 */
const PRODUCTS = [
  { id: "send", label: "Send", url: import.meta.env.VITE_AMFORGE_SEND_URL || "http://send.100-110-241-2.sslip.io" },
  { id: "sign", label: "Sign", url: import.meta.env.VITE_AMFORGE_SIGN_URL || "http://sign-dev.100-110-241-2.sslip.io" },
];

export function AmforgeProductSwitcher({ current, className }) {
  return (
    <nav
      aria-label="AmForge products"
      className={cn("inline-flex h-8 items-center rounded-md bg-muted p-0.5 text-muted-foreground", className)}
    >
      {PRODUCTS.map((product) => {
        const isActive = product.id === current;

        return (
          <a
            key={product.id}
            href={isActive ? undefined : product.url}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "inline-flex h-7 items-center rounded-sm px-3 text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
              isActive ? "bg-background text-foreground shadow-sm" : "hover:text-foreground"
            )}
          >
            {product.label}
          </a>
        );
      })}
    </nav>
  );
}
