import { useCallback, useEffect, useState } from "react";
import { PageHeader, Card, Badge, EmptyState } from "../ui/primitives";
import { useAuthUser } from "../components/authContext";
import { useNav } from "../appShell/AppShell";
import { Info, ShieldCheck, Volume2, Trash2, Brain } from "lucide-react";
import { listFacts, deleteFact, Fact } from "../lib/api";

export function SettingsPage() {
  const user = useAuthUser();
  const { setSection } = useNav();
  const apiUrl = (import.meta.env.VITE_DISHA_API_URL as string | undefined) ?? "http://127.0.0.1:8000";
  const [facts, setFacts] = useState<Fact[]>([]);

  const loadFacts = useCallback(async () => {
    try {
      setFacts(await listFacts());
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    loadFacts();
  }, [loadFacts]);

  async function removeFact(id: string) {
    try {
      await deleteFact(id);
      await loadFacts();
    } catch { /* ignore */ }
  }

  return (
    <div className="space-y-5">
      <PageHeader title="Settings" subtitle="Demo account, preferences and data honesty." />

      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Account</div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Display name</span><span className="font-medium text-navy-900">{user.display_name}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">User id</span><span className="font-mono text-xs">{user.user_id}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Role</span><Badge tone="navy">{user.role}</Badge></div>
            <div className="flex justify-between"><span className="text-slate-500">API base</span><span className="font-mono text-xs">{apiUrl}</span></div>
          </div>
          <button
            onClick={() => setSection("overview")}
            className="mt-4 text-xs text-slate-500 hover:text-navy-900 underline"
          >
            Return to overview
          </button>
        </Card>

        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Preferences</div>
          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <Volume2 size={15} className="text-slate-400 mt-0.5" />
              <div>
                <div className="font-medium text-navy-900">Voice replies</div>
                <div className="text-xs text-slate-500">Toggle mute inside the AI Assistant (persists in this browser).</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Info size={15} className="text-slate-400 mt-0.5" />
              <div>
                <div className="font-medium text-navy-900">Data source</div>
                <div className="text-xs text-slate-500">Everything on this platform is synthetic demo data — no real bookings, carriers or market data.</div>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <ShieldCheck size={15} className="text-slate-400 mt-0.5" />
              <div>
                <div className="font-medium text-navy-900">Human approval</div>
                <div className="text-xs text-slate-500">Every write action (requests, offers, availability, counter-offers, confirmations) waits for explicit approval — no API keys are stored in this app.</div>
              </div>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">Memory (your facts)</div>
          <div className="flex items-start gap-2 mb-3">
            <Brain size={15} className="text-slate-400 mt-0.5" />
            <div>
              <div className="font-medium text-navy-900">Stored preferences</div>
              <div className="text-xs text-slate-500">Only facts you explicitly asked DISHA to remember. You can delete any of them here.</div>
            </div>
          </div>
          {facts.length === 0 ? (
            <EmptyState title="No facts stored" hint='Say "remember that …" in the AI Assistant to add one.' />
          ) : (
            <ul className="space-y-2">
              {facts.map((f) => (
                <li key={f.id} className="flex items-start justify-between gap-3 text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                  <span className="text-navy-900">{f.text}</span>
                  <button onClick={() => removeFact(f.id)} className="text-slate-400 hover:text-red-600" title="Delete fact">
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
