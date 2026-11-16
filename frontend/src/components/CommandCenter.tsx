import { useCallback, useEffect, useState } from "react";
import {
  metrics,
  Metrics,
  myRequests,
  MarketplaceRequest,
  threadEvents,
  ThreadEvent,
  threads,
  apiJson,
} from "../lib/api";
import { DemoBadge } from "./DemoBadge";
import { CandidateCard } from "./ChatView";
import { Activity, Gauge, Loader2 } from "lucide-react";

interface PipelineState {
  understand: string;
  discover: string;
  rank: string;
  coordinate: string;
  execute: string;
}

const NODE_LABELS: Record<keyof PipelineState, string> = {
  understand: "Understand",
  discover: "Discover",
  rank: "Rank",
  coordinate: "Coordinate",
  execute: "Execute",
};

function emptyPipeline(): PipelineState {
  return { understand: "idle", discover: "idle", rank: "idle", coordinate: "idle", execute: "idle" };
}

export function CommandCenter() {
  const [pipeline, setPipeline] = useState<PipelineState>(emptyPipeline());
  const [events, setEvents] = useState<ThreadEvent[]>([]);
  const [activeRequest, setActiveRequest] = useState<MarketplaceRequest | null>(null);
  const [matches, setMatches] = useState<any[]>([]);
  const [metricsData, setMetricsData] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const tids = await threads();
      if (tids.length > 0) {
        const evs = await threadEvents(tids[0]);
        setEvents(evs);
        const pipe = emptyPipeline();
        for (const e of evs) {
          const key = (Object.keys(NODE_LABELS) as (keyof PipelineState)[]).find((k) => k === e.node);
          if (key) pipe[key] = e.status === "error" ? "error" : "done";
        }
        setPipeline(pipe);
      }

      const reqs = await myRequests();
      const pending = reqs.find((r) => r.status === "pending");
      setActiveRequest(pending ?? null);
      if (pending) {
        const result = await apiJson<{ candidates: any[] }>("/market/search/trips", {
          method: "POST",
          body: JSON.stringify({
            origin: pending.origin_city,
            destination: pending.destination_city,
            weight_tonnes: pending.weight_tonnes,
            pickup_date: pending.pickup_date,
            budget_inr: pending.budget_inr,
          }),
        });
        setMatches(result.candidates);
      } else {
        setMatches([]);
      }

      setMetricsData(await metrics());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load command center");
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 8000);
    return () => clearInterval(t);
  }, [refresh]);

  const statusColor = (s: string) =>
    s === "done" ? "bg-emerald-500" : s === "error" ? "bg-red-500" : s === "working" ? "bg-disha-500 animate-pulse" : "bg-slate-700";

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold">Command Center</h1>
        <DemoBadge />
        {error && <span className="text-xs text-red-400">{error}</span>}
      </div>

      <div className="grid lg:grid-cols-[280px_1fr_320px] gap-5">
        {/* left: pipeline */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Agent pipeline</h2>
          <div className="space-y-2.5">
            {(Object.keys(NODE_LABELS) as (keyof PipelineState)[]).map((k) => (
              <div key={k} className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${statusColor(pipeline[k])}`} />
                <span className="text-sm">{NODE_LABELS[k]}</span>
                <span className="ml-auto text-[10px] uppercase text-slate-500">{pipeline[k]}</span>
              </div>
            ))}
          </div>
        </section>

        {/* center: active shipment + matches */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Active shipment</h2>
          {activeRequest ? (
            <>
              <div className="rounded-xl bg-slate-950 border border-slate-800 p-3.5">
                <div className="text-sm font-semibold">
                  {activeRequest.origin_city} → {activeRequest.destination_city}
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  {activeRequest.goods || "Goods"} · {activeRequest.weight_tonnes}t · pickup {activeRequest.pickup_date || "—"}
                  {activeRequest.budget_inr ? ` · budget ₹${Number(activeRequest.budget_inr).toLocaleString()}` : ""}
                </div>
                <div className="mt-2 inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-amber-300 border border-amber-500/30 rounded-md px-2 py-0.5 bg-amber-500/10">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                  status: {activeRequest.status}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-400 mb-2">Matched trucks (score)</div>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {matches.map((c) => (
                    <CandidateCard key={c.id} c={c} />
                  ))}
                  {matches.length === 0 && (
                    <div className="text-xs text-slate-500">No active candidates for this corridor right now.</div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="text-sm text-slate-500 py-8 text-center">
              No pending shipment right now.
              <br />
              <span className="text-xs">Create one in the Shipper Portal or Disha Chat.</span>
            </div>
          )}
        </section>

        {/* right: activity feed */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3 flex items-center gap-2">
            <Activity size={13} /> Activity feed
          </h2>
          <div className="space-y-2 overflow-y-auto max-h-[420px] pr-1">
            {events.length === 0 && (
              <div className="text-xs text-slate-500">No agent activity yet this session.</div>
            )}
            {[...events].reverse().map((e) => (
              <div key={e.id} className="text-[11px] bg-slate-950 rounded-lg px-2.5 py-2 border border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-disha-500">{e.node}</span>
                  <span className={`text-[9px] uppercase ${e.status === "error" ? "text-red-400" : "text-slate-500"}`}>
                    {e.status}
                  </span>
                </div>
                {e.payload_summary && <div className="text-slate-400 mt-0.5">{e.payload_summary}</div>}
                <div className="text-slate-600 mt-0.5">{new Date(e.created_at).toLocaleTimeString()}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* metrics strip */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3 flex items-center gap-2">
          <Gauge size={13} /> Measured metrics (from recorded events)
        </h2>
        {!metricsData ? (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Loader2 size={13} className="animate-spin" /> computing…
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
            <Metric label="Request → match (s)" value={metricsData.request_to_match_seconds} />
            <Metric label="Eligible trucks found" value={metricsData.eligible_trucks_found} />
            <Metric label="Offers sent" value={metricsData.offers_sent} />
            <Metric label="Acceptance rate" value={metricsData.acceptance_rate != null ? `${(metricsData.acceptance_rate * 100).toFixed(0)}%` : null} />
            <Metric label="Time to booking (s)" value={metricsData.time_to_booking_confirmation_seconds} />
            <Metric label="Match success rate" value={metricsData.match_success_rate != null ? `${(metricsData.match_success_rate * 100).toFixed(0)}%` : null} />
          </div>
        )}
        <div className="mt-3 text-[10px] text-slate-500">
          Every number comes from the backend events store. When a value cannot be computed it shows “unavailable” — never an estimate.
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string | null }) {
  return (
    <div className="rounded-xl bg-slate-950 border border-slate-800 p-3">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-xl font-bold mt-1">
        {value == null ? <span className="text-slate-600 text-sm font-normal">unavailable</span> : value}
      </div>
    </div>
  );
}
