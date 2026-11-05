import React, { useState, useEffect } from "react";
import { Ico, Scene, Badge, Bell, useLoad, useAction, useUI, UploadBox, FileChip, CopyBtn, Field, Empty } from "./ui.jsx";
import { post, put, fileUrl, STEPS, FASI, fd, eur, daysTo, affName, stepOf, statoInfo, causale, DOCT } from "./lib.js";
import { DocTab, PagTab, NewsTab, MatTab } from "./AffTabs.jsx";
import { AffCourses } from "./Courses.jsx";
import Tickets from "./Tickets.jsx";

const TABS = [["percorso", "Il mio percorso", "plane"], ["documenti", "Documenti", "file"], ["pagamenti", "Pagamenti", "card"], ["bacheca", "Bacheca", "news"], ["materiali", "Materiali", "folder"], ["corsi", "Corsi", "book"], ["ticket", "Assistenza", "ticket"]];

export default function AffApp({ user, logout }) {
  const [tab, setTab] = useState("percorso");
  const [ref, setRef] = useState(null);
  const [me, reload] = useLoad("/aff/me", [tab]);
  if (!me) return <div className="denied muted">Caricamento…</div>;
  const a = me.aff;
  const go = (n) => { setRef(n.ref || null); setTab(n.view === "documenti" || TABS.some((t) => t[0] === n.view) ? n.view : "percorso"); };
  return (
    <div data-testid="affiliate-app">
      <div className="top">
        <div className="brand"><img src="/logo-alpimo.png" alt="Alpimo" className="brand-logo" data-testid="brand-logo" /><span>Portale Affiliati</span></div>
        <div className="right">
          <span className="small muted">{user.email}</span>
          <Bell onGo={go} />
          <button className="btn sm" onClick={logout} data-testid="logout-btn"><Ico n="logout" s={15} />Esci</button>
        </div>
      </div>
      <div className="wrap">
        <Trip a={a} />
        <div className="subtabs">
          {TABS.map(([k, l, i]) => (
            <button key={k} className={tab === k ? "on" : ""} onClick={() => { setTab(k); setRef(null); }} data-testid={`aff-tab-${k}`}>
              <Ico n={i} s={16} />{l}{k === "bacheca" && me.newsUnread > 0 && <span className="count">{me.newsUnread}</span>}
            </button>
          ))}
        </div>
        {tab === "percorso" && <Percorso me={me} reload={reload} setTab={setTab} />}
        {tab === "documenti" && <DocTab me={me} reload={reload} />}
        {tab === "pagamenti" && <PagTab />}
        {tab === "bacheca" && <NewsTab onRead={reload} />}
        {tab === "materiali" && <MatTab />}
        {tab === "corsi" && <AffCourses a={a} me={me} initial={ref} />}
        {tab === "ticket" && <Tickets role="affiliate" initial={ref} />}
      </div>
    </div>
  );
}

function Trip({ a }) {
  const st = stepOf(a);
  const [lbl, k] = statoInfo(a);
  return (
    <div className="trip" data-testid="trip-hero">
      <Scene id="trip" />
      <div className="trip-in">
        <div className="trip-top">
          <div>
            <p>Benvenuto a bordo</p>
            <h1>{affName(a)}</h1>
            <div className="trip-sub"><Ico n="globe" s={14} />{a.urlDef || "URL da definire"}</div>
          </div>
          <Badge k={k} data-testid="aff-status-badge">{lbl}</Badge>
        </div>
        <div className="route" data-testid="itinerary">
          {STEPS.map((s, i) => (
            <div key={s} className={`stop ${i < st || (st === 5 && a.consegnato) ? "done" : i === st ? "cur" : ""}`}>
              <div className="pin">{i < st || (st === 5 && a.consegnato) ? <Ico n="check" s={16} /> : i === st ? <Ico n="plane" s={16} /> : i + 1}</div>{s}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Percorso({ me, reload, setTab }) {
  const a = me.aff;
  return (
    <div>
      {me.newsUnread > 0 && <div className="note info teaser" data-testid="alert-news"><span>Hai <b>{me.newsUnread}</b> comunicazioni non lette in bacheca.</span><button className="btn sm" onClick={() => setTab("bacheca")}>Leggi</button></div>}
      {me.docsMancanti.length > 0 && <div className="note warn teaser" data-testid="alert-docs"><span>Documenti obbligatori mancanti: {me.docsMancanti.map((d) => DOCT[d][0]).join(", ")}.</span><button className="btn sm" onClick={() => setTab("documenti")}>Carica</button></div>}
      <Profilo a={a} reload={reload} setTab={setTab} />
      {a.stato === "accettata" && <LogoUrl a={a} reload={reload} />}
      {a.urlDefinitivo != null && a.pagamento !== "confermato" && <Pagamento me={me} reload={reload} />}
      {a.pagamento === "confermato" && a.consegna && <Consegna a={a} />}
      {a.consegnato && <Sito a={a} reload={reload} />}
    </div>
  );
}

function Profilo({ a, reload, setTab }) {
  const edit = a.stato === "bozza" || a.stato === "rifiutata";
  const [f, setF] = useState(null);
  const act = useAction();
  const { ask } = useUI();
  useEffect(() => { setF({ ...a, urls: a.urls.map((u) => u.value) }); }, [a]);
  if (!f) return null;
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const setP = (i, k, v) => setF({ ...f, persone: f.persone.map((p, j) => (j === i ? { ...p, [k]: v } : p)) });
  const save = () => act(() => put("/aff/profile", f), "Bozza salvata").then((r) => r && reload());
  const send = async () => {
    if (!(await put("/aff/profile", f).then(() => true).catch(() => false))) return act(() => put("/aff/profile", f));
    if (!(await ask({ title: "Inviare la richiesta?", text: "Dopo l'invio i dati non saranno più modificabili fino alla risposta dell'amministratore." }))) return;
    act(() => post("/aff/submit"), "Richiesta inviata").then((r) => r && reload());
  };
  return (
    <div className="card" data-testid="card-profilo">
      <div className="card-h"><h3><span className="num">1</span>Dati affiliato</h3>{!edit && <Badge k={statoInfo(a)[1]}>{a.stato === "in_attesa" ? "In attesa di approvazione" : "Inviati"}</Badge>}</div>
      {a.stato === "rifiutata" && <div className="note bad" data-testid="reject-reason">Richiesta non approvata. Motivo: <b>{a.nota}</b>. Correggi i dati e inviala di nuovo.</div>}
      {a.stato === "in_attesa" && <div className="note info">La tua richiesta è in valutazione: riceverai un'email con l'esito.</div>}
      {edit ? (
        <div style={{ display: "grid", gap: 12 }}>
          <div className="seg">
            {["persona", "azienda"].map((t) => <label key={t}><input type="radio" checked={f.tipo === t} onChange={() => setF({ ...f, tipo: t })} data-testid={`profile-tipo-${t}`} />{t === "persona" ? "Persona fisica" : "Azienda"}</label>)}
          </div>
          {f.tipo === "persona" ? (
            <div>
              {f.persone.map((p, i) => (
                <div className="persona" key={i}>
                  <Field label="Nome"><input type="text" value={p.nome} onChange={(e) => setP(i, "nome", e.target.value)} data-testid={`profile-nome-${i}`} /></Field>
                  <Field label="Cognome"><input type="text" value={p.cognome} onChange={(e) => setP(i, "cognome", e.target.value)} data-testid={`profile-cognome-${i}`} /></Field>
                  <button className="btn sm danger" disabled={f.persone.length < 2} onClick={() => setF({ ...f, persone: f.persone.filter((_, j) => j !== i) })}>Rimuovi</button>
                </div>
              ))}
              <button className="btn sm" data-testid="profile-add-persona" onClick={() => setF({ ...f, persone: [...f.persone, { nome: "", cognome: "" }] })}>+ Aggiungi affiliato</button>
            </div>
          ) : (
            <div className="grid3">
              <Field label="Ragione sociale"><input type="text" value={f.azienda} onChange={set("azienda")} data-testid="profile-azienda" /></Field>
              <Field label="P.IVA"><input type="text" value={f.piva} onChange={set("piva")} data-testid="profile-piva" /></Field>
              <Field label="Referente"><input type="text" value={f.referente} onChange={set("referente")} data-testid="profile-referente" /></Field>
            </div>
          )}
          <div className="grid3">
            <Field label="Nome dell'agenzia"><input type="text" value={f.nomeAgenzia} onChange={set("nomeAgenzia")} data-testid="profile-agenzia" /></Field>
            <Field label="Telefono"><input type="text" value={f.telefono} onChange={set("telefono")} data-testid="profile-telefono" /></Field>
            <Field label="Città"><input type="text" value={f.citta} onChange={set("citta")} data-testid="profile-citta" /></Field>
          </div>
          <div>
            <div className="lbl" style={{ marginBottom: 6 }}>URL desiderati (fino a 3, in ordine di preferenza)</div>
            {[0, 1, 2].map((i) => (
              <div className="urlrow" key={i}><span className="i">{i + 1}</span>
                <input type="text" placeholder="es. miaagenzia.it" value={f.urls[i] || ""} onChange={(e) => setF({ ...f, urls: f.urls.map((u, j) => (j === i ? e.target.value : u)) })} data-testid={`profile-url-${i}`} />
                <span />
              </div>
            ))}
          </div>
          <div className="note info small">Per inviare la richiesta servono anche i dati di fatturazione completi. <a href="#d" onClick={(e) => { e.preventDefault(); setTab("documenti"); }}>Compilali in Documenti</a>.</div>
          <div className="row end-m" style={{ justifyContent: "flex-end" }}>
            <button className="btn" onClick={save} data-testid="profile-save">Salva bozza</button>
            <button className="btn primary" onClick={send} data-testid="profile-submit">Invia richiesta</button>
          </div>
        </div>
      ) : <DatiKV a={a} />}
    </div>
  );
}

export function DatiKV({ a }) {
  return (
    <dl className="kv">
      <dt>Tipo</dt><dd>{a.tipo === "azienda" ? "Azienda" : "Persona fisica"}</dd>
      {a.tipo === "azienda" ? <><dt>Ragione sociale</dt><dd>{a.azienda}</dd><dt>P.IVA</dt><dd>{a.piva}</dd><dt>Referente</dt><dd>{a.referente}</dd></>
        : <><dt>Affiliati</dt><dd>{a.persone.map((p) => `${p.nome} ${p.cognome}`).join(", ")}</dd></>}
      <dt>Agenzia</dt><dd>{a.nomeAgenzia}</dd><dt>Telefono</dt><dd>{a.telefono}</dd><dt>Città</dt><dd>{a.citta}</dd>
      <dt>URL proposti</dt><dd>{a.urls.filter((u) => u.value).map((u) => u.value).join(" · ")}</dd>
    </dl>
  );
}

const URLST = { da_verificare: ["In verifica", "warn"], disponibile: ["Disponibile", "ok"], non_disponibile: ["Non disponibile", "bad"] };

function LogoUrl({ a, reload }) {
  const act = useAction();
  const { ask } = useUI();
  const [alt, setAlt] = useState({});
  const logoOk = a.sceltaFinale || a.loghi.every(Boolean);
  const finalTxt = "\n\nCon logo e URL scelti, le altre proposte verranno eliminate e la scelta sarà definitiva.";
  const choose = async (i) => {
    if (!(await ask({ title: "Confermi l'URL definitivo?", text: `${a.urls[i].value}\n\nDopo la conferma non potrai più cambiarlo.${a.logoScelto != null ? finalTxt : ""}` }))) return;
    act(() => post("/aff/url-final", { idx: i }), "URL definitivo confermato").then((r) => r && reload());
  };
  const pickLogo = async (i) => {
    if (a.sceltaFinale || a.logoScelto === i) return;
    if (a.urlDefinitivo != null && !(await ask({ title: `Confermi il logo ${i + 1}?`, text: finalTxt.trim() }))) return;
    act(() => post("/aff/logo", { idx: i }), "Logo selezionato").then((r) => r && reload());
  };
  const logo = a.logoScelto != null && a.loghiInfo[a.logoScelto];
  return (
    <div className="card" data-testid="card-logo-url">
      {!a.sceltaFinale && <div className="note info small" data-testid="final-choice-note">Quando avrai scelto sia il logo sia l'URL definitivo, le proposte non scelte verranno eliminate.</div>}
      <div className="card-h"><h3><span className="num">2</span>URL e logo</h3></div>
      <h4>Scegli il logo</h4>
      {logoOk ? (
        <div className="logos">
          {a.loghiInfo.map((f, i) => f && (
            <button key={i} className={`logo-tile ${a.logoScelto === i ? "sel" : ""}`} onClick={() => pickLogo(i)} data-testid={`logo-choice-${i}`}>
              {a.logoScelto === i && <span className="tag"><Badge k="accent">Scelto</Badge></span>}
              <div className="img"><img src={fileUrl(f.id)} alt={`Logo ${i + 1}`} /></div><b>Proposta {i + 1}</b>
            </button>
          ))}
        </div>
      ) : <Empty>Stiamo preparando le 3 proposte di logo: ti avviseremo appena pronte.</Empty>}
      <h4>URL del sito</h4>
      {a.urls.map((u, i) => (u.value || a.urls[i].stato === "non_disponibile") && (
        <div key={i} className={`urlrow ${a.urlDefinitivo === i ? "def" : ""}`} data-testid={`url-row-${i}`}>
          <span className="i">{i + 1}</span>
          <div className="row"><span className="mono">{u.value}</span><Badge k={URLST[u.stato][1]}>{URLST[u.stato][0]}</Badge>{a.urlDefinitivo === i && <Badge k="info">Definitivo</Badge>}</div>
          <div className="row">
            {a.urlDefinitivo == null && u.stato === "disponibile" && <button className="btn sm primary" onClick={() => choose(i)} data-testid={`url-choose-${i}`}>Scegli come definitivo</button>}
            {a.urlDefinitivo == null && u.stato === "non_disponibile" && (<>
              <input type="text" style={{ width: 180 }} placeholder="URL alternativo" value={alt[i] || ""} onChange={(e) => setAlt({ ...alt, [i]: e.target.value })} data-testid={`url-alt-input-${i}`} />
              <button className="btn sm" onClick={() => act(() => post("/aff/url-alt", { idx: i, value: alt[i] }), "Nuovo URL proposto").then((r) => r && reload())} data-testid={`url-alt-submit-${i}`}>Proponi</button>
            </>)}
          </div>
        </div>
      ))}
      <div className="browser" data-testid="browser-preview">
        <div className="bar"><div className="dots"><i /><i /><i /></div><div className="addr">https://<b>{a.urlDef || a.urls.find((u) => u.value)?.value || "tuaagenzia.it"}</b></div></div>
        <div className="site">{logo ? <img src={fileUrl(logo.id)} alt="logo" /> : <span className="muted small">Logo</span>}<span className="nm">{a.nomeAgenzia}</span></div>
        <div className="heroimg"><Scene id="br" /><span>Viaggi su misura</span></div>
      </div>
    </div>
  );
}

export function PayBox({ pag, a, importo, causaleText }) {
  if (!pag.iban || !pag.intestatario) return <div className="note warn">I dati per il pagamento non sono ancora disponibili: ti avviseremo a breve.</div>;
  const iva = parseFloat(String(pag.iva).replace(",", ".")) || 0;
  const tot = importo != null ? importo : (parseFloat(String(pag.importo).replace(",", ".")) || 0) * (1 + iva / 100);
  const rows = [["Intestatario", pag.intestatario, 1], ["IBAN", pag.iban, 1], pag.banca && ["Banca", pag.banca], pag.bic && ["BIC / SWIFT", pag.bic, 1], ["Causale", causaleText || causale(pag, a), 1]].filter(Boolean);
  return (
    <>
      <div className="pay" data-testid="pay-box">
        <div className="k">Importo</div><div><span className="tot" data-testid="pay-total">{eur(tot)}</span><div className="small muted">{importo != null ? "IVA inclusa" : `${eur(pag.importo)} + IVA ${iva}%`}</div></div><div />
        {rows.map(([k, v, c]) => <React.Fragment key={k}><div className="k">{k}</div><div className={`v ${k === "IBAN" ? "mono" : ""}`}>{v}</div>{c ? <CopyBtn v={v} testid={`copy-${k.toLowerCase().split(" ")[0]}`} /> : <div />}</React.Fragment>)}
        {pag.scadenza && importo == null && <><div className="k">Termine</div><div className="v">{pag.scadenza}</div><div /></>}
      </div>
      {pag.note && <p className="small muted" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>{pag.note}</p>}
    </>
  );
}

function Pagamento({ me, reload }) {
  const a = me.aff;
  const act = useAction();
  return (
    <div className="card" data-testid="card-pagamento">
      <div className="card-h"><h3><span className="num">3</span>Pagamento</h3>{a.pagamento === "in_verifica" && <Badge k="warn">Ricevuta in verifica</Badge>}</div>
      {a.pagamento === "respinto" && <div className="note bad" data-testid="payment-reject-reason">Ricevuta respinta. Motivo: <b>{a.notaPagamento}</b>. Caricane una nuova.</div>}
      <PayBox pag={me.pag} a={a} />
      <h4>Ricevuta del bonifico</h4>
      {a.ricevutaInfo && <FileChip f={a.ricevutaInfo} testid="receipt-open" />}
      {a.pagamento === "in_verifica" ? <div className="note info" style={{ marginTop: 10 }}>Stiamo verificando il pagamento: riceverai un'email di conferma.</div>
        : <UploadBox label="Carica la ricevuta" testid="receipt-upload" onDone={(f) => act(() => post("/aff/receipt", { file: f.id }), "Ricevuta caricata").then((r) => r && reload())} />}
    </div>
  );
}

function Consegna({ a }) {
  const c = a.consegna;
  const fase = a.consegnato ? 3 : c.fase;
  const tot = Math.max(1, daysTo(c.dataPrevista) + (Date.now() - new Date(c.inizio + "T00:00")) / 86400000);
  const pct = a.consegnato ? 100 : Math.min(100, Math.round(((Date.now() - new Date(c.inizio + "T00:00")) / 86400000 / tot) * 100));
  const left = daysTo(c.dataPrevista);
  return (
    <div className="card" data-testid="card-consegna">
      <div className="card-h"><h3><span className="num">4</span>Tempi di consegna</h3></div>
      <div className="row between">
        <div><div className="lbl">Consegna prevista</div><div className="big" data-testid="delivery-date">{fd(c.dataPrevista)}</div></div>
        <div style={{ textAlign: "right" }}><div className="lbl">{a.consegnato ? "Stato" : "Giorni mancanti"}</div><div className="big">{a.consegnato ? "Consegnato" : Math.max(0, left)}</div></div>
      </div>
      <div className="progress"><i style={{ width: pct + "%" }} /></div>
      <div className="fasi">{FASI.map((f, i) => <div key={f} className={i < fase || (a.consegnato && i === 3) ? "done" : i === fase ? "cur" : ""}>{f}<small>{i < fase || a.consegnato ? "Completata" : i === fase ? "In corso" : "Da iniziare"}</small></div>)}</div>
    </div>
  );
}

function CredRow({ k, v, secret, off, testid }) {
  const [show, setShow] = useState(!secret);
  return (
    <>
      <div className="lbl">{k}</div>
      <div className="v"><input type={show ? "text" : "password"} readOnly value={v || ""} className={off ? "off" : ""} data-testid={testid} /></div>
      <div className="row">{secret && <button className="btn sm" onClick={() => setShow(!show)} data-testid={`${testid}-show`}>{show ? "Nascondi" : "Mostra"}</button>}<CopyBtn v={v} testid={`${testid}-copy`} /></div>
    </>
  );
}

function Sito({ a, reload }) {
  const act = useAction();
  const { ask } = useUI();
  const c = a.cred || {};
  const req = async () => { if (await ask({ title: "Mettere online il sito?", text: "Confermi di aver terminato le modifiche? L'amministratore riceverà la richiesta." })) act(() => post("/aff/request-online"), "Richiesta inviata").then((r) => r && reload()); };
  return (
    <div className="card pass" data-testid="card-sito">
      <div className="pass-h"><b><Ico n="plane" s={18} />Il tuo sito · Carta d'imbarco</b><span className="route-mini">PORTALE <i /> {(a.urlDef || "").toUpperCase()}</span></div>
      <div className="pass-b">
        <div className="cred">
          <CredRow k="URL Admin" v={c.url} testid="cred-url" />
          <CredRow k="Utente" v={c.utente} testid="cred-user" />
          <CredRow k="Password Admin" v={c.password} secret testid="cred-pass" />
          <CredRow k="Password sito" v={c.passwordSito} secret off={a.online} testid="cred-sitepass" />
        </div>
        {(c.emailUrl || c.emailUtente) && <><div className="lbl" style={{ marginTop: 14 }}><Ico n="mail" s={14} /> Casella email</div>
          <div className="cred" data-testid="cred-email-box">
            <CredRow k="URL webmail" v={c.emailUrl} testid="cred-email-url" />
            <CredRow k="Utente" v={c.emailUtente} testid="cred-email-user" />
            <CredRow k="Password provvisoria" v={c.emailPassword} secret testid="cred-email-pass" />
          </div>
          <p className="small muted" style={{ marginTop: 6 }}>Al primo accesso cambia la password provvisoria della casella email.</p></>}
        <p className="small muted" style={{ marginTop: 10 }}>{a.online ? "Il sito è online: la password di anteprima non è più necessaria." : "La password sito protegge l'anteprima finché il sito non viene messo online."}</p>
        <div className="row between" style={{ marginTop: 14 }}>
          <div><div className="lbl">Dominio</div><b className="mono">{a.urlDef}</b> · scadenza {fd(a.dominio.scadenza)}</div>
          {a.online ? <Badge k="ok">Sito online</Badge> : a.richiestaOnline ? <Badge k="warn" data-testid="online-requested">Messa online richiesta</Badge>
            : <button className="btn accent" onClick={req} data-testid="request-online-btn">Ho finito le modifiche: metti online</button>}
        </div>
      </div>
    </div>
  );
}
