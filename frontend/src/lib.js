import { ICONS } from "./art.js";

Object.assign(ICONS, {
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  file: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/>',
  download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>',
  news: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/>',
  folder: '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  logout: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l5-5-5-5M15 12H4"/>',
  play: '<path d="M7 4l13 8-13 8z"/>',
  upload: '<path d="M12 20V9M7 14l5-5 5 5M5 4h14"/>',
});

export const API = process.env.REACT_APP_BACKEND_URL + "/api";
export const fileUrl = (id, dl) => `${API}/files/${id}${dl ? "?dl=1" : ""}`;

function errText(d) {
  if (!d) return "Si è verificato un errore, riprova.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => e.msg || JSON.stringify(e)).join(" ");
  return d.msg || String(d);
}

let refreshing = null;
export async function api(method, path, body, retry = true) {
  const opt = { method, credentials: "include", headers: {} };
  if (body instanceof FormData) opt.body = body;
  else if (body !== undefined) { opt.body = JSON.stringify(body); opt.headers["Content-Type"] = "application/json"; }
  const r = await fetch(API + path, opt);
  if (r.status === 401 && retry && !path.startsWith("/auth/")) {
    refreshing = refreshing || fetch(API + "/auth/refresh", { method: "POST", credentials: "include" }).finally(() => setTimeout(() => (refreshing = null), 100));
    const rr = await refreshing;
    if (rr.ok) return api(method, path, body, false);
  }
  const ct = r.headers.get("content-type") || "";
  const data = ct.includes("json") ? await r.json() : await r.text();
  if (!r.ok) throw new Error(errText(data && data.detail));
  return data;
}
export const get = (p) => api("GET", p);
export const post = (p, b = {}) => api("POST", p, b);
export const put = (p, b = {}) => api("PUT", p, b);
export const del = (p) => api("DELETE", p);
export async function upload(file, owner) {
  const fd = new FormData();
  fd.append("file", file);
  if (owner) fd.append("owner", owner);
  return api("POST", "/files", fd);
}

export const STEPS = ["Dati", "Approvazione", "URL e logo", "Pagamento", "Realizzazione", "Consegna"];
export const FASI = ["Pagamento ricevuto", "Sviluppo in corso", "Revisione e test", "Consegnato"];
export const REM = [30, 15, 7, 1];
export const REM_LBL = { 30: "1 mese prima", 15: "15 giorni prima", 7: "7 giorni prima", 1: "Giorno prima" };
export const CAT = { Sito: ["#1b75b0", "#4aa3dc", "globe"], Marketing: ["#f07c1b", "#f7a23c", "sun"], Vendita: ["#0f3a5a", "#1b75b0", "card"], Clienti: ["#e06a10", "#f5a03a", "users"], Gestione: ["#145d8e", "#3a9ad6", "settings"], Altro: ["#5b6b7c", "#8da0b3", "pin"] };
export const LIVELLI = ["Base", "Intermedio", "Avanzato"];
export const NEWSCAT = ["Novità", "Promozione", "Avviso", "Evento"];
export const MATCAT = ["Loghi e grafica", "Brochure e cataloghi", "Social media", "Modulistica", "Altro"];
export const DOCT = { identita: ["Documento d'identità", true], cf: ["Codice fiscale o tessera sanitaria", true], visura: ["Visura camerale", "azienda"], licenza: ["Licenza agenzia di viaggi", false], altro: ["Altro", false] };
export const PERMS = { richieste: "Richieste", affiliati: "Affiliati (schede, documenti, pagamenti)", ticket: "Ticket", corsi: "Corsi", bacheca: "Bacheca", materiali: "Materiali", scadenze: "Scadenze domini", report: "Report ed export", email: "Registro email", impostazioni: "Impostazioni" };
export const PAYST = { pagato: ["Pagato", "ok"], in_verifica: ["In verifica", "warn"], respinto: ["Respinto", "bad"] };

export function fd(x) {
  if (!x) return "—";
  const d = typeof x === "string" && x.length === 10 ? new Date(x + "T00:00") : new Date(x);
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
}
export const fdt = (x) => new Date(x).toLocaleString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
export function eur(v) { const n = parseFloat(String(v).replace(",", ".")); return isNaN(n) ? "" : n.toLocaleString("it-IT", { style: "currency", currency: "EUR" }); }
export function daysTo(iso) { const t = new Date(new Date().toISOString().slice(0, 10) + "T00:00"); return Math.round((new Date(iso + "T00:00") - t) / 86400000); }
export function affName(a) {
  if (!a) return "";
  if (a.nomeAgenzia) return a.nomeAgenzia;
  if (a.tipo === "azienda" && a.azienda) return a.azienda;
  const p = (a.persone || [{}])[0];
  return `${p.nome || ""} ${p.cognome || ""}`.trim() || a.email;
}
export function stepOf(a) {
  if (a.stato === "bozza" || a.stato === "rifiutata") return 0;
  if (a.stato === "in_attesa") return 1;
  if (a.urlDefinitivo == null || a.logoScelto == null) return 2;
  if (a.pagamento !== "confermato") return 3;
  if (!a.consegnato) return 4;
  return 5;
}
export function statoInfo(a) {
  if (a.online) return ["Online", "ok"];
  if (a.consegnato) return ["Consegnato", "ok"];
  if (a.pagamento === "confermato") return ["In realizzazione", "info"];
  if (a.pagamento === "in_verifica") return ["Ricevuta in verifica", "warn"];
  return { bozza: ["Bozza", "neutral"], in_attesa: ["In attesa", "warn"], accettata: ["Approvata", "ok"], rifiutata: ["Rifiutata", "bad"] }[a.stato] || ["—", "neutral"];
}
export function causale(pag, a) { return (pag.causale || "").replace(/\{agenzia\}/g, a.nomeAgenzia || "").replace(/\{url\}/g, a.urlDef || ""); }
export function embedUrl(u) {
  if (!u) return null;
  let m = u.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([\w-]{6,})/);
  if (m) return `https://www.youtube-nocookie.com/embed/${m[1]}?rel=0`;
  m = u.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  if (m) return `https://player.vimeo.com/video/${m[1]}`;
  m = u.match(/drive\.google\.com\/file\/d\/([\w-]+)/);
  if (m) return `https://drive.google.com/file/d/${m[1]}/preview`;
  return null;
}
export function genPw() { const c = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!#$"; let s = ""; const a = crypto.getRandomValues(new Uint32Array(12)); a.forEach((x) => (s += c[x % c.length])); return s; }
export function downloadUrl(url) { const a = document.createElement("a"); a.href = url; a.target = "_blank"; a.rel = "noopener"; document.body.appendChild(a); a.click(); a.remove(); }
