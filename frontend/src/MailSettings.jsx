import React, { useState, useEffect } from "react";
import { Badge, useLoad, useAction, useUI, Field } from "./ui.jsx";
import { post, put, del } from "./lib.js";

const Pw = ({ has, value, onChange, onClear, testid, label }) => (
  <Field label={label}>
    <div className="row"><input type="password" autoComplete="new-password" value={value} onChange={(e) => onChange(e.target.value)} placeholder={has ? "•••••••• salvata (scrivi per sostituirla)" : "Non inserita"} data-testid={testid} />
      {has && <button type="button" className="btn sm ghost" onClick={onClear} data-testid={`${testid}-clear`}>Rimuovi</button>}</div>
  </Field>
);

function TestBox({ me, ready }) {
  const [to, setTo] = useState(me.email);
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (provider) => { setBusy(true); setRes(null); try { setRes({ ...(await post("/admin/mail-test", { to, provider })), provider }); } finally { setBusy(false); ready(); } };
  return (
    <div className="card" data-testid="mail-test-card"><h3 style={{ marginBottom: 6 }}>Email di prova</h3>
      <p className="small muted" style={{ marginBottom: 10 }}>Salva prima le impostazioni, poi invia una prova. Se la prova generale riesce, la conferma email dei nuovi affiliati si attiva in automatico.</p>
      <Field label="Invia a"><input type="email" value={to} onChange={(e) => setTo(e.target.value)} data-testid="mail-test-to" /></Field>
      <div className="row" style={{ marginTop: 10, flexWrap: "wrap" }}>
        <button className="btn primary" disabled={busy} onClick={() => run("")} data-testid="mail-test-send">{busy ? "Invio in corso…" : "Invia email di prova"}</button>
        <button className="btn sm" disabled={busy} onClick={() => run("aruba")} data-testid="mail-test-aruba">Prova solo Aruba</button>
        <button className="btn sm" disabled={busy} onClick={() => run("brevo")} data-testid="mail-test-brevo">Prova solo Brevo</button>
      </div>
      {res && <div className={`note ${res.ok ? "ok" : "bad"} small`} style={{ marginTop: 12 }} data-testid="mail-test-result">
        {res.ok ? <>Email inviata con <b>{res.provider === "aruba" ? "Aruba" : "Brevo"}</b> a {to}. Controlla la casella (anche lo spam).</> : <>Invio non riuscito.</>}
        {res.errors?.length > 0 && <ul style={{ margin: "6px 0 0 16px" }}>{res.errors.map((e) => <li key={e} className="mono">{e}</li>)}</ul>}
      </div>}
    </div>
  );
}

export default function MailSettings({ me }) {
  const [d, reload] = useLoad("/admin/mail-settings");
  const [f, setF] = useState(null);
  const act = useAction();
  const { ask } = useUI();
  useEffect(() => { if (d) setF({ arubaHost: d.arubaHost, arubaPort: d.arubaPort, arubaUser: d.arubaUser, fromName: d.fromName, brevoSender: d.brevoSender, verificaEmail: d.verificaEmail, arubaPassword: "", brevoKey: "" }); }, [d]);
  if (!d || !f) return null;
  const I = (k, l, t = "text", ph = "") => <Field label={l}><input type={t} value={f[k]} placeholder={ph} onChange={(e) => setF({ ...f, [k]: t === "number" ? Number(e.target.value) : e.target.value })} data-testid={`mail-${k}`} /></Field>;
  const save = () => act(() => put("/admin/mail-settings", f), "Impostazioni email salvate").then((r) => r && reload());
  const clear = async (k, l) => { if (await ask({ title: `Rimuovere ${l}?`, danger: true, ok: "Rimuovi" })) act(() => del(`/admin/mail-settings/${k}`), "Rimossa").then((r) => r && reload()); };
  const S = d.status;
  return (
    <div className="sch-grid" data-testid="mail-settings">
      <div className="card"><div className="row between" style={{ marginBottom: 10 }}><h3>Aruba (invio principale)</h3><Badge k={S.aruba ? "ok" : "warn"} data-testid="mail-status-aruba">{S.aruba ? "Configurato" : "Da configurare"}</Badge></div>
        <div style={{ display: "grid", gap: 12 }}>
          <div className="grid2">{I("arubaHost", "Server SMTP", "text", "smtps.aruba.it")}{I("arubaPort", "Porta", "number")}</div>
          {I("arubaUser", "Utente (indirizzo email Aruba)", "email", "info@tuodominio.it")}
          <Pw label="Password della casella" has={d.hasArubaPassword} value={f.arubaPassword} onChange={(v) => setF({ ...f, arubaPassword: v })} onClear={() => clear("arubaPassword", "la password Aruba")} testid="mail-arubaPassword" />
          {I("fromName", "Nome mittente", "text", "Rete Agenzie Alpimo")}
          <p className="small muted">Porta 465 = SSL (consigliata per Aruba), 587 = STARTTLS.</p>
        </div></div>
      <div className="card"><div className="row between" style={{ marginBottom: 10 }}><h3>Brevo (riserva automatica)</h3><Badge k={S.brevo ? "ok" : "neutral"} data-testid="mail-status-brevo">{S.brevo ? "Configurato" : "Facoltativo"}</Badge></div>
        <div style={{ display: "grid", gap: 12 }}>
          <Pw label="Chiave API Brevo" has={d.hasBrevoKey} value={f.brevoKey} onChange={(v) => setF({ ...f, brevoKey: v })} onClear={() => clear("brevoKey", "la chiave Brevo")} testid="mail-brevoKey" />
          {I("brevoSender", "Email mittente verificata su Brevo", "email", f.arubaUser || "info@tuodominio.it")}
          <p className="small muted">Se Aruba non risponde, l'email parte con Brevo. La chiave si crea su Brevo in «SMTP & API &gt; API Keys».</p>
        </div>
        <label className="chk" style={{ marginTop: 14 }}><input type="checkbox" checked={f.verificaEmail} onChange={(e) => setF({ ...f, verificaEmail: e.target.checked })} data-testid="mail-verificaEmail" />Chiedi ai nuovi affiliati di confermare l'email con un codice</label>
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}><button className="btn primary" onClick={save} data-testid="mail-save">Salva impostazioni email</button></div>
      </div>
      <TestBox me={me} ready={reload} />
    </div>
  );
}
