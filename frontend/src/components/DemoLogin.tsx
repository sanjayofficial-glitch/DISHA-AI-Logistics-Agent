import { useState } from "react";
import { apiJson } from "../lib/api";
import { Bot } from "lucide-react";

interface Props {
  onLogin: (token: string, user: { user_id: string; display_name: string; role: "shipper" | "transporter" }) => void;
}

const DEMO_ACCOUNTS = [
  { user_id: "demo-shipper-01", display_name: "Demo Shipper 01", role: "shipper" as const },
  { user_id: "demo-transporter-01", display_name: "Demo Transporter 01", role: "transporter" as const },
  { user_id: "demo-transporter-02", display_name: "Demo Transporter 02", role: "transporter" as const },
  { user_id: "demo-shipper-02", display_name: "Demo Shipper 02", role: "shipper" as const },
];

export function DemoLogin({ onLogin }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function login(account: { user_id: string; display_name: string; role: "shipper" | "transporter" }) {
    setBusy(true);
    setError(null);
    try {
      const data = await apiJson<{ token: string }>("/auth/demo-login", {
        method: "POST",
        body: JSON.stringify({ user_id: account.user_id, display_name: account.display_name }),
      });
      onLogin(data.token, account);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-disha-500 to-disha-700 flex items-center justify-center text-white">
            <Bot size={22} />
          </div>
          <div>
            <h1 className="text-xl font-bold">DISHA</h1>
            <p className="text-xs text-slate-400">LoadSaathi AI logistics agent</p>
          </div>
        </div>

        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300 mb-6">
          DEMO MODE — synthetic seed data. No real carriers or bookings. The demo
          backend is at <code className="text-amber-200">127.0.0.1:8000</code>.
        </div>

        <p className="text-sm text-slate-300 mb-3">Sign in as a demo account:</p>
        <div className="space-y-2">
          {DEMO_ACCOUNTS.map((a) => (
            <button
              key={a.user_id}
              disabled={busy}
              onClick={() => login(a)}
              className="w-full flex items-center justify-between px-4 py-3 rounded-xl border border-slate-700 hover:border-disha-600/60 hover:bg-disha-600/10 disabled:opacity-50 transition-colors"
            >
              <span className="font-medium text-sm">{a.display_name}</span>
              <span className="text-[11px] uppercase tracking-wide text-slate-400">{a.role}</span>
            </button>
          ))}
        </div>

        {error && <p className="mt-4 text-xs text-red-400">{error}</p>}
      </div>
    </div>
  );
}
