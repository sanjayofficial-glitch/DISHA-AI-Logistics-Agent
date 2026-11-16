import { useEffect, useState } from "react";
import { getToken, getUser, saveSession, clearSession, DemoUser } from "./lib/api";
import { DemoLogin } from "./components/DemoLogin";
import { ChatView } from "./components/ChatView";
import { CommandCenter } from "./components/CommandCenter";
import { ShipperPortal } from "./components/ShipperPortal";
import { TruckerPortal } from "./components/TruckerPortal";
import { DemoBadge } from "./components/DemoBadge";
import { Bot, Command, Truck, PackageSearch, LogOut } from "lucide-react";

type Tab = "chat" | "command" | "shipper" | "trucker";

export default function App() {
  const [user, setUser] = useState<DemoUser | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (getToken() && getUser()) {
      setUser(getUser());
    }
    setReady(true);
  }, []);

  if (!ready) return null;

  if (!user) {
    return (
      <DemoLogin
        onLogin={(token, u) => {
          saveSession(token, u);
          setUser(u);
        }}
      />
    );
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "chat", label: "Disha Chat", icon: <Bot size={16} /> },
    { id: "command", label: "Command Center", icon: <Command size={16} /> },
    { id: "shipper", label: "Shipper Portal", icon: <PackageSearch size={16} /> },
    { id: "trucker", label: "Trucker Portal", icon: <Truck size={16} /> },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-disha-500 to-disha-700 flex items-center justify-center text-white font-black">
              D
            </div>
            <div className="leading-tight">
              <div className="font-bold text-sm">DISHA</div>
              <div className="text-[11px] text-slate-400">LoadSaathi AI Agent</div>
            </div>
            <DemoBadge className="ml-2" />
          </div>
          <div className="flex items-center gap-1 text-xs overflow-x-auto">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
                  tab === t.id
                    ? "bg-disha-600/20 text-disha-500 border border-disha-600/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400 hidden sm:inline">{user.display_name}</span>
            <button
              onClick={() => {
                clearSession();
                setUser(null);
              }}
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800"
              title="Log out"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6">
        {tab === "chat" && <ChatView />}
        {tab === "command" && <CommandCenter />}
        {tab === "shipper" && <ShipperPortal />}
        {tab === "trucker" && <TruckerPortal />}
      </main>
    </div>
  );
}
