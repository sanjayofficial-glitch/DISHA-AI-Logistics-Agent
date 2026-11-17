/** Shared UI primitives for the DISHA Command Center. */
import { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { DemoBadge } from "../components/DemoBadge";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  accent = "navy",
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  accent?: "navy" | "orange" | "emerald" | "amber";
}) {
  const accentMap: Record<string, string> = {
    navy: "text-navy-900",
    orange: "text-disha-600",
    emerald: "text-emerald-600",
    amber: "text-amber-600",
  };
  return (
    <Card className="p-4">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-2xl font-extrabold mt-1 ${accentMap[accent]}`}>{value}</div>
      {sub && <div className="text-[11px] text-slate-400 mt-1">{sub}</div>}
    </Card>
  );
}

export function Badge({
  tone = "slate",
  children,
}: {
  tone?: "slate" | "emerald" | "amber" | "red" | "navy" | "orange";
  children: ReactNode;
}) {
  const tones: Record<string, string> = {
    slate: "text-slate-600 border-slate-300 bg-slate-100",
    emerald: "text-emerald-700 border-emerald-300 bg-emerald-50",
    amber: "text-amber-700 border-amber-300 bg-amber-50",
    red: "text-red-700 border-red-300 bg-red-50",
    navy: "text-navy-800 border-navy-200 bg-navy-100",
    orange: "text-disha-700 border-disha-300 bg-disha-50",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
      <div>
        <h1 className="text-xl font-extrabold text-navy-900">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        <DemoBadge />
        {actions}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-10 px-4">
      <Inbox size={28} className="text-slate-300" />
      <div className="text-sm font-medium text-slate-500 mt-2">{title}</div>
      {hint && <div className="text-xs text-slate-400 mt-1">{hint}</div>}
    </div>
  );
}

export function ScoreBar({ label, score }: { label: string; score: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] text-slate-500">
        <span className="capitalize">{label}</span>
        <span className="font-mono">{score.toFixed(2)}</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mt-0.5">
        <div className="h-full bg-disha-500" style={{ width: `${Math.min(100, score * 100)}%` }} />
      </div>
    </div>
  );
}

export function EstimatePanel({ quote }: { quote: { available: boolean; reason?: string; total_inr?: number; per_tonne_inr?: number; breakdown?: Record<string, unknown>; assumptions?: string[]; distance_assumption_km?: number; weight_tonnes?: number; origin?: string; destination?: string } }) {
  if (!quote.available) {
    return (
      <Card className="p-4 border-amber-300 bg-amber-50">
        <div className="text-sm font-semibold text-amber-800">Estimate unavailable</div>
        <div className="text-xs text-amber-700 mt-1">{quote.reason ?? "Cannot estimate."}</div>
      </Card>
    );
  }
  const bd = (quote.breakdown ?? {}) as { formula?: string; base_charge_per_km_inr?: number; fuel_toll_factor?: number };
  return (
    <Card className="p-4 border-navy-200">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Estimated total (₹)</div>
          <div className="text-3xl font-extrabold text-navy-900 mt-0.5">
            ₹{Number(quote.total_inr).toLocaleString("en-IN")}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Per tonne</div>
          <div className="text-lg font-bold text-disha-600 mt-0.5">
            ₹{Number(quote.per_tonne_inr).toLocaleString("en-IN")}
          </div>
        </div>
      </div>
      <div className="mt-3 rounded-lg bg-navy-950 text-navy-100 px-3 py-2 text-xs space-y-1">
        <div className="font-semibold text-white">Calculation breakdown</div>
        <div>• base ₹{bd.base_charge_per_km_inr ?? "?"}/km × {quote.distance_assumption_km} km × fuel/toll {bd.fuel_toll_factor}</div>
        <div>• {bd.formula}</div>
      </div>
      <div className="mt-3 text-[11px] text-slate-500 space-y-0.5">
        <div className="font-semibold text-slate-600">Assumptions</div>
        {quote.assumptions?.map((a) => (
          <div key={a}>• {a}</div>
        ))}
      </div>
      <div className="mt-3 text-[11px] font-semibold text-disha-700 bg-disha-50 border border-disha-200 rounded-lg px-3 py-2">
        ESTIMATE ONLY — route-based (distance) demo figure, not a weight-sensitive or vehicle-sensitive market quotation.
      </div>
    </Card>
  );
}
