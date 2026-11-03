import React, { useState, useEffect, useCallback, createContext, useContext, useRef } from "react";
import { ICONS, scene, sceneW } from "./art.js";
import { get, post, upload, fileUrl, fdt } from "./lib.js";

export const Ico = ({ n, s = 18 }) => (
  <svg className="ico" width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" dangerouslySetInnerHTML={{ __html: ICONS[n] || "" }} />
);
export const Scene = ({ id, wide }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: wide ? sceneW(id) : scene(id) }} />;
export const Badge = ({ k = "neutral", children, ...p }) => <span className={`badge ${k}`} {...p}>{children}</span>;
export const Html = ({ h }) => <span dangerouslySetInnerHTML={{ __html: h }} />;

const Ctx = createContext(null);
export const useUI = () => useContext(Ctx);

export function UIProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const [modal, setModal] = useState(null);
  const toast = useCallback((t, k = "") => {
    const id = Math.random();
    setToasts((L) => [...L.slice(-2), { id, t, k }]);
    setTimeout(() => setToasts((L) => L.filter((x) => x.id !== id)), 3400);
  }, []);
  const ask = useCallback((o) => new Promise((res) => setModal({ ...o, res })), []);
  const close = (v) => { modal && modal.res(v); setModal(null); };
  return (
    <Ctx.Provider value={{ toast, ask, openModal: setModal }}>
      {children}
      {modal && <Modal m={modal} close={close} />}
      <div id="toast">{toasts.map((x) => <div key={x.id} className={`toast ${x.k}`} data-testid="toast">{x.t}</div>)}</div>
    </Ctx.Provider>
  );
}

function Modal({ m, close }) {
  const [v, setV] = useState(m.value || "");
  return (
    <div className="ov" onClick={(e) => e.target === e.currentTarget && close(null)}>
      <div className={`modal ${m.wide ? "wide" : ""}`} data-testid="modal">
        <h3>{m.title}</h3>
        {m.text && <p className="muted" style={{ whiteSpace: "pre-wrap" }}>{m.text}</p>}
        {m.body}
        {m.input && (m.input === "textarea"
          ? <textarea data-testid="modal-input" value={v} onChange={(e) => setV(e.target.value)} placeholder={m.placeholder} />
          : <input data-testid="modal-input" type={m.input} value={v} onChange={(e) => setV(e.target.value)} placeholder={m.placeholder} />)}
        <div className="act">
          {!m.noCancel && <button className="btn" data-testid="modal-cancel" onClick={() => close(null)}>{m.cancel || "Annulla"}</button>}
          {m.ok !== false && <button className={`btn ${m.danger ? "danger solid" : "primary"}`} data-testid="modal-confirm" onClick={() => close(m.input ? v : true)}>{m.ok || "Conferma"}</button>}
        </div>
      </div>
    </div>
  );
}

export function useLoad(path, deps = []) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const reload = useCallback(() => get(path).then(setData).catch((e) => setErr(e.message)), [path]); // eslint-disable-line
  useEffect(() => { if (path) reload(); }, [path, ...deps]); // eslint-disable-line
  return [data, reload, err];
}

export function useAction() {
  const { toast } = useUI();
  return useCallback(async (fn, okMsg) => {
    try { const r = await fn(); if (okMsg) toast(okMsg); return r || true; } catch (e) { toast(e.message, "bad"); return false; }
  }, [toast]);
}

export function UploadBox({ label = "Carica file", hint = "PDF o immagine, max 10 MB", accept = ".pdf,image/*", owner, onDone, small, testid = "upload-input" }) {
  const [busy, setBusy] = useState(false);
  const { toast } = useUI();
  const ref = useRef();
  const pick = async (e) => {
    const f = e.target.files[0];
    e.target.value = "";
    if (!f) return;
    setBusy(true);
    try { const r = await upload(f, owner); await onDone(r); } catch (er) { toast(er.message, "bad"); }
    setBusy(false);
  };
  return (
    <label className={`upload ${small ? "sm" : ""}`}>
      <input ref={ref} type="file" accept={accept} onChange={pick} data-testid={testid} disabled={busy} />
      <Ico n="upload" s={22} />
      <div><b>{busy ? "Caricamento in corso…" : label}</b><div className="small muted">{hint}</div></div>
    </label>
  );
}

export function FileChip({ f, testid }) {
  if (!f) return null;
  const ext = (f.name.split(".").pop() || "").toUpperCase().slice(0, 4);
  return (
    <div className="docf">
      <span className="ic">{ext}</span>
      <span className="nm" style={{ flex: 1, minWidth: 0 }}>{f.name}</span>
      <a className="btn sm" href={fileUrl(f.id)} target="_blank" rel="noreferrer" data-testid={testid || "file-open"}>Apri</a>
    </div>
  );
}

export function CopyBtn({ v, testid }) {
  const { toast } = useUI();
  return <button className="btn sm" data-testid={testid} onClick={() => navigator.clipboard.writeText(v || "").then(() => toast("Copiato negli appunti"))}>Copia</button>;
}

export function Bell({ onGo }) {
  const [open, setOpen] = useState(false);
  const [L, setL] = useState([]);
  const load = useCallback(() => get("/notifications").then(setL).catch(() => {}), []);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);
  const un = L.filter((n) => !n.letto).length;
  const go = async (n) => { await post(`/notifications/${n.id}/read`); setOpen(false); load(); onGo && onGo(n); };
  return (
    <div className="bellwrap">
      <button className="bell" data-testid="notif-bell" onClick={() => { setOpen(!open); load(); }} aria-label="Notifiche">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></svg>
        {un > 0 && <span className="count" data-testid="notif-count">{un}</span>}
      </button>
      {open && (
        <div className="npanel" data-testid="notif-panel">
          <div className="row between nph"><b>Notifiche</b>{un > 0 && <button className="btn sm ghost" data-testid="notif-read-all" onClick={async () => { await post("/notifications/read-all"); load(); }}>Segna tutte come lette</button>}</div>
          {L.length ? L.map((n) => (
            <button key={n.id} className={`nitem ${n.letto ? "" : "new"}`} data-testid="notif-item" onClick={() => go(n)}><Html h={n.testo} /><small>{fdt(n.at)}</small></button>
          )) : <p className="muted small" style={{ padding: 14 }}>Nessuna notifica.</p>}
        </div>
      )}
    </div>
  );
}

export function Field({ label, children, style }) {
  return <div className="field" style={style}><label>{label}</label>{children}</div>;
}

export function Inp({ v, set, k, ...p }) {
  return <input type="text" value={v[k] ?? ""} onChange={(e) => set({ ...v, [k]: e.target.value })} {...p} />;
}

export const Empty = ({ children }) => <div className="empty">{children}</div>;

const toIt = (iso) => (iso && /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso.split("-").reverse().join("/") : "");

export function DateInput({ value, onChange, testid }) {
  const [t, setT] = useState(toIt(value));
  const [bad, setBad] = useState(false);
  useEffect(() => { if (value) { setT(toIt(value)); setBad(false); } }, [value]);
  const type = (e) => {
    const d = e.target.value.replace(/\D/g, "").slice(0, 8);
    const s = d.length > 4 ? `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}` : d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
    setT(s);
    if (d.length === 8) {
      const iso = `${d.slice(4)}-${d.slice(2, 4)}-${d.slice(0, 2)}`;
      const [dd, mm, yy] = [+d.slice(0, 2), +d.slice(2, 4), +d.slice(4)];
      const dt = new Date(yy, mm - 1, dd);
      const ok = yy > 1900 && dt.getFullYear() === yy && dt.getMonth() === mm - 1 && dt.getDate() === dd;
      setBad(!ok);
      onChange(ok ? iso : "");
    } else { setBad(d.length > 0); onChange(""); }
  };
  return <input type="text" inputMode="numeric" placeholder="gg/mm/aaaa" value={t} onChange={type} style={bad ? { borderColor: "var(--bad)" } : undefined} data-testid={testid} />;
}
