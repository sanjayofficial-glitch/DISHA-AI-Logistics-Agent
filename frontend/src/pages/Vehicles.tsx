import { useCallback, useEffect, useState } from "react";
import { marketTrips, TripRow, chat, approve } from "../lib/api";
import { PageHeader, Card, Badge, EmptyState, ScoreBar } from "../ui/primitives";
import { ApprovalCard } from "../components/ChatView";
import { Loader2 } from "lucide-react";
import { useAuthUser } from "../components/authContext";
import { PendingAction } from "../lib/api";

export function VehiclesPage() {
  const user = useAuthUser();
  const [trips, setTrips] = useState<TripRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState<string | null>(null);
  const [form, setForm] = useState({ capacity: "14", origin: "Rourkela", destination: "Ranchi", vehicle: "open body" });
  const [pending, setPending] = useState<{ action: PendingAction; threadId: string } | null>(null);

  const refresh = useCallback(async () => {
    try {
      setTrips(await marketTrips());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load vehicles");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function publishAvailability() {
    setBusy(true);
    setStatusLine(null);
    setPending(null);
    try {
      const msg = `I have a ${form.capacity}-tonne ${form.vehicle} available from ${form.origin} to ${form.destination}`;
      const { done } = await chat(msg);
      if (done.status === "needs_input") {
        const confirmMsg = `yes confirm ${form.capacity} tonne vehicle from ${form.origin.toLowerCase()} to ${form.destination.toLowerCase()}`;
        const { done: done2 } = await chat(confirmMsg);
        if (done2.status === "approval_required" && done2.pending_action) {
          setPending({ action: done2.pending_action, threadId: done2.thread_id });
        } else {
          setStatusLine(done2.reply ?? "Request received.");
        }
      } else if (done.status === "approval_required" && done.pending_action) {
        setPending({ action: done.pending_action, threadId: done.thread_id });
      } else {
        setStatusLine(done.reply ?? "Request received.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "publish failed");
    } finally {
      setBusy(false);
    }
  }

  async function resolveApproval(approveAction: boolean) {
    if (!pending) return;
    setBusy(true);
    try {
      if (approveAction) {
        const res = await approve(pending.threadId);
        setStatusLine(res.reply);
      } else {
        setStatusLine("Rejected — nothing was published.");
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
    <div className="space-y-5">
      <PageHeader title="Vehicles" subtitle="Active vehicle availability on the demo marketplace (synthetic)." />
      {error && <div className="text-xs text-red-500">{error}</div>}
      {statusLine && <div className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">{statusLine}</div>}

      {user.role === "transporter" && (
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Publish vehicle availability</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" placeholder="Capacity (t)" value={form.capacity} onChange={(e) => setForm((f) => ({ ...f, capacity: e.target.value }))} />
            <input className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" placeholder="Origin" value={form.origin} onChange={(e) => setForm((f) => ({ ...f, origin: e.target.value }))} />
            <input className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" placeholder="Destination" value={form.destination} onChange={(e) => setForm((f) => ({ ...f, destination: e.target.value }))} />
            <select className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-disha-500" value={form.vehicle} onChange={(e) => setForm((f) => ({ ...f, vehicle: e.target.value }))}>
              <option value="open body">Open body</option>
              <option value="trailer">Trailer</option>
              <option value="covered body">Covered body</option>
            </select>
          </div>
          <button
            onClick={publishAvailability}
            disabled={busy || pending !== null}
            className="mt-3 flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-disha-600 text-white hover:bg-disha-500 disabled:opacity-40"
          >
            {busy ? <Loader2 size={15} className="animate-spin" /> : null}
            Publish (requires approval)
          </button>
          {pending && (
            <div className="mt-3">
              <ApprovalCard action={pending.action} threadId={pending.threadId} busy={busy} onApprove={() => resolveApproval(true)} onReject={() => resolveApproval(false)} onSpeak={() => {}} />
            </div>
          )}
        </Card>
      )}

      <Card>
        {trips.length === 0 ? (
          <EmptyState title="No active vehicles" hint="Publish availability or check the demo seed data." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-slate-500 border-b border-slate-200">
                  <th className="px-4 py-2.5">Vehicle</th>
                  <th className="px-4 py-2.5">Route</th>
                  <th className="px-4 py-2.5">Departure</th>
                  <th className="px-4 py-2.5">Capacity</th>
                  <th className="px-4 py-2.5">Rate</th>
                  <th className="px-4 py-2.5">Reliability</th>
                  <th className="px-4 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {trips.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="font-mono text-xs text-slate-400">{t.id}</div>
                      <div className="capitalize text-navy-900 font-medium">{t.vehicle_type}</div>
                    </td>
                    <td className="px-4 py-3">{t.origin_city} → {t.destination_city}</td>
                    <td className="px-4 py-3">{t.departure_date || "—"}</td>
                    <td className="px-4 py-3">{t.capacity_tonnes != null ? `${t.capacity_tonnes}t` : "—"}</td>
                    <td className="px-4 py-3">{t.price_per_tonne != null ? `₹${Number(t.price_per_tonne).toLocaleString("en-IN")}/t` : "—"}</td>
                    <td className="px-4 py-3 w-32">
                      <ScoreBar label="reliability" score={t.reliability_score ?? 0} />
                    </td>
                    <td className="px-4 py-3"><Badge tone="navy">{t.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
