import React, { useState } from "react";
import { Badge, useLoad, useAction, useUI, UploadBox, Field, Empty, Ico } from "./ui.jsx";
import { post, put, del, NEWSCAT, MATCAT, PERMS, eur, genPw } from "./lib.js";
import { NewsCard, MatCard } from "./AffTabs.jsx";
import { PayBox } from "./Aff.jsx";
import RolesSettings, { Checks } from "./AdminRoles.jsx";

export function AdminNews() {
  const [L, reload] = useLoad("/admin/news");
  const [f, setF] = useState(null);
  const act = useAction();
  const { ask } = useUI();
  if (!L) return null;
  const save = async () => { const r = await act(() => (f.id ? put(`/admin/news/${f.id}`, f) : post("/admin/news", f)), "Comunicazione pubblicata"); if (r) { setF(null); reload(); } };
  return (
    <div data-testid="admin-news">
      <div className="row between" style={{ marginBottom: 16 }}><h2><Ico n="news" s={22} />Bacheca</h2><button className="btn primary" onClick={() => setF({ titolo: "", categoria: "Novità", testo: "", immagine: null, inEvidenza: false, email: false })} data-testid="news-new-btn">+ Nuova comunicazione</button></div>
      {f && (
        <div className="card" style={{ marginBottom: 16 }} data-testid="news-form">
          <div style={{ display: "grid", gap: 12 }}>
            <div className="grid2"><Field label="Titolo"><input type="text" value={f.titolo} onChange={(e) => setF({ ...f, titolo: e.target.value })} data-testid="news-title" /></Field>
              <Field label="Categoria"><select value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })} data-testid="news-category">{NEWSCAT.map((c) => <option key={c}>{c}</option>)}</select></Field></div>
            <Field label="Testo"><textarea value={f.testo} onChange={(e) => setF({ ...f, testo: e.target.value })} data-testid="news-text" /></Field>
            {f.immagine ? <div className="row"><Badge k="ok">Immagine caricata</Badge><button className="btn sm ghost" onClick={() => setF({ ...f, immagine: null })}>Rimuovi</button></div>
              : <UploadBox small label="Immagine (facoltativa)" hint="JPG o PNG" accept="image/*" owner="public" testid="news-image-upload" onDone={(r) => setF({ ...f, immagine: r.id })} />}
            <label className="chk"><input type="checkbox" checked={f.inEvidenza} onChange={(e) => setF({ ...f, inEvidenza: e.target.checked })} data-testid="news-pin" />In evidenza</label>
            {!f.id && <label className="chk"><input type="checkbox" checked={f.email} onChange={(e) => setF({ ...f, email: e.target.checked })} data-testid="news-email" />Invia anche per email a tutti gli affiliati</label>}
            <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn" onClick={() => setF(null)}>Annulla</button><button className="btn primary" onClick={save} data-testid="news-save">Pubblica</button></div>
          </div>
        </div>
      )}
      <div className="newsgrid">{L.length ? L.map((n) => <NewsCard key={n.id} n={n} admin onEdit={() => setF(n)} onDel={async () => { if (await ask({ title: "Eliminare la comunicazione?", danger: true, ok: "Elimina" })) act(() => del(`/admin/news/${n.id}`), "Eliminata").then((r) => r && reload()); }} />) : <Empty>Nessuna comunicazione.</Empty>}</div>
    </div>
  );
}

export function AdminMats() {
  const [L, reload] = useLoad("/admin/materials");
  const [f, setF] = useState({ titolo: "", categoria: MATCAT[0], descrizione: "", file: null, name: "" });
  const act = useAction();
  const { ask } = useUI();
  if (!L) return null;
  const save = async () => { if (await act(() => post("/admin/materials", f), "Materiale caricato")) { setF({ titolo: "", categoria: MATCAT[0], descrizione: "", file: null, name: "" }); reload(); } };
  return (
    <div data-testid="admin-materials">
      <h2 style={{ marginBottom: 16 }}><Ico n="folder" s={22} />Materiali</h2>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "grid", gap: 12 }}>
          <div className="grid2"><Field label="Titolo"><input type="text" value={f.titolo} onChange={(e) => setF({ ...f, titolo: e.target.value })} data-testid="material-title" /></Field>
            <Field label="Categoria"><select value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })} data-testid="material-category">{MATCAT.map((c) => <option key={c}>{c}</option>)}</select></Field></div>
          <Field label="Descrizione"><input type="text" value={f.descrizione} onChange={(e) => setF({ ...f, descrizione: e.target.value })} /></Field>
          {f.file ? <div className="row"><Badge k="ok">{f.name}</Badge><button className="btn sm ghost" onClick={() => setF({ ...f, file: null })}>Cambia</button></div>
            : <UploadBox small label="Scegli il file" hint="PDF, immagini, ZIP, DOCX, PPTX, XLSX, CSV, MP4, TXT – max 50 MB" accept="*" owner="public" testid="material-upload" onDone={(r) => setF({ ...f, file: r.id, name: r.name })} />}
          <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" disabled={!f.file || !f.titolo} onClick={save} data-testid="material-save">Pubblica materiale</button></div>
        </div>
      </div>
      {L.length ? <div className="mgrid">{L.map((m) => <MatCard key={m.id} m={m} admin onDel={async () => { if (await ask({ title: "Eliminare il materiale?", danger: true, ok: "Elimina" })) act(() => del(`/admin/materials/${m.id}`), "Eliminato").then((r) => r && reload()); }} />)}</div> : <Empty>Nessun materiale.</Empty>}
    </div>
  );
}

export function Settings({ user }) {
  const perm = user.is_super || (user.perms || []).includes("impostazioni");
  const full = perm && (user.is_super || user.tutteAziende);
  const tabs = [full && ["pag", "Pagamento predefinito"], user.is_super && ["aziende", "Aziende"], perm && ["pw", "Password affiliati"], full && ["legal", "Contratto e privacy"], user.is_super && ["team", "Team admin"], user.is_super && ["ruoli", "Ruoli e reparti"], ["gen", "Generali"]].filter(Boolean);
  const [t, setT] = useState(tabs[0][0]);
  const [s, reload] = useLoad("/admin/settings");
  if (!s) return null;
  return (
    <div data-testid="admin-settings">
      <h2 style={{ marginBottom: 16 }}><Ico n="settings" s={22} />Impostazioni</h2>
      <div className="subtabs">{tabs.map(([k, l]) => <button key={k} className={t === k ? "on" : ""} onClick={() => setT(k)} data-testid={`settings-tab-${k}`}>{l}</button>)}</div>
      {t === "pag" && <><p className="muted" style={{ marginBottom: 12 }}>Usato per gli affiliati senza azienda o con un'azienda che non ha dati di pagamento propri.</p><PagSettings value={s.pag} onSave={(p) => put("/admin/settings", { pag: p })} reload={reload} /></>}
      {t === "aziende" && <Companies />}
      {t === "pw" && <PwSettings />}
      {t === "legal" && <LegalSettings s={s} reload={reload} />}
      {t === "team" && <Team me={user} />}
      {t === "ruoli" && <RolesSettings />}
      {t === "gen" && <General s={s} reload={reload} full={full} />}
    </div>
  );
}

function Companies() {
  const [L, reload] = useLoad("/admin/companies");
  const [sel, setSel] = useState(null);
  const act = useAction();
  const { ask } = useUI();
  if (!L) return null;
  if (sel) return <CompanyForm c={sel} back={() => { setSel(null); reload(); }} />;
  const remove = async (c) => { if (await ask({ title: `Eliminare ${c.nome}?`, danger: true, ok: "Elimina" })) act(() => del(`/admin/companies/${c.id}`), "Azienda eliminata").then((r) => r && reload()); };
  return (
    <div data-testid="companies-settings">
      <div className="row between" style={{ marginBottom: 12 }}><p className="muted">Ogni azienda può avere i propri dati di pagamento. Assegna l'azienda dalla scheda dell'affiliato (Dati interni).</p>
        <button className="btn primary" onClick={() => setSel({ nome: "", pag: {} })} data-testid="company-new-btn">+ Nuova azienda</button></div>
      <div className="card">{L.length ? L.map((c) => (
        <div className="todo" key={c.id} data-testid="company-row"><div><b>{c.nome}</b><div className="small muted">{c.affiliati} affiliati · {c.pag?.iban ? `IBAN ${c.pag.iban}` : "usa il pagamento predefinito"}</div></div>
          <div className="row"><button className="btn sm" onClick={() => setSel(c)} data-testid="company-edit">Modifica</button><button className="btn sm danger" onClick={() => remove(c)} data-testid="company-delete">Elimina</button></div></div>
      )) : <Empty>Nessuna azienda. Creane una per assegnarle affiliati e modalità di pagamento.</Empty>}</div>
    </div>
  );
}

function CompanyForm({ c, back }) {
  const [nome, setNome] = useState(c.nome);
  return (
    <div data-testid="company-form">
      <button className="back" onClick={back}>← Aziende</button>
      <div className="card" style={{ marginBottom: 14 }}><Field label="Nome azienda"><input type="text" value={nome} onChange={(e) => setNome(e.target.value)} data-testid="company-name" /></Field>
        <p className="small muted" style={{ marginTop: 8 }}>Lascia vuoto l'IBAN per usare il pagamento predefinito. Gli altri campi lasciati vuoti (causale, importi, termine…) prendono i valori del pagamento predefinito.</p></div>
      <PagSettings value={c.pag || {}} onSave={(p) => (c.id ? put(`/admin/companies/${c.id}`, { nome, pag: p }) : post("/admin/companies", { nome, pag: p }))} reload={back} />
    </div>
  );
}

function PagSettings({ value, onSave, reload }) {
  const [p, setP] = useState(value);
  const act = useAction();
  const F = (k, l, ph) => <Field label={l}><input type="text" value={p[k] || ""} placeholder={ph} onChange={(e) => setP({ ...p, [k]: e.target.value })} data-testid={`pag-${k}`} /></Field>;
  return (
    <div className="sch-grid">
      <div className="card"><div style={{ display: "grid", gap: 12 }}>
        {F("intestatario", "Intestatario")}{F("iban", "IBAN")}<div className="grid2">{F("banca", "Banca")}{F("bic", "BIC / SWIFT")}</div>
        <div className="grid3">{F("importo", "Imponibile attivazione €")}{F("iva", "IVA %")}{F("rinnovo", "Rinnovo dominio € (imponibile)")}</div>
        {F("causale", "Causale", "Usa {agenzia} e {url}")}{F("scadenza", "Termine di pagamento")}
        <Field label="Note"><textarea value={p.note || ""} onChange={(e) => setP({ ...p, note: e.target.value })} /></Field>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={() => act(() => onSave(p), "Dati pagamento salvati").then((r) => r && reload())} data-testid="pag-save">Salva</button></div>
      </div></div>
      <div className="card"><h3 style={{ marginBottom: 10 }}>Anteprima per l'affiliato</h3><PayBox pag={p} a={{ nomeAgenzia: "Agenzia Esempio", urlDef: "agenziaesempio.it" }} /><p className="small muted" style={{ marginTop: 8 }}>Totale attivazione: {eur((parseFloat(p.importo) || 0) * (1 + (parseFloat(p.iva) || 0) / 100))}</p></div>
    </div>
  );
}

function PwSettings() {
  const [L] = useLoad("/admin/affiliates");
  const [pw, setPw] = useState({});
  const act = useAction();
  if (!L) return null;
  return (
    <div className="card" data-testid="pw-settings">{L.map((r) => (
      <div className="pwrow" key={r.id}><div><b>{r.nome}</b><div className="small muted">{r.email}</div></div>
        <div className="ctl"><input type="text" value={pw[r.id] || ""} placeholder="Nuova password" onChange={(e) => setPw({ ...pw, [r.id]: e.target.value })} data-testid={`pw-input-${r.id}`} /><button className="btn sm" onClick={() => setPw({ ...pw, [r.id]: genPw() })}>Genera</button></div>
        <button className="btn sm primary" onClick={() => act(() => post(`/admin/affiliates/${r.id}/password`, { password: pw[r.id] || "" }), "Password aggiornata")} data-testid={`pw-save-${r.id}`}>Imposta</button></div>
    ))}</div>
  );
}

function LegalSettings({ s, reload }) {
  const [f, setF] = useState({ contratto: s.legali.contratto, privacy: s.legali.privacy });
  const act = useAction();
  const { ask } = useUI();
  const pub = async (nv) => { if (nv && !(await ask({ title: "Pubblicare una nuova versione?", text: "Tutti gli affiliati dovranno riaccettare i termini al prossimo accesso." }))) return; act(() => post("/admin/legal", { ...f, nuovaVersione: nv }), nv ? "Nuova versione pubblicata" : "Testi salvati").then((r) => r && reload()); };
  return (
    <div className="card" data-testid="legal-settings"><p className="muted">Versione attuale: <b>v{s.legali.versione}</b></p>
      <div style={{ display: "grid", gap: 12, marginTop: 10 }}>
        <Field label="Contratto di affiliazione"><textarea style={{ minHeight: 200 }} value={f.contratto} onChange={(e) => setF({ ...f, contratto: e.target.value })} data-testid="legal-contratto" /></Field>
        <Field label="Informativa privacy"><textarea style={{ minHeight: 200 }} value={f.privacy} onChange={(e) => setF({ ...f, privacy: e.target.value })} data-testid="legal-privacy" /></Field>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn" onClick={() => pub(false)}>Salva correzioni (stessa versione)</button><button className="btn primary" onClick={() => pub(true)} data-testid="legal-publish">Pubblica come nuova versione</button></div>
      </div>
    </div>
  );
}

function Team({ me }) {
  const [L, reload] = useLoad("/admin/team");
  const [C] = useLoad("/admin/companies");
  const [RL] = useLoad("/admin/ruoli");
  const [R] = useLoad("/reparti");
  const [f, setF] = useState(null);
  const act = useAction();
  if (!L || !C || !RL || !R) return null;
  const save = async () => { const r = await act(() => (f.id ? put(`/admin/team/${f.id}`, f) : post("/admin/team", f)), "Utente salvato"); if (r) { setF(null); reload(); } };
  const cn = Object.fromEntries(C.map((c) => [c.id, c.nome]));
  const scope = (u) => (u.is_super || u.tutteAziende ? "tutte le aziende" : (u.aziende || []).map((x) => cn[x]).filter(Boolean).join(", ") || "nessuna azienda");
  const edit = (u) => setF({ ...u, password: "", full: !!u.is_super, tutteAziende: !!u.tutteAziende, aziende: u.aziende || [], perms: u.perms || [], ruoloId: u.ruoloId || "", reparti: u.reparti || [] });
  const tog = (k, id, on) => setF({ ...f, [k]: on ? [...f[k], id] : f[k].filter((x) => x !== id) });
  return (
    <div data-testid="team-settings">
      <div className="row" style={{ justifyContent: "flex-end", marginBottom: 12 }}><button className="btn primary" onClick={() => setF({ nome: "", email: "", password: genPw(), perms: [], active: true, full: false, tutteAziende: true, aziende: [], ruoloId: "", reparti: [] })} data-testid="team-new-btn">+ Aggiungi utente</button></div>
      {f && <div className="card" style={{ marginBottom: 16 }} data-testid="team-form"><div style={{ display: "grid", gap: 12 }}>
        <div className="grid3"><Field label="Nome"><input type="text" value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} data-testid="team-name" /></Field>
          <Field label="Email"><input type="email" value={f.email} disabled={!!f.id} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="team-email" /></Field>
          <Field label={f.id ? "Nuova password (facoltativa)" : "Password"}><input type="text" value={f.password || ""} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="team-password" /></Field></div>
        {!f.is_master && <label className="chk"><input type="checkbox" checked={f.full} onChange={(e) => setF({ ...f, full: e.target.checked })} data-testid="team-full" /><span><b>Accesso completo come il Master</b> · vede tutti gli affiliati di tutte le aziende, ha tutti i permessi e gestisce il team</span></label>}
        {!f.full && (<>
          <div className="lbl">Quali affiliati vede</div>
          <div className="seg"><label><input type="radio" checked={f.tutteAziende} onChange={() => setF({ ...f, tutteAziende: true })} data-testid="team-scope-all" />Tutte le aziende</label>
            <label><input type="radio" checked={!f.tutteAziende} onChange={() => setF({ ...f, tutteAziende: false })} data-testid="team-scope-some" />Solo le aziende selezionate</label></div>
          {!f.tutteAziende && (C.length ? <div className="permgrid">{C.map((c) => <label className="chk" key={c.id}><input type="checkbox" checked={f.aziende.includes(c.id)} onChange={(e) => tog("aziende", c.id, e.target.checked)} data-testid={`team-company-${c.id}`} />{c.nome}</label>)}</div>
            : <div className="note warn small">Nessuna azienda creata: aggiungile in Impostazioni &gt; Aziende.</div>)}
          {!f.tutteAziende && !f.aziende.length && <div className="note warn small" data-testid="team-no-company-warn">Nessuna azienda selezionata: questo utente non vedrà affiliati né ticket.</div>}
          <div className="lbl">Ruolo</div>
          <select value={f.ruoloId} onChange={(e) => setF({ ...f, ruoloId: e.target.value })} data-testid="team-ruolo"><option value="">Personalizzato (scegli sezioni e reparti qui sotto)</option>{RL.map((r) => <option key={r.id} value={r.id}>{r.nome}</option>)}</select>
          {f.ruoloId ? <div className="note info small">Sezioni e reparti vengono dal ruolo: modificali in Impostazioni &gt; Ruoli e reparti.</div> : <>
            <div className="lbl">Permessi</div>
            <div className="permgrid">{Object.entries(PERMS).map(([k, l]) => <label className="chk" key={k}><input type="checkbox" checked={f.perms.includes(k)} onChange={(e) => tog("perms", k, e.target.checked)} data-testid={`team-perm-${k}`} />{l}</label>)}</div>
            <div className="lbl">Reparti ticket <span className="small muted">(nessuno = tutti)</span></div>
            <Checks items={R.map((r) => [r.id, r.nome])} value={f.reparti} onChange={(v) => setF({ ...f, reparti: v })} prefix="team-rep" /></>}
        </>)}
        {!f.is_master && <label className="chk"><input type="checkbox" checked={f.active} onChange={(e) => setF({ ...f, active: e.target.checked })} data-testid="team-active" />Attivo</label>}
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn" onClick={() => setF(null)}>Annulla</button><button className="btn primary" onClick={save} data-testid="team-save">Salva</button></div>
      </div></div>}
      <div className="card">{L.map((u) => (
        <div className="todo" key={u.id} data-testid="team-row"><div><b>{u.nome || u.email}</b> {u.is_master ? <Badge k="accent">Master</Badge> : u.is_super && <Badge k="info">Accesso completo</Badge>} {!u.active && <Badge k="bad">Disattivato</Badge>}{!u.is_super && u.ruoloNome && <Badge k="info">{u.ruoloNome}</Badge>}
          <div className="small muted">{u.email} · {u.is_super ? "tutti i permessi" : (u.perms || []).map((p) => PERMS[p]?.split(" ")[0]).join(", ") || "nessun permesso"} · vede: {scope(u)}{!u.is_super && (u.perms || []).includes("ticket") && ` · reparti: ${(u.reparti || []).map((x) => R.find((r) => r.id === x)?.nome).filter(Boolean).join(", ") || "tutti"}`}</div></div>
          {(!u.is_master || me.is_master) && <button className="btn sm" onClick={() => edit(u)} data-testid="team-edit">Modifica</button>}</div>
      ))}</div>
    </div>
  );
}

function General({ s, reload, full }) {
  const [g, setG] = useState({ adminEmail: s.adminEmail, giorni: s.giorni });
  const [pw, setPw] = useState({ old: "", new: "" });
  const act = useAction();
  return (
    <div className="sch-grid">
      {full && <div className="card"><h3 style={{ marginBottom: 10 }}>Generali</h3><div style={{ display: "grid", gap: 12 }}>
        <Field label="Email dell'admin per le notifiche"><input type="email" value={g.adminEmail} onChange={(e) => setG({ ...g, adminEmail: e.target.value })} data-testid="gen-admin-email" /></Field>
        <Field label="Giorni lavorativi di consegna predefiniti"><input type="number" value={g.giorni} onChange={(e) => setG({ ...g, giorni: e.target.value })} data-testid="gen-days" /></Field>
        <div className="note info small">Email: Aruba {s.email.aruba ? "attivo" : "non configurato"} · Brevo (riserva) {s.email.brevo ? "attivo" : "non configurato"}.</div>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={() => act(() => put("/admin/settings", g), "Impostazioni salvate").then((r) => r && reload())} data-testid="gen-save">Salva</button></div></div></div>}
      <div className="card"><h3 style={{ marginBottom: 10 }}>Cambia la tua password</h3><div style={{ display: "grid", gap: 12 }}>
        <Field label="Password attuale"><input type="password" value={pw.old} onChange={(e) => setPw({ ...pw, old: e.target.value })} data-testid="own-pw-old" /></Field>
        <Field label="Nuova password (min 8)"><input type="password" value={pw.new} onChange={(e) => setPw({ ...pw, new: e.target.value })} data-testid="own-pw-new" /></Field>
        <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn primary" onClick={() => act(() => post("/auth/change-password", pw), "Password aggiornata").then((r) => r && setPw({ old: "", new: "" }))} data-testid="own-pw-save">Aggiorna password</button></div></div></div>
    </div>
  );
}

