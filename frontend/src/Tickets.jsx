import React, { useState, useEffect, useRef } from "react";
import { Badge, useLoad, useAction, Field, Empty } from "./ui.jsx";
import { get, post, fdt } from "./lib.js";

const ST = { aperto: ["Aperto", "warn"], in_lavorazione: ["In lavorazione", "info"], chiuso: ["Chiuso", "ok"] };
const PR = { bassa: "neutral", media: "info", alta: "bad" };

export default function Tickets({ role, initial, affId }) {
  const admin = role === "admin";
  const [filter, setFilter] = useState("aperti");
  const [sel, setSel] = useState(initial || null);
  const [L, reload] = useLoad(`/tickets${affId ? `?affId=${affId}` : ""}`);
  const [R] = useLoad("/reparti");
  const [rep, setRep] = useState("");
  const [nuovo, setNuovo] = useState(false);
  useEffect(() => { if (initial) setSel(initial); }, [initial]);
  if (!L || !R) return null;
  const rn = Object.fromEntries(R.map((r) => [r.id, r.nome]));
  const V = L.filter((t) => (!rep || t.reparto === rep) && (filter === "tutti" || (filter === "aperti" ? t.stato !== "chiuso" : t.stato === "chiuso")));
  const unread = (t) => (admin ? !t.lettoAdmin : !t.lettoAff);
  return (
    <div className="tk" data-testid="tickets-view">
      <div className="tk-list">
        {!admin && <button className="btn primary" onClick={() => { setNuovo(true); setSel(null); }} data-testid="ticket-new-btn">+ Nuovo ticket</button>}
        <div className="row chips">{["aperti", "chiusi", "tutti"].map((f) => <button key={f} className={`chip ${filter === f ? "on" : ""}`} onClick={() => setFilter(f)} data-testid={`ticket-filter-${f}`}>{f[0].toUpperCase() + f.slice(1)}</button>)}</div>
        {admin && <select value={rep} onChange={(e) => setRep(e.target.value)} data-testid="ticket-reparto-filter"><option value="">Tutti i reparti</option>{R.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}</select>}
        {V.length ? V.map((t) => (
          <button key={t.id} className={`tk-item ${sel === t.id ? "on" : ""} ${unread(t) ? "unread" : ""}`} onClick={() => { setSel(t.id); setNuovo(false); }} data-testid="ticket-item">
            <div className="row between"><span><span className="tknum">#{t.num}</span><Badge k={ST[t.stato][1]}>{ST[t.stato][0]}</Badge></span><Badge k={PR[t.priorita]}>{t.priorita}</Badge></div>
            <div className="t" style={{ marginTop: 6 }}>{t.oggetto}</div>
            <div className="small muted">{t.reparto && <span className="tkrep" data-testid="ticket-item-reparto">{rn[t.reparto] || "—"}</span>}{admin && t.agenzia ? t.agenzia + " · " : ""}{fdt(t.createdAt)}</div>
          </button>
        )) : <Empty>Nessun ticket.</Empty>}
      </div>
      <div>
        {nuovo && <NewTicket R={R} onDone={(t) => { setNuovo(false); reload(); setSel(t.id); }} />}
        {sel && !nuovo && <TicketDetail id={sel} admin={admin} R={R} rn={rn} onChange={reload} />}
        {!sel && !nuovo && <Empty>Seleziona un ticket {admin ? "" : "o aprine uno nuovo"}.</Empty>}
      </div>
    </div>
  );
}

function NewTicket({ R, onDone }) {
  const [f, setF] = useState({ oggetto: "", priorita: "media", testo: "", reparto: "" });
  const act = useAction();
  const send = async () => { const r = await act(() => post("/tickets", f), "Ticket aperto"); if (r && r.id) onDone(r); };
  return (
    <div className="card" data-testid="ticket-new-form">
      <h3 style={{ marginBottom: 12 }}>Nuovo ticket</h3>
      <div style={{ display: "grid", gap: 12 }}>
        <Field label="A quale reparto ti rivolgi?"><div className="row" style={{ flexWrap: "wrap", gap: 6 }} data-testid="ticket-reparto">{R.map((r) => (
          <button type="button" key={r.id} className={`btn sm ${f.reparto === r.id ? "primary" : "ghost"}`} onClick={() => setF({ ...f, reparto: r.id })} data-testid={`ticket-reparto-${r.id}`}>{r.nome}</button>))}</div></Field>
        <Field label="Oggetto"><input type="text" value={f.oggetto} onChange={(e) => setF({ ...f, oggetto: e.target.value })} data-testid="ticket-subject" /></Field>
        <Field label="Priorità"><select value={f.priorita} onChange={(e) => setF({ ...f, priorita: e.target.value })} data-testid="ticket-priority"><option value="bassa">Bassa</option><option value="media">Media</option><option value="alta">Alta</option></select></Field>
        <Field label="Descrizione"><textarea value={f.testo} onChange={(e) => setF({ ...f, testo: e.target.value })} data-testid="ticket-text" /></Field>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={send} disabled={!f.reparto} title={f.reparto ? "" : "Scegli prima il reparto"} data-testid="ticket-submit">Invia ticket</button></div>
      </div>
    </div>
  );
}

function TicketDetail({ id, admin, R, rn, onChange }) {
  const [t, setT] = useState(null);
  const [txt, setTxt] = useState("");
  const act = useAction();
  const box = useRef();
  const load = () => get(`/tickets/${id}`).then((x) => { setT(x); onChange(); });
  useEffect(() => { load(); }, [id]); // eslint-disable-line
  useEffect(() => { if (box.current) box.current.scrollTop = 99999; }, [t]);
  if (!t) return null;
  const send = async () => { if (await act(() => post(`/tickets/${id}/msg`, { testo: txt }), "Messaggio inviato")) { setTxt(""); load(); } };
  const status = (s) => act(() => post(`/tickets/${id}/status`, { stato: s }), "Stato aggiornato").then(load);
  const move = (r) => act(() => post(`/tickets/${id}/reparto`, { reparto: r }), `Ticket spostato in ${rn[r]}`).then((x) => x && (get(`/tickets/${id}`).then(setT, () => setT(null)), onChange()));
  return (
    <div className="card" data-testid="ticket-detail">
      <div className="card-h">
        <div><span className="tknum">#{t.num}</span><h3 style={{ display: "inline" }}>{t.oggetto}</h3><div className="small muted">Aperto il {fdt(t.createdAt)} · priorità {t.priorita}{!admin && t.reparto ? ` · reparto ${rn[t.reparto] || ""}` : ""}</div></div>
        {admin ? (
          <div className="row"><select value={t.reparto || ""} onChange={(e) => move(e.target.value)} style={{ width: 190 }} data-testid="ticket-reparto-select">
            {!t.reparto && <option value="">Senza reparto</option>}{R.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}
          </select>
          <select value={t.stato} onChange={(e) => status(e.target.value)} style={{ width: 170 }} data-testid="ticket-status-select">
            {Object.entries(ST).map(([k, v]) => <option key={k} value={k}>{v[0]}</option>)}
          </select></div>
        ) : <Badge k={ST[t.stato][1]} data-testid="ticket-status">{ST[t.stato][0]}</Badge>}
      </div>
      <div className="msgs" ref={box}>
        {t.messaggi.map((m, i) => {
          const mine = (m.da === "admin") === admin;
          return <div key={i} className={`msg ${mine ? "me" : "other"}`}>{m.testo}<small>{m.da === "admin" ? "Supporto" : "Affiliato"} · {fdt(m.at)}</small></div>;
        })}
      </div>
      <textarea value={txt} onChange={(e) => setTxt(e.target.value)} placeholder={t.stato === "chiuso" && !admin ? "Rispondendo riaprirai il ticket…" : "Scrivi una risposta…"} data-testid="ticket-reply" />
      <div className="row" style={{ justifyContent: "flex-end", marginTop: 10 }}>
        {!admin && t.stato !== "chiuso" && <button className="btn" onClick={() => status("chiuso")} data-testid="ticket-resolve">Segna come risolto</button>}
        <button className="btn primary" onClick={send} data-testid="ticket-send">Invia</button>
      </div>
      {admin && (
        <details className="tkmails"><summary>Email inviate per questo ticket ({t.emails.length})</summary>
          {t.emails.map((e) => <div key={e.id} className="small" style={{ padding: "6px 0" }}><b>{e.subject}</b> → {e.to} · {fdt(e.at)} · <span className="muted">{e.status}</span></div>)}
        </details>
      )}
    </div>
  );
}
