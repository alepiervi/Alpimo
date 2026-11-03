import React, { useState, useEffect } from "react";
import { Ico, Badge, useLoad, useAction, useUI, UploadBox, Field, Empty } from "./ui.jsx";
import { get, post, put, del, fileUrl, eur, fd, CAT, LIVELLI, embedUrl } from "./lib.js";
import { PayBox } from "./Aff.jsx";

export function Cover({ c, big }) {
  const [c1, c2, ic] = CAT[c.categoria] || CAT.Altro;
  return (
    <div className={`cover ${big ? "big" : ""}`} style={{ background: `linear-gradient(135deg,${c1},${c2})` }}>
      {c.copertina ? <img src={fileUrl(c.copertina)} alt="" /> : (<>
        <svg className="cv-wave" viewBox="0 0 400 90" preserveAspectRatio="none"><path d="M0 50 Q100 20 200 50 T400 50 V90 H0z" fill="rgba(255,255,255,.14)" /><path d="M0 66 Q100 40 200 66 T400 66 V90 H0z" fill="rgba(255,255,255,.18)" /></svg>
        <div className="cv-ico"><Ico n={ic} s={34} /></div></>)}
      <span className="cv-cat">{c.categoria}</span>
      {c.premium ? <span className="cv-prem">★ Premium · {eur(c.prezzo)}</span> : <span className="cv-free">Gratis</span>}
    </div>
  );
}

function CourseCard({ c, onOpen, admin }) {
  return (
    <button className="ccard" onClick={onOpen} data-testid="course-card">
      <Cover c={c} />
      <div className="cbody">
        <h3>{c.titolo}</h3><p className="cdesc">{c.descrizione}</p>
        <div className="cmeta"><Ico n="play" s={13} />{c.lezioni.length} video · {c.livello}{admin && !c.pubblicato && <Badge k="neutral">Bozza</Badge>}</div>
        <div className="cfoot">
          {admin ? <div className="cstats"><span><b>{c.iscritti}</b> iscritti</span><span><b>{c.completati}</b> completati</span><span><b>{c.acquisti}</b> acquisti</span></div>
            : <><div className="pbar"><i style={{ width: c.progress + "%" }} /></div><span className="small muted">{c.progress}%</span></>}
        </div>
      </div>
    </button>
  );
}

export function AffCourses({ a, me, initial }) {
  const [open, setOpen] = useState(initial || null);
  const [f, setF] = useState("tutti");
  const [L, reload] = useLoad(a.pagamento === "confermato" ? "/aff/courses" : null, [open]);
  if (a.pagamento !== "confermato") {
    const why = a.stato !== "accettata" ? "Prima serve l'approvazione della tua richiesta." : a.urlDefinitivo == null ? "Scegli l'URL definitivo e carica la ricevuta del pagamento." : a.pagamento === "in_verifica" ? "La tua ricevuta è in verifica: appena confermata si sbloccano i corsi." : "Carica la ricevuta del pagamento del sito per sbloccare i corsi.";
    return <div className="card gate" data-testid="courses-locked"><div className="gate-ico"><Ico n="lock" s={28} /></div><h2>Academy affiliati</h2><p className="muted">I corsi sono disponibili dopo la conferma del pagamento del sito e del dominio.</p><div className="note warn">{why}</div></div>;
  }
  if (!L) return null;
  if (open) return <CoursePage id={open} me={me} back={() => { setOpen(null); reload(); }} />;
  const cont = L.find((c) => c.progress > 0 && c.progress < 100 && c.unlocked);
  const V = L.filter((c) => f === "tutti" || (f === "corso" ? c.progress > 0 && c.progress < 100 : f === "completati" ? c.progress === 100 : c.premium));
  return (
    <div data-testid="courses-list">
      <div className="academy">
        <div><p>Academy affiliati</p><h2>Impara, vendi, cresci.</h2><span>{L.length} corsi disponibili per far decollare la tua agenzia.</span></div>
        {cont && <button className="cont" onClick={() => setOpen(cont.id)} data-testid="course-continue"><small>Continua da dove eri rimasto</small><b>{cont.titolo}</b><div className="pbar light"><i style={{ width: cont.progress + "%" }} /></div><span>{cont.progress}% completato</span></button>}
      </div>
      <div className="row chips" style={{ margin: "18px 0 14px" }}>
        {[["tutti", "Tutti"], ["corso", "In corso"], ["completati", "Completati"], ["premium", "Premium"]].map(([k, l]) => <button key={k} className={`chip ${f === k ? "on" : ""}`} onClick={() => setF(k)} data-testid={`course-filter-${k}`}>{l}</button>)}
      </div>
      {V.length ? <div className="cgrid">{V.map((c) => <CourseCard key={c.id} c={c} onOpen={() => setOpen(c.id)} />)}</div> : <Empty>Nessun corso in questa sezione.</Empty>}
    </div>
  );
}

function Player({ l, onEnded }) {
  if (!l || l.locked) return <div className="player"><div className="pl-in"><div className="play"><Ico n="lock" s={26} /></div><b>Lezione bloccata</b><span>Acquista il corso per sbloccare tutti i video.</span></div></div>;
  if (l.file) return <div className="player"><video key={l.id} src={fileUrl(l.file)} controls onEnded={onEnded} data-testid="lesson-video" /></div>;
  const e = embedUrl(l.url);
  if (e) return <div className="player"><iframe key={l.id} src={e} title={l.titolo} style={{ width: "100%", height: "100%", border: 0 }} allow="autoplay; fullscreen; picture-in-picture" allowFullScreen data-testid="lesson-embed" /></div>;
  return <div className="player"><div className="pl-in"><b>{l.titolo}</b>{l.url ? <a className="btn" href={l.url} target="_blank" rel="noreferrer">Apri il video</a> : <span>Video non ancora disponibile</span>}</div></div>;
}

function CoursePage({ id, me, back }) {
  const [c, setC] = useState(null);
  const [cur, setCur] = useState(0);
  const act = useAction();
  const load = () => get(`/aff/courses/${id}`).then(setC);
  useEffect(() => { load(); }, [id]); // eslint-disable-line
  if (!c) return null;
  const l = c.lezioni[cur];
  const done = async () => { if (l && !l.locked && !l.done) { await act(() => post(`/aff/courses/${id}/done`, { lid: l.id }), "Lezione completata"); load(); } };
  const next = () => setCur(Math.min(cur + 1, c.lezioni.length - 1));
  return (
    <div data-testid="course-page">
      <button className="back" onClick={back} data-testid="course-back">← Tutti i corsi</button>
      <div className="chead"><Cover c={c} /><div><h2>{c.titolo}</h2><p className="muted">{c.descrizione}</p><div className="row"><Badge k="info">{c.livello}</Badge><span className="small muted">{c.lezioni.length} video</span></div>
        <div className="row" style={{ marginTop: 8 }}><div className="pbar"><i style={{ width: c.progress + "%" }} /></div><b data-testid="course-progress">{c.progress}%</b></div></div></div>
      {c.progress === 100 && <div className="note ok" data-testid="course-completed">Corso completato! Complimenti.</div>}
      <div className="learn">
        <div>
          <Player l={l} onEnded={done} />
          {l && <div className="card" style={{ marginTop: 14 }}><div className="row between"><h3>{l.titolo}</h3><div className="row">
            {!l.locked && <button className="btn" disabled={l.done} onClick={done} data-testid="lesson-complete">{l.done ? "Completato" : "Segna come completato"}</button>}
            <button className="btn primary" disabled={cur >= c.lezioni.length - 1} onClick={next} data-testid="lesson-next">Video successivo</button></div></div>
            {l.descrizione && <p className="muted" style={{ marginTop: 8 }}>{l.descrizione}</p>}</div>}
          {c.premium && !c.unlocked && <BuyBox c={c} me={me} reload={load} />}
        </div>
        <div className="card lezlist">
          <h4 style={{ marginTop: 0 }}>Lezioni</h4>
          {c.lezioni.map((x, i) => (
            <button key={x.id} className={`lz ${x.done ? "done" : ""} ${i === cur ? "on" : ""}`} onClick={() => setCur(i)} data-testid={`lesson-item-${i}`}>
              <span className="lzi">{x.done ? <Ico n="check" s={14} /> : x.locked ? <Ico n="lock" s={12} /> : i + 1}</span>
              <span className="lzt">{x.titolo}<small>{x.durata}{i === 0 && c.premium && !c.unlocked ? " · Anteprima gratuita" : ""}</small></span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function BuyBox({ c, me, reload }) {
  const act = useAction();
  const p = c.purchase;
  return (
    <div className="card buy" data-testid="course-buy-box">
      <h3>Sblocca il corso completo</h3>
      {p && p.stato === "in_verifica" ? <div className="note info" style={{ marginTop: 10 }}>Ricevuta in verifica: sbloccheremo il corso appena confermato il pagamento.</div> : (<>
        {p && p.stato === "respinto" && <div className="note bad" style={{ marginTop: 10 }} data-testid="course-buy-rejected">Pagamento rifiutato: {p.nota}</div>}
        <div style={{ margin: "12px 0" }}><PayBox pag={me.pag} a={me.aff} importo={c.prezzo} causaleText={`Corso ${c.titolo} - ${me.aff.nomeAgenzia}`} /></div>
        <UploadBox label="Carica la ricevuta del corso" testid="course-receipt-upload" onDone={(f) => act(() => post(`/aff/courses/${c.id}/buy`, { file: f.id }), "Ricevuta inviata").then((r) => r && reload())} />
      </>)}
    </div>
  );
}

// ---------------- ADMIN ----------------
export function AdminCourses({ initial }) {
  const [L, reload] = useLoad("/admin/courses");
  const [P, reloadP] = useLoad("/admin/course-purchases");
  const [edit, setEdit] = useState(initial ? "x" : null);
  const act = useAction();
  const { ask } = useUI();
  if (!L || !P) return null;
  if (edit) return <CourseEditor c={edit === "new" ? null : L.find((c) => c.id === edit)} back={() => { setEdit(null); reload(); }} />;
  const decide = async (p, confirm) => {
    const nota = confirm ? "" : await ask({ title: "Rifiuta pagamento", input: "textarea", placeholder: "Motivo del rifiuto" });
    if (!confirm && !nota) return;
    act(() => post(`/admin/course-purchases/${p.id}`, { confirm, nota }), confirm ? "Corso sbloccato" : "Pagamento rifiutato").then(() => { reloadP(); reload(); });
  };
  const pend = P.filter((p) => p.stato === "in_verifica");
  return (
    <div data-testid="admin-courses">
      <div className="row between" style={{ marginBottom: 16 }}><h2><Ico n="book" s={22} />Corsi</h2><button className="btn primary" onClick={() => setEdit("new")} data-testid="course-new-btn">+ Nuovo corso</button></div>
      {pend.length > 0 && <div className="card" style={{ marginBottom: 16 }} data-testid="course-purchases-pending"><h3>Acquisti Premium da verificare</h3>
        {pend.map((p) => <div className="todo" key={p.id}><div><b>{p.agenzia}</b> · {p.descrizione} · {eur(p.totale)}<div className="small muted">{fd(p.at)}</div></div>
          <div className="row">{p.ricevutaInfo && <a className="btn sm" href={fileUrl(p.ricevuta)} target="_blank" rel="noreferrer">Vedi ricevuta</a>}<button className="btn sm primary" onClick={() => decide(p, true)} data-testid="course-purchase-confirm">Conferma e sblocca</button><button className="btn sm danger" onClick={() => decide(p, false)} data-testid="course-purchase-reject">Rifiuta</button></div></div>)}
      </div>}
      {L.length ? <div className="cgrid">{L.map((c) => <CourseCard key={c.id} c={c} admin onOpen={() => setEdit(c.id)} />)}</div> : <Empty>Nessun corso.</Empty>}
    </div>
  );
}

function CourseEditor({ c, back }) {
  const [f, setF] = useState(c || { titolo: "", categoria: "Sito", livello: "Base", descrizione: "", premium: false, prezzo: 0, pubblicato: false, copertina: null, lezioni: [] });
  const act = useAction();
  const { ask } = useUI();
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const setL = (i, k, v) => setF({ ...f, lezioni: f.lezioni.map((l, j) => (j === i ? { ...l, [k]: v } : l)) });
  const move = (i, d) => { const L = [...f.lezioni]; const j = i + d; if (j < 0 || j >= L.length) return; [L[i], L[j]] = [L[j], L[i]]; setF({ ...f, lezioni: L }); };
  const save = async () => {
    const body = { ...f, prezzo: parseFloat(f.prezzo) || 0 };
    const r = await act(() => (c ? put(`/admin/courses/${c.id}`, body) : post("/admin/courses", body)), "Corso salvato");
    if (r) back();
  };
  const remove = async () => { if (await ask({ title: "Eliminare il corso?", danger: true, ok: "Elimina" })) act(() => del(`/admin/courses/${c.id}`), "Corso eliminato").then((r) => r && back()); };
  return (
    <div data-testid="course-editor">
      <button className="back" onClick={back}>← Corsi</button>
      <div className="editc">
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>{c ? "Modifica corso" : "Nuovo corso"}</h3>
          <div style={{ display: "grid", gap: 12 }}>
            <Field label="Titolo"><input type="text" value={f.titolo} onChange={set("titolo")} data-testid="course-title" /></Field>
            <div className="grid2">
              <Field label="Categoria"><select value={f.categoria} onChange={set("categoria")} data-testid="course-category">{Object.keys(CAT).map((k) => <option key={k}>{k}</option>)}</select></Field>
              <Field label="Livello"><select value={f.livello} onChange={set("livello")}>{LIVELLI.map((k) => <option key={k}>{k}</option>)}</select></Field>
            </div>
            <Field label="Descrizione"><textarea value={f.descrizione} onChange={set("descrizione")} data-testid="course-desc" /></Field>
            <div className="row"><label className="chk"><input type="checkbox" checked={f.premium} onChange={set("premium")} data-testid="course-premium" />Corso Premium (a pagamento)</label>
              {f.premium && <input type="number" style={{ width: 130 }} value={f.prezzo} onChange={set("prezzo")} placeholder="Prezzo € IVA incl." data-testid="course-price" />}</div>
            <label className="chk"><input type="checkbox" checked={f.pubblicato} onChange={set("pubblicato")} data-testid="course-published" />Pubblicato (visibile agli affiliati)</label>
          </div>
          <h4>Video ({f.lezioni.length})</h4>
          {f.lezioni.map((l, i) => (
            <div className="lzedit" key={l.id || i}>
              <span className="lzn">{i + 1}</span>
              <div style={{ display: "grid", gap: 8 }}>
                <div className="grid2" style={{ gridTemplateColumns: "2fr 1fr" }}><input type="text" placeholder="Titolo" value={l.titolo} onChange={(e) => setL(i, "titolo", e.target.value)} data-testid={`lesson-title-${i}`} /><input type="text" placeholder="Durata (es. 8 min)" value={l.durata} onChange={(e) => setL(i, "durata", e.target.value)} /></div>
                <input type="text" placeholder="Descrizione" value={l.descrizione} onChange={(e) => setL(i, "descrizione", e.target.value)} />
                <input type="text" placeholder="Link YouTube, Vimeo o Drive (oppure carica un MP4)" value={l.url || ""} onChange={(e) => setL(i, "url", e.target.value)} data-testid={`lesson-url-${i}`} />
                {l.file ? <div className="row"><Badge k="ok">MP4 caricato</Badge><button className="btn sm ghost" onClick={() => setL(i, "file", null)}>Rimuovi file</button></div>
                  : <UploadBox small label="Carica video MP4" hint="MP4, max 500 MB" accept="video/mp4,.mp4,.mov,.webm" owner="public" testid={`lesson-upload-${i}`} onDone={(r) => setL(i, "file", r.id)} />}
              </div>
              <div className="lzc"><button className="btn sm" onClick={() => move(i, -1)}>↑</button><button className="btn sm" onClick={() => move(i, 1)}>↓</button><button className="btn sm danger" onClick={() => setF({ ...f, lezioni: f.lezioni.filter((_, j) => j !== i) })} data-testid={`lesson-delete-${i}`}>✕</button></div>
            </div>
          ))}
          <button className="btn sm" onClick={() => setF({ ...f, lezioni: [...f.lezioni, { titolo: "", durata: "", descrizione: "", url: "", file: null }] })} data-testid="lesson-add">+ Aggiungi video</button>
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}>{c && <button className="btn danger" onClick={remove} data-testid="course-delete">Elimina</button>}<button className="btn primary" onClick={save} data-testid="course-save">Salva corso</button></div>
        </div>
        <div className="card">
          <h4 style={{ marginTop: 0 }}>Copertina</h4>
          <Cover c={f} />
          <div style={{ marginTop: 10 }}>{f.copertina ? <button className="btn sm" onClick={() => setF({ ...f, copertina: null })}>Rimuovi immagine</button>
            : <UploadBox small label="Carica immagine" hint="JPG o PNG" accept="image/*" owner="public" testid="course-cover-upload" onDone={(r) => setF({ ...f, copertina: r.id })} />}</div>
        </div>
      </div>
    </div>
  );
}

