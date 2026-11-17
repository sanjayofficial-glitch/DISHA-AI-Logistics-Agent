import { useState } from "react";
import { quotePrice, QuotePayload } from "../lib/api";
import { PageHeader, Card, EstimatePanel } from "../ui/primitives";
import { Calculator, Loader2 } from "lucide-react";

export function PricingPage() {
  const [form, setForm] = useState({ origin: "Rourkela", destination: "Ranchi", weight: "8", vehicle: "open body" });
  const [quote, setQuote] = useState<QuotePayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function estimate() {
    setBusy(true);
    setError(null);
    try {
      const q = await quotePrice({
        origin: form.origin,
        destination: form.destination,
        weight_tonnes: Number(form.weight),
        vehicle_type: form.vehicle,
      });
      setQuote(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : "quote failed");
      setQuote(null);
    } finally {
      setBusy(false);
    }
  }

  const inputCls = "bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500 w-full";

  return (
    <div className="space-y-5">
      <PageHeader title="Pricing" subtitle="Deterministic freight estimate — labeled an estimate, never a market quotation." />
      <Card className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <input className={inputCls} placeholder="Origin" value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))} />
          <input className={inputCls} placeholder="Destination" value={form.destination} onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))} />
          <input className={inputCls} type="number" placeholder="Weight (t)" value={form.weight} onChange={(e) => setForm((f) => ({ ...f, weight: e.target.value }))} />
          <select className={inputCls} value={form.vehicle} onChange={(e) => setForm((f) => ({ ...f, vehicle: e.target.value }))}>
            <option value="open body">Open body</option>
            <option value="trailer">Trailer</option>
            <option value="covered body">Covered body</option>
          </select>
        </div>
        <button
          onClick={estimate}
          disabled={busy || !form.origin || !form.destination || !form.weight}
          className="mt-3 flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-disha-600 text-white hover:bg-disha-500 disabled:opacity-40"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Calculator size={15} />}
          Estimate freight
        </button>
        {error && <div className="mt-3 text-xs text-red-500">{error}</div>}
      </Card>

      {quote && <EstimatePanel quote={quote} />}
    </div>
  );
}
