import React, { useState, useEffect, useCallback } from "react";
import { UIProvider } from "./ui.jsx";
import { get, post } from "./lib.js";
import { AuthScreen, VerifyScreen, TermsGate } from "./Auth.jsx";
import AffApp from "./Aff.jsx";
import AdminApp from "./Admin.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const refresh = useCallback(() => get("/auth/me").then(setUser).catch(() => setUser(false)), []);
  useEffect(() => { refresh(); }, [refresh]);
  const logout = async () => { await post("/auth/logout").catch(() => {}); setUser(false); };
  let body;
  if (user === null) body = <div className="denied muted" data-testid="app-loading">Caricamento…</div>;
  else if (!user) body = <AuthScreen onAuth={refresh} />;
  else if (user.role === "affiliate" && !user.verified) body = <VerifyScreen user={user} onDone={refresh} logout={logout} />;
  else if (user.role === "affiliate" && user.termsOutdated) body = <TermsGate onDone={refresh} logout={logout} />;
  else if (user.role === "affiliate") body = <AffApp user={user} logout={logout} />;
  else body = <AdminApp user={user} logout={logout} />;
  return <UIProvider>{body}</UIProvider>;
}
