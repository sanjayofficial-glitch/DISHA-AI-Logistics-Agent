import { useState } from "react";
import { apiJson, Candidate, truckerShipments, Shipment, ptlCheck, PtlResult } from "../lib/api";
import { PageHeader, Card, EmptyState } from "../ui/primitives";
import { CandidateCard } from "../components/ChatView";
import { Search, Loader2, Combine } from "lucide-react";

export function MatchingPage() {
  const [form, setForm] = useState({ origin: "Rourkela", destination: "Ranchi", weight: "8", date: "", budget: "" });
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // PTL panel state
  const [loads, setLoads] = useState<Shipment[]>([]);
  const [ptlTrip, setPtlTrip] = useState("");
  const [ptlLoadA, setPtlLoadA] = useState("");
  const [ptlLoadB, setPtlLoadB] = useState("");
  const [ptlResult, setPtlResult] = useState<PtlResult | null>(null);
  const [ptlBusy, setPtlBusy] = useState(false);

  async function openPtl() {
    if (loads.length === 0) {
      try {
        setLoads(await truckerShipments());
      } catch { /* ignore */ }
    }
  }

  async function runPtl() {
    if (!ptlTrip || !ptlLoadA || !ptlLoadB) return;
    setPtlBusy(true);
    setPtlResult(null);
    try {
      setPtlResult(await ptlCheck({ trip_id: ptlTrip, load_ids: [ptlLoadA, ptlLoadB] }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "PTL check failed");
    } finally {
      setPtlBusy(false);
    }
  }

  async function search() {
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        origin: form.origin,
        destination: form.destination,
        weight_tonnes: Number(form.weight) || undefined,
      };
      if (form.date) body.pickup_date = form.date;
      if (form.budget) body.budget_inr = Number(form.budget);
      const data = await apiJson<{ candidates: Candidate[] }>("/market/search/trips", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setCandidates(data.candidates);
    } catch (e) {
      setError(e instanceof Error ? e.message : "search failed");
    } finally {
      setBusy(false);
    }
  }

  const inputCls = "bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500 w-full";

  return (
    <div className="space-y-5">
      <PageHeader title="Matching" subtitle="Deterministic ranking — route 35% · capacity 25% · price 20% · date 10% · reliability 10%." />
      <Card className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <input className={inputCls} placeholder="Origin" value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))} />
          <input className={inputCls} placeholder="Destination" value={form.destination} onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))} />
          <input className={inputCls} type="number" placeholder="Weight (t)" value={form.weight} onChange={(e) => setForm((f) => ({ ...f, weight: e.target.value }))} />
          <input className={inputCls} type="date" value={form.date} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} />
          <input className={inputCls} type="number" placeholder="Budget ₹" value={form.budget} onChange={(e) => setForm((f) => ({ ...f, budget: e.target.value }))} />
        </div>
        <button
          onClick={search}
          disabled={busy || !form.origin || !form.destination}
          className="mt-3 flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-40"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          Find matching vehicles
        </button>
        {error && <div className="mt-3 text-xs text-red-500">{error}</div>}
      </Card>

      {candidates && (
        <div className="grid md:grid-cols-2 gap-3">
          {candidates.length === 0 && (
            <Card className="md:col-span-2"><EmptyState title="No matches for this corridor" hint="Try Rourkela → Ranchi with the demo seed." /></Card>
          )}
          {candidates.map((c) => (
            <Card key={c.id} className="p-3">
              <CandidateCard c={c} />
            </Card>
          ))}
        </div>
      )}

      {/* PTL combination panel */}
      <Card className="p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-navy-900">
          <Combine size={15} className="text-disha-600" /> Partial Truckload (PTL) feasibility check
        </div>
        <div className="text-xs text-slate-500 mt-1">
          Pick a vehicle (from search results) and two loads — DISHA evaluates whether they can realistically travel together (demo corridor).
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
          <select className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" value={ptlTrip} onChange={(e) => setPtlTrip(e.target.value)} onFocus={openPtl}>
            <option value="">Vehicle (trip)</option>
            {(candidates ?? []).map((c) => (
              <option key={c.id} value={c.id}>{c.id} — {c.origin_city} → {c.destination_city}</option>
            ))}
          </select>
          <select className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" value={ptlLoadA} onChange={(e) => setPtlLoadA(e.target.value)} onFocus={openPtl}>
            <option value="">Load A</option>
            {loads.map((s) => (
              <option key={s.id} value={s.id}>{s.id} — {s.weight_tonnes}t {s.origin_city}→{s.destination_city}</option>
            ))}
          </select>
          <select className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" value={ptlLoadB} onChange={(e) => setPtlLoadB(e.target.value)} onFocus={openPtl}>
            <option value="">Load B</option>
            {loads.map((s) => (
              <option key={s.id} value={s.id}>{s.id} — {s.weight_tonnes}t {s.origin_city}→{s.destination_city}</option>
            ))}
          </select>
        </div>
        <button
          onClick={runPtl}
          disabled={ptlBusy || !ptlTrip || !ptlLoadA || !ptlLoadB}
          className="mt-3 flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-40"
        >
          {ptlBusy ? <Loader2 size={15} className="animate-spin" /> : <Combine size={15} />}
          Evaluate combination
        </button>
        {ptlResult && (
          <div className={`mt-3 rounded-xl border p-3 text-sm ${
            ptlResult.feasible ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-red-300 bg-red-50 text-red-700"
          }`}>
            <div className="font-semibold">
              {ptlResult.feasible ? "Feasible combination" : "Not feasible"}
            </div>
            <div className="text-xs mt-1">
              {ptlResult.reason ?? ""}
              {ptlResult.feasible && ptlResult.utilization != null && (
                <> · Utilization {Math.round(ptlResult.utilization * 100)}% · {ptlResult.route}</>
              )}
              {ptlResult.detour_estimate_km != null && ` · est. detour ${ptlResult.detour_estimate_km} km`}
            </div>
            <div className="text-[10px] mt-1 opacity-70">{ptlResult.note}</div>
          </div>
        )}
      </Card>
    </div>
  );
}
