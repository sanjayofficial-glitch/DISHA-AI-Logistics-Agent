import { useEffect, useState } from "react";
import { getToken, getUser, saveSession, clearSession, DemoUser } from "./lib/api";
import { DemoLogin } from "./components/DemoLogin";
import { AppShell } from "./appShell/AppShell";
import { AuthUserProvider } from "./components/authContext";

export default function App() {
  const [user, setUser] = useState<DemoUser | null>(null);
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

  return (
    <AuthUserProvider value={user}>
      <AppShell
        user={user}
        onLogout={() => {
          clearSession();
          setUser(null);
        }}
      />
    </AuthUserProvider>
  );
}
