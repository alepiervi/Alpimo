import React, { useState } from "react";
import { Badge, useLoad, useAction, useUI, Field, Empty } from "./ui.jsx";
import { post, put, del, PERMS } from "./lib.js";

export const Checks = ({ items, value, onChange, prefix }) => (
  <div className="permgrid">{items.map(([k, l]) => <label className="chk" key={k}><input type="checkbox" checked={value.includes(k)} onChange={(e) => onChange(e.target.checked ? [...value, k] : value.filter((x) => x !== k))} data-testid={`${prefix}-${k}`} />{l}</label>)}</div>
);

function Reparti({ R, reload }) {
  const [nome, setNome] = useState("");
  const act = useAction();
  const { ask } = useUI();
  const add = async () => { if (await act(() => post("/admin/reparti", { nome, ordine: R.length }), "Reparto aggiunto")) { setNome(""); reload(); } };
  const ren = async (r) => { const n = await ask({ title: "Rinomina reparto", input: "text", value: r.nome }); if (n) act(() => put(`/admin/reparti/${r.id}`, { nome: n, ordine: r.ordine }), "Reparto rinominato").then((x) => x && reload()); };
  const rm = async (r) => { if (await ask({ title: `Eliminare il reparto ${r.nome}?`, danger: true, ok: "Elimina" })) act(() => del(`/admin/reparti/${r.id}`), "Reparto eliminato").then((x) => x && reload()); };
  return (
    <div className="card" data-testid="reparti-card"><h3 style={{ marginBottom: 4 }}>Reparti dei ticket</h3><p className="small muted" style={{ marginBottom: 10 }}>L'affiliato sceglie il reparto quando apre un ticket.</p>
      {R.map((r) => <div className="todo" key={r.id} data-testid="reparto-row"><b>{r.nome}</b><div className="row"><button className="btn sm" onClick={() => ren(r)} data-testid="reparto-rename">Rinomina</button><button className="btn sm danger" onClick={() => rm(r)} data-testid="reparto-delete">Elimina</button></div></div>)}
      <div className="row" style={{ marginTop: 12 }}><input type="text" placeholder="Nuovo reparto" value={nome} onChange={(e) => setNome(e.target.value)} data-testid="reparto-new-name" /><button className="btn primary" onClick={add} data-testid="reparto-add">Aggiungi</button></div>
    </div>
  );
}

function RuoloForm({ f, setF, R, save }) {
  return (
    <div className="card" style={{ marginBottom: 12 }} data-testid="ruolo-form"><div style={{ display: "grid", gap: 12 }}>
      <Field label="Nome del ruolo"><input type="text" value={f.nome} onChange={(e) => setF({ ...f, nome: e.target.value })} placeholder="es. Operatore IT" data-testid="ruolo-name" /></Field>
      <div className="lbl">Sezioni visibili</div><Checks items={Object.entries(PERMS)} value={f.perms} onChange={(v) => setF({ ...f, perms: v })} prefix="ruolo-perm" />
      <div className="lbl">Reparti ticket <span className="small muted">(nessuno = tutti)</span></div><Checks items={R.map((r) => [r.id, r.nome])} value={f.reparti} onChange={(v) => setF({ ...f, reparti: v })} prefix="ruolo-rep" />
      <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn" onClick={() => setF(null)}>Annulla</button><button className="btn primary" onClick={save} data-testid="ruolo-save">Salva ruolo</button></div>
    </div></div>
  );
}

function Ruoli({ R }) {
  const [L, reload] = useLoad("/admin/ruoli");
  const [f, setF] = useState(null);
  const act = useAction();
  const { ask } = useUI();
  if (!L) return null;
  const rn = Object.fromEntries(R.map((r) => [r.id, r.nome]));
  const save = async () => { if (await act(() => (f.id ? put(`/admin/ruoli/${f.id}`, f) : post("/admin/ruoli", f)), "Ruolo salvato")) { setF(null); reload(); } };
  const rm = async (r) => { if (await ask({ title: `Eliminare il ruolo ${r.nome}?`, danger: true, ok: "Elimina" })) act(() => del(`/admin/ruoli/${r.id}`), "Ruolo eliminato").then((x) => x && reload()); };
  return (
    <div data-testid="ruoli-card">
      <div className="row between" style={{ marginBottom: 10 }}><h3>Ruoli del team</h3><button className="btn primary sm" onClick={() => setF({ nome: "", perms: ["ticket"], reparti: [] })} data-testid="ruolo-new-btn">+ Nuovo ruolo</button></div>
      {f && <RuoloForm f={f} setF={setF} R={R} save={save} />}
      <div className="card">{L.length ? L.map((r) => (
        <div className="todo" key={r.id} data-testid="ruolo-row"><div><b>{r.nome}</b> <Badge k="neutral">{r.utenti} utenti</Badge>
          <div className="small muted">Sezioni: {r.perms.map((p) => PERMS[p]?.split(" ")[0]).join(", ") || "nessuna"} · Reparti: {r.reparti.map((x) => rn[x]).filter(Boolean).join(", ") || "tutti"}</div></div>
          <div className="row"><button className="btn sm" onClick={() => setF(r)} data-testid="ruolo-edit">Modifica</button><button className="btn sm danger" onClick={() => rm(r)} data-testid="ruolo-delete">Elimina</button></div></div>
      )) : <Empty>Nessun ruolo. Creane uno e assegnalo agli utenti in Team admin.</Empty>}</div>
    </div>
  );
}

export default function RolesSettings() {
  const [R, reload] = useLoad("/reparti");
  if (!R) return null;
  return <div className="sch-grid" data-testid="roles-settings"><Ruoli R={R} /><Reparti R={R} reload={reload} /></div>;
}
