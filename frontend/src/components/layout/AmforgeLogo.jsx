import {
  AMFORGE_MARK,
  AMFORGE_PRODUCTS,
  AMFORGE_VIEWBOX_HEIGHT,
  AMFORGE_VIEWBOX_TOP,
  AMFORGE_WORDMARK,
} from "../../lib/amforgeBrandPaths";

/**
 * AmForge lockup (mark + wordmark [+ product]). Same geometry as Sign's BrandingLogo.
 * Text uses currentColor; the mark uses --brand tokens. Inside the app shell pass no product
 * (the product switcher names it); outside (login, emails) pass product="send".
 */
export function AmforgeLogo({ product, ...props }) {
  const productPath = product ? AMFORGE_PRODUCTS[product] : null;
  const width = productPath ? productPath.width : AMFORGE_WORDMARK.width;
  const label = productPath ? `AmForge ${productPath.label}` : "AmForge";

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 ${AMFORGE_VIEWBOX_TOP} ${width} ${AMFORGE_VIEWBOX_HEIGHT}`}
      role="img"
      aria-label={label}
      {...props}
    >
      <rect
        x={AMFORGE_MARK.x}
        y={AMFORGE_MARK.y}
        width={AMFORGE_MARK.size}
        height={AMFORGE_MARK.size}
        rx={AMFORGE_MARK.rx}
        style={{ fill: "hsl(var(--brand))" }}
      />
      <path style={{ fill: "hsl(var(--brand-foreground))" }} d={AMFORGE_MARK.glyph} />
      <path fill="currentColor" d={AMFORGE_WORDMARK.d} />
      {productPath && <path fill="currentColor" fillOpacity={0.6} d={productPath.d} />}
    </svg>
  );
}

/** Square AmForge mark (collapsed sidebar, favicons). */
export function AmforgeMark(props) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 ${AMFORGE_MARK.y} ${AMFORGE_MARK.size} ${AMFORGE_MARK.size}`}
      role="img"
      aria-label="AmForge"
      {...props}
    >
      <rect
        x={0}
        y={AMFORGE_MARK.y}
        width={AMFORGE_MARK.size}
        height={AMFORGE_MARK.size}
        rx={AMFORGE_MARK.rx}
        style={{ fill: "hsl(var(--brand))" }}
      />
      <path style={{ fill: "hsl(var(--brand-foreground))" }} d={AMFORGE_MARK.glyph} />
    </svg>
  );
}
