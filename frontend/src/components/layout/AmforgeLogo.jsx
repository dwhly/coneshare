import { useBranding } from '../../contexts/BrandingProvider';
export function AmforgeLogo({ product, className = '', ...props }) {
  const brand = useBranding();
  return <span role="img" aria-label={`${brand.brandName}${product ? ` ${product}` : ''}`} className={`inline-flex items-center gap-2 ${className}`} {...props}><img src={brand.brandLogoUrl} alt="" className="h-8 w-8"/><span className="font-semibold tracking-tight text-xl">{brand.brandName}</span>{product && <span className="text-slate-500 capitalize">{product}</span>}</span>;
}
export function AmforgeMark(props) {
  const brand = useBranding();
  return <img src={brand.brandLogoUrl} alt={brand.brandName} {...props}/>;
}
