import React, { useState, useEffect } from "react";
import { Badge, useLoad, useAction, useUI, UploadBox, FileChip, Field, Empty, Ico } from "./ui.jsx";
import { post, put, fileUrl, fd, fdt, FASI, DOCT, statoInfo, genPw, STEPS } from "./lib.js";
import { DatiKV } from "./Aff.jsx";
import { BillingForm, PayTable } from "./AffTabs.jsx";
import { RemChips, canP } from "./Admin.jsx";

const URLST = { da_verificare: ["Da verificare", "warn"], disponibile: ["Disponibile", "ok"], non_disponibile: ["Non disponibile", "bad"] };
const DST = { in_verifica: ["In verifica", "warn"], approvato: ["Approvato", "ok"], rifiutato: ["Rifiutato", "bad"] };

export default function Scheda({ id, user, back }) {
  const [a, reload] = useLoad(`/admin/affiliates/${id}`);
  const act = useAction();
  if (!a) return null;
  const [lbl, k] = statoInfo(a);
  const A = (path, body, msg) => act(() => post(`/admin/affiliates/${id}/${path}`, body), msg).then((r) => r && reload());
  const P = { a, A, reload, act, id, user };
  return (
    <div data-testid="affiliate-detail">
      <button className="back" onClick={back} data-testid="detail-back">← Affiliati</button>
      <div className="sch-h">
        <div><h2>{a.nomeAgenzia || a.email}</h2><div className="row" style={{ marginTop: 6 }}><Badge k={k} data-testid="detail-status">{lbl}</Badge><span className="small muted">{a.email} · tappa: {STEPS[a.step]}</span>{!a.user?.verified && <><Badge k="warn">Email non verificata</Badge><button className="btn sm" onClick={() => A("verify-email", {}, "Email segnata come verificata")} data-testid="detail-verify-email">Segna come verificata</button></>}</div></div>
      </div>
      <div className="sch-grid">
        <div className="card"><h3 style={{ marginBottom: 10 }}>Dati anagrafici</h3><DatiKV a={a} />{a.stato === "rifiutata" && <div className="note bad" style={{ marginTop: 10 }}>Rifiutata: {a.nota}</div>}</div>
        <UrlCard {...P} />
        <LogoCard {...P} />
        <PayCard {...P} />
        {a.consegna && <ConsegnaCard {...P} />}
        {a.pagamento === "confermato" && <CredCard {...P} />}
        {canP(user, "scadenze") && <DomCard {...P} />}
        <div className="card"><h3 style={{ marginBottom: 10 }}>Fatturazione</h3><BillingForm value={a.fatturazione} tipo={a.tipo} testid="admin-billing" onSave={(f) => act(() => put(`/admin/affiliates/${id}/billing`, f), "Fatturazione salvata").then((r) => r && reload())} /></div>
        <div className="card"><h3 style={{ marginBottom: 10 }}>Account e consensi</h3><dl className="kv">
          <dt>Registrato</dt><dd>{fdt(a.createdAt)}</dd><dt>Contratto</dt><dd>v{a.consensi?.contratto?.versione} · {fdt(a.consensi?.contratto?.at)}</dd>
          <dt>Privacy</dt><dd>v{a.consensi?.privacy?.versione} · {fdt(a.consensi?.privacy?.at)}</dd><dt>Marketing</dt><dd>{a.consensi?.marketing?.value ? "Sì" : "No"} · {fdt(a.consensi?.marketing?.at)}</dd></dl></div>
        <DocsCard {...P} />
        <PaymentsCard {...P} />
        <div className="card"><h3 style={{ marginBottom: 10 }}>Avanzamento corsi</h3>{a.progress.length ? a.progress.map((p, i) => <div className="todo" key={i}><span>{p.titolo}</span><span className="small">{p.fatte}/{p.tot} video {p.completatoAt && <Badge k="ok">Completato</Badge>}</span></div>) : <Empty>Nessun corso iniziato.</Empty>}</div>
        <div className="card"><h3 style={{ marginBottom: 10 }}>Ticket</h3>{a.tickets.length ? a.tickets.map((t) => <div className="todo" key={t.id}><span><span className="tknum">#{t.num}</span>{t.oggetto}</span><Badge k={t.stato === "chiuso" ? "ok" : "warn"}>{t.stato}</Badge></div>) : <Empty>Nessun ticket.</Empty>}</div>
      </div>
    </div>
  );
}

function UrlCard({ a, A }) {
  return (
    <div className="card" data-testid="detail-url-card"><h3 style={{ marginBottom: 10 }}>Verifica URL</h3>
      {a.urls.map((u, i) => u.value && (
        <div className={`urlrow ${a.urlDefinitivo === i ? "def" : ""}`} key={i}><span className="i">{i + 1}</span><div className="row"><span className="mono">{u.value}</span><Badge k={URLST[u.stato][1]}>{URLST[u.stato][0]}</Badge>{a.urlDefinitivo === i && <Badge k="info">Definitivo</Badge>}</div>
          {a.urlDefinitivo == null && <div className="row"><button className="btn sm" onClick={() => A("url", { idx: i, stato: "disponibile" }, "URL disponibile")} data-testid={`url-ok-${i}`}>Disponibile</button><button className="btn sm danger" onClick={() => A("url", { idx: i, stato: "non_disponibile" }, "URL non disponibile")} data-testid={`url-ko-${i}`}>Non disp.</button></div>}
        </div>
      ))}
    </div>
  );
}

function LogoCard({ a, A, id }) {
  return (
    <div className="card" data-testid="detail-logo-card"><h3 style={{ marginBottom: 10 }}>Loghi proposti</h3>
      <div className="logos">{[0, 1, 2].map((i) => { const f = a.loghiInfo[i]; return (
        <div key={i} className={`logo-slot ${a.logoScelto === i ? "chosen" : ""}`} data-testid={`logo-slot-${i}`}>
          <div className="row between"><b>Logo {i + 1}</b>{a.logoScelto === i && <Badge k="accent">Scelto</Badge>}</div>
          <div className="img">{f ? <img src={fileUrl(f.id)} alt="" /> : <span className="small muted">Vuoto</span>}</div>
          {f ? <button className="btn sm" onClick={() => A("logo", { idx: i, file: null }, "Logo rimosso")} data-testid={`logo-remove-${i}`}>Rimuovi</button>
            : <UploadBox small label="Carica" hint="PNG, JPG o SVG" accept="image/*,.svg" owner={id} testid={`logo-upload-${i}`} onDone={(r) => A("logo", { idx: i, file: r.id }, "Logo caricato")} />}
        </div>); })}</div>
    </div>
  );
}

function PayCard({ a, A }) {
  const [g, setG] = useState(15);
  const { ask } = useUI();
  const reject = async () => { const nota = await ask({ title: "Respingi ricevuta", input: "textarea", placeholder: "Motivo" }); if (nota) A("payment", { confirm: false, nota }, "Ricevuta respinta"); };
  const ST = { nessuno: ["Nessuna ricevuta", "neutral"], in_verifica: ["Da verificare", "warn"], confermato: ["Confermato", "ok"], respinto: ["Respinto", "bad"] };
  return (
    <div className="card" data-testid="detail-payment-card"><div className="row between"><h3>Pagamento attivazione</h3><Badge k={ST[a.pagamento][1]}>{ST[a.pagamento][0]}</Badge></div>
      {a.ricevutaInfo ? <FileChip f={a.ricevutaInfo} testid="detail-receipt-open" /> : <p className="muted small" style={{ marginTop: 8 }}>L'affiliato non ha ancora caricato la ricevuta.</p>}
      {a.pagamento === "respinto" && <div className="note bad small" style={{ marginTop: 8 }}>{a.notaPagamento}</div>}
      {a.pagamento === "in_verifica" && <div className="row" style={{ marginTop: 12 }}><Field label="Giorni lavorativi di consegna"><input type="number" value={g} onChange={(e) => setG(+e.target.value)} style={{ width: 110 }} data-testid="payment-days" /></Field>
        <button className="btn primary" onClick={() => A("payment", { confirm: true, giorni: g }, "Pagamento confermato")} data-testid="payment-confirm">Conferma</button><button className="btn danger" onClick={reject} data-testid="payment-reject">Respingi</button></div>}
    </div>
  );
}

function ConsegnaCard({ a, A }) {
  const [d, setD] = useState(a.consegna.dataPrevista);
  useEffect(() => setD(a.consegna.dataPrevista), [a.consegna.dataPrevista]);
  return (
    <div className="card" data-testid="detail-delivery-card"><h3 style={{ marginBottom: 10 }}>Tempi di consegna</h3>
      <div className="row"><Field label="Data prevista"><input type="date" value={d} onChange={(e) => setD(e.target.value)} data-testid="delivery-date-input" /></Field><button className="btn sm" style={{ alignSelf: "flex-end" }} onClick={() => A("consegna", { dataPrevista: d }, "Data aggiornata")} data-testid="delivery-date-save">Salva data</button></div>
      <div className="fasi">{FASI.map((f, i) => <div key={f} className={i < a.consegna.fase ? "done" : i === a.consegna.fase ? "cur" : ""} style={{ cursor: "pointer" }} onClick={() => A("consegna", { fase: i }, "Fase aggiornata")} data-testid={`phase-${i}`}>{f}</div>)}</div>
    </div>
  );
}

function CredCard({ a, A, act, id, reload }) {
  const [c, setC] = useState(a.cred || {});
  const [s, setS] = useState(a.superAdmin || {});
  const { ask } = useUI();
  useEffect(() => { setC(a.cred || {}); setS(a.superAdmin || {}); }, [a]);
  const I = (o, set, k, l, gen) => <Field label={l}><div className="row" style={{ flexWrap: "nowrap" }}><input type="text" className="mono" value={o[k] || ""} onChange={(e) => set({ ...o, [k]: e.target.value })} data-testid={`cred-${set === setS ? "sa" : "aff"}-${k}`} />{gen && <button className="btn sm" onClick={() => set({ ...o, [k]: genPw() })}>Genera</button>}</div></Field>;
  const save = () => act(() => post(`/admin/affiliates/${id}/cred`, { cred: c, superAdmin: s }), "Credenziali salvate").then((r) => r && reload());
  return (
    <div className="card full" data-testid="detail-cred-card"><h3 style={{ marginBottom: 10 }}>Accessi al sito</h3>
      <div className="grid2">
        <div style={{ display: "grid", gap: 10 }}><h4 style={{ margin: 0 }}>Super Admin (solo admin)</h4>{I(s, setS, "url", "URL")}{I(s, setS, "utente", "Utente")}{I(s, setS, "password", "Password", 1)}</div>
        <div style={{ display: "grid", gap: 10 }}><h4 style={{ margin: 0 }}>Admin affiliato</h4>{I(c, setC, "url", "URL admin")}{I(c, setC, "utente", "Utente")}{I(c, setC, "password", "Password admin", 1)}{I(c, setC, "passwordSito", "Password di sblocco sito", 1)}</div>
      </div>
      <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}>
        {a.richiestaOnline && !a.online && <Badge k="warn">L'affiliato chiede la messa online</Badge>}
        <button className="btn" onClick={save} data-testid="cred-save">Salva credenziali</button>
        {!a.consegnato && <button className="btn primary" onClick={async () => { await save(); if (await ask({ title: "Consegnare il sito?", text: "L'affiliato riceverà le credenziali via email." })) A("deliver", {}, "Sito consegnato"); }} data-testid="deliver-btn">Consegna all'affiliato</button>}
        {a.consegnato && !a.online && <button className="btn accent" onClick={async () => { if (await ask({ title: "Mettere online?", text: "La password del sito verrà disattivata." })) A("online", {}, "Sito online"); }} data-testid="online-btn">Metti online</button>}
        {a.online && <Badge k="ok">Online dal {fd(a.onlineAt)}</Badge>}
      </div>
    </div>
  );
}

function DomCard({ a, A }) {
  const [d, setD] = useState(a.dominio.scadenza || "");
  useEffect(() => setD(a.dominio.scadenza || ""), [a.dominio.scadenza]);
  return (
    <div className="card" data-testid="detail-domain-card"><h3 style={{ marginBottom: 10 }}>Scadenza dominio</h3>
      <div className="row"><Field label="Scadenza"><input type="date" value={d} onChange={(e) => setD(e.target.value)} data-testid="domain-date-input" /></Field><button className="btn sm" style={{ alignSelf: "flex-end" }} onClick={() => A("domain", { scadenza: d }, "Scadenza aggiornata")} data-testid="domain-date-save">Salva</button>
        {a.dominio.scadenza && <button className="btn sm primary" style={{ alignSelf: "flex-end" }} onClick={() => A("renew", {}, "Rinnovo registrato: +1 anno")} data-testid="detail-renew">Rinnovo pagato (+1 anno)</button>}</div>
      {a.dominio.scadenza && <div style={{ marginTop: 10 }}><RemChips r={{ scadenza: a.dominio.scadenza, inviati: a.dominio.inviati }} /></div>}
      {a.dominio.storico?.length > 0 && <><h4>Storico rinnovi</h4>{a.dominio.storico.map((s, i) => <div key={i} className="small">{fd(s.da)} → {fd(s.a)} · registrato {fd(s.at)}</div>)}</>}
    </div>
  );
}

function DocsCard({ a, act, reload }) {
  const { ask } = useUI();
  const dec = async (d, approve) => { const nota = approve ? "" : await ask({ title: "Rifiuta documento", input: "textarea", placeholder: "Motivo" }); if (!approve && !nota) return; act(() => post(`/admin/docs/${d.id}`, { approve, nota }), approve ? "Documento approvato" : "Documento rifiutato").then((r) => r && reload()); };
  return (
    <div className="card" data-testid="detail-docs-card"><h3 style={{ marginBottom: 10 }}>Documenti</h3>
      {a.docs.length ? a.docs.map((d) => (
        <div className="docrow" key={d.id}><div className="row between"><b>{DOCT[d.tipo][0]}</b><Badge k={DST[d.stato][1]}>{DST[d.stato][0]}</Badge></div>
          <div className="docf"><span className="ic">{d.name.split(".").pop().toUpperCase().slice(0, 4)}</span><span className="nm" style={{ flex: 1 }}>{d.name}</span><a className="btn sm" href={fileUrl(d.file)} target="_blank" rel="noreferrer">Apri</a>
            {d.stato === "in_verifica" && <><button className="btn sm primary" onClick={() => dec(d, true)} data-testid="doc-approve">Approva</button><button className="btn sm danger" onClick={() => dec(d, false)} data-testid="doc-reject">Rifiuta</button></>}</div>
          {d.nota && <div className="small muted">Motivo: {d.nota}</div>}</div>
      )) : <Empty>Nessun documento caricato.</Empty>}
    </div>
  );
}

function PaymentsCard({ a, act, reload, id }) {
  const { ask } = useUI();
  const manual = async () => {
    const descr = await ask({ title: "Registra pagamento manuale", input: "text", placeholder: "Descrizione (es. Servizio extra)" }); if (!descr) return;
    const tot = await ask({ title: "Importo IVA inclusa (€)", input: "number", placeholder: "es. 122" }); if (!tot) return;
    act(() => post("/admin/payments", { affId: id, descrizione: descr, totale: parseFloat(tot) }), "Pagamento registrato").then((r) => r && reload());
  };
  const extra = (p) => p.stato === "pagato" && <UploadBox small label={p.invoice ? "Sostituisci fattura" : "Allega fattura"} hint="PDF" accept=".pdf" owner={id} testid={`invoice-upload-${p.id}`} onDone={(r) => act(() => post(`/admin/payments/${p.id}/invoice`, { file: r.id }), "Fattura allegata").then((r) => r && reload())} />;
  return (
    <div className="card full" data-testid="detail-payments-card"><div className="row between" style={{ marginBottom: 10 }}><h3>Pagamenti e fatture</h3><button className="btn sm" onClick={manual} data-testid="manual-payment-btn"><Ico n="card" s={14} />Registra pagamento</button></div>
      <PayTable L={a.payments} admin extra={extra} />
    </div>
  );
}
