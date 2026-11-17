import { PageHeader, Card, Badge } from "../ui/primitives";
import { useAuthUser } from "../components/authContext";
import { useNav } from "../appShell/AppShell";
import { Info, ShieldCheck, Volume2 } from "lucide-react";

export function SettingsPage() {
  const user = useAuthUser();
  const { setSection } = useNav();
  const apiUrl = (import.meta.env.VITE_DISHA_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

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
      </div>
    </div>
  );
}
