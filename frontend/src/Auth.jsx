import React, { useState } from "react";
import { Scene, Ico, useUI, Field } from "./ui.jsx";
import { post, get } from "./lib.js";

export async function showLegal(openModal, which) {
  const L = await get("/auth/legal");
  openModal({ title: which === "privacy" ? "Informativa privacy" : "Contratto di affiliazione", wide: true, noCancel: true, ok: "Chiudi",
    body: <div className="pre" data-testid="legal-text">{which === "privacy" ? L.privacy : L.contratto}</div>, text: `Versione ${L.versione}`, res: () => {} });
}

function Art() {
  return (
    <div className="auth-art">
      <Scene id="auth" />
      <div>
        <div className="brand" style={{ color: "#fff" }}><img src="/logo-mark.png" alt="" className="brand-mark" />Alpimo · Rete Agenzie</div>
      </div>
      <div>
        <h1>Il sito della tua agenzia, pronto al decollo.</h1>
        <p>Registrati, scegli dominio e logo, segui la realizzazione e cresci con i corsi dell'Academy.</p>
        <div className="steps">
          {["Inserisci i dati della tua agenzia", "Scegli URL e logo", "Paga con bonifico e carica la ricevuta", "Ricevi il sito pronto da personalizzare"].map((t, i) => (
            <div key={i}><span>{i + 1}</span>{t}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AuthScreen({ onAuth }) {
  const [tab, setTab] = useState("login");
  const [f, setF] = useState({ email: "", password: "", password2: "", tipo: "persona", contratto: false, privacy: false, marketing: false, code: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const { openModal, toast } = useUI();
  const s = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const run = async (fn) => { setErr(""); setBusy(true); try { await fn(); } catch (e) { setErr(e.message); } setBusy(false); };
  const login = (e) => { e.preventDefault(); run(async () => { await post("/auth/login", { email: f.email, password: f.password }); onAuth(); }); };
  const register = (e) => {
    e.preventDefault();
    if (f.password.length < 8) return setErr("La password deve avere almeno 8 caratteri");
    if (f.password !== f.password2) return setErr("Le password non coincidono");
    if (!f.contratto || !f.privacy) return setErr("Accetta contratto e informativa privacy per continuare");
    run(async () => { await post("/auth/register", f); onAuth(); });
  };
  const forgot = (e) => { e.preventDefault(); run(async () => { await post("/auth/forgot", { email: f.email }); setTab("reset"); toast("Se l'email è registrata, riceverai un codice"); }); };
  const reset = (e) => {
    e.preventDefault();
    if (f.password !== f.password2) return setErr("Le password non coincidono");
    run(async () => { await post("/auth/reset", { email: f.email, code: f.code, password: f.password }); toast("Password aggiornata: ora puoi accedere"); setTab("login"); });
  };
  const pw2 = <Field label="Conferma password"><input type="password" data-testid="auth-password2" value={f.password2} onChange={s("password2")} required /></Field>;
  return (
    <div className="auth" data-testid="auth-screen">
      <Art />
      <div className="auth-form">
        <div className="auth-box">
          <img src="/logo-alpimo.png" alt="Alpimo – Affiliazione per agenzie di viaggi" className="auth-logo" data-testid="auth-logo" />
          <div className="tag"><Ico n="plane" s={14} />Portale affiliati</div>
          <h2>{tab === "register" ? "Crea il tuo account" : tab === "login" ? "Bentornato a bordo" : "Recupera la password"}</h2>
          {(tab === "login" || tab === "register") && (
            <div className="tabs">
              <button className={tab === "login" ? "on" : ""} data-testid="tab-login" onClick={() => { setTab("login"); setErr(""); }}>Accedi</button>
              <button className={tab === "register" ? "on" : ""} data-testid="tab-register" onClick={() => { setTab("register"); setErr(""); }}>Registrati</button>
            </div>
          )}
          {tab === "login" && (
            <form onSubmit={login} style={{ display: "grid", gap: 12 }}>
              <Field label="Email"><input type="email" data-testid="auth-email" value={f.email} onChange={s("email")} required /></Field>
              <Field label="Password"><input type="password" data-testid="auth-password" value={f.password} onChange={s("password")} required /></Field>
              <div className="auth-links"><a href="#forgot" data-testid="forgot-link" onClick={(e) => { e.preventDefault(); setTab("forgot"); setErr(""); }}>Password dimenticata?</a></div>
              <div className="err" data-testid="auth-error">{err}</div>
              <button className="btn primary" style={{ justifyContent: "center" }} disabled={busy} data-testid="login-submit">Accedi</button>
            </form>
          )}
          {tab === "register" && (
            <form onSubmit={register} style={{ display: "grid", gap: 12 }}>
              <div className="seg">
                <label><input type="radio" name="tipo" checked={f.tipo === "persona"} onChange={() => setF({ ...f, tipo: "persona" })} data-testid="reg-tipo-persona" />Persona fisica</label>
                <label><input type="radio" name="tipo" checked={f.tipo === "azienda"} onChange={() => setF({ ...f, tipo: "azienda" })} data-testid="reg-tipo-azienda" />Azienda</label>
              </div>
              <Field label="Email"><input type="email" data-testid="auth-email" value={f.email} onChange={s("email")} required /></Field>
              <Field label="Password (minimo 8 caratteri)"><input type="password" data-testid="auth-password" value={f.password} onChange={s("password")} required /></Field>
              {pw2}
              <label className="chk"><input type="checkbox" checked={f.contratto} onChange={s("contratto")} data-testid="reg-contratto" /><span>Accetto il <a href="#c" onClick={(e) => { e.preventDefault(); showLegal(openModal, "contratto"); }} data-testid="link-contratto">contratto di affiliazione</a> *</span></label>
              <label className="chk"><input type="checkbox" checked={f.privacy} onChange={s("privacy")} data-testid="reg-privacy" /><span>Ho letto l'<a href="#p" onClick={(e) => { e.preventDefault(); showLegal(openModal, "privacy"); }} data-testid="link-privacy">informativa privacy</a> *</span></label>
              <label className="chk"><input type="checkbox" checked={f.marketing} onChange={s("marketing")} data-testid="reg-marketing" /><span>Acconsento a ricevere comunicazioni marketing (facoltativo)</span></label>
              <div className="err" data-testid="auth-error">{err}</div>
              <button className="btn accent" style={{ justifyContent: "center" }} disabled={busy} data-testid="register-submit">Crea account</button>
            </form>
          )}
          {tab === "forgot" && (
            <form onSubmit={forgot} style={{ display: "grid", gap: 12, marginTop: 14 }}>
              <p className="muted">Inserisci la tua email: ti invieremo un codice di 6 cifre valido 30 minuti.</p>
              <Field label="Email"><input type="email" data-testid="auth-email" value={f.email} onChange={s("email")} required /></Field>
              <div className="err" data-testid="auth-error">{err}</div>
              <button className="btn primary" style={{ justifyContent: "center" }} disabled={busy} data-testid="forgot-submit">Invia codice</button>
              <button type="button" className="back" onClick={() => setTab("login")} data-testid="back-login">← Torna all'accesso</button>
            </form>
          )}
          {tab === "reset" && (
            <form onSubmit={reset} style={{ display: "grid", gap: 12, marginTop: 14 }}>
              <Field label="Codice ricevuto via email"><input type="text" className="otp" maxLength={6} data-testid="reset-code" value={f.code} onChange={s("code")} required /></Field>
              <Field label="Nuova password"><input type="password" data-testid="auth-password" value={f.password} onChange={s("password")} required /></Field>
              {pw2}
              <div className="err" data-testid="auth-error">{err}</div>
              <button className="btn primary" style={{ justifyContent: "center" }} disabled={busy} data-testid="reset-submit">Imposta nuova password</button>
              <button type="button" className="back" onClick={() => setTab("login")}>← Torna all'accesso</button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

export function VerifyScreen({ user, onDone, logout }) {
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");
  const { toast } = useUI();
  const go = async (e) => { e.preventDefault(); setErr(""); try { await post("/auth/verify", { code }); toast("Email verificata!"); onDone(); } catch (x) { setErr(x.message); } };
  return (
    <div className="wrap">
      <div className="card gate" data-testid="verify-screen">
        <div className="gate-ico"><Ico n="mail" s={28} /></div>
        <h2>Conferma la tua email</h2>
        <p className="muted">Abbiamo inviato un codice di 6 cifre a <b>{user.email}</b>. È valido 24 ore.</p>
        <form onSubmit={go} style={{ display: "grid", gap: 12, justifyItems: "center", marginTop: 16 }}>
          <input type="text" className="otp" maxLength={6} value={code} onChange={(e) => setCode(e.target.value)} data-testid="verify-code" placeholder="000000" />
          <div className="err" data-testid="verify-error">{err}</div>
          <button className="btn primary" data-testid="verify-submit">Verifica</button>
        </form>
        <div className="row" style={{ justifyContent: "center", marginTop: 14 }}>
          <button className="btn sm" data-testid="verify-resend" onClick={async () => { await post("/auth/resend"); toast("Nuovo codice inviato"); }}>Reinvia codice</button>
          <button className="btn sm ghost" onClick={logout} data-testid="logout-btn">Esci</button>
        </div>
      </div>
    </div>
  );
}

export function TermsGate({ onDone, logout }) {
  const [ok, setOk] = useState({ c: false, p: false });
  const { openModal } = useUI();
  return (
    <div className="wrap">
      <div className="card gate" data-testid="terms-gate">
        <div className="gate-ico"><Ico n="file" s={28} /></div>
        <h2>Abbiamo aggiornato i termini</h2>
        <p className="muted">Per continuare a usare il portale leggi e accetta la nuova versione di contratto e informativa privacy.</p>
        <div style={{ textAlign: "left", margin: "16px auto", maxWidth: 380 }}>
          <label className="chk"><input type="checkbox" checked={ok.c} onChange={(e) => setOk({ ...ok, c: e.target.checked })} data-testid="terms-contratto" /><span>Accetto il <a href="#c" onClick={(e) => { e.preventDefault(); showLegal(openModal, "contratto"); }}>contratto di affiliazione</a></span></label>
          <label className="chk"><input type="checkbox" checked={ok.p} onChange={(e) => setOk({ ...ok, p: e.target.checked })} data-testid="terms-privacy" /><span>Ho letto l'<a href="#p" onClick={(e) => { e.preventDefault(); showLegal(openModal, "privacy"); }}>informativa privacy</a></span></label>
        </div>
        <div className="row" style={{ justifyContent: "center" }}>
          <button className="btn primary" disabled={!ok.c || !ok.p} data-testid="terms-accept" onClick={async () => { await post("/auth/accept-terms"); onDone(); }}>Accetta e continua</button>
          <button className="btn ghost" onClick={logout}>Esci</button>
        </div>
      </div>
    </div>
  );
}
