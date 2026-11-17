import { useCallback, useEffect, useState } from "react";
import { myRequests, MarketplaceRequest, truckerShipments, Shipment, chat, approve, reject, PendingAction, ApiError } from "../lib/api";
import { PageHeader, Card, Badge, EmptyState } from "../ui/primitives";
import { ApprovalCard } from "../components/ChatView";
import { CheckCircle2, Loader2, Send } from "lucide-react";
import { useAuthUser } from "../components/authContext";

export function ShipmentsPage() {
  const user = useAuthUser();
  const [requests, setRequests] = useState<MarketplaceRequest[]>([]);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [prices, setPrices] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<{ action: PendingAction; threadId: string } | null>(null);
  const isShipper = user.role === "shipper";

  const refresh = useCallback(async () => {
    try {
      if (isShipper) {
        setRequests(await myRequests());
      } else {
        setShipments(await truckerShipments());
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load shipments");
    }
  }, [isShipper]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function confirmRequest(id: string) {
    setBusy(true);
    setPending(null);
    try {
      const { done } = await chat(`confirm request ${id}`);
      if (done.status === "approval_required" && done.pending_action) {
        setStatusLine("Approval required — review the action below.");
        setPending({ action: done.pending_action, threadId: done.thread_id });
      } else {
        setStatusLine(done.reply ?? "Request processed.");
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "confirmation failed");
    } finally {
      setBusy(false);
    }
  }

  async function sendOffer(s: Shipment) {
    setBusy(true);
    setPending(null);
    try {
      const price = prices[s.id]?.trim();
      const { done } = await chat(`send offer for ${s.id}${price ? ` at ${price}` : ""}`);
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

  if (isShipper) {
    return (
      <div>
        <PageHeader title="Shipments" subtitle="Your requests and their journey status." />
        {statusLine && <div className="mb-4 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">{statusLine}</div>}
        {error && <div className="mb-4 text-xs text-red-500">{error}</div>}
        {pending && (
          <div className="mb-4">
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
        <Card>
          {requests.length === 0 ? (
            <EmptyState title="No requests yet" hint="Create one in the Shipper flow or ask Disha." />
          ) : (
            <div className="divide-y divide-slate-100">
              {requests.map((r) => (
                <div key={r.id} className="p-4 flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-semibold text-navy-900">{r.origin_city} → {r.destination_city}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {r.goods || "Goods"} · {r.weight_tonnes}t
                      {r.pickup_date ? ` · pickup ${r.pickup_date}` : ""}
                      {r.budget_inr ? ` · budget ₹${Number(r.budget_inr).toLocaleString("en-IN")}` : ""}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 mt-1">{r.id}</div>
                    {r.status_explained && <div className="text-xs text-slate-600 mt-1.5">{r.status_explained}</div>}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Badge tone={r.status === "confirmed" ? "emerald" : "amber"}>{r.status}</Badge>
                    {r.status === "pending" && (
                      <button
                        onClick={() => confirmRequest(r.id)}
                        disabled={busy}
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40"
                      >
                        {busy ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />}
                        Confirm booking
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Shipments" subtitle="Pending loads available on the demo marketplace." />
      {statusLine && <div className="mb-4 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">{statusLine}</div>}
      {error && <div className="mb-4 text-xs text-red-500">{error}</div>}
      {pending && (
        <div className="mb-4">
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
      <Card>
        {shipments.length === 0 ? (
          <EmptyState title="No pending loads" hint="Check back later — demo shipments appear on the Rourkela–Ranchi corridor." />
        ) : (
          <div className="divide-y divide-slate-100">
            {shipments.map((s) => (
              <div key={s.id} className="p-4 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-semibold text-navy-900">{s.origin_city} → {s.destination_city}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {s.goods || "Goods"} · {s.weight_tonnes}t
                    {s.pickup_date ? ` · pickup ${s.pickup_date}` : ""}
                    {s.budget_inr ? ` · budget ₹${Number(s.budget_inr).toLocaleString("en-IN")}` : ""}
                  </div>
                  <div className="text-xs text-slate-600 mt-1.5">score <span className="text-disha-600 font-bold">{s.score.toFixed(2)}</span> · {s.explanation}</div>
                  {s.status_explained && <div className="text-xs text-slate-500 mt-1">{s.status_explained}</div>}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    className="w-24 bg-white border border-slate-300 rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-disha-500"
                    placeholder="₹ offer"
                    value={prices[s.id] ?? ""}
                    onChange={(e) => setPrices((p) => ({ ...p, [s.id]: e.target.value }))}
                  />
                  <button
                    onClick={() => sendOffer(s)}
                    disabled={busy}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-disha-600 text-white hover:bg-disha-500 disabled:opacity-40"
                  >
                    {busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                    Send offer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
