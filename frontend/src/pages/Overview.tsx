import { useCallback, useEffect, useState } from "react";
import { marketStats, MarketStats, metrics, Metrics, approvals } from "../lib/api";
import { PageHeader, StatCard, Card, EmptyState } from "../ui/primitives";
import { useNav } from "../appShell/AppShell";
import { Bot, PackageSearch, Route, ShieldCheck } from "lucide-react";

export function OverviewPage() {
  const { setSection } = useNav();
  const [stats, setStats] = useState<MarketStats | null>(null);
  const [mets, setMets] = useState<Metrics | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, m, a] = await Promise.all([marketStats(), metrics(), approvals()]);
      setStats(s);
      setMets(m);
      setPendingApprovals(a.length);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load overview");
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 8000);
    return () => clearInterval(t);
  }, [refresh]);

  const qa = [
    { label: "Ask Disha", icon: <Bot size={16} />, go: () => setSection("assistant") },
    { label: "New shipment", icon: <PackageSearch size={16} />, go: () => setSection("shipments") },
    { label: "Match a load", icon: <Route size={16} />, go: () => setSection("matching") },
    { label: "Approvals", icon: <ShieldCheck size={16} />, go: () => setSection("approvals") },
  ];

  return (
    <div className="space-y-5">
      <PageHeader title="Overview" subtitle="Live operational summary — every number comes from the backend." />
      {error && <div className="text-xs text-red-500">{error}</div>}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <StatCard label="Active vehicles" value={stats?.active_trips ?? "—"} accent="navy" />
        <StatCard label="Pending shipments" value={stats?.pending_shipments ?? "—"} accent="navy" />
        <StatCard label="My pending requests" value={stats?.my_pending_requests ?? "—"} accent="amber" />
        <StatCard label="Approvals waiting" value={pendingApprovals} accent="orange" />
        <StatCard label="Offers sent" value={mets?.offers_sent ?? "—"} accent="emerald" />
        <StatCard
          label="Acceptance rate"
          value={mets?.acceptance_rate != null ? `${(mets.acceptance_rate * 100).toFixed(0)}%` : "unavailable"}
          accent="emerald"
        />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Quick actions</div>
          <div className="grid grid-cols-2 gap-2">
            {qa.map((q) => (
              <button
                key={q.label}
                onClick={q.go}
                className="flex items-center gap-2 text-sm px-3 py-2.5 rounded-xl border border-slate-200 hover:border-disha-400 hover:bg-disha-50 text-navy-900 transition-colors"
              >
                <span className="text-disha-600">{q.icon}</span>
                {q.label}
              </button>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Agent metrics (recorded events)</div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Request → first match</span><span className="font-mono">{mets?.request_to_match_seconds != null ? `${mets.request_to_match_seconds}s` : "unavailable"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Time to booking confirmation</span><span className="font-mono">{mets?.time_to_booking_confirmation_seconds != null ? `${mets.time_to_booking_confirmation_seconds}s` : "unavailable"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Match success rate</span><span className="font-mono">{mets?.match_success_rate != null ? `${(mets.match_success_rate * 100).toFixed(0)}%` : "unavailable"}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Eligible trucks found</span><span className="font-mono">{mets?.eligible_trucks_found ?? "unavailable"}</span></div>
          </div>
        </Card>
      </div>

      {!stats && !error && <EmptyState title="Loading overview…" />}
    </div>
  );
}
