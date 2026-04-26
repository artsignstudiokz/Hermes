import { Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { TitleBar } from "@/components/titlebar/TitleBar";
import { SplashScreen } from "@/components/splash/SplashScreen";
import { AppShell } from "@/components/layout/AppShell";
import { Unlock } from "@/pages/Unlock";
import { Onboarding } from "@/pages/Onboarding";
import { Dashboard } from "@/pages/Dashboard";
import { Brokers } from "@/pages/Brokers";
import { Strategy } from "@/pages/Strategy";
import { Trades } from "@/pages/Trades";
import { Backtest } from "@/pages/Backtest";
import { Optimize } from "@/pages/Optimize";
import { Logs } from "@/pages/Logs";
import { MobileLink } from "@/pages/MobileLink";
import { Notifications } from "@/pages/Notifications";
import { Settings } from "@/pages/Settings";
import { About } from "@/pages/About";
import { api } from "@/lib/api";

interface AuthState {
  first_run: boolean;
  locked: boolean;
}

export default function App() {
  const [bootState, setBootState] = useState<"splash" | "ready">("splash");
  const [auth, setAuth] = useState<AuthState | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const s = await api.get<AuthState>("/api/auth/state");
        if (active) {
          setAuth(s);
          await new Promise((r) => setTimeout(r, 700));
          if (active) setBootState("ready");
        }
      } catch {
        setTimeout(() => location.reload(), 1500);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (bootState === "splash" || !auth) {
    return (
      <div className="flex min-h-screen flex-col bg-background">
        <TitleBar />
        <SplashScreen />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TitleBar />
      <Suspense fallback={<SplashScreen />}>
        <Routes>
          {auth.first_run ? (
            <>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="*" element={<Navigate to="/onboarding" replace />} />
            </>
          ) : auth.locked ? (
            <>
              <Route
                path="/unlock"
                element={<Unlock onUnlocked={() => setAuth({ ...auth, locked: false })} />}
              />
              <Route path="*" element={<Navigate to="/unlock" replace />} />
            </>
          ) : (
            <Route element={<AppShell />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/brokers" element={<Brokers />} />
              <Route path="/strategy" element={<Strategy />} />
              <Route path="/trades" element={<Trades />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/optimize" element={<Optimize />} />
              <Route path="/mobile" element={<MobileLink />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/about" element={<About />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          )}
        </Routes>
      </Suspense>
    </div>
  );
}
