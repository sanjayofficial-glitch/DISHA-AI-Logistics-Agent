import { useState } from "react";
import { apiJson, Candidate } from "../lib/api";
import { PageHeader, Card, EmptyState } from "../ui/primitives";
import { CandidateCard } from "../components/ChatView";
import { Search, Loader2 } from "lucide-react";

export function MatchingPage() {
  const [form, setForm] = useState({ origin: "Rourkela", destination: "Ranchi", weight: "8", date: "", budget: "" });
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    </div>
  );
}
