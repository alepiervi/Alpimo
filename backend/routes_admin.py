import io
import re
import csv
import secrets
from datetime import date
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
from core import (db, nowiso, today, uid, admin_user, need, super_user, can, get_settings, notify, notify_admins, send_mail, aff_name,
                  url_def, enc, dec, file_info, itd, scope_all, aff_q, scope_ids, pag_for, add_biz, add_year, days_to, hash_pw, next_seq, PERMS, email_status)
from routes_aff import billing_errors

router = APIRouter(prefix="/api/admin")
REM = [30, 15, 7, 1]


async def get_aff(aid, u=None):
    a = await db.affiliates.find_one({"id": aid}, {"_id": 0})
    if not a or (u and not scope_all(u) and a.get("aziendaId") not in (u.get("aziende") or [])):
        raise HTTPException(404, "Affiliato non trovato")
    return a


def step_of(a):
    if a["stato"] in ("bozza", "rifiutata"):
        return 0
    if a["stato"] == "in_attesa":
        return 1
    if a.get("urlDefinitivo") is None or a.get("logoScelto") is None:
        return 2
    if a["pagamento"] != "confermato":
        return 3
    if not a.get("consegnato"):
        return 4
    return 5


def row(a, users, comps):
    u = users.get(a["id"], {})
    return {"id": a["id"], "email": a["email"], "nome": aff_name(a), "tipo": a["tipo"], "citta": a.get("citta"), "stato": a["stato"],
            "pagamento": a["pagamento"], "url": url_def(a), "urls": a["urls"], "step": step_of(a), "consegnato": a.get("consegnato"),
            "online": a.get("online"), "richiestaOnline": a.get("richiestaOnline"), "scadenza": a["dominio"].get("scadenza"),
            "inviati": a["dominio"].get("inviati", []), "verified": u.get("verified"), "createdAt": a.get("createdAt"),
            "submittedAt": a.get("submittedAt"), "nota": a.get("nota"), "consegna": a.get("consegna"), "loghi": a.get("loghi"),
            "logoScelto": a.get("logoScelto"), "urlDefinitivo": a.get("urlDefinitivo"), "sceltaFinale": a.get("sceltaFinale", False),
            "aziendaId": a.get("aziendaId"), "azienda": comps.get(a.get("aziendaId"), ""), "registrar": a.get("registrar", "")}


async def comp_names():
    return {c["id"]: c["nome"] for c in await db.companies.find({}, {"_id": 0}).to_list(500)}


async def all_rows(me):
    users = {u["id"]: u for u in await db.users.find({"role": "affiliate"}, {"_id": 0, "password_hash": 0}).to_list(5000)}
    comps = await comp_names()
    return [row(a, users, comps) for a in await db.affiliates.find(aff_q(me), {"_id": 0}).sort("createdAt", -1).to_list(5000)]


@router.get("/dashboard")
async def dashboard(u=Depends(admin_user)):
    R = await all_rows(u)
    todo = []
    P = lambda p: can(u, p)  # noqa: E731
    if P("richieste"):
        todo += [{"k": "richiesta", "t": f"Nuova richiesta da {r['nome']}", "id": r["id"]} for r in R if r["stato"] == "in_attesa"]
    if P("affiliati"):
        for r in R:
            if r["pagamento"] == "in_verifica":
                todo.append({"k": "ricevuta", "t": f"Ricevuta da verificare: {r['nome']}", "id": r["id"]})
            if r["stato"] == "accettata" and any(x["value"] and x["stato"] == "da_verificare" for x in r["urls"]) and r["urlDefinitivo"] is None:
                todo.append({"k": "url", "t": f"URL da verificare: {r['nome']}", "id": r["id"]})
            if r["stato"] == "accettata" and not r.get("sceltaFinale") and not all(r["loghi"] or [None]):
                todo.append({"k": "loghi", "t": f"Loghi da caricare: {r['nome']}", "id": r["id"]})
            if r["richiestaOnline"] and not r["online"]:
                todo.append({"k": "online", "t": f"Richiesta messa online: {r['nome']}", "id": r["id"]})
            c = r.get("consegna")
            if c and not r["consegnato"] and days_to(c["dataPrevista"]) <= 3:
                todo.append({"k": "consegna", "t": f"Consegna vicina ({c['dataPrevista']}): {r['nome']}", "id": r["id"]})
        names = {r["id"]: r["nome"] for r in R}
        for d in await db.documents.find({"stato": "in_verifica", "affId": {"$in": list(names)}}, {"_id": 0}).to_list(500):
            todo.append({"k": "documento", "t": f"Documento da verificare ({d['tipo']}): {names.get(d['affId'], '')}", "id": d["affId"]})
    if P("corsi"):
        for p in await db.payments.find({"kind": "corso", "stato": "in_verifica", "affId": {"$in": [r["id"] for r in R]}}, {"_id": 0}).to_list(500):
            todo.append({"k": "corso", "t": f"Acquisto corso da verificare: {p['descrizione']}", "id": p["ref"], "view": "corsi"})
    rid = {"$in": [r["id"] for r in R]}
    tk_open = await db.tickets.count_documents({"stato": {"$ne": "chiuso"}, "affId": rid}) if P("ticket") else 0
    if P("ticket"):
        for t in await db.tickets.find({"lettoAdmin": False, "affId": rid}, {"_id": 0}).to_list(200):
            todo.append({"k": "ticket", "t": f"Ticket non letto #{t['num']}: {t['oggetto']}", "id": t["id"], "view": "ticket"})
    dom = sorted([r for r in R if r["scadenza"] and days_to(r["scadenza"]) <= 30], key=lambda r: r["scadenza"]) if P("scadenze") else []
    return {"kpi": {"richieste": len([r for r in R if r["stato"] == "in_attesa"]), "ricevute": len([r for r in R if r["pagamento"] == "in_verifica"]),
                    "realizzazione": len([r for r in R if r["pagamento"] == "confermato" and not r["consegnato"]]), "ticket": tk_open, "domini": len(dom)},
            "todo": todo, "domini": dom, "email": email_status()}


@router.get("/counts")
async def counts(u=Depends(admin_user)):
    ids = await scope_ids(u)
    f = {} if ids is None else {"affId": {"$in": list(ids)}}
    return {"richieste": await db.affiliates.count_documents({"stato": "in_attesa", **aff_q(u)}),
            "ticket": await db.tickets.count_documents({"lettoAdmin": False, **f}),
            "corsi": await db.payments.count_documents({"kind": "corso", "stato": "in_verifica", **f})}


@router.get("/affiliates")
async def affiliates(u=Depends(admin_user)):
    if not (can(u, "affiliati") or can(u, "richieste") or can(u, "scadenze")):
        raise HTTPException(403, "Permesso negato")
    return await all_rows(u)


@router.get("/affiliates/{aid}")
async def affiliate(aid: str, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    usr = await db.users.find_one({"id": aid}, {"_id": 0, "password_hash": 0})
    a["cred"] = dec(a.get("cred"))
    a["superAdmin"] = dec(a.get("superAdmin"))
    a["loghiInfo"] = [await file_info(x) for x in a.get("loghi") or [None] * 3]
    a["ricevutaInfo"] = await file_info(a.get("ricevuta"))
    a["urlDef"] = url_def(a)
    a["step"] = step_of(a)
    a["user"] = usr
    a["docs"] = await db.documents.find({"affId": aid}, {"_id": 0}).sort("uploadedAt", -1).to_list(200)
    pays = await db.payments.find({"affId": aid}, {"_id": 0}).sort("at", -1).to_list(200)
    for p in pays:
        p["ricevutaInfo"] = await file_info(p.get("ricevuta"))
    a["payments"] = pays
    courses = {c["id"]: c for c in await db.courses.find({}, {"_id": 0}).to_list(500)}
    a["progress"] = [{"titolo": courses[p["courseId"]]["titolo"], "fatte": len(p.get("fatte", [])), "tot": len(courses[p["courseId"]].get("lezioni", [])),
                      "completatoAt": p.get("completatoAt")} for p in await db.progress.find({"affId": aid}, {"_id": 0}).to_list(500) if p["courseId"] in courses]
    a["tickets"] = await db.tickets.find({"affId": aid}, {"_id": 0, "messaggi": 0}).sort("createdAt", -1).to_list(200)
    return a


@router.delete("/affiliates/{aid}")
async def delete_aff(aid: str, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    for c in ("documents", "payments", "tickets", "progress"):
        await db[c].delete_many({"affId": aid})
    await db.notifications.delete_many({"$or": [{"to": aid}, {"ref": aid}]})
    await db.codes.delete_many({"user_id": aid})
    await db.files.update_many({"owner": aid}, {"$set": {"is_deleted": True}})
    await db.affiliates.delete_one({"id": aid})
    await db.users.delete_one({"id": aid, "role": "affiliate"})
    return {"ok": True, "email": a["email"]}


class DecideIn(BaseModel):
    accept: bool
    nota: str = ""


@router.post("/affiliates/{aid}/decide")
async def decide(aid: str, body: DecideIn, u=Depends(need("richieste"))):
    a = await get_aff(aid, u)
    if a["stato"] != "in_attesa":
        raise HTTPException(400, "La richiesta non è in attesa")
    if not body.accept and not body.nota.strip():
        raise HTTPException(400, "Indica il motivo del rifiuto")
    st = "accettata" if body.accept else "rifiutata"
    await db.affiliates.update_one({"id": aid}, {"$set": {"stato": st, "nota": body.nota.strip(), "decidedAt": nowiso()}})
    ag = aff_name(a)
    if body.accept:
        await send_mail(a["email"], "La tua richiesta di affiliazione è stata approvata", f"Ciao {ag},\n\nla tua richiesta è stata approvata! A breve troverai nel portale le proposte di logo e la verifica degli URL.", aid)
        await notify(aid, "La tua richiesta è stata <b>approvata</b>!", "percorso")
    else:
        await send_mail(a["email"], "La tua richiesta di affiliazione non è stata approvata", f"Ciao {ag},\n\nla tua richiesta non è stata approvata.\nMotivo: {body.nota}\n\nPuoi correggere i dati dal portale e inviarla di nuovo.", aid)
        await notify(aid, f"Richiesta non approvata: {body.nota}", "percorso")
    return {"ok": True}


@router.post("/affiliates/{aid}/verify-email")
async def verify_email(aid: str, u=Depends(need("affiliati"))):
    await get_aff(aid, u)
    await db.users.update_one({"id": aid}, {"$set": {"verified": True}})
    return {"ok": True}


class UrlStatoIn(BaseModel):
    idx: int
    stato: str


@router.post("/affiliates/{aid}/url")
async def url_stato(aid: str, body: UrlStatoIn, u=Depends(need("affiliati"))):
    if body.stato not in ("disponibile", "non_disponibile", "da_verificare") or not 0 <= body.idx < 3:
        raise HTTPException(400, "Dati non validi")
    a = await get_aff(aid, u)
    await db.affiliates.update_one({"id": aid}, {"$set": {f"urls.{body.idx}.stato": body.stato}})
    v = a["urls"][body.idx]["value"]
    await notify(aid, f"URL <b>{v}</b>: {body.stato.replace('_', ' ')}", "percorso")
    return {"ok": True}


class LogoIn(BaseModel):
    idx: int
    file: Optional[str] = None


@router.post("/affiliates/{aid}/logo")
async def set_logo(aid: str, body: LogoIn, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    if not 0 <= body.idx < 3:
        raise HTTPException(400, "Slot non valido")
    if body.file:
        await db.files.update_one({"id": body.file}, {"$set": {"owner": aid}})
    upd = {f"loghi.{body.idx}": body.file}
    if not body.file and a.get("logoScelto") == body.idx:
        upd["logoScelto"] = None
    await db.affiliates.update_one({"id": aid}, {"$set": upd})
    a = await get_aff(aid, u)
    if all(a["loghi"]):
        await notify(aid, "Le proposte di logo sono pronte: scegli la tua preferita!", "percorso")
    return {"ok": True}


class PayIn(BaseModel):
    confirm: bool
    giorni: int = Field(15, ge=1, le=365)
    nota: str = ""


@router.post("/affiliates/{aid}/payment")
async def payment(aid: str, body: PayIn, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    if a["pagamento"] != "in_verifica":
        raise HTTPException(400, "Nessuna ricevuta in verifica")
    ag = aff_name(a)
    if body.confirm:
        start = today()
        prev = add_biz(start, body.giorni)
        await db.affiliates.update_one({"id": aid}, {"$set": {"pagamento": "confermato", "pagamentoAt": nowiso(), "notaPagamento": "",
                                                              "consegna": {"inizio": start, "giorni": body.giorni, "dataPrevista": prev, "fase": 1},
                                                              "dominio.scadenza": a["dominio"].get("scadenza") or add_year(start)}})
        await db.payments.update_one({"affId": aid, "kind": "attivazione"}, {"$set": {"stato": "pagato", "pagatoAt": nowiso()}})
        await send_mail(a["email"], "Pagamento confermato: lavori avviati", f"Ciao {ag},\n\nabbiamo confermato il tuo pagamento e i lavori per il sito {url_def(a)} sono iniziati.\nData di consegna prevista: {itd(prev)}.\n\nDa oggi hai accesso ai corsi dell'Academy affiliati.", aid)
        await notify(aid, f"Pagamento confermato! Consegna prevista il <b>{itd(prev)}</b>. Corsi sbloccati.", "percorso")
    else:
        if not body.nota.strip():
            raise HTTPException(400, "Indica il motivo")
        await db.affiliates.update_one({"id": aid}, {"$set": {"pagamento": "respinto", "notaPagamento": body.nota.strip()}})
        await db.payments.update_one({"affId": aid, "kind": "attivazione"}, {"$set": {"stato": "respinto", "nota": body.nota.strip()}})
        await send_mail(a["email"], "Ricevuta di pagamento respinta", f"Ciao {ag},\n\nnon abbiamo potuto confermare la ricevuta.\nMotivo: {body.nota}\n\nCarica una nuova ricevuta dal portale.", aid)
        await notify(aid, f"Ricevuta respinta: {body.nota}", "percorso")
    return {"ok": True}


class ConsegnaIn(BaseModel):
    dataPrevista: Optional[str] = None
    fase: Optional[int] = None


@router.post("/affiliates/{aid}/consegna")
async def consegna(aid: str, body: ConsegnaIn, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    if not a.get("consegna"):
        raise HTTPException(400, "Pagamento non ancora confermato")
    upd = {}
    if body.dataPrevista:
        upd["consegna.dataPrevista"] = body.dataPrevista
    if body.fase is not None and 0 <= body.fase <= 3:
        upd["consegna.fase"] = body.fase
    await db.affiliates.update_one({"id": aid}, {"$set": upd})
    return {"ok": True}


class CredIn(BaseModel):
    cred: dict
    superAdmin: dict


@router.post("/affiliates/{aid}/cred")
async def cred(aid: str, body: CredIn, u=Depends(need("affiliati"))):
    await get_aff(aid, u)
    c = {k: str(body.cred.get(k) or "") for k in ("url", "utente", "password", "passwordSito")}
    s = {k: str(body.superAdmin.get(k) or "") for k in ("url", "utente", "password")}
    await db.affiliates.update_one({"id": aid}, {"$set": {"cred": enc(c), "superAdmin": enc(s)}})
    return {"ok": True}


@router.post("/affiliates/{aid}/deliver")
async def deliver(aid: str, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    c = dec(a.get("cred"))
    if a["pagamento"] != "confermato" or not (c.get("url") and c.get("utente") and c.get("password")):
        raise HTTPException(400, "Salva prima le credenziali dell'admin affiliato")
    await db.affiliates.update_one({"id": aid}, {"$set": {"consegnato": True, "consegnatoAt": nowiso(), "consegna.fase": 3}})
    ag = aff_name(a)
    await send_mail(a["email"], "Il tuo sito è pronto!", f"Ciao {ag},\n\nil sito {url_def(a)} è stato consegnato.\n\nURL admin: {c['url']}\nUtente: {c['utente']}\nPassword: {c['password']}\nPassword sito (anteprima): {c.get('passwordSito', '')}\n\nQuando hai finito le modifiche usa il pulsante \"Metti online\" nel portale.", aid)
    await notify(aid, "Il tuo sito è stato <b>consegnato</b>! Trovi le credenziali nel portale.", "percorso")
    return {"ok": True}


@router.post("/affiliates/{aid}/online")
async def online(aid: str, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    if not a.get("consegnato"):
        raise HTTPException(400, "Sito non ancora consegnato")
    await db.affiliates.update_one({"id": aid}, {"$set": {"online": True, "onlineAt": nowiso(), "richiestaOnline": False}})
    await send_mail(a["email"], "Il tuo sito è online!", f"Ciao {aff_name(a)},\n\nil sito {url_def(a)} è ora online e la password di anteprima è stata disattivata.", aid)
    await notify(aid, "Il tuo sito è <b>online</b>!", "percorso")
    return {"ok": True}


class InternalIn(BaseModel):
    aziendaId: Optional[str] = None
    registrar: str = ""


@router.post("/affiliates/{aid}/internal")
async def internal(aid: str, body: InternalIn, u=Depends(need("affiliati"))):
    await get_aff(aid, u)
    if body.aziendaId and not await db.companies.find_one({"id": body.aziendaId}):
        raise HTTPException(400, "Azienda non valida")
    if body.aziendaId and not scope_all(u) and body.aziendaId not in (u.get("aziende") or []):
        raise HTTPException(403, "Non puoi assegnare questa azienda")
    await db.affiliates.update_one({"id": aid}, {"$set": {"aziendaId": body.aziendaId or None, "registrar": body.registrar.strip()}})
    return {"ok": True}


@router.get("/internal-options")
async def internal_options(u=Depends(admin_user)):
    return {"registrar": sorted(x for x in await db.affiliates.distinct("registrar") if x)}


PAG_KEYS = ("intestatario", "iban", "banca", "bic", "importo", "iva", "rinnovo", "causale", "scadenza", "note")


def clean_pag(src):
    p = {k: str((src or {}).get(k) or "").strip() for k in PAG_KEYS}
    iban = p["iban"].replace(" ", "").upper()
    if iban and not (15 <= len(iban) <= 34 and iban[:2].isalpha() and iban[2:4].isdigit()):
        raise HTTPException(400, "IBAN non valido")
    return p


class CompanyIn(BaseModel):
    nome: str
    pag: dict = {}


@router.get("/companies")
async def companies(u=Depends(admin_user)):
    q = {} if scope_all(u) else {"id": {"$in": u.get("aziende") or []}}
    L = await db.companies.find(q, {"_id": 0}).sort("nome", 1).to_list(500)
    for c in L:
        c["affiliati"] = await db.affiliates.count_documents({"aziendaId": c["id"]})
    return L


@router.post("/companies")
async def company_new(body: CompanyIn, u=Depends(super_user)):
    if not body.nome.strip():
        raise HTTPException(400, "Inserisci il nome dell'azienda")
    c = {"id": uid(), "nome": body.nome.strip(), "pag": clean_pag(body.pag), "createdAt": nowiso()}
    await db.companies.insert_one(dict(c))
    return {"id": c["id"]}


@router.put("/companies/{cid}")
async def company_upd(cid: str, body: CompanyIn, u=Depends(super_user)):
    if not body.nome.strip():
        raise HTTPException(400, "Inserisci il nome dell'azienda")
    r = await db.companies.update_one({"id": cid}, {"$set": {"nome": body.nome.strip(), "pag": clean_pag(body.pag)}})
    if not r.matched_count:
        raise HTTPException(404, "Azienda non trovata")
    return {"ok": True}


@router.delete("/companies/{cid}")
async def company_del(cid: str, u=Depends(super_user)):
    if await db.affiliates.count_documents({"aziendaId": cid}):
        raise HTTPException(400, "Ci sono affiliati assegnati a questa azienda: spostali prima di eliminarla")
    await db.companies.delete_one({"id": cid})
    await db.users.update_many({"role": "admin"}, {"$pull": {"aziende": cid}})
    return {"ok": True}


class DomIn(BaseModel):
    scadenza: str


@router.post("/affiliates/{aid}/domain")
async def domain(aid: str, body: DomIn, u=Depends(need("scadenze"))):
    await get_aff(aid, u)
    try:
        date.fromisoformat(body.scadenza)
    except ValueError:
        raise HTTPException(400, "Data non valida")
    await db.affiliates.update_one({"id": aid}, {"$set": {"dominio.scadenza": body.scadenza, "dominio.inviati": []}})
    return {"ok": True}


@router.post("/affiliates/{aid}/renew")
async def renew(aid: str, u=Depends(need("scadenze"))):
    a = await get_aff(aid, u)
    sc = a["dominio"].get("scadenza") or today()
    new = add_year(sc)
    pg = await pag_for(a)
    imp = float(str(pg.get("rinnovo") or 0).replace(",", ".") or 0)
    iva = float(str(pg.get("iva") or 0).replace(",", ".") or 0)
    await db.affiliates.update_one({"id": aid}, {"$set": {"dominio.scadenza": new, "dominio.inviati": []},
                                                 "$push": {"dominio.storico": {"da": sc, "a": new, "at": nowiso()}}})
    await db.payments.insert_one({"id": uid(), "affId": aid, "kind": "rinnovo", "descrizione": f"Rinnovo dominio {url_def(a)} fino al {itd(new)}", "imponibile": imp,
                                  "iva": iva, "totale": round(imp * (1 + iva / 100), 2), "stato": "pagato", "ricevuta": None, "nota": "", "at": nowiso(), "invoice": None})
    return {"ok": True, "scadenza": new}


class PwSetIn(BaseModel):
    password: str


@router.post("/affiliates/{aid}/password")
async def set_pw(aid: str, body: PwSetIn, u=Depends(need("impostazioni"))):
    await get_aff(aid, u)
    if len(body.password) < 8:
        raise HTTPException(400, "Minimo 8 caratteri")
    r = await db.users.update_one({"id": aid, "role": "affiliate"}, {"$set": {"password_hash": hash_pw(body.password)}})
    if not r.matched_count:
        raise HTTPException(404, "Affiliato non trovato")
    return {"ok": True}


@router.put("/affiliates/{aid}/billing")
async def admin_billing(aid: str, body: dict, u=Depends(need("affiliati"))):
    a = await get_aff(aid, u)
    f = {k: str(body.get(k) or "").strip() for k in ("intestatario", "cf", "piva", "sdi", "pec", "indirizzo", "cap", "citta", "provincia")}
    e = billing_errors(f, a["tipo"])
    if e:
        raise HTTPException(400, "; ".join(e))
    await db.affiliates.update_one({"id": aid}, {"$set": {"fatturazione": f}})
    return {"ok": True}


class DocDecIn(BaseModel):
    approve: bool
    nota: str = ""


@router.post("/docs/{did}")
async def doc_decide(did: str, body: DocDecIn, u=Depends(need("affiliati"))):
    d = await db.documents.find_one({"id": did}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Documento non trovato")
    await get_aff(d["affId"], u)
    if not body.approve and not body.nota.strip():
        raise HTTPException(400, "Indica il motivo")
    st = "approvato" if body.approve else "rifiutato"
    await db.documents.update_one({"id": did}, {"$set": {"stato": st, "nota": body.nota.strip()}})
    a = await get_aff(d["affId"], u)
    msg = f"Il documento \"{d['name']}\" è stato {st}." + (f"\nMotivo: {body.nota}\nPuoi caricarne uno nuovo dal portale." if not body.approve else "")
    await send_mail(a["email"], f"Documento {st}", f"Ciao {aff_name(a)},\n\n{msg}", d["affId"])
    await notify(d["affId"], f"Documento <b>{d['name']}</b> {st}" + (f": {body.nota}" if not body.approve else ""), "documenti")
    return {"ok": True}


class ManualPayIn(BaseModel):
    affId: str
    descrizione: str
    totale: float = Field(gt=0)
    kind: str = "altro"


@router.post("/payments")
async def manual_pay(body: ManualPayIn, u=Depends(need("affiliati"))):
    a = await get_aff(body.affId, u)
    iva = float(str((await pag_for(a)).get("iva") or 0).replace(",", ".") or 0)
    await db.payments.insert_one({"id": uid(), "affId": body.affId, "kind": body.kind if body.kind in ("attivazione", "corso", "rinnovo", "altro") else "altro",
                                  "descrizione": body.descrizione.strip() or "Pagamento", "imponibile": round(body.totale / (1 + iva / 100), 2), "iva": iva,
                                  "totale": body.totale, "stato": "pagato", "ricevuta": None, "nota": "manuale", "at": nowiso(), "invoice": None})
    return {"ok": True}


class InvIn(BaseModel):
    file: str


@router.post("/payments/{pid}/invoice")
async def invoice(pid: str, body: InvIn, u=Depends(need("affiliati"))):
    p = await db.payments.find_one({"id": pid}, {"_id": 0})
    if not p or p["stato"] != "pagato":
        raise HTTPException(400, "La fattura si allega solo a voci pagate")
    await get_aff(p["affId"], u)
    yr = date.today().year
    num = (p.get("invoice") or {}).get("numero") or f"FT {await next_seq(f'ft-{yr}')}/{yr}"
    await db.files.update_one({"id": body.file}, {"$set": {"owner": p["affId"]}})
    await db.payments.update_one({"id": pid}, {"$set": {"invoice": {"numero": num, "file": body.file, "at": nowiso()}}})
    a = await get_aff(p["affId"], u)
    await send_mail(a["email"], f"Fattura {num} disponibile", f"Ciao {aff_name(a)},\n\nla fattura {num} per \"{p['descrizione']}\" è disponibile nel portale, sezione Pagamenti.", p["affId"])
    await notify(p["affId"], f"Fattura <b>{num}</b> disponibile", "pagamenti")
    return {"ok": True, "numero": num}


class CoursePayIn(BaseModel):
    confirm: bool
    nota: str = ""


@router.get("/course-purchases")
async def course_purchases(u=Depends(need("corsi"))):
    names = {a["id"]: aff_name(a) for a in await db.affiliates.find(aff_q(u), {"_id": 0}).to_list(5000)}
    L = await db.payments.find({"kind": "corso", "affId": {"$in": list(names)}}, {"_id": 0}).sort("at", -1).to_list(500)
    for p in L:
        p["agenzia"] = names.get(p["affId"], "")
        p["ricevutaInfo"] = await file_info(p.get("ricevuta"))
    return L


@router.post("/course-purchases/{pid}")
async def course_pay(pid: str, body: CoursePayIn, u=Depends(need("corsi"))):
    p = await db.payments.find_one({"id": pid, "kind": "corso"}, {"_id": 0})
    if not p or p["stato"] != "in_verifica":
        raise HTTPException(400, "Acquisto non in verifica")
    await get_aff(p["affId"], u)
    if not body.confirm and not body.nota.strip():
        raise HTTPException(400, "Indica il motivo")
    a = await get_aff(p["affId"], u)
    c = await db.courses.find_one({"id": p["ref"]}, {"_id": 0}) or {"titolo": ""}
    if body.confirm:
        await db.payments.update_one({"id": pid}, {"$set": {"stato": "pagato", "pagatoAt": nowiso()}})
        await send_mail(a["email"], f"Corso sbloccato: {c['titolo']}", f"Ciao {aff_name(a)},\n\nabbiamo confermato il pagamento: il corso \"{c['titolo']}\" è ora sbloccato.", p["ref"])
        await notify(p["affId"], f"Corso <b>{c['titolo']}</b> sbloccato!", "corsi", p["ref"])
    else:
        await db.payments.update_one({"id": pid}, {"$set": {"stato": "respinto", "nota": body.nota.strip()}})
        await send_mail(a["email"], f"Pagamento corso rifiutato: {c['titolo']}", f"Ciao {aff_name(a)},\n\nnon abbiamo potuto confermare il pagamento del corso \"{c['titolo']}\".\nMotivo: {body.nota}", p["ref"])
        await notify(p["affId"], f"Pagamento del corso <b>{c['titolo']}</b> rifiutato: {body.nota}", "corsi", p["ref"])
    return {"ok": True}


# ---------- corsi CRUD ----------
class CourseIn(BaseModel):
    titolo: str
    categoria: str = "Sito"
    livello: str = "Base"
    descrizione: str = ""
    premium: bool = False
    prezzo: float = 0
    pubblicato: bool = False
    copertina: Optional[str] = None
    lezioni: List[dict] = []


def clean_lessons(L):
    return [{"id": x.get("id") or uid(), "titolo": str(x.get("titolo") or "Lezione"), "durata": str(x.get("durata") or ""),
             "descrizione": str(x.get("descrizione") or ""), "file": x.get("file") or None, "url": (x.get("url") or "").strip() or None} for x in L]


@router.get("/courses")
async def a_courses(u=Depends(need("corsi"))):
    L = await db.courses.find({}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    for c in L:
        c["iscritti"] = await db.progress.count_documents({"courseId": c["id"]})
        c["completati"] = await db.progress.count_documents({"courseId": c["id"], "completatoAt": {"$ne": None}})
        c["acquisti"] = await db.payments.count_documents({"kind": "corso", "ref": c["id"], "stato": "pagato"})
    return L


async def announce_course(c):
    for a in await db.affiliates.find({"pagamento": "confermato"}, {"_id": 0}).to_list(5000):
        await notify(a["id"], f"Nuovo corso disponibile: <b>{c['titolo']}</b>", "corsi", c["id"])


@router.post("/courses")
async def a_course_new(body: CourseIn, u=Depends(need("corsi"))):
    c = {**body.model_dump(), "id": uid(), "lezioni": clean_lessons(body.lezioni), "createdAt": nowiso(), "annunciato": body.pubblicato}
    await db.courses.insert_one(dict(c))
    if body.pubblicato:
        await announce_course(c)
    return {"id": c["id"]}


@router.put("/courses/{cid}")
async def a_course_upd(cid: str, body: CourseIn, u=Depends(need("corsi"))):
    old = await db.courses.find_one({"id": cid}, {"_id": 0})
    if not old:
        raise HTTPException(404, "Corso non trovato")
    upd = {**body.model_dump(), "lezioni": clean_lessons(body.lezioni)}
    if body.pubblicato and not old.get("annunciato"):
        upd["annunciato"] = True
        await announce_course({**old, **upd})
    await db.courses.update_one({"id": cid}, {"$set": upd})
    return {"ok": True}


@router.delete("/courses/{cid}")
async def a_course_del(cid: str, u=Depends(need("corsi"))):
    await db.courses.delete_one({"id": cid})
    return {"ok": True}


# ---------- bacheca ----------
class NewsIn(BaseModel):
    titolo: str
    categoria: str = "Novità"
    testo: str = ""
    immagine: Optional[str] = None
    inEvidenza: bool = False
    email: bool = False


@router.get("/news")
async def a_news(u=Depends(need("bacheca"))):
    tot = await db.affiliates.count_documents({})
    L = await db.news.find({}, {"_id": 0}).sort("at", -1).to_list(500)
    for n in L:
        n["letti"] = len(n.pop("lettiDa", []) or [])
        n["tot"] = tot
    return L


@router.post("/news")
async def a_news_new(body: NewsIn, u=Depends(need("bacheca"))):
    n = {**body.model_dump(exclude={"email"}), "id": uid(), "lettiDa": [], "at": nowiso()}
    await db.news.insert_one(dict(n))
    for a in await db.affiliates.find({}, {"_id": 0}).to_list(5000):
        await notify(a["id"], f"Nuova comunicazione in bacheca: <b>{n['titolo']}</b>", "bacheca")
        if body.email:
            await send_mail(a["email"], f"[Bacheca] {n['titolo']}", f"{n['titolo']}\n\n{n['testo']}\n\nLeggi la comunicazione completa nel portale affiliati.", n["id"])
    return {"id": n["id"]}


@router.put("/news/{nid}")
async def a_news_upd(nid: str, body: NewsIn, u=Depends(need("bacheca"))):
    await db.news.update_one({"id": nid}, {"$set": body.model_dump(exclude={"email"})})
    return {"ok": True}


@router.delete("/news/{nid}")
async def a_news_del(nid: str, u=Depends(need("bacheca"))):
    await db.news.delete_one({"id": nid})
    return {"ok": True}


# ---------- materiali ----------
class MatIn(BaseModel):
    titolo: str
    categoria: str = "Altro"
    descrizione: str = ""
    file: str


@router.get("/materials")
async def a_mats(u=Depends(need("materiali"))):
    return await db.materials.find({"deleted": {"$ne": True}}, {"_id": 0}).sort("at", -1).to_list(500)


@router.post("/materials")
async def a_mat_new(body: MatIn, u=Depends(need("materiali"))):
    f = await file_info(body.file)
    if not f:
        raise HTTPException(400, "File non valido")
    await db.files.update_one({"id": body.file}, {"$set": {"owner": "public"}})
    m = {**body.model_dump(), "id": uid(), "name": f["name"], "type": f["type"], "size": f["size"], "downloads": 0, "at": nowiso()}
    await db.materials.insert_one(dict(m))
    for a in await db.affiliates.find({}, {"_id": 0}).to_list(5000):
        await notify(a["id"], f"Nuovo materiale disponibile: <b>{m['titolo']}</b>", "materiali")
    return {"id": m["id"]}


@router.delete("/materials/{mid}")
async def a_mat_del(mid: str, u=Depends(need("materiali"))):
    m = await db.materials.find_one({"id": mid}, {"_id": 0})
    if m:
        await db.files.update_one({"id": m["file"]}, {"$set": {"is_deleted": True}})
    await db.materials.update_one({"id": mid}, {"$set": {"deleted": True}})
    return {"ok": True}


# ---------- report / export ----------
@router.get("/report")
async def report(year: int = 0, u=Depends(need("report"))):
    yr = year or date.today().year
    ids = await scope_ids(u)
    pays = await db.payments.find({} if ids is None else {"affId": {"$in": list(ids)}}, {"_id": 0}).to_list(10000)
    byk = {"attivazione": 0, "corso": 0, "rinnovo": 0, "altro": 0}
    months = [0.0] * 12
    verif = 0.0
    years = sorted({int((p.get("pagatoAt") or p["at"])[:4]) for p in pays} | {date.today().year})
    for p in pays:
        if p["stato"] == "in_verifica":
            verif += p["totale"]
        if p["stato"] == "pagato" and int((p.get("pagatoAt") or p["at"])[:4]) == yr:
            byk[p["kind"]] = byk.get(p["kind"], 0) + p["totale"]
            months[int((p.get("pagatoAt") or p["at"])[5:7]) - 1] += p["totale"]
    R = await all_rows(u)
    rete = {"affiliati": len(R), "inAttesa": len([r for r in R if r["stato"] == "in_attesa"]), "consegnati": len([r for r in R if r["consegnato"]]),
            "online": len([r for r in R if r["online"]]), "realizzazione": len([r for r in R if r["pagamento"] == "confermato" and not r["consegnato"]])}
    return {"year": yr, "years": years, "byKind": byk, "totale": sum(byk.values()), "inVerifica": verif, "months": months, "rete": rete}


def csv_resp(name, header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(header)
    w.writerows(rows)
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}.csv"'})


@router.get("/export/{kind}")
async def export(kind: str, u=Depends(admin_user)):
    if not (can(u, "report") or (kind == "affiliati" and can(u, "affiliati"))):
        raise HTTPException(403, "Permesso negato")
    affs = await db.affiliates.find(aff_q(u), {"_id": 0}).to_list(5000)
    names = {a["id"]: aff_name(a) for a in affs}
    inids = {"affId": {"$in": list(names)}}
    comps = await comp_names()
    if kind == "affiliati":
        H = ["Agenzia", "Email", "Tipo", "Città", "Telefono", "Stato", "Pagamento", "URL", "Scadenza dominio", "Azienda affiliante", "Piattaforma dominio", "Intestatario", "CF", "P.IVA", "SDI", "PEC", "Indirizzo", "CAP", "Città fatt.", "Prov."]
        rows = []
        for a in affs:
            f = a.get("fatturazione") or {}
            rows.append([aff_name(a), a["email"], a["tipo"], a.get("citta"), a.get("telefono"), a["stato"], a["pagamento"], url_def(a), a["dominio"].get("scadenza"), comps.get(a.get("aziendaId"), ""), a.get("registrar", "")] +
                        [f.get(k, "") for k in ("intestatario", "cf", "piva", "sdi", "pec", "indirizzo", "cap", "citta", "provincia")])
        return csv_resp("affiliati", H, rows)
    if kind == "pagamenti":
        L = await db.payments.find(inids, {"_id": 0}).sort("at", -1).to_list(10000)
        return csv_resp("pagamenti", ["Data", "Agenzia", "Tipo", "Descrizione", "Imponibile", "IVA %", "Totale", "Stato", "Fattura"],
                        [[p["at"][:10], names.get(p["affId"]), p["kind"], p["descrizione"], str(p["imponibile"]).replace(".", ","), p["iva"], str(p["totale"]).replace(".", ","), p["stato"], (p.get("invoice") or {}).get("numero", "")] for p in L])
    if kind == "scadenze":
        L = sorted([a for a in affs if a["dominio"].get("scadenza")], key=lambda a: a["dominio"]["scadenza"])
        return csv_resp("scadenze", ["Agenzia", "URL", "Piattaforma", "Scadenza", "Giorni mancanti", "Promemoria inviati"],
                        [[aff_name(a), url_def(a), a.get("registrar", ""), a["dominio"]["scadenza"], days_to(a["dominio"]["scadenza"]), ",".join(str(x) for x in a["dominio"].get("inviati", []))] for a in L])
    if kind == "corsi":
        cs = {c["id"]: c for c in await db.courses.find({}, {"_id": 0}).to_list(500)}
        L = await db.progress.find(inids, {"_id": 0}).to_list(10000)
        return csv_resp("corsi", ["Agenzia", "Corso", "Lezioni completate", "Totale lezioni", "Completato il"],
                        [[names.get(p["affId"]), cs[p["courseId"]]["titolo"], len(p.get("fatte", [])), len(cs[p["courseId"]].get("lezioni", [])), (p.get("completatoAt") or "")[:10]] for p in L if p["courseId"] in cs])
    raise HTTPException(404, "Export non trovato")


@router.get("/emails")
async def emails(q: str = "", ref: str = "", u=Depends(need("email"))):
    f = {}
    if not scope_all(u):
        f["to"] = {"$in": [a["email"] for a in await db.affiliates.find(aff_q(u), {"_id": 0, "email": 1}).to_list(10000)]}
    if ref:
        f["ref"] = ref
    if q:
        f["$or"] = [{"to": {"$regex": re.escape(q), "$options": "i"}}, {"subject": {"$regex": re.escape(q), "$options": "i"}}]
    return {"items": await db.email_log.find(f, {"_id": 0}).sort("at", -1).to_list(300), "status": email_status()}


# ---------- impostazioni ----------
@router.get("/settings")
async def settings(u=Depends(admin_user)):
    s = await get_settings()
    return {**s, "email": email_status()}


@router.put("/settings")
async def settings_upd(body: dict, u=Depends(need("impostazioni"))):
    if not scope_all(u):
        raise HTTPException(403, "Solo chi vede tutte le aziende può modificare le impostazioni generali")
    upd = {}
    if "pag" in body:
        upd["pag"] = clean_pag(body["pag"])
    if "giorni" in body:
        upd["giorni"] = max(1, int(body["giorni"]))
    if "adminEmail" in body:
        upd["adminEmail"] = str(body["adminEmail"]).strip()
    await db.settings.update_one({"_id": "main"}, {"$set": upd})
    return {"ok": True}


class LegalIn(BaseModel):
    contratto: str
    privacy: str
    nuovaVersione: bool = True


@router.post("/legal")
async def legal(body: LegalIn, u=Depends(need("impostazioni"))):
    if not scope_all(u):
        raise HTTPException(403, "Solo chi vede tutte le aziende può modificare contratto e privacy")
    s = await get_settings()
    v = s["legali"]["versione"] + (1 if body.nuovaVersione else 0)
    await db.settings.update_one({"_id": "main"}, {"$set": {"legali": {"versione": v, "contratto": body.contratto, "privacy": body.privacy, "at": nowiso()}}})
    return {"ok": True, "versione": v}


@router.get("/team")
async def team(u=Depends(super_user)):
    return await db.users.find({"role": "admin"}, {"_id": 0, "password_hash": 0}).to_list(200)


class TeamIn(BaseModel):
    nome: str
    email: str
    password: Optional[str] = None
    perms: List[str] = []
    active: bool = True
    full: bool = False
    tutteAziende: bool = False
    aziende: List[str] = []


async def team_fields(body):
    valid = {c["id"] for c in await db.companies.find({}, {"_id": 0, "id": 1}).to_list(500)}
    if body.full:
        return {"is_super": True, "perms": PERMS, "tutteAziende": True, "aziende": []}
    return {"is_super": False, "perms": [p for p in body.perms if p in PERMS], "tutteAziende": body.tutteAziende,
            "aziende": [] if body.tutteAziende else [c for c in body.aziende if c in valid]}


@router.post("/team")
async def team_new(body: TeamIn, u=Depends(super_user)):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Email non valida")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email già usata")
    pw = body.password or secrets.token_urlsafe(9)
    if len(pw) < 8:
        raise HTTPException(400, "Password minimo 8 caratteri")
    await db.users.insert_one({"id": uid(), "email": email, "password_hash": hash_pw(pw), "role": "admin", "nome": body.nome,
                               "verified": True, "active": body.active, "created_at": nowiso(), **(await team_fields(body))})
    await send_mail(email, "Accesso al Portale Affiliati", f"Ciao {body.nome},\n\nsei stato aggiunto al team amministratori del Portale Affiliati con l'email {email}.\nLa password ti verrà comunicata dall'amministratore. Ti consigliamo di cambiarla al primo accesso (Impostazioni > Generali).", "team")
    return {"ok": True}


@router.put("/team/{tid}")
async def team_upd(tid: str, body: TeamIn, u=Depends(super_user)):
    t = await db.users.find_one({"id": tid, "role": "admin"})
    if not t:
        raise HTTPException(404, "Utente non trovato")
    if t.get("is_master"):
        if not u.get("is_master"):
            raise HTTPException(403, "Solo il Master può modificare il proprio account")
        body.full, body.active = True, True
    upd = {"nome": body.nome, "active": body.active, **(await team_fields(body))}
    if body.password:
        if len(body.password) < 8:
            raise HTTPException(400, "Password minimo 8 caratteri")
        upd["password_hash"] = hash_pw(body.password)
    await db.users.update_one({"id": tid}, {"$set": upd})
    return {"ok": True}


@router.get("/domains")
async def domains(u=Depends(need("scadenze"))):
    R = [r for r in await all_rows(u) if r["scadenza"]]
    return sorted(R, key=lambda r: r["scadenza"])


async def domain_job():
    adm = (await get_settings()).get("adminEmail")
    for a in await db.affiliates.find({"dominio.scadenza": {"$nin": ["", None]}}, {"_id": 0}).to_list(5000):
        d = days_to(a["dominio"]["scadenza"])
        sent = a["dominio"].get("inviati", [])
        due = [r for r in REM if 0 <= d <= r]
        if not due or min(due) in sent:
            continue
        r = min(due)
        ag, url = aff_name(a), url_def(a)
        await send_mail(adm, f"Dominio in scadenza tra {d} giorni: {url}", f"Il dominio {url} di {ag} scade il {itd(a['dominio']['scadenza'])} (tra {d} giorni).\nRicordati di rinnovarlo e segnarlo come pagato nel portale.", a["id"])
        await send_mail(a["email"], f"Il tuo dominio {url} scade tra {d} giorni", f"Ciao {ag},\n\nil dominio {url} scade il {itd(a['dominio']['scadenza'])}. Ti contatteremo per il rinnovo.", a["id"])
        await notify_admins(f"Dominio <b>{url}</b> in scadenza tra {d} giorni", "scadenze", a["id"])
        await db.affiliates.update_one({"id": a["id"]}, {"$addToSet": {"dominio.inviati": {"$each": [x for x in REM if x >= r]}}})
