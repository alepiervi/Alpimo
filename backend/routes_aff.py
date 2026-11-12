import re
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from core import (db, nowiso, uid, affiliate_user, get_settings, notify, notify_admins, send_mail, admin_email, aff_name,
                  url_def, dec, file_info, pag_for)

router = APIRouter(prefix="/api/aff")
DOC_TYPES = {"identita": True, "cf": True, "visura": None, "licenza": False, "altro": False}


def clean_url(v):
    v = (v or "").strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^www\.", "", v)
    return v.split("/")[0]


URL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9-]+)*\.[a-z]{2,}$")


def billing_errors(f, tipo):
    f = f or {}
    e = []
    for k, lbl in (("intestatario", "Intestatario"), ("indirizzo", "Indirizzo"), ("cap", "CAP"), ("citta", "Città"), ("provincia", "Provincia")):
        if not (f.get(k) or "").strip():
            e.append(f"{lbl} obbligatorio")
    if f.get("cap") and not re.fullmatch(r"\d{5}", f["cap"].strip()):
        e.append("CAP: 5 cifre")
    if f.get("provincia") and not re.fullmatch(r"[A-Za-z]{2}", f["provincia"].strip()):
        e.append("Provincia: 2 lettere")
    cf, piva, sdi, pec = [(f.get(k) or "").strip() for k in ("cf", "piva", "sdi", "pec")]
    if cf and not (re.fullmatch(r"[A-Za-z0-9]{16}", cf) or re.fullmatch(r"\d{11}", cf)):
        e.append("Codice fiscale: 16 caratteri (o 11 cifre)")
    if piva and not re.fullmatch(r"\d{11}", piva):
        e.append("P.IVA: 11 cifre")
    if sdi and not re.fullmatch(r"[A-Za-z0-9]{7}", sdi):
        e.append("Codice SDI: 7 caratteri")
    if tipo == "azienda":
        if not piva:
            e.append("Per le aziende serve la P.IVA")
        if not (sdi or pec):
            e.append("Per le aziende serve almeno uno tra SDI e PEC")
    elif not (cf or piva):
        e.append("Serve il codice fiscale o la P.IVA")
    return e


async def view_aff(a, s=None):
    s = s or await get_settings()
    out = dict(a)
    out["cred"] = dec(a.get("cred")) if a.get("consegnato") else {}
    for k in ("superAdmin", "aziendaAffiliante", "aziendaId", "registrar", "tipologia"):
        out.pop(k, None)
    out["loghiInfo"] = [await file_info(x) for x in a.get("loghi") or [None] * 3]
    out["ricevutaInfo"] = await file_info(a.get("ricevuta"))
    out["urlDef"] = url_def(a)
    return out


@router.get("/me")
async def me(u=Depends(affiliate_user)):
    s = await get_settings()
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    docs = await db.documents.find({"affId": u["id"]}, {"_id": 0}).to_list(100)
    have = {d["tipo"] for d in docs if d["stato"] != "rifiutato"}
    need = [t for t, req in DOC_TYPES.items() if req or (req is None and a["tipo"] == "azienda")]
    unread = await db.news.count_documents({"lettiDa": {"$ne": u["id"]}})
    return {"aff": await view_aff(a, s), "pag": await pag_for(a), "giorni": s["giorni"], "legali": {"versione": s["legali"]["versione"]},
            "docsMancanti": [t for t in need if t not in have], "newsUnread": unread}


class ProfileIn(BaseModel):
    tipo: str
    persone: List[dict] = []
    azienda: str = ""
    piva: str = ""
    referente: str = ""
    nomeAgenzia: str = ""
    telefono: str = ""
    citta: str = ""
    urls: List[str] = []


@router.put("/profile")
async def save_profile(body: ProfileIn, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if a["stato"] not in ("bozza", "rifiutata"):
        raise HTTPException(400, "I dati sono già stati inviati")
    urls = [clean_url(x) for x in (body.urls + ["", "", ""])[:3]]
    for x in urls:
        if x and not URL_RE.match(x):
            raise HTTPException(400, f"URL non valido: {x}")
    pers = [{"nome": (p.get("nome") or "").strip(), "cognome": (p.get("cognome") or "").strip()} for p in body.persone][:10] or [{"nome": "", "cognome": ""}]
    upd = body.model_dump()
    upd.update({"persone": pers, "tipo": "azienda" if body.tipo == "azienda" else "persona",
                "urls": [{"value": x, "stato": "da_verificare"} for x in urls]})
    await db.affiliates.update_one({"id": u["id"]}, {"$set": upd})
    return {"ok": True}


@router.post("/submit")
async def submit(u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if a["stato"] not in ("bozza", "rifiutata"):
        raise HTTPException(400, "Richiesta già inviata")
    e = []
    if a["tipo"] == "azienda":
        if not (a.get("azienda") and a.get("referente")):
            e.append("ragione sociale e referente")
        if not re.fullmatch(r"\d{11}", a.get("piva") or ""):
            e.append("P.IVA di 11 cifre")
    elif not all(p.get("nome") and p.get("cognome") for p in a["persone"]):
        e.append("nome e cognome di ogni affiliato")
    for k, lbl in (("nomeAgenzia", "nome agenzia"), ("telefono", "telefono"), ("citta", "città")):
        if not a.get(k):
            e.append(lbl)
    if not any(x["value"] for x in a["urls"]):
        e.append("almeno un URL")
    if e:
        raise HTTPException(400, "Completa: " + ", ".join(e))
    be = billing_errors(a.get("fatturazione"), a["tipo"])
    if be:
        raise HTTPException(400, "Completa i dati di fatturazione (scheda Documenti): " + "; ".join(be))
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"stato": "in_attesa", "submittedAt": nowiso(), "nota": ""}})
    ag = aff_name(a)
    await notify_admins(f"Nuova richiesta di affiliazione da <b>{ag}</b>", "affiliato", u["id"])
    await send_mail(await admin_email(), f"Nuova richiesta di affiliazione: {ag}", f"{ag} ({a['email']}) ha inviato i dati per l'affiliazione.\n\nURL proposti: {', '.join(x['value'] for x in a['urls'] if x['value'])}", u["id"])
    return {"ok": True}


@router.put("/billing")
async def billing(body: dict, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    keys = ("intestatario", "cf", "piva", "sdi", "pec", "indirizzo", "cap", "citta", "provincia")
    f = {k: (str(body.get(k) or "")).strip() for k in keys}
    f["provincia"] = f["provincia"].upper()
    f["cf"] = f["cf"].upper()
    f["sdi"] = f["sdi"].upper()
    e = billing_errors(f, a["tipo"])
    if e:
        raise HTTPException(400, "; ".join(e))
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"fatturazione": f}})
    return {"ok": True}


class IdxIn(BaseModel):
    idx: int
    value: Optional[str] = None


@router.post("/logo")
async def pick_logo(body: IdxIn, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if a["stato"] != "accettata" or not (0 <= body.idx < 3) or not a["loghi"][body.idx]:
        raise HTTPException(400, "Logo non disponibile")
    if a.get("sceltaFinale") or a["pagamento"] == "confermato":
        raise HTTPException(400, "Il logo non si può più cambiare")
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"logoScelto": body.idx}})
    await notify_admins(f"<b>{aff_name(a)}</b> ha scelto il logo {body.idx + 1}", "affiliato", u["id"])
    await finalize(u["id"])
    return {"ok": True}


@router.post("/url-final")
async def url_final(body: IdxIn, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if a["stato"] != "accettata" or a.get("urlDefinitivo") is not None:
        raise HTTPException(400, "URL definitivo già scelto")
    if not (0 <= body.idx < 3) or a["urls"][body.idx]["stato"] != "disponibile":
        raise HTTPException(400, "Puoi scegliere solo un URL disponibile")
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"urlDefinitivo": body.idx}})
    await notify_admins(f"<b>{aff_name(a)}</b> ha scelto l'URL definitivo <b>{a['urls'][body.idx]['value']}</b>", "affiliato", u["id"])
    await finalize(u["id"])
    return {"ok": True}


async def finalize(aid):
    a = await db.affiliates.find_one({"id": aid}, {"_id": 0})
    li, ui = a.get("logoScelto"), a.get("urlDefinitivo")
    if li is None or ui is None or a.get("sceltaFinale"):
        return
    drop = [f for i, f in enumerate(a["loghi"]) if i != li and f]
    await db.files.update_many({"id": {"$in": drop}}, {"$set": {"is_deleted": True}})
    loghi = [f if i == li else None for i, f in enumerate(a["loghi"])]
    urls = [x if i == ui else {"value": "", "stato": "da_verificare"} for i, x in enumerate(a["urls"])]
    await db.affiliates.update_one({"id": aid}, {"$set": {"loghi": loghi, "urls": urls, "sceltaFinale": True}})


class ProposteRisp(BaseModel):
    idx: int = -1
    urls: List[str] = []


def free_slot(a):
    return next((i for i, x in enumerate(a["urls"]) if not x["value"] or x["stato"] == "non_disponibile"), 0)


@router.post("/proposte/accetta")
async def proposte_accetta(body: ProposteRisp, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    p = a.get("proposte") or {}
    if a["stato"] != "accettata" or a.get("urlDefinitivo") is not None or p.get("stato") != "inviate" or not 0 <= body.idx < len(p["domini"]):
        raise HTTPException(400, "Operazione non consentita")
    d, i = p["domini"][body.idx], free_slot(a)
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {f"urls.{i}": {"value": d, "stato": "disponibile"}, "urlDefinitivo": i, "proposte.stato": "accettata", "proposte.scelto": d}})
    await notify_admins(f"<b>{aff_name(a)}</b> ha accettato il dominio proposto <b>{d}</b> come URL definitivo", "affiliato", u["id"])
    await finalize(u["id"])
    return {"ok": True}


@router.post("/proposte/rifiuta")
async def proposte_rifiuta(body: ProposteRisp, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if a["stato"] != "accettata" or a.get("urlDefinitivo") is not None or (a.get("proposte") or {}).get("stato") != "inviate":
        raise HTTPException(400, "Operazione non consentita")
    N = [clean_url(x) for x in body.urls if x.strip()][:3]
    if not N:
        raise HTTPException(400, "Indica almeno un dominio alternativo")
    for x in N:
        if not URL_RE.match(x):
            raise HTTPException(400, f"URL non valido: {x}")
    slots = [i for i, x in enumerate(a["urls"]) if not x["value"] or x["stato"] == "non_disponibile"] or [0, 1, 2]
    upd = {f"urls.{i}": {"value": v, "stato": "da_verificare"} for i, v in zip(slots, N)}
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {**upd, "proposte.stato": "rifiutate"}})
    await notify_admins(f"<b>{aff_name(a)}</b> ha rifiutato le proposte e indicato nuovi domini: <b>{', '.join(N)}</b>", "affiliato", u["id"])
    await send_mail(await admin_email(), f"{aff_name(a)}: nuovi domini da verificare", f"{aff_name(a)} ha rifiutato i domini proposti e indica questi da verificare:\n\n" + "\n".join(f"• {x}" for x in N), u["id"])
    return {"ok": True}


@router.post("/url-alt")
async def url_alt(body: IdxIn, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    v = clean_url(body.value)
    if a["stato"] != "accettata" or a.get("urlDefinitivo") is not None or not (0 <= body.idx < 3):
        raise HTTPException(400, "Operazione non consentita")
    if a["urls"][body.idx]["value"] and a["urls"][body.idx]["stato"] != "non_disponibile":
        raise HTTPException(400, "Puoi sostituire solo un URL non disponibile")
    if not URL_RE.match(v):
        raise HTTPException(400, "URL non valido")
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {f"urls.{body.idx}": {"value": v, "stato": "da_verificare"}}})
    await notify_admins(f"<b>{aff_name(a)}</b> ha proposto un nuovo URL: <b>{v}</b>", "affiliato", u["id"])
    return {"ok": True}


class FileIn(BaseModel):
    file: str


async def own_file(fid, u):
    f = await db.files.find_one({"id": fid, "owner": u["id"], "is_deleted": False})
    if not f:
        raise HTTPException(400, "File non valido")
    return f


@router.post("/receipt")
async def receipt(body: FileIn, u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    await own_file(body.file, u)
    if a.get("urlDefinitivo") is None or a["pagamento"] not in ("nessuno", "respinto"):
        raise HTTPException(400, "Caricamento ricevuta non disponibile")
    pg = await pag_for(a)
    imp = float(str(pg.get("importo") or 0).replace(",", ".") or 0)
    iva = float(str(pg.get("iva") or 0).replace(",", ".") or 0)
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"ricevuta": body.file, "ricevutaAt": nowiso(), "pagamento": "in_verifica", "notaPagamento": ""}})
    pay = {"affId": u["id"], "kind": "attivazione", "descrizione": f"Attivazione sito {url_def(a)}", "imponibile": imp, "iva": iva,
           "totale": round(imp * (1 + iva / 100), 2), "stato": "in_verifica", "ricevuta": body.file, "nota": "", "at": nowiso()}
    ex = await db.payments.find_one({"affId": u["id"], "kind": "attivazione"})
    if ex:
        await db.payments.update_one({"_id": ex["_id"]}, {"$set": pay})
    else:
        await db.payments.insert_one({"id": uid(), **pay, "invoice": None})
    ag = aff_name(a)
    await notify_admins(f"<b>{ag}</b> ha caricato la ricevuta del pagamento", "affiliato", u["id"])
    await send_mail(await admin_email(), f"Ricevuta di pagamento da verificare: {ag}", f"{ag} ha caricato la ricevuta del bonifico per l'attivazione del sito {url_def(a)}.", u["id"])
    return {"ok": True}


@router.post("/request-online")
async def request_online(u=Depends(affiliate_user)):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if not a.get("consegnato") or a.get("online"):
        raise HTTPException(400, "Operazione non disponibile")
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"richiestaOnline": True}})
    ag = aff_name(a)
    await notify_admins(f"<b>{ag}</b> chiede di mettere online il sito", "affiliato", u["id"])
    await send_mail(await admin_email(), f"Richiesta messa online: {ag}", f"{ag} ha finito le modifiche e chiede di mettere online {url_def(a)}.", u["id"])
    return {"ok": True}


@router.post("/marketing")
async def marketing(body: dict, u=Depends(affiliate_user)):
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"consensi.marketing": {"value": bool(body.get("value")), "at": nowiso()}}})
    return {"ok": True}


# ---------- documenti ----------
@router.get("/docs")
async def docs(u=Depends(affiliate_user)):
    L = await db.documents.find({"affId": u["id"]}, {"_id": 0}).sort("uploadedAt", -1).to_list(200)
    for d in L:
        d["fileInfo"] = await file_info(d["file"])
    return L


class DocIn(BaseModel):
    tipo: str
    file: str


@router.post("/docs")
async def add_doc(body: DocIn, u=Depends(affiliate_user)):
    if body.tipo not in DOC_TYPES:
        raise HTTPException(400, "Tipo non valido")
    f = await own_file(body.file, u)
    if body.tipo != "altro":
        ex = await db.documents.find_one({"affId": u["id"], "tipo": body.tipo})
        if ex and ex["stato"] == "approvato":
            raise HTTPException(400, "Documento già approvato")
        await db.documents.delete_many({"affId": u["id"], "tipo": body.tipo})
    await db.documents.insert_one({"id": uid(), "affId": u["id"], "tipo": body.tipo, "file": body.file, "name": f["name"], "stato": "in_verifica", "nota": "", "uploadedAt": nowiso()})
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    await notify_admins(f"<b>{aff_name(a)}</b> ha caricato un documento ({body.tipo})", "affiliato", u["id"])
    return {"ok": True}


# ---------- pagamenti ----------
@router.get("/payments")
async def payments(u=Depends(affiliate_user)):
    L = await db.payments.find({"affId": u["id"]}, {"_id": 0}).sort("at", -1).to_list(200)
    for p in L:
        p["ricevutaInfo"] = await file_info(p.get("ricevuta"))
    return L


# ---------- bacheca / materiali ----------
@router.get("/news")
async def news(u=Depends(affiliate_user)):
    L = await db.news.find({}, {"_id": 0}).sort("at", -1).to_list(200)
    for n in L:
        n["letto"] = u["id"] in (n.pop("lettiDa", []) or [])
    return L


@router.post("/news/read")
async def news_read(u=Depends(affiliate_user)):
    await db.news.update_many({}, {"$addToSet": {"lettiDa": u["id"]}})
    return {"ok": True}


@router.get("/materials")
async def materials(u=Depends(affiliate_user)):
    return await db.materials.find({"deleted": {"$ne": True}}, {"_id": 0}).sort("at", -1).to_list(500)


@router.post("/materials/{mid}/download")
async def mat_dl(mid: str, u=Depends(affiliate_user)):
    await db.materials.update_one({"id": mid, "deleted": {"$ne": True}}, {"$inc": {"downloads": 1}})
    return {"ok": True}


# ---------- corsi ----------
async def course_gate(u):
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    if a["pagamento"] != "confermato":
        raise HTTPException(403, "Academy disponibile dopo la conferma del pagamento")
    return a


def course_view(c, prog, purch):
    unlocked = bool(not c.get("premium") or (purch and purch["stato"] == "pagato"))
    fatte = (prog or {}).get("fatte", [])
    les = []
    for i, l in enumerate(c.get("lezioni", [])):
        lock = not unlocked and i > 0
        les.append({**l, "file": None if lock else l.get("file"), "url": None if lock else l.get("url"), "locked": lock, "done": l["id"] in fatte})
    n = len(les)
    return {**c, "lezioni": les, "unlocked": unlocked, "progress": round(100 * len([x for x in les if x["done"]]) / n) if n else 0,
            "purchase": {k: purch.get(k) for k in ("stato", "nota", "at")} if purch else None, "completatoAt": (prog or {}).get("completatoAt")}


@router.get("/courses")
async def courses(u=Depends(affiliate_user)):
    await course_gate(u)
    L = await db.courses.find({"pubblicato": True}, {"_id": 0}).sort("createdAt", 1).to_list(200)
    prog = {p["courseId"]: p for p in await db.progress.find({"affId": u["id"]}, {"_id": 0}).to_list(500)}
    purch = {p["ref"]: p for p in await db.payments.find({"affId": u["id"], "kind": "corso"}, {"_id": 0}).to_list(500)}
    return [course_view(c, prog.get(c["id"]), purch.get(c["id"])) for c in L]


@router.get("/courses/{cid}")
async def course(cid: str, u=Depends(affiliate_user)):
    await course_gate(u)
    c = await db.courses.find_one({"id": cid, "pubblicato": True}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Corso non trovato")
    prog = await db.progress.find_one({"affId": u["id"], "courseId": cid}, {"_id": 0})
    purch = await db.payments.find_one({"affId": u["id"], "kind": "corso", "ref": cid}, {"_id": 0})
    return course_view(c, prog, purch)


class LessonIn(BaseModel):
    lid: str


@router.post("/courses/{cid}/done")
async def lesson_done(cid: str, body: LessonIn, u=Depends(affiliate_user)):
    a = await course_gate(u)
    c = await db.courses.find_one({"id": cid, "pubblicato": True}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Corso non trovato")
    purch = await db.payments.find_one({"affId": u["id"], "kind": "corso", "ref": cid})
    v = course_view(c, None, purch)
    les = next((x for x in v["lezioni"] if x["id"] == body.lid), None)
    if not les or les["locked"]:
        raise HTTPException(400, "Lezione bloccata")
    await db.progress.update_one({"affId": u["id"], "courseId": cid}, {"$addToSet": {"fatte": body.lid}}, upsert=True)
    p = await db.progress.find_one({"affId": u["id"], "courseId": cid}, {"_id": 0})
    ids = {x["id"] for x in c["lezioni"]}
    if ids and ids <= set(p["fatte"]) and not p.get("completatoAt"):
        await db.progress.update_one({"affId": u["id"], "courseId": cid}, {"$set": {"completatoAt": nowiso()}})
        await notify_admins(f"<b>{aff_name(a)}</b> ha completato il corso <b>{c['titolo']}</b>", "corsi", cid)
    return {"ok": True}


@router.post("/courses/{cid}/buy")
async def course_buy(cid: str, body: FileIn, u=Depends(affiliate_user)):
    a = await course_gate(u)
    await own_file(body.file, u)
    c = await db.courses.find_one({"id": cid, "pubblicato": True, "premium": True}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Corso non trovato")
    ex = await db.payments.find_one({"affId": u["id"], "kind": "corso", "ref": cid})
    if ex and ex["stato"] in ("in_verifica", "pagato"):
        raise HTTPException(400, "Ricevuta già caricata")
    iva = float(str((await pag_for(a)).get("iva") or 0).replace(",", ".") or 0)
    tot = float(c.get("prezzo") or 0)
    imp = round(tot / (1 + iva / 100), 2)
    pay = {"affId": u["id"], "kind": "corso", "ref": cid, "descrizione": f"Corso Premium: {c['titolo']}", "imponibile": imp, "iva": iva,
           "totale": tot, "stato": "in_verifica", "ricevuta": body.file, "nota": "", "at": nowiso()}
    if ex:
        await db.payments.update_one({"_id": ex["_id"]}, {"$set": pay})
    else:
        await db.payments.insert_one({"id": uid(), **pay, "invoice": None})
    ag = aff_name(a)
    await notify_admins(f"<b>{ag}</b> ha acquistato il corso <b>{c['titolo']}</b>: ricevuta da verificare", "corsi", cid)
    await send_mail(await admin_email(), f"Ricevuta corso Premium da verificare: {ag}", f"{ag} ha caricato la ricevuta per il corso \"{c['titolo']}\" ({tot} € IVA inclusa).", cid)
    await send_mail(a["email"], f"Abbiamo ricevuto la tua ricevuta per \"{c['titolo']}\"", f"Ciao {ag},\n\nabbiamo ricevuto la ricevuta per il corso \"{c['titolo']}\". Lo sbloccheremo appena verificato il pagamento.", cid)
    await notify(u["id"], f"Ricevuta per <b>{c['titolo']}</b> inviata: in verifica", "corsi", cid)
    return {"ok": True}
