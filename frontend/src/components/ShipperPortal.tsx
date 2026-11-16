import { useCallback, useEffect, useState } from "react";
import { chat, approve, myRequests, MarketplaceRequest, ApiError } from "../lib/api";
import { DemoBadge } from "./DemoBadge";
import { Loader2, Send, CheckCircle2 } from "lucide-react";

interface FormState {
  origin: string;
  destination: string;
  goods: string;
  weight: string;
  vehicle: string;
  date: string;
  budget: string;
}

const EMPTY: FormState = { origin: "", destination: "", goods: "", weight: "", vehicle: "", date: "", budget: "" };

export function ShipperPortal() {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [requests, setRequests] = useState<MarketplaceRequest[]>([]);
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setRequests(await myRequests());
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load requests");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function set<K extends keyof FormState>(k: K, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit() {
    setBusy(true);
    setError(null);
    setStatusLine(null);
    const msg =
      `Create a request: from ${form.origin} to ${form.destination}, ` +
      `${form.weight} tonnes, ${form.goods || "goods"}${form.vehicle ? ", " + form.vehicle : ""}, ` +
      `${form.date || "tomorrow"}${form.budget ? ", budget " + form.budget : ""}`;
    try {
      const { done } = await chat(msg);
      if (done.status === "approval_required" && done.pending_action) {
        setStatusLine(`Approval required: ${done.pending_action.summary}`);
        const res = await approve(done.thread_id);
        setStatusLine(res.reply);
      } else if (done.status === "needs_input") {
        setStatusLine(`Disha needs more detail: ${done.reply ?? ""}`);
      } else {
        setStatusLine(done.reply ?? "Request created.");
      }
      setForm(EMPTY);
      await refresh();
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 429
          ? "Rate limited — please wait a moment."
          : e instanceof Error
            ? e.message
            : "Request failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmRequest(id: string) {
    setBusy(true);
    setError(null);
    try {
      const { done } = await chat(`confirm request ${id}`);
      if (done.status === "approval_required" && done.pending_action) {
        const res = await approve(done.thread_id);
        setStatusLine(res.reply);
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "confirmation failed");
    } finally {
      setBusy(false);
    }
  }

  const inputCls =
    "bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-disha-600/60 w-full";

  return (
    <div className="grid lg:grid-cols-[420px_1fr] gap-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4 h-fit">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-bold">Shipper Portal</h1>
          <DemoBadge />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="space-y-1 text-xs text-slate-400">
            Pickup city
            <input className={inputCls} value={form.origin} onChange={(e) => set("origin", e.target.value)} placeholder="Rourkela" />
          </label>
          <label className="space-y-1 text-xs text-slate-400">
            Delivery city
            <input className={inputCls} value={form.destination} onChange={(e) => set("destination", e.target.value)} placeholder="Ranchi" />
          </label>
        </div>
        <label className="block space-y-1 text-xs text-slate-400">
          Goods description
          <input className={inputCls} value={form.goods} onChange={(e) => set("goods", e.target.value)} placeholder="Industrial goods" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="space-y-1 text-xs text-slate-400">
            Weight (tonnes)
            <input className={inputCls} type="number" value={form.weight} onChange={(e) => set("weight", e.target.value)} placeholder="8" />
          </label>
          <label className="space-y-1 text-xs text-slate-400">
            Vehicle
            <select className={inputCls} value={form.vehicle} onChange={(e) => set("vehicle", e.target.value)}>
              <option value="">Any</option>
              <option value="open body">Open body</option>
              <option value="trailer">Trailer</option>
              <option value="covered body">Covered body</option>
            </select>
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="space-y-1 text-xs text-slate-400">
            Pickup date
            <input className={inputCls} type="date" value={form.date} onChange={(e) => set("date", e.target.value)} />
          </label>
          <label className="space-y-1 text-xs text-slate-400">
            Budget (₹)
            <input className={inputCls} type="number" value={form.budget} onChange={(e) => set("budget", e.target.value)} placeholder="40000" />
          </label>
        </div>
        {error && <div className="text-xs text-red-400">{error}</div>}
        {statusLine && <div className="text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">{statusLine}</div>}
        <button
          onClick={submit}
          disabled={busy || !form.origin || !form.destination || !form.weight}
          className="w-full flex items-center justify-center gap-2 bg-disha-600 hover:bg-disha-500 text-white rounded-xl px-4 py-2.5 text-sm font-semibold disabled:opacity-40 transition-colors"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          Find my truck
        </button>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">My requests</h2>
        {requests.length === 0 && <div className="text-sm text-slate-500">No requests yet.</div>}
        <div className="space-y-3">
          {requests.map((r) => (
            <div key={r.id} className="rounded-xl bg-slate-950 border border-slate-800 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">
                    {r.origin_city} → {r.destination_city}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {r.goods || "Goods"} · {r.weight_tonnes}t
                    {r.pickup_date ? ` · pickup ${r.pickup_date}` : ""}
                    {r.budget_inr ? ` · budget ₹${Number(r.budget_inr).toLocaleString()}` : ""}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 mt-1">{r.id}</div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span
                    className={`text-[10px] uppercase tracking-wide rounded-md px-2 py-0.5 border ${
                      r.status === "confirmed"
                        ? "text-emerald-300 border-emerald-500/40 bg-emerald-500/10"
                        : "text-amber-300 border-amber-500/40 bg-amber-500/10"
                    }`}
                  >
                    {r.status}
                  </span>
                  {r.status === "pending" && (
                    <button
                      onClick={() => confirmRequest(r.id)}
                      disabled={busy}
                      className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-emerald-600/20 border border-emerald-600/40 text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-40"
                    >
                      <CheckCircle2 size={13} /> Confirm booking
                    </button>
                  )}
                </div>
              </div>
              {r.confirmed_at && (
                <div className="text-[10px] text-slate-500 mt-2">confirmed {new Date(r.confirmed_at).toLocaleString()}</div>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
