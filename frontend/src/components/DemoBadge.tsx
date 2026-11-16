export function DemoBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-md border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-300 ${className}`}
    >
      demo data (synthetic)
    </span>
  );
}
