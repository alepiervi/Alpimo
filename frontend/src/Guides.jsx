import React, { useState } from "react";
import { Ico, Badge, useLoad, useAction, useUI, UploadBox, Field, Empty } from "./ui.jsx";
import { post, put, del, fileUrl, embedUrl, fd } from "./lib.js";

export const SEZ = [["dashboard", "Panoramica"], ["richieste", "Richieste"], ["affiliati", "Affiliati"], ["ticket", "Ticket"], ["corsi", "Corsi"], ["bacheca", "Bacheca"], ["materiali", "Materiali"], ["scadenze", "Scadenze domini"], ["report", "Report"], ["email", "Registro email"], ["impostazioni", "Impostazioni"]];
const GCAT = ["Primi passi", "Affiliati", "Pagamenti e fatture", "Assistenza", "Contenuti", "Domini e report", "Impostazioni e team"];

function Video({ g }) {
  if (g.video) return <div className="player"><video src={fileUrl(g.video)} controls data-testid="guide-video" /></div>;
  const e = embedUrl(g.videoUrl);
  if (e) return <div className="player"><iframe src={e} title={g.titolo} style={{ width: "100%", height: "100%", border: 0 }} allowFullScreen data-testid="guide-video-embed" /></div>;
  return null;
}

function GuidePage({ g, back, canEdit, onEdit, inModal }) {
  const { openModal } = useUI();
  const zoom = (id) => inModal ? window.open(fileUrl(id), "_blank") : openModal({ title: "", wide: true, noCancel: true, ok: "Chiudi", body: <img src={fileUrl(id)} alt="" style={{ width: "100%", borderRadius: 10 }} />, res: () => {} });
  return (
    <div data-testid="guide-page">
      {!inModal && <div className="row between"><button className="back" onClick={back} data-testid="guide-back">← Tutte le guide</button>{canEdit && <button className="btn sm" onClick={onEdit} data-testid="guide-edit">Modifica guida</button>}</div>}
      <div className="guide-h"><Badge k="info">{g.categoria}</Badge><h2>{g.titolo}</h2>{g.descrizione && <p className="muted">{g.descrizione}</p>}<span className="small muted">Aggiornata il {fd(g.at)}</span></div>
      {(g.video || g.videoUrl) && <div className="card" style={{ marginBottom: 16 }}><h3 style={{ marginBottom: 10 }}><Ico n="play" s={16} /> Video guida</h3><Video g={g} /></div>}
      {g.passi.map((p, i) => (
        <div className="card gstep" key={i} data-testid={`guide-step-${i}`}>
          <div className="gstep-t"><span className="num">{i + 1}</span><div><h3>{p.titolo}</h3><div className="pre gtext">{p.testo}</div></div></div>
          {p.immagine && <button className="gshot" onClick={() => zoom(p.immagine)} data-testid={`guide-shot-${i}`}><img src={fileUrl(p.immagine)} alt={p.titolo} loading="lazy" /><span>Clicca per ingrandire</span></button>}
        </div>
      ))}
    </div>
  );
}

function GuideEditor({ g, back }) {
  const [f, setF] = useState(g || { titolo: "", categoria: GCAT[0], descrizione: "", ordine: 100, passi: [{ titolo: "", testo: "", immagine: null }], video: null, videoUrl: "", sezioni: [] });
  const sz = f.sezioni || [];
  const togS = (k) => setF({ ...f, sezioni: sz.includes(k) ? sz.filter((x) => x !== k) : [...sz, k] });
  const act = useAction();
  const { ask } = useUI();
  const setP = (i, k, v) => setF({ ...f, passi: f.passi.map((p, j) => (j === i ? { ...p, [k]: v } : p)) });
  const move = (i, d) => { const L = [...f.passi]; const j = i + d; if (j < 0 || j >= L.length) return; [L[i], L[j]] = [L[j], L[i]]; setF({ ...f, passi: L }); };
  const save = async () => { if (await act(() => (g ? put(`/admin/guides/${g.id}`, f) : post("/admin/guides", f)), "Guida salvata")) back(); };
  const remove = async () => { if (await ask({ title: "Eliminare la guida?", danger: true, ok: "Elimina" })) { await act(() => del(`/admin/guides/${g.id}`), "Guida eliminata"); back(); } };
  return (
    <div className="card" data-testid="guide-editor">
      <button className="back" onClick={back}>← Guide</button>
      <div style={{ display: "grid", gap: 12, marginTop: 8 }}>
        <div className="grid3"><Field label="Titolo"><input type="text" value={f.titolo} onChange={(e) => setF({ ...f, titolo: e.target.value })} data-testid="guide-title" /></Field>
          <Field label="Categoria"><select value={f.categoria} onChange={(e) => setF({ ...f, categoria: e.target.value })} data-testid="guide-category">{GCAT.map((c) => <option key={c}>{c}</option>)}</select></Field>
          <Field label="Ordine"><input type="number" value={f.ordine} onChange={(e) => setF({ ...f, ordine: +e.target.value })} /></Field></div>
        <Field label="Descrizione breve"><input type="text" value={f.descrizione} onChange={(e) => setF({ ...f, descrizione: e.target.value })} data-testid="guide-desc" /></Field>
        <Field label="Mostra il pulsante Guida in queste sezioni"><div className="row" style={{ flexWrap: "wrap", gap: 6 }} data-testid="guide-sections">{SEZ.map(([k, l]) => (
          <button type="button" key={k} className={`btn sm ${sz.includes(k) ? "primary" : "ghost"}`} onClick={() => togS(k)} data-testid={`guide-section-${k}`}>{l}</button>))}</div></Field>
        <div className="grid2">
          <Field label="Link video (YouTube, Vimeo, Drive)"><input type="text" value={f.videoUrl || ""} onChange={(e) => setF({ ...f, videoUrl: e.target.value })} data-testid="guide-video-url" /></Field>
          <div>{f.video ? <div className="row" style={{ marginTop: 22 }}><Badge k="ok">Video caricato</Badge><button className="btn sm ghost" onClick={() => setF({ ...f, video: null })}>Rimuovi</button></div>
            : <UploadBox small label="Oppure carica un video" hint="MP4 o WEBM, max 500 MB" accept="video/*" owner="admin-guide" testid="guide-video-upload" onDone={(r) => setF({ ...f, video: r.id })} />}</div>
        </div>
        <h4>Passaggi</h4>
        {f.passi.map((p, i) => (
          <div className="lzedit" key={i}><span className="lzn">{i + 1}</span>
            <div style={{ display: "grid", gap: 8 }}>
              <input type="text" placeholder="Titolo del passaggio" value={p.titolo} onChange={(e) => setP(i, "titolo", e.target.value)} data-testid={`guide-step-title-${i}`} />
              <textarea placeholder="Cosa fare, passo per passo" value={p.testo} onChange={(e) => setP(i, "testo", e.target.value)} data-testid={`guide-step-text-${i}`} />
              {p.immagine ? <div className="row"><img src={fileUrl(p.immagine)} alt="" style={{ height: 70, borderRadius: 6, border: "1px solid var(--line)" }} /><button className="btn sm ghost" onClick={() => setP(i, "immagine", null)}>Rimuovi immagine</button></div>
                : <UploadBox small label="Carica screenshot" hint="PNG o JPG" accept="image/*" owner="admin-guide" testid={`guide-step-image-${i}`} onDone={(r) => setP(i, "immagine", r.id)} />}
            </div>
            <div className="lzc"><button className="btn sm" onClick={() => move(i, -1)}>↑</button><button className="btn sm" onClick={() => move(i, 1)}>↓</button><button className="btn sm danger" onClick={() => setF({ ...f, passi: f.passi.filter((_, j) => j !== i) })}>✕</button></div>
          </div>
        ))}
        <button className="btn sm" onClick={() => setF({ ...f, passi: [...f.passi, { titolo: "", testo: "", immagine: null }] })} data-testid="guide-step-add">+ Aggiungi passaggio</button>
        <div className="row" style={{ justifyContent: "flex-end" }}>{g && <button className="btn danger" onClick={remove} data-testid="guide-delete">Elimina</button>}<button className="btn primary" onClick={save} data-testid="guide-save">Salva guida</button></div>
      </div>
    </div>
  );
}

export default function Guides({ user }) {
  const [L, reload] = useLoad("/admin/guides");
  const [open, setOpen] = useState(null);
  const [edit, setEdit] = useState(null);
  const [q, setQ] = useState("");
  if (!L) return null;
  if (edit) return <GuideEditor g={edit === "new" ? null : edit} back={() => { setEdit(null); setOpen(null); reload(); }} />;
  const g = open && L.find((x) => x.id === open);
  if (g) return <GuidePage g={g} back={() => setOpen(null)} canEdit={user.is_super} onEdit={() => setEdit(g)} />;
  const V = L.filter((x) => !q || `${x.titolo} ${x.descrizione} ${x.passi.map((p) => p.titolo + p.testo).join(" ")}`.toLowerCase().includes(q.toLowerCase()));
  const cats = [...GCAT, ...new Set(V.map((x) => x.categoria).filter((c) => !GCAT.includes(c)))];
  return (
    <div data-testid="admin-guides">
      <div className="row between" style={{ marginBottom: 6 }}><h2><Ico n="book" s={22} />Guide del portale</h2>
        <div className="row"><input type="text" placeholder="Cerca nelle guide…" value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 260 }} data-testid="guide-search" />{user.is_super && <button className="btn primary" onClick={() => setEdit("new")} data-testid="guide-new-btn">+ Nuova guida</button>}</div></div>
      <p className="muted" style={{ marginBottom: 18 }}>Come funziona ogni sezione della piattaforma, con screenshot e video.</p>
      {cats.map((c) => { const G = V.filter((x) => x.categoria === c); return G.length > 0 && (
        <div key={c} style={{ marginBottom: 22 }}><h4 className="gcat">{c}</h4>
          <div className="ggrid">{G.map((x) => (
            <button key={x.id} className="gcard" onClick={() => setOpen(x.id)} data-testid="guide-card">
              {x.passi.find((p) => p.immagine) ? <img src={fileUrl(x.passi.find((p) => p.immagine).immagine)} alt="" loading="lazy" /> : <div className="gph"><Ico n="book" s={26} /></div>}
              <div className="gb"><b>{x.titolo}</b><span className="small muted">{x.descrizione}</span>
                <span className="small" style={{ marginTop: 6 }}>{x.passi.length} passaggi{(x.video || x.videoUrl) && <> · <Ico n="play" s={12} /> video</>}</span></div>
            </button>
          ))}</div>
        </div>); })}
      {!V.length && <Empty>Nessuna guida trovata.</Empty>}
    </div>
  );
}

function HelpBody({ G }) {
  const [i, setI] = useState(0);
  return (
    <div data-testid="section-help-modal">
      {G.length > 1 && <div className="row" style={{ flexWrap: "wrap", gap: 6, marginBottom: 12 }}>{G.map((x, j) => (
        <button key={x.id} className={`btn sm ${i === j ? "primary" : "ghost"}`} onClick={() => setI(j)} data-testid={`section-help-tab-${j}`}>{x.titolo}</button>))}</div>}
      <GuidePage key={G[i].id} g={G[i]} inModal />
    </div>
  );
}

export function SectionHelp({ view }) {
  const [L] = useLoad("/admin/guides");
  const { openModal } = useUI();
  const G = (L || []).filter((x) => (x.sezioni || []).includes(view));
  if (!G.length) return null;
  const open = () => openModal({ title: "Guida della sezione", wide: true, noCancel: true, ok: "Chiudi", body: <HelpBody G={G} />, res: () => {} });
  return <div className="help-bar"><button className="btn sm help-btn" onClick={open} data-testid="section-help-btn"><Ico n="book" s={14} />Guida{G.length > 1 && <span className="help-n">{G.length}</span>}</button></div>;
}
