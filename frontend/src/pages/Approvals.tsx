import { useCallback, useEffect, useState } from "react";
import { approvals, ApprovalRow, approve, reject } from "../lib/api";
import { PageHeader, Card, Badge, EmptyState } from "../ui/primitives";
import { Check, X, Loader2 } from "lucide-react";

export function ApprovalsPage() {
  const [rows, setRows] = useState<ApprovalRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setRows(await approvals());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load approvals");
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 6000);
    return () => clearInterval(t);
  }, [refresh]);

  async function act(threadId: string, doApprove: boolean) {
    setBusy(true);
    try {
      if (doApprove) await approve(threadId);
      else await reject(threadId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "action failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Approvals" subtitle="Human-in-the-loop — nothing is written until you approve." />
      {error && <div className="mb-4 text-xs text-red-500">{error}</div>}
      <Card>
        {rows.length === 0 ? (
          <EmptyState title="No pending approvals" hint="When Disha prepares an action (request, offer, availability, counter-offer) it appears here." />
        ) : (
          <div className="divide-y divide-slate-100">
            {rows.map((a) => (
              <div key={a.thread_id} className="p-4 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge tone="amber">approval required</Badge>
                    <span className="text-[10px] font-mono text-slate-400">{a.type}</span>
                  </div>
                  <div className="text-sm font-medium text-navy-900 mt-2">{a.summary}</div>
                  <div className="text-[10px] text-slate-400 mt-1">thread {a.thread_id} · {a.created_at}</div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => act(a.thread_id, true)}
                    disabled={busy}
                    className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40"
                  >
                    {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                    Approve
                  </button>
                  <button
                    onClick={() => act(a.thread_id, false)}
                    disabled={busy}
                    className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg border border-slate-300 text-slate-600 hover:border-red-400 hover:text-red-600 disabled:opacity-40"
                  >
                    <X size={13} />
                    Reject
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
