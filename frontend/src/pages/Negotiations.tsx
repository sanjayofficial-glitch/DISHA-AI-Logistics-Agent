import { useCallback, useEffect, useState } from "react";
import { myRequests, MarketplaceRequest, myOffers, Offer, negotiations, NegotiationRow, chat, approve, PendingAction } from "../lib/api";
import { PageHeader, Card, Badge, EmptyState } from "../ui/primitives";
import { ApprovalCard } from "../components/ChatView";
import { useAuthUser } from "../components/authContext";
import { Handshake, Loader2 } from "lucide-react";

export function NegotiationsPage() {
  const user = useAuthUser();
  const isShipper = user.role === "shipper";
  const [requests, setRequests] = useState<MarketplaceRequest[]>([]);
  const [offers, setOffers] = useState<Offer[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [history, setHistory] = useState<NegotiationRow[] | null>(null);
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<{ action: PendingAction; threadId: string } | null>(null);

  const refresh = useCallback(async () => {
    try {
      if (isShipper) {
        setRequests(await myRequests());
      } else {
        setOffers(await myOffers());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load");
    }
  }, [isShipper]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loadHistory = useCallback(async (id: string) => {
    try {
      setHistory(await negotiations(id));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load negotiation history");
      setHistory(null);
    }
  }, []);

  function select(id: string) {
    setSelectedId(id);
    setPending(null);
    setStatusLine(null);
    loadHistory(id);
  }

  async function sendCounter() {
    if (!selectedId) return;
    setBusy(true);
    setStatusLine(null);
    setPending(null);
    try {
      const { done } = await chat(`counter offer on ${selectedId} at ${amount}`);
      if (done.status === "approval_required" && done.pending_action) {
        setPending({ action: done.pending_action, threadId: done.thread_id });
      } else {
        setStatusLine(done.reply ?? "Request received.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "counter-offer failed");
    } finally {
      setBusy(false);
    }
  }

  async function resolveApproval(approveAction: boolean) {
    if (!pending || !selectedId) return;
    setBusy(true);
    try {
      if (approveAction) {
        const res = await approve(pending.threadId);
        setStatusLine(res.reply);
      } else {
        setStatusLine("Rejected — nothing was recorded.");
      }
      setPending(null);
      await loadHistory(selectedId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "approval failed");
    } finally {
      setBusy(false);
    }
  }

  const options = isShipper
    ? requests.map((r) => ({ id: r.id, label: `${r.origin_city} → ${r.destination_city} (${r.status})` }))
    : Array.from(new Map(offers.map((o) => [o.request_id, o])).values())
        .filter((o) => o.request_id)
        .map((o) => ({ id: o.request_id!, label: `${o.request_id} — ${o.origin_city || "?"} → ${o.destination_city || "?"} (${o.status})` }));

  return (
    <div className="space-y-5">
      <PageHeader title="Negotiations" subtitle="Offers and counter-offers — recorded only with human approval." />
      {error && <div className="text-xs text-red-500">{error}</div>}
      {statusLine && <div className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">{statusLine}</div>}

      <Card className="p-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Select a request</div>
        <div className="flex flex-wrap gap-2">
          {options.length === 0 && <span className="text-xs text-slate-500">No requests available to negotiate on.</span>}
          {options.map((o) => (
            <button
              key={o.id}
              onClick={() => select(o.id)}
              className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg border transition-colors ${
                selectedId === o.id
                  ? "border-navy-700 bg-navy-900 text-white"
                  : "border-slate-300 text-slate-600 hover:border-navy-400"
              }`}
            >
              <Handshake size={13} />
              {o.label}
            </button>
          ))}
        </div>
      </Card>

      {selectedId && (
        <>
          <Card className="p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Counter-offer</div>
            <div className="flex flex-wrap items-center gap-2">
              <input
                className="w-40 bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500"
                type="number"
                placeholder="Amount ₹"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <button
                onClick={sendCounter}
                disabled={busy || !amount || pending !== null}
                className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-disha-600 text-white hover:bg-disha-500 disabled:opacity-40"
              >
                {busy ? <Loader2 size={15} className="animate-spin" /> : null}
                Propose counter-offer (needs approval)
              </button>
            </div>
            {pending && (
              <div className="mt-3">
                <ApprovalCard action={pending.action} threadId={pending.threadId} busy={busy} onApprove={() => resolveApproval(true)} onReject={() => resolveApproval(false)} onSpeak={() => {}} />
              </div>
            )}
          </Card>

          <Card>
            {history === null ? (
              <EmptyState title="Loading history…" />
            ) : history.length === 0 ? (
              <EmptyState title="No negotiations yet" hint="Propose a counter-offer above." />
            ) : (
              <div className="divide-y divide-slate-100">
                {history.map((n) => (
                  <div key={n.id} className="p-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-navy-900">
                        ₹{Number(n.amount_inr).toLocaleString("en-IN")}
                        <span className="ml-2 text-xs font-normal text-slate-500">{n.message}</span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-400 mt-1">{n.id} · {n.party_user_id}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{new Date(n.created_at).toLocaleString()}</div>
                    </div>
                    <Badge tone={n.status === "counter" ? "orange" : n.status === "accepted" ? "emerald" : "slate"}>{n.status}</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
