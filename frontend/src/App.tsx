import { Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { TitleBar } from "@/components/titlebar/TitleBar";
import { SplashScreen } from "@/components/splash/SplashScreen";
import { AppShell } from "@/components/layout/AppShell";
import { CommandPalette } from "@/components/ui/CommandPalette";
import { Toaster } from "@/components/ui/Toaster";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Tutorial, shouldShowTutorial } from "@/components/Tutorial/Tutorial";
import { Unlock } from "@/pages/Unlock";
import { Onboarding } from "@/pages/Onboarding";
import { Dashboard } from "@/pages/Dashboard";
import { Brokers } from "@/pages/Brokers";
import { Strategy } from "@/pages/Strategy";
import { Trades } from "@/pages/Trades";
import { Backtest } from "@/pages/Backtest";
import { Optimize } from "@/pages/Optimize";
import { Adaptive } from "@/pages/Adaptive";
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
  // Tutorial visibility - read once on boot. We deliberately don't read
  // localStorage on every render; once dismissed, it stays dismissed for
  // this session even before the flag persists.
  const [tutorialOpen, setTutorialOpen] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const s = await api.get<AuthState>("/api/auth/state");
        if (active) {
          setAuth(s);
          await new Promise((r) => setTimeout(r, 700));
          if (active) {
            setBootState("ready");
            try {
              if (await shouldShowTutorial()) setTutorialOpen(true);
            } catch {
              /* never let tutorial check block app boot */
            }
          }
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
      <Toaster />
      <CommandPalette />
      <ErrorBoundary>
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
              <Route path="/adaptive" element={<Adaptive />} />
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
        {/* Tutorial MUST live inside ErrorBoundary so a bug in its
            spotlight measurement / step indexing doesn't take down
            the whole SPA (that was the white-screen on restart). */}
        <Tutorial open={tutorialOpen} onClose={() => setTutorialOpen(false)} />
      </ErrorBoundary>
    </div>
  );
}
