import React, { useState } from "react";
import { Ico, Scene, Badge, Bell, useLoad, useAction, useUI, Empty } from "./ui.jsx";
import { post, API, fd, fdt, eur, daysTo, statoInfo, REM, REM_LBL, STEPS, downloadUrl } from "./lib.js";
import Scheda from "./AdminScheda.jsx";
import Tickets from "./Tickets.jsx";
import { AdminCourses } from "./Courses.jsx";
import { AdminNews, AdminMats, Settings } from "./AdminMisc.jsx";

const MENU = [["dashboard", "Panoramica", "home", null], ["richieste", "Richieste", "inbox", "richieste"], ["affiliati", "Affiliati", "users", "affiliati"], ["ticket", "Ticket", "ticket", "ticket"],
  ["corsi", "Corsi", "book", "corsi"], ["bacheca", "Bacheca", "news", "bacheca"], ["materiali", "Materiali", "folder", "materiali"], ["scadenze", "Scadenze domini", "calendar", "scadenze"],
  ["report", "Report", "chart", "report"], ["email", "Registro email", "mail", "email"], ["impostazioni", "Impostazioni", "settings", null]];

export const canP = (u, p) => !p || u.is_super || (u.perms || []).includes(p);

export default function AdminApp({ user, logout }) {
  const [view, setView] = useState("dashboard");
  const [sel, setSel] = useState(null);
  const [ref, setRef] = useState(null);
  const [counts] = useLoad("/admin/counts", [view, sel]);
  const nav = (v, id) => { setView(v); setSel(id || null); setRef(null); };
  const go = (n) => {
    if (n.view === "affiliato" && canP(user, "affiliati")) nav("affiliati", n.ref);
    else if (n.view === "ticket") { setView("ticket"); setSel(null); setRef(n.ref); }
    else if (n.view === "corsi") nav("corsi");
    else if (n.view === "scadenze" && canP(user, "affiliati")) nav("affiliati", n.ref);
    else nav(n.view && MENU.some((m) => m[0] === n.view) ? n.view : "dashboard");
  };
  const cnt = { richieste: counts?.richieste, ticket: counts?.ticket, corsi: counts?.corsi };
  const allowed = MENU.filter((m) => canP(user, m[3]));
  const V = allowed.find((m) => m[0] === view) ? view : "dashboard";
  return (
    <div data-testid="admin-app">
      <div className="top">
        <div className="brand"><i><Ico n="plane" s={18} /></i><span>Portale Affiliati · Admin</span></div>
        <div className="right"><span className="small muted">{user.nome || user.email}</span><Bell onGo={go} /><button className="btn sm" onClick={logout} data-testid="logout-btn"><Ico n="logout" s={15} />Esci</button></div>
      </div>
      <div className="admin">
        <nav className="side" data-testid="admin-sidebar">
          {allowed.map(([k, l, i], idx) => (
            <React.Fragment key={k}>
              {idx === 1 && <div className="sep" />}
              <button className={V === k ? "on" : ""} onClick={() => nav(k)} data-testid={`nav-${k}`}><span className="lb"><Ico n={i} s={17} />{l}</span>{cnt[k] > 0 && <span className="count">{cnt[k]}</span>}</button>
            </React.Fragment>
          ))}
        </nav>
        <main className="amain">
          {V === "dashboard" && <Dash user={user} nav={nav} />}
          {V === "richieste" && <Richieste nav={nav} canOpen={canP(user, "affiliati")} />}
          {V === "affiliati" && (sel ? <Scheda id={sel} user={user} back={() => setSel(null)} /> : <Affiliati nav={nav} />)}
          {V === "ticket" && <><h2 style={{ marginBottom: 16 }}><Ico n="ticket" s={22} />Ticket</h2><Tickets role="admin" initial={ref} /></>}
          {V === "corsi" && <AdminCourses />}
          {V === "bacheca" && <AdminNews />}
          {V === "materiali" && <AdminMats />}
          {V === "scadenze" && <Scadenze nav={nav} canOpen={canP(user, "affiliati")} />}
          {V === "report" && <Report />}
          {V === "email" && <Emails />}
          {V === "impostazioni" && <Settings user={user} />}
        </main>
      </div>
    </div>
  );
}

function Dash({ user, nav }) {
  const [d, reload] = useLoad("/admin/dashboard");
  const act = useAction();
  if (!d) return null;
  const h = new Date().getHours();
  const hi = h < 13 ? "Buongiorno" : h < 18 ? "Buon pomeriggio" : "Buonasera";
  const K = [["richieste", "Richieste in attesa", "inbox", "richieste"], ["ricevute", "Ricevute da verificare", "card", "affiliati"], ["realizzazione", "Siti in realizzazione", "clock", "affiliati"], ["ticket", "Ticket aperti", "ticket", "ticket"], ["domini", "Alert domini", "calendar", "scadenze"]];
  const open = (t) => (t.view ? nav(t.view) : t.k === "richiesta" ? nav("richieste") : nav("affiliati", t.id));
  return (
    <div data-testid="admin-dashboard">
      <div className="dash-hero"><Scene id="dash" wide /><div><p>Panoramica</p><h2>{hi}, {user.nome || "admin"}</h2><span className="sub">Hai {d.todo.length} attività da gestire oggi.</span></div></div>
      {!d.email.aruba && !d.email.brevo && <div className="note warn" style={{ marginTop: 14 }} data-testid="email-not-configured">Invio email non ancora configurato: le email vengono salvate nel Registro email ma non partono. Inserisci le credenziali Aruba (e Brevo come riserva) per attivarlo.</div>}
      <div className="kpis">{K.filter((k) => canP(user, k[3])).map(([k, l, i, v]) => <button key={k} className={`kpi ${d.kpi[k] ? "hot" : ""}`} onClick={() => nav(v)} data-testid={`kpi-${k}`}><span className="ki"><Ico n={i} s={17} /></span><span>{l}</span><b>{d.kpi[k]}</b></button>)}</div>
      <div className="sch-grid">
        <div className="card"><h3 style={{ marginBottom: 8 }}>Da fare</h3>
          {d.todo.length ? d.todo.map((t, i) => <div className="todo" key={i} data-testid="todo-item"><span><span className="dot" style={{ background: t.k === "ticket" ? "var(--accent)" : "var(--primary)" }} />{t.t}</span><button className="btn sm" onClick={() => open(t)}>Apri</button></div>) : <Empty>Tutto in ordine!</Empty>}
        </div>
        <div className="card"><h3 style={{ marginBottom: 8 }}>Domini in scadenza</h3>
          {d.domini.length ? d.domini.map((r) => <div className="todo" key={r.id}><div><b className="mono">{r.url}</b><div className="small muted">{r.nome} · {fd(r.scadenza)} ({daysTo(r.scadenza)} gg)</div></div>
            <button className="btn sm primary" onClick={() => act(() => post(`/admin/affiliates/${r.id}/renew`), "Rinnovo registrato").then((r) => r && reload())} data-testid="dash-renew">Rinnovo pagato</button></div>) : <Empty>Nessun dominio in scadenza nei prossimi 30 giorni.</Empty>}
        </div>
      </div>
    </div>
  );
}

function Richieste({ nav, canOpen }) {
  const [L, reload] = useLoad("/admin/affiliates");
  const act = useAction();
  const { ask } = useUI();
  if (!L) return null;
  const decide = async (r, accept) => {
    const nota = accept ? "" : await ask({ title: `Rifiuta ${r.nome}`, input: "textarea", placeholder: "Motivo del rifiuto (verrà inviato all'affiliato)" });
    if (!accept && !nota) return;
    if (accept && !(await ask({ title: `Accettare ${r.nome}?`, text: "L'affiliato riceverà un'email di conferma." }))) return;
    act(() => post(`/admin/affiliates/${r.id}/decide`, { accept, nota }), accept ? "Richiesta accettata" : "Richiesta rifiutata").then((r) => r && reload());
  };
  const wait = L.filter((r) => r.stato === "in_attesa"), draft = L.filter((r) => r.stato === "bozza"), rej = L.filter((r) => r.stato === "rifiutata");
  return (
    <div data-testid="admin-requests">
      <h2 style={{ marginBottom: 16 }}><Ico n="inbox" s={22} />Richieste</h2>
      <div className="card"><h3>In attesa ({wait.length})</h3>
        {wait.length ? wait.map((r) => <div className="todo" key={r.id} data-testid="request-row"><div><b>{r.nome}</b> · {r.email}<div className="small muted">{r.citta} · URL: {r.urls.filter((u) => u.value).map((u) => u.value).join(", ")} · inviata {fd(r.submittedAt)}</div></div>
          <div className="row">{canOpen && <button className="btn sm" onClick={() => nav("affiliati", r.id)}>Scheda</button>}<button className="btn sm primary" onClick={() => decide(r, true)} data-testid="request-accept">Accetta</button><button className="btn sm danger" onClick={() => decide(r, false)} data-testid="request-reject">Rifiuta</button></div></div>) : <Empty>Nessuna richiesta in attesa.</Empty>}
      </div>
      <div className="card"><h3>Registrati senza dati inviati ({draft.length})</h3>{draft.map((r) => <div className="todo" key={r.id}><span>{r.email} {!r.verified && <Badge k="warn">Email non verificata</Badge>}</span><span className="small muted">{fd(r.createdAt)}</span></div>)}</div>
      <div className="card"><h3>Rifiutate ({rej.length})</h3>{rej.map((r) => <div className="todo" key={r.id}><span><b>{r.nome}</b> · {r.nota}</span><span className="small muted">{r.email}</span></div>)}</div>
    </div>
  );
}

function Affiliati({ nav }) {
  const [L] = useLoad("/admin/affiliates");
  const [C] = useLoad("/admin/companies");
  const [q, setQ] = useState("");
  const [co, setCo] = useState("");
  if (!L) return null;
  const V = L.filter((r) => (!co || (co === "-" ? !r.aziendaId : r.aziendaId === co)) && (!q || `${r.nome} ${r.email} ${r.url} ${r.citta} ${r.azienda} ${r.registrar}`.toLowerCase().includes(q.toLowerCase())));
  return (
    <div data-testid="admin-affiliates">
      <div className="row between" style={{ marginBottom: 16 }}><h2><Ico n="users" s={22} />Affiliati</h2>
        <div className="row">{C && C.length > 0 && <select value={co} onChange={(e) => setCo(e.target.value)} style={{ width: 200 }} data-testid="affiliates-company-filter"><option value="">Tutte le aziende</option>{C.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}<option value="-">Senza azienda</option></select>}
          <input type="text" placeholder="Cerca…" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 240 }} data-testid="affiliates-search" /><button className="btn" onClick={() => downloadUrl(`${API}/admin/export/affiliati`)} data-testid="export-affiliati">Export CSV</button></div></div>
      <div className="card tablewrap"><table className="resp"><thead><tr><th>Agenzia</th><th>Azienda affiliante</th><th>Stato</th><th>Tappa</th><th>URL</th><th>Scadenza dominio</th></tr></thead>
        <tbody>{V.map((r) => { const [l, k] = statoInfo(r); return (
          <tr key={r.id} className="click" onClick={() => nav("affiliati", r.id)} data-testid="affiliate-row"><td data-l="Agenzia"><b>{r.nome}</b><div className="small muted">{r.email}</div></td><td data-l="Azienda affiliante">{r.azienda || "—"}</td><td data-l="Stato"><Badge k={k}>{l}</Badge></td><td data-l="Tappa">{STEPS[r.step]}</td><td data-l="URL"><span className="mono">{r.url || "—"}</span>{r.registrar && <div className="small muted">su {r.registrar}</div>}</td><td data-l="Scadenza">{fd(r.scadenza)}</td></tr>); })}</tbody></table>{!V.length && <Empty>Nessun affiliato corrisponde ai filtri.</Empty>}</div>
    </div>
  );
}

export function RemChips({ r }) {
  const d = r.scadenza ? daysTo(r.scadenza) : null;
  return <div className="reminders">{REM.map((x) => <span key={x} className={`rem ${(r.inviati || []).includes(x) ? (d != null && d <= x && !REM.some((y) => y < x && d <= y) ? "now" : "sent") : ""}`}>{REM_LBL[x]}</span>)}</div>;
}

function Scadenze({ nav, canOpen }) {
  const [L, reload] = useLoad("/admin/domains");
  const act = useAction();
  if (!L) return null;
  return (
    <div data-testid="admin-domains">
      <div className="row between" style={{ marginBottom: 16 }}><h2><Ico n="calendar" s={22} />Scadenze domini</h2><button className="btn" onClick={() => downloadUrl(`${API}/admin/export/scadenze`)}>Export CSV</button></div>
      <div className="card tablewrap"><table className="resp"><thead><tr><th>Dominio</th><th>Scadenza</th><th>Promemoria</th><th /></tr></thead>
        <tbody>{L.map((r) => { const d = daysTo(r.scadenza); return (
          <tr key={r.id} data-testid="domain-row"><td data-l="Dominio"><b className="mono">{r.url}</b> {r.registrar && <Badge k="neutral">{r.registrar}</Badge>}<div className="small muted">{canOpen ? <a href="#a" onClick={(e) => { e.preventDefault(); nav("affiliati", r.id); }}>{r.nome}</a> : r.nome}</div></td>
            <td data-l="Scadenza">{fd(r.scadenza)}<div><Badge k={d <= 7 ? "bad" : d <= 30 ? "warn" : "ok"}>{d < 0 ? "Scaduto" : `${d} giorni`}</Badge></div></td><td data-l="Promemoria"><RemChips r={r} /></td>
            <td><button className="btn sm primary" onClick={() => act(() => post(`/admin/affiliates/${r.id}/renew`), "Rinnovo registrato: +1 anno").then((r) => r && reload())} data-testid="domain-renew">Rinnovo pagato</button></td></tr>); })}</tbody></table>
        {!L.length && <Empty>Nessun dominio attivo.</Empty>}</div>
    </div>
  );
}

function Report() {
  const [year, setYear] = useState(0);
  const [d] = useLoad(`/admin/report?year=${year}`, [year]);
  if (!d) return null;
  const max = Math.max(1, ...d.months);
  const M = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"];
  return (
    <div data-testid="admin-report">
      <div className="row between" style={{ marginBottom: 16 }}><h2><Ico n="chart" s={22} />Report</h2><select value={d.year} onChange={(e) => setYear(+e.target.value)} style={{ width: 120 }} data-testid="report-year">{d.years.map((y) => <option key={y}>{y}</option>)}</select></div>
      <div className="kpis">
        <div className="kpi"><span>Incassi {d.year} (IVA incl.)</span><b data-testid="report-total">{eur(d.totale)}</b></div>
        <div className="kpi"><span>Attivazioni</span><b>{eur(d.byKind.attivazione)}</b></div><div className="kpi"><span>Corsi</span><b>{eur(d.byKind.corso)}</b></div>
        <div className="kpi"><span>Rinnovi + altro</span><b>{eur(d.byKind.rinnovo + d.byKind.altro)}</b></div><div className="kpi hot"><span>In verifica</span><b>{eur(d.inVerifica)}</b></div>
      </div>
      <div className="card"><h3>Incassi mensili</h3><div className="bars">{d.months.map((v, i) => <div className="bar" key={i}><span className="bv">{v ? eur(v) : ""}</span><i style={{ height: (v / max) * 100 + "%" }} /><small>{M[i]}</small></div>)}</div></div>
      <div className="sch-grid" style={{ marginTop: 16 }}>
        <div className="card"><h3>Panoramica rete</h3><dl className="kv" style={{ marginTop: 10 }}><dt>Affiliati</dt><dd>{d.rete.affiliati}</dd><dt>In attesa</dt><dd>{d.rete.inAttesa}</dd><dt>In realizzazione</dt><dd>{d.rete.realizzazione}</dd><dt>Consegnati</dt><dd>{d.rete.consegnati}</dd><dt>Online</dt><dd>{d.rete.online}</dd></dl></div>
        <div className="card"><h3>Export CSV</h3><p className="small muted">Separatore ";" compatibile con Excel.</p><div className="row" style={{ marginTop: 10 }}>
          {["affiliati", "pagamenti", "scadenze", "corsi"].map((k) => <button key={k} className="btn sm" onClick={() => downloadUrl(`${API}/admin/export/${k}`)} data-testid={`export-${k}-btn`}>{k[0].toUpperCase() + k.slice(1)}</button>)}</div></div>
      </div>
    </div>
  );
}

const EST = { inviata: ["Inviata", "ok"], in_invio: ["In invio", "info"], errore: ["Errore", "bad"], non_configurato: ["Non inviata (email non configurata)", "warn"] };

function Emails() {
  const [q, setQ] = useState("");
  const [d] = useLoad(`/admin/emails?q=${encodeURIComponent(q)}`, [q]);
  return (
    <div data-testid="admin-emails">
      <div className="row between" style={{ marginBottom: 6 }}><h2><Ico n="mail" s={22} />Registro email</h2><input type="text" placeholder="Cerca per destinatario o oggetto…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 300 }} data-testid="email-search" /></div>
      {d && <div className="note info" style={{ marginTop: 10 }}>Invio tramite Aruba: <b>{d.status.aruba ? "attivo" : "non configurato"}</b> · Riserva Brevo: <b>{d.status.brevo ? "attiva" : "non configurata"}</b>. Se Aruba non risponde, l'email parte automaticamente con Brevo.</div>}
      <div className="card" style={{ padding: "6px 16px" }}>
        {d && d.items.length ? d.items.map((e) => (
          <details className="mail" key={e.id} data-testid="email-item"><summary><div className="mto"><Badge k={(EST[e.status] || EST.in_invio)[1]}>{(EST[e.status] || EST.in_invio)[0]}</Badge> <span className="mono small">{e.to}</span></div><div className="msub">{e.subject}</div><small className="muted">{fdt(e.at)}</small></summary>
            <div className="mbody"><div className="small muted">A: {e.to} · Oggetto: {e.subject}{e.provider ? ` · via ${e.provider}` : ""}</div><div className="pre" style={{ marginTop: 8 }}>{e.body}</div>{e.errors && e.errors.length > 0 && <div className="small muted" style={{ marginTop: 6 }}>{e.errors.join(" · ")}</div>}</div></details>
        )) : <p className="muted" style={{ padding: "14px 0" }}>Nessuna email.</p>}
      </div>
    </div>
  );
}
