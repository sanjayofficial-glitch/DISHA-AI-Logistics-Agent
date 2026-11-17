import { useCallback, useEffect, useState } from "react";
import { chat, approve, reject, myOffers, truckerShipments, Shipment, Offer, PendingAction, ApiError } from "../lib/api";
import { DemoBadge } from "./DemoBadge";
import { ApprovalCard } from "./ChatView";
import { Loader2, Send } from "lucide-react";

export function TruckerPortal() {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<{ action: PendingAction; threadId: string } | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, o] = await Promise.all([truckerShipments(), myOffers()]);
      setShipments(s);
      setOffers(o);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load portal");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function sendOffer(s: Shipment) {
    setBusy(true);
    setError(null);
    setPending(null);
    try {
      const price = prices[s.id]?.trim();
      const msg = `send offer for ${s.id}${price ? ` at ${price}` : ""}`;
      const { done } = await chat(msg);
      if (done.status === "approval_required" && done.pending_action) {
        setStatusLine("Approval required — review the action below.");
        setPending({ action: done.pending_action, threadId: done.thread_id });
      } else {
        setStatusLine(done.reply ?? "Offer sent.");
      }
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError && e.status === 429 ? "Rate limited — wait a moment." : e instanceof Error ? e.message : "Offer failed.");
    } finally {
      setBusy(false);
    }
  }

  async function acceptOffer(o: Offer) {
    setBusy(true);
    setError(null);
    setPending(null);
    try {
      const { done } = await chat(`accept offer ${o.id}`);
      if (done.status === "approval_required" && done.pending_action) {
        setStatusLine("Approval required — review the action below.");
        setPending({ action: done.pending_action, threadId: done.thread_id });
      } else {
        setStatusLine(done.reply ?? "Offer processed.");
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "accept failed");
    } finally {
      setBusy(false);
    }
  }

  async function resolveApproval(doApprove: boolean) {
    if (!pending) return;
    setBusy(true);
    try {
      if (doApprove) {
        const res = await approve(pending.threadId);
        setStatusLine(res.reply);
      } else {
        await reject(pending.threadId);
        setStatusLine("Rejected — nothing was written.");
      }
      setPending(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "approval failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center gap-2 mb-4">
          <h1 className="text-lg font-bold">Trucker Portal</h1>
          <DemoBadge />
        </div>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">Compatible pending loads</h2>
        {error && <div className="text-xs text-red-400 mb-3">{error}</div>}
        {statusLine && (
          <div className="text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2 mb-3">{statusLine}</div>
        )}
        {pending && (
          <div className="mb-3">
            <ApprovalCard
              action={pending.action}
              threadId={pending.threadId}
              busy={busy}
              onApprove={() => resolveApproval(true)}
              onReject={() => resolveApproval(false)}
              onSpeak={() => {}}
            />
          </div>
        )}
        <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
          {shipments.length === 0 && <div className="text-sm text-slate-500">No pending loads right now.</div>}
          {shipments.map((s) => (
            <div key={s.id} className="rounded-xl bg-slate-950 border border-slate-800 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">
                    {s.origin_city} → {s.destination_city}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {s.goods || "Goods"} · {s.weight_tonnes}t
                    {s.pickup_date ? ` · pickup ${s.pickup_date}` : ""}
                    {s.budget_inr ? ` · budget ₹${Number(s.budget_inr).toLocaleString()}` : ""}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 mt-1">{s.id}</div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    score <span className="text-disha-500 font-bold">{s.score.toFixed(2)}</span> · {s.explanation}
                  </div>
                </div>
                <div className="text-right space-y-2">
                  <input
                    className="w-28 bg-slate-950 border border-slate-700 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-disha-600/60"
                    placeholder="₹"
                    value={prices[s.id] ?? ""}
                    onChange={(e) => setPrices((p) => ({ ...p, [s.id]: e.target.value }))}
                  />
                  <button
                    onClick={() => sendOffer(s)}
                    disabled={busy}
                    className="w-full flex items-center justify-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg bg-disha-600/20 border border-disha-600/40 text-disha-500 hover:bg-disha-600/30 disabled:opacity-40"
                  >
                    {busy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                    Send offer
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">My offers & jobs</h2>
        {offers.length === 0 && <div className="text-sm text-slate-500">No offers yet — send one from the left panel.</div>}
        <div className="space-y-3">
          {offers.map((o) => (
            <div key={o.id} className="rounded-xl bg-slate-950 border border-slate-800 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold">
                    {o.origin_city || "—"} → {o.destination_city || "—"}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {o.goods || "Goods"} · {o.weight_tonnes ?? "—"}t
                    {o.price_inr ? ` · offer ₹${Number(o.price_inr).toLocaleString()}` : ""}
                  </div>
                  <div className="text-[10px] font-mono text-slate-500 mt-1">{o.id} · {o.request_id}</div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span
                    className={`text-[10px] uppercase tracking-wide rounded-md px-2 py-0.5 border ${
                      o.status === "accepted"
                        ? "text-emerald-300 border-emerald-500/40 bg-emerald-500/10"
                        : o.status === "declined"
                          ? "text-red-400 border-red-500/40 bg-red-500/10"
                          : "text-amber-300 border-amber-500/40 bg-amber-500/10"
                    }`}
                  >
                    {o.status}
                  </span>
                  {o.status === "pending" && (
                    <button
                      onClick={() => acceptOffer(o)}
                      disabled={busy}
                      className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-emerald-600/20 border border-emerald-600/40 text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-40"
                    >
                      Accept offer
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
