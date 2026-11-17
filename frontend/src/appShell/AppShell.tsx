/** DISHA Command Center shell — navy sidebar + top bar + mobile drawer. */
import { createContext, useContext, useState, ReactNode } from "react";
import {
  LayoutDashboard,
  Bot,
  PackageSearch,
  Truck,
  Route,
  IndianRupee,
  Handshake,
  ShieldCheck,
  Activity,
  Settings,
  Menu,
  X,
  LogOut,
} from "lucide-react";
import { DemoUser } from "../lib/api";
import { DemoBadge } from "../components/DemoBadge";
import { OverviewPage } from "../pages/Overview";
import { AiAssistantPage } from "../pages/AiAssistant";
import { ShipmentsPage } from "../pages/Shipments";
import { VehiclesPage } from "../pages/Vehicles";
import { MatchingPage } from "../pages/Matching";
import { PricingPage } from "../pages/Pricing";
import { NegotiationsPage } from "../pages/Negotiations";
import { ApprovalsPage } from "../pages/Approvals";
import { ActivityPage } from "../pages/Activity";
import { SettingsPage } from "../pages/Settings";

export type Section =
  | "overview"
  | "assistant"
  | "shipments"
  | "vehicles"
  | "matching"
  | "pricing"
  | "negotiations"
  | "approvals"
  | "activity"
  | "settings";

const SECTIONS: { id: Section; label: string; icon: ReactNode }[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard size={16} /> },
  { id: "assistant", label: "AI Assistant", icon: <Bot size={16} /> },
  { id: "shipments", label: "Shipments", icon: <PackageSearch size={16} /> },
  { id: "vehicles", label: "Vehicles", icon: <Truck size={16} /> },
  { id: "matching", label: "Matching", icon: <Route size={16} /> },
  { id: "pricing", label: "Pricing", icon: <IndianRupee size={16} /> },
  { id: "negotiations", label: "Negotiations", icon: <Handshake size={16} /> },
  { id: "approvals", label: "Approvals", icon: <ShieldCheck size={16} /> },
  { id: "activity", label: "Activity", icon: <Activity size={16} /> },
  { id: "settings", label: "Settings", icon: <Settings size={16} /> },
];

interface NavCtx {
  section: Section;
  setSection: (s: Section) => void;
}
const NavContext = createContext<NavCtx>({ section: "overview", setSection: () => {} });

export function useNav() {
  return useContext(NavContext);
}

function SectionView({ section }: { section: Section }) {
  switch (section) {
    case "overview": return <OverviewPage />;
    case "assistant": return <AiAssistantPage />;
    case "shipments": return <ShipmentsPage />;
    case "vehicles": return <VehiclesPage />;
    case "matching": return <MatchingPage />;
    case "pricing": return <PricingPage />;
    case "negotiations": return <NegotiationsPage />;
    case "approvals": return <ApprovalsPage />;
    case "activity": return <ActivityPage />;
    case "settings": return <SettingsPage />;
  }
}

function NavList({ section, onSelect }: { section: Section; onSelect: (s: Section) => void }) {
  return (
    <nav className="space-y-1">
      {SECTIONS.map((s) => (
        <button
          key={s.id}
          onClick={() => onSelect(s.id)}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
            section === s.id
              ? "bg-navy-700 text-white font-semibold"
              : "text-navy-100/70 hover:text-white hover:bg-navy-800"
          }`}
        >
          {s.icon}
          {s.label}
        </button>
      ))}
    </nav>
  );
}

export function AppShell({ user, onLogout }: { user: DemoUser; onLogout: () => void }) {
  const [section, setSection] = useState<Section>("overview");
  const [drawer, setDrawer] = useState(false);

  const go = (s: Section) => {
    setSection(s);
    setDrawer(false);
  };

  return (
    <NavContext.Provider value={{ section, setSection: go }}>
      <div className="min-h-screen bg-slate-50 text-slate-800 flex">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex w-60 shrink-0 flex-col bg-navy-950 text-white">
          <div className="h-16 flex items-center gap-2.5 px-4 border-b border-navy-800">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-disha-500 to-disha-700 flex items-center justify-center text-white font-black">
              D
            </div>
            <div className="leading-tight">
              <div className="font-bold text-sm">DISHA</div>
              <div className="text-[11px] text-navy-200/70">Logistics Command Center</div>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <NavList section={section} onSelect={go} />
          </div>
          <div className="p-3 border-t border-navy-800">
            <div className="flex items-center justify-between gap-2 px-2 py-1.5">
              <div className="min-w-0">
                <div className="text-xs font-semibold truncate">{user.display_name}</div>
                <div className="text-[10px] uppercase text-navy-200/60">{user.role}</div>
              </div>
              <button onClick={onLogout} title="Log out" className="p-1.5 rounded-lg text-navy-200/70 hover:text-white hover:bg-navy-800">
                <LogOut size={15} />
              </button>
            </div>
          </div>
        </aside>

        {/* Mobile drawer */}
        {drawer && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <div className="absolute inset-0 bg-black/50" onClick={() => setDrawer(false)} />
            <div className="absolute inset-y-0 left-0 w-64 bg-navy-950 text-white flex flex-col">
              <div className="h-16 flex items-center justify-between px-4 border-b border-navy-800">
                <div className="font-bold text-sm">DISHA</div>
                <button onClick={() => setDrawer(false)} className="p-1.5 rounded-lg text-navy-200/70 hover:text-white">
                  <X size={18} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-3">
                <NavList section={section} onSelect={go} />
              </div>
            </div>
          </div>
        )}

        {/* Main column */}
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-16 flex items-center gap-3 px-4 border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-30">
            <button className="lg:hidden p-2 rounded-lg hover:bg-slate-100" onClick={() => setDrawer(true)}>
              <Menu size={20} />
            </button>
            <div className="lg:hidden flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-disha-500 to-disha-700 flex items-center justify-center text-white text-xs font-black">D</div>
              <span className="font-bold text-sm">DISHA</span>
            </div>
            <div className="flex-1" />
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-500">
              <span>{user.display_name}</span>
              <span className="text-slate-300">·</span>
              <span className="uppercase text-[10px]">{user.role}</span>
            </div>
            <DemoBadge />
          </header>

          <main className="flex-1 w-full max-w-[1440px] mx-auto px-4 py-6">
            <SectionView section={section} />
          </main>
        </div>
      </div>
    </NavContext.Provider>
  );
}
