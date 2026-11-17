import { useCallback, useEffect, useState } from "react";
import { threads, threadEvents, ThreadEvent, notifications, NotificationRow } from "../lib/api";
import { PageHeader, Card, Badge, EmptyState } from "../ui/primitives";

type ActivityItem =
  | { kind: "event"; event: ThreadEvent }
  | { kind: "notification"; note: NotificationRow };

export function ActivityPage() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const tids = await threads();
      const eventItems: ActivityItem[] = [];
      for (const tid of tids.slice(0, 5)) {
        const evs = await threadEvents(tid);
        for (const e of evs) eventItems.push({ kind: "event", event: e });
      }
      const notes = await notifications();
      const noteItems: ActivityItem[] = notes.map((n) => ({ kind: "notification", note: n }));
      const all = [...noteItems, ...eventItems].sort((a, b) => {
        const ta = a.kind === "event" ? a.event.created_at : a.note.created_at;
        const tb = b.kind === "event" ? b.event.created_at : b.note.created_at;
        return tb.localeCompare(ta);
      });
      setItems(all);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load activity");
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 8000);
    return () => clearInterval(t);
  }, [refresh]);

  return (
    <div>
      <PageHeader title="Activity" subtitle="Recorded agent events and notifications — newest first." />
      {error && <div className="mb-4 text-xs text-red-500">{error}</div>}
      <Card>
        {items.length === 0 ? (
          <EmptyState title="No activity yet" hint="Talk to Disha or create a request to see events here." />
        ) : (
          <div className="divide-y divide-slate-100">
            {items.map((it, i) => {
              if (it.kind === "notification") {
                const n = it.note;
                return (
                  <div key={`n-${n.id}-${i}`} className="p-4">
                    <div className="flex items-center gap-2">
                      <Badge tone="navy">notification</Badge>
                      <span className="text-sm font-medium text-navy-900">{n.title}</span>
                      <span className="ml-auto text-xs text-slate-400">{new Date(n.created_at).toLocaleTimeString()}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{n.body}</div>
                  </div>
                );
              }
              const e = it.event;
              return (
                <div key={`e-${e.id}-${i}`} className="p-4">
                  <div className="flex items-center gap-2">
                    <Badge tone={e.status === "error" ? "red" : "slate"}>{e.node}</Badge>
                    <span className="text-[10px] uppercase tracking-wide text-slate-400">{e.status}</span>
                    <span className="ml-auto text-xs text-slate-400">{new Date(e.created_at).toLocaleTimeString()}</span>
                  </div>
                  {e.payload_summary && <div className="text-xs text-slate-600 mt-1.5">{e.payload_summary}</div>}
                  <div className="text-[10px] font-mono text-slate-400 mt-1">{e.thread_id}</div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
