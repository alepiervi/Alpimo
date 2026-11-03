import React, { useState, useEffect } from "react";
import { Badge, useLoad, useAction, UploadBox, FileChip, Field, Empty, Ico } from "./ui.jsx";
import { post, put, fileUrl, fd, fdt, eur, DOCT, PAYST, NEWSCAT, MATCAT, downloadUrl } from "./lib.js";
import { showLegal } from "./Auth.jsx";
import { useUI } from "./ui.jsx";

const DST = { in_verifica: ["In verifica", "warn"], approvato: ["Approvato", "ok"], rifiutato: ["Rifiutato", "bad"] };

export function BillingForm({ value, tipo, onSave, testid = "billing" }) {
  const [f, setF] = useState(value || {});
  useEffect(() => setF(value || {}), [value]);
  const F = (k, l, p = {}) => <Field label={l}><input type="text" value={f[k] || ""} onChange={(e) => setF({ ...f, [k]: e.target.value })} data-testid={`${testid}-${k}`} {...p} /></Field>;
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="grid2">{F("intestatario", "Intestatario")}{F("cf", "Codice fiscale")}{F("piva", "P.IVA")}{F("sdi", "Codice SDI", { maxLength: 7 })}{F("pec", "PEC")}{F("indirizzo", "Indirizzo")}</div>
      <div className="grid3">{F("cap", "CAP", { maxLength: 5 })}{F("citta", "Città")}{F("provincia", "Provincia (sigla)", { maxLength: 2 })}</div>
      <p className="small muted">{tipo === "azienda" ? "Azienda: P.IVA obbligatoria e almeno uno tra SDI e PEC." : "Persona: serve il codice fiscale o la P.IVA."}</p>
      <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={() => onSave(f)} data-testid={`${testid}-save`}>Salva dati di fatturazione</button></div>
    </div>
  );
}

export function DocTab({ me, reload }) {
  const a = me.aff;
  const [docs, reloadDocs] = useLoad("/aff/docs");
  const act = useAction();
  const { openModal } = useUI();
  if (!docs) return null;
  const add = (tipo) => (f) => act(() => post("/aff/docs", { tipo, file: f.id }), "Documento caricato").then(() => { reloadDocs(); reload(); });
  const c = a.consensi || {};
  return (
    <div>
      <div className="card" data-testid="card-documenti">
        <div className="card-h"><h3>Documenti</h3></div>
        {Object.entries(DOCT).map(([t, [lbl, req]]) => {
          if (req === "azienda" && a.tipo !== "azienda") return null;
          const L = docs.filter((d) => d.tipo === t);
          const canUp = t === "altro" || !L.length || L[0].stato === "rifiutato";
          return (
            <div className="docrow" key={t} data-testid={`doc-row-${t}`}>
              <div className="row between"><b>{lbl}</b><Badge k={req ? "accent" : "neutral"}>{req ? "Obbligatorio" : "Facoltativo"}</Badge></div>
              {L.map((d) => (
                <div key={d.id}>
                  <div className="row" style={{ marginTop: 6 }}><Badge k={DST[d.stato][1]} data-testid={`doc-status-${t}`}>{DST[d.stato][0]}</Badge><span className="small muted">Caricato il {fd(d.uploadedAt)}</span></div>
                  {d.stato === "rifiutato" && <div className="note bad small" style={{ marginTop: 6 }}>Motivo: {d.nota}</div>}
                  <FileChip f={d.fileInfo} />
                </div>
              ))}
              {canUp && <UploadBox small label={L.length ? "Carica di nuovo" : "Carica documento"} testid={`doc-upload-${t}`} onDone={add(t)} />}
            </div>
          );
        })}
      </div>
      <div className="card" data-testid="card-fatturazione">
        <div className="card-h"><h3>Dati di fatturazione</h3></div>
        <BillingForm value={a.fatturazione} tipo={a.tipo} onSave={(f) => act(() => put("/aff/billing", f), "Dati di fatturazione salvati").then(reload)} />
      </div>
      <div className="card" data-testid="card-consensi">
        <div className="card-h"><h3>Consensi</h3></div>
        <dl className="kv">
          <dt>Contratto</dt><dd>Accettato il {fdt(c.contratto?.at)} (v{c.contratto?.versione}) · <a href="#c" onClick={(e) => { e.preventDefault(); showLegal(openModal, "contratto"); }}>Leggi</a></dd>
          <dt>Privacy</dt><dd>Accettata il {fdt(c.privacy?.at)} (v{c.privacy?.versione}) · <a href="#p" onClick={(e) => { e.preventDefault(); showLegal(openModal, "privacy"); }}>Leggi</a></dd>
          <dt>Marketing</dt><dd>
            <label className="chk" style={{ marginTop: 0 }}><input type="checkbox" checked={!!c.marketing?.value} onChange={(e) => act(() => post("/aff/marketing", { value: e.target.checked }), e.target.checked ? "Consenso marketing dato" : "Consenso marketing revocato").then(reload)} data-testid="marketing-toggle" />
              <span>{c.marketing?.value ? "Consenso dato" : "Nessun consenso"} · {fdt(c.marketing?.at)}</span></label>
          </dd>
        </dl>
      </div>
    </div>
  );
}

export function PayTable({ L, admin, extra }) {
  if (!L.length) return <Empty>Nessun pagamento registrato.</Empty>;
  return (
    <div className="tablewrap">
      <table className="resp" data-testid="payments-table">
        <thead><tr><th>Data</th><th>Descrizione</th><th>Importo</th><th>Stato</th><th>Ricevuta</th><th>Fattura</th>{admin && <th />}</tr></thead>
        <tbody>{L.map((p) => (
          <tr key={p.id} data-testid="payment-row">
            <td data-l="Data">{fd(p.at)}</td>
            <td data-l="Descrizione">{p.descrizione}{p.stato === "respinto" && p.nota && <div className="small" style={{ color: "var(--bad)" }}>{p.nota}</div>}</td>
            <td data-l="Importo"><b>{eur(p.totale)}</b><div className="small muted">{eur(p.imponibile)} + IVA {p.iva}%</div></td>
            <td data-l="Stato"><Badge k={PAYST[p.stato][1]}>{PAYST[p.stato][0]}</Badge></td>
            <td data-l="Ricevuta">{p.ricevutaInfo ? <a className="btn sm" href={fileUrl(p.ricevuta)} target="_blank" rel="noreferrer">Vedi</a> : <span className="muted small">—</span>}</td>
            <td data-l="Fattura">{p.invoice ? <a className="btn sm primary" href={fileUrl(p.invoice.file, 1)} data-testid="invoice-download">{p.invoice.numero}</a> : <span className="muted small">{p.stato === "pagato" ? "In preparazione" : "—"}</span>}</td>
            {admin && <td>{extra(p)}</td>}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

export function PagTab() {
  const [L] = useLoad("/aff/payments");
  if (!L) return null;
  const sum = (st) => L.filter((p) => p.stato === st).reduce((s, p) => s + p.totale, 0);
  return (
    <div>
      <div className="kpis k3">
        <div className="kpi"><span>Totale pagato (IVA incl.)</span><b data-testid="pag-total">{eur(sum("pagato"))}</b></div>
        <div className="kpi hot"><span>In verifica</span><b>{eur(sum("in_verifica"))}</b></div>
        <div className="kpi"><span>Fatture</span><b>{L.filter((p) => p.invoice).length}</b></div>
      </div>
      <div className="card"><PayTable L={L} /></div>
    </div>
  );
}

export function NewsCard({ n, admin, onEdit, onDel }) {
  return (
    <div className={`news ${n.inEvidenza ? "pin" : ""} ${!admin && !n.letto ? "unread" : ""}`} data-testid="news-card">
      {n.immagine && <img src={fileUrl(n.immagine)} alt="" />}
      <div className="nb">
        <div className="row"><Badge k="info">{n.categoria}</Badge>{n.inEvidenza && <Badge k="accent">In evidenza</Badge>}{!admin && !n.letto && <Badge k="ok">Nuovo</Badge>}<span className="small muted">{fd(n.at)}</span></div>
        <h3>{n.titolo}</h3><div className="nt">{n.testo}</div>
        {admin && <div className="row between" style={{ marginTop: 10 }}><span className="small muted">Letta da {n.letti} su {n.tot} affiliati</span><div className="row"><button className="btn sm" onClick={onEdit} data-testid="news-edit">Modifica</button><button className="btn sm danger" onClick={onDel} data-testid="news-delete">Elimina</button></div></div>}
      </div>
    </div>
  );
}

export function NewsTab({ onRead }) {
  const [L] = useLoad("/aff/news");
  useEffect(() => { post("/aff/news/read").then(onRead).catch(() => {}); }, []); // eslint-disable-line
  if (!L) return null;
  return <div className="newsgrid">{L.length ? L.map((n) => <NewsCard key={n.id} n={n} />) : <Empty>Nessuna comunicazione.</Empty>}{NEWSCAT.length === 0 && null}</div>;
}

export function MatCard({ m, onDl, admin, onDel }) {
  const ext = (m.name.split(".").pop() || "").toUpperCase();
  const isImg = (m.type || "").startsWith("image/");
  return (
    <div className="mcard" data-testid="material-card">
      <div className="mth">{isImg ? <img src={fileUrl(m.file)} alt="" /> : <span className="mext">{ext}</span>}</div>
      <div className="mb">
        <Badge k="neutral">{m.categoria}</Badge><b>{m.titolo}</b><p className="small muted">{m.descrizione}</p>
        <div className="row between" style={{ marginTop: "auto", paddingTop: 8 }}>
          <span className="small muted">{m.downloads} download</span>
          <div className="row">
            <a className="btn sm" href={fileUrl(m.file)} target="_blank" rel="noreferrer">Anteprima</a>
            {admin ? <button className="btn sm danger" onClick={onDel} data-testid="material-delete">Elimina</button> : <button className="btn sm primary" onClick={onDl} data-testid="material-download"><Ico n="download" s={14} />Scarica</button>}
          </div>
        </div>
      </div>
    </div>
  );
}

export function MatTab() {
  const [L, reload] = useLoad("/aff/materials");
  const [cat, setCat] = useState("");
  if (!L) return null;
  const dl = async (m) => { await post(`/aff/materials/${m.id}/download`); downloadUrl(fileUrl(m.file, 1)); reload(); };
  const V = L.filter((m) => !cat || m.categoria === cat);
  return (
    <div>
      <div className="row chips" style={{ marginBottom: 14 }}>
        {["", ...MATCAT].map((c) => <button key={c} className={`chip ${cat === c ? "on" : ""}`} onClick={() => setCat(c)} data-testid={`mat-filter-${c || "tutti"}`}>{c || "Tutti"}</button>)}
      </div>
      {V.length ? <div className="mgrid">{V.map((m) => <MatCard key={m.id} m={m} onDl={() => dl(m)} />)}</div> : <Empty>Nessun materiale in questa categoria.</Empty>}
    </div>
  );
}
