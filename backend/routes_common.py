import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Response
from pydantic import BaseModel
from core import (db, nowiso, uid, current_user, can, put_object, get_object, notify, notify_admins, send_mail, admin_email,
                  aff_name, next_seq, scope_ids, tk_rep_q, reparto_emails)

router = APIRouter(prefix="/api")
EXT_AFF = {"pdf", "jpg", "jpeg", "png", "webp", "gif", "heic"}
EXT_ADMIN = EXT_AFF | {"svg", "zip", "docx", "pptx", "xlsx", "csv", "mp4", "txt", "doc", "xls", "ppt", "mov", "webm"}


@router.post("/files")
async def upload(file: UploadFile = File(...), owner: str = Form(""), u=Depends(current_user)):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in file.filename else "").lower()
    data = await file.read()
    if u["role"] == "affiliate":
        if ext not in EXT_AFF:
            raise HTTPException(400, "Formato non ammesso: carica un PDF o un'immagine")
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(400, "File troppo grande (max 10 MB)")
        owner = u["id"]
    else:
        if ext not in EXT_ADMIN:
            raise HTTPException(400, "Formato non ammesso")
        limit = 500 if ext in ("mp4", "mov", "webm") else 50
        if len(data) > limit * 1024 * 1024:
            raise HTTPException(400, f"File troppo grande (max {limit} MB)")
        owner = owner or "public"
    path = f"{os.environ.get('APP_NAME', 'alpimo')}/uploads/{owner}/{uuid.uuid4()}.{ext or 'bin'}"
    ctype = file.content_type or "application/octet-stream"
    try:
        res = put_object(path, data, ctype)
    except Exception as e:
        raise HTTPException(502, f"Archiviazione non disponibile: {str(e)[:80]}")
    doc = {"id": uid(), "path": res["path"], "name": file.filename, "type": ctype, "size": len(data), "owner": owner,
           "uploader": u["id"], "is_deleted": False, "created_at": nowiso()}
    await db.files.insert_one(doc)
    return {"id": doc["id"], "name": doc["name"], "type": ctype, "size": doc["size"]}


async def check_course_video(fid, u):
    c = await db.courses.find_one({"lezioni.file": fid}, {"_id": 0})
    if not c:
        return
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0, "pagamento": 1})
    if not c.get("pubblicato") or (a or {}).get("pagamento") != "confermato":
        raise HTTPException(403, "Video non disponibile")
    idx = next(i for i, l in enumerate(c["lezioni"]) if l.get("file") == fid)
    if c.get("premium") and idx > 0:
        paid = await db.payments.find_one({"affId": u["id"], "kind": "corso", "ref": c["id"], "stato": "pagato"})
        if not paid:
            raise HTTPException(403, "Video riservato a chi ha acquistato il corso")


@router.get("/files/{fid}")
async def download(fid: str, dl: int = 0, u=Depends(current_user)):
    f = await db.files.find_one({"id": fid, "is_deleted": False})
    if not f:
        raise HTTPException(404, "File non trovato")
    if u["role"] != "admin" and f["owner"] not in (u["id"], "public"):
        raise HTTPException(403, "Accesso negato")
    if u["role"] != "admin":
        await check_course_video(fid, u)
    data, ct = get_object(f["path"])
    disp = "attachment" if dl else "inline"
    safe = f["name"].encode("ascii", "ignore").decode().replace('"', "") or "file"
    return Response(content=data, media_type=f.get("type") or ct, headers={"Content-Disposition": f'{disp}; filename="{safe}"', "Cache-Control": "private, max-age=3600"})


# ---------- notifications ----------
def nkey(u):
    return {"$in": ["admin", u["id"]]} if u["role"] == "admin" else u["id"]


VIEW_PERMS = {"affiliato": ["affiliati", "richieste"], "ticket": ["ticket"], "corsi": ["corsi"], "scadenze": ["scadenze", "affiliati"]}


async def nquery(u):
    q = {"to": nkey(u)}
    if u["role"] == "admin" and not u.get("is_super"):
        views = [v for v, ps in VIEW_PERMS.items() if any(can(u, p) for p in ps)]
        ids = await scope_ids(u)
        rq = tk_rep_q(u)
        if ids is None and not rq:
            q["view"] = {"$in": [None] + views}
        else:
            tq = {**rq, **({} if ids is None else {"affId": {"$in": list(ids)}})}
            tids = [t["id"] for t in await db.tickets.find(tq, {"_id": 0, "id": 1}).to_list(10000)]
            ors = [{"view": None}]
            if ids is None:
                ors.append({"view": {"$in": [v for v in views if v != "ticket"]}})
            else:
                ors += [{"view": v, "ref": {"$in": list(ids)}} for v in views if v in ("affiliato", "scadenze")]
            if "ticket" in views:
                ors.append({"view": "ticket", "ref": {"$in": tids}})
            q["$or"] = ors
    return q


@router.get("/notifications")
async def notifs(u=Depends(current_user)):
    return await db.notifications.find(await nquery(u), {"_id": 0}).sort("at", -1).to_list(40)


@router.post("/notifications/read-all")
async def notifs_all(u=Depends(current_user)):
    await db.notifications.update_many(await nquery(u), {"$set": {"letto": True}})
    return {"ok": True}


@router.post("/notifications/{nid}/read")
async def notif_read(nid: str, u=Depends(current_user)):
    await db.notifications.update_one({**(await nquery(u)), "id": nid}, {"$set": {"letto": True}})
    return {"ok": True}


# ---------- tickets ----------
class TicketIn(BaseModel):
    oggetto: str
    priorita: str = "media"
    testo: str
    reparto: str = ""


class RepIn(BaseModel):
    reparto: str


async def rep_name(rid):
    r = await db.reparti.find_one({"id": rid}, {"_id": 0}) if rid else None
    return r["nome"] if r else "Senza reparto"


async def tk_mail(t, subject, body):
    for to in {await admin_email(), *(await reparto_emails(t.get("reparto")))} - {None, ""}:
        await send_mail(to, subject, body, t["id"])


@router.get("/reparti")
async def reparti(u=Depends(current_user)):
    return await db.reparti.find({}, {"_id": 0}).sort([("ordine", 1), ("nome", 1)]).to_list(100)


class MsgIn(BaseModel):
    testo: str


class StatoIn(BaseModel):
    stato: str


LBL = {"aperto": "Aperto", "in_lavorazione": "In lavorazione", "chiuso": "Chiuso"}


async def tk_access(tid, u):
    t = await db.tickets.find_one({"id": tid}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Ticket non trovato")
    if u["role"] == "affiliate" and t["affId"] != u["id"]:
        raise HTTPException(403, "Accesso negato")
    if u["role"] == "admin" and not can(u, "ticket") and not can(u, "affiliati"):
        raise HTTPException(403, "Permesso negato")
    if u["role"] == "admin":
        ids = await scope_ids(u)
        if ids is not None and t["affId"] not in ids:
            raise HTTPException(404, "Ticket non trovato")
        rq = tk_rep_q(u)
        if rq and t.get("reparto") not in rq["reparto"]["$in"]:
            raise HTTPException(404, "Ticket non trovato")
    return t


@router.get("/tickets")
async def tickets(affId: str = "", u=Depends(current_user)):
    q = {"affId": u["id"]} if u["role"] == "affiliate" else ({"affId": affId} if affId else {})
    if u["role"] == "admin" and not (can(u, "ticket") or can(u, "affiliati")):
        raise HTTPException(403, "Permesso negato")
    if u["role"] == "admin":
        ids = await scope_ids(u)
        if ids is not None:
            q = {"affId": affId if affId in ids else {"$in": list(ids)}}
        q.update(tk_rep_q(u))
    L = await db.tickets.find(q, {"_id": 0} if u["role"] == "admin" else {"_id": 0, "assegnato": 0, "note": 0}).sort("createdAt", -1).to_list(500)
    if u["role"] == "admin":
        names = {a["id"]: aff_name(a) for a in await db.affiliates.find({"id": {"$in": list({t["affId"] for t in L})}}, {"_id": 0}).to_list(1000)}
        for t in L:
            t["agenzia"] = names.get(t["affId"], "")
    return L


@router.post("/tickets")
async def new_ticket(body: TicketIn, u=Depends(current_user)):
    if u["role"] != "affiliate":
        raise HTTPException(403, "Solo gli affiliati aprono ticket")
    if not body.oggetto.strip() or not body.testo.strip():
        raise HTTPException(400, "Compila oggetto e descrizione")
    if not await db.reparti.find_one({"id": body.reparto}):
        raise HTTPException(400, "Scegli il reparto")
    a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0})
    n = "T-" + str(await next_seq("ticket")).zfill(4)
    t = {"id": uid(), "num": n, "affId": u["id"], "oggetto": body.oggetto.strip(), "priorita": body.priorita, "stato": "aperto", "reparto": body.reparto,
         "messaggi": [{"da": "affiliato", "testo": body.testo.strip(), "at": nowiso()}], "lettoAdmin": False, "lettoAff": True, "createdAt": nowiso()}
    await db.tickets.insert_one(dict(t))
    ag = aff_name(a)
    rn = await rep_name(body.reparto)
    await tk_mail(t, f"[Ticket #{n}] [{rn}] Nuovo ticket da {ag} – priorità {t['priorita']}", f"Nuovo ticket #{n} aperto da {ag} ({u['email']}).\n\nReparto: {rn}\nOggetto: {t['oggetto']}\nPriorità: {t['priorita']}\n\nMessaggio:\n{body.testo}")
    await send_mail(u["email"], f"[Ticket #{n}] Abbiamo ricevuto la tua richiesta", f"Ciao {ag},\n\nabbiamo ricevuto il tuo ticket #{n}: \"{t['oggetto']}\".\nTi risponderemo il prima possibile.", t["id"])
    await notify_admins(f"Nuovo ticket <b>#{n}</b> da <b>{ag}</b>: {t['oggetto']}", "ticket", t["id"])
    await notify(u["id"], f"Ticket <b>#{n}</b> aperto. Ti abbiamo inviato un'email di conferma.", "ticket", t["id"])
    t.pop("_id", None)
    return t


@router.get("/tickets/{tid}")
async def get_ticket(tid: str, u=Depends(current_user)):
    t = await tk_access(tid, u)
    field = "lettoAdmin" if u["role"] == "admin" else "lettoAff"
    await db.tickets.update_one({"id": tid}, {"$set": {field: True}})
    await db.notifications.update_many({"to": nkey(u), "ref": tid}, {"$set": {"letto": True}})
    t["emails"] = await db.email_log.find({"ref": tid}, {"_id": 0}).sort("at", -1).to_list(50) if u["role"] == "admin" else []
    if u["role"] != "admin":
        t.pop("assegnato", None)
        t.pop("note", None)
    return t


class NoteIn(BaseModel):
    testo: str


def team_only(u):
    if u["role"] != "admin" or not can(u, "ticket"):
        raise HTTPException(403, "Permesso negato")


@router.post("/tickets/{tid}/note")
async def ticket_note(tid: str, body: NoteIn, u=Depends(current_user)):
    team_only(u)
    t = await tk_access(tid, u)
    if not body.testo.strip():
        raise HTTPException(400, "Scrivi la nota")
    n = {"id": uid(), "testo": body.testo.strip(), "da": who(u), "at": nowiso()}
    await db.tickets.update_one({"id": tid}, {"$push": {"note": n}})
    a = t.get("assegnato")
    if a and a["id"] != u["id"]:
        x = await db.users.find_one({"id": a["id"], "active": {"$ne": False}}, {"_id": 0, "email": 1})
        await notify(a["id"], f"Nota interna di <b>{n['da']['nome']}</b> sul ticket <b>#{t['num']}</b>", "ticket", tid)
        if x:
            await send_mail(x["email"], f"[Ticket #{t['num']}] Nuova nota interna da {n['da']['nome']}", f"Ciao {a['nome']},\n\n{n['da']['nome']} ha aggiunto una nota interna al ticket #{t['num']} \"{t['oggetto']}\" che hai in carico:\n\n{n['testo']}", tid)
    return n


@router.delete("/tickets/{tid}/note/{nid}")
async def ticket_note_del(tid: str, nid: str, u=Depends(current_user)):
    team_only(u)
    t = await tk_access(tid, u)
    n = next((x for x in t.get("note") or [] if x["id"] == nid), None)
    if not n:
        raise HTTPException(404, "Nota non trovata")
    if n["da"]["id"] != u["id"] and not u.get("is_super"):
        raise HTTPException(403, "Puoi eliminare solo le tue note")
    await db.tickets.update_one({"id": tid}, {"$pull": {"note": {"id": nid}}})
    return {"ok": True}


class AssignIn(BaseModel):
    userId: str = ""


def who(x):
    return {"id": x["id"], "nome": x.get("nome") or x["email"]}


@router.post("/tickets/{tid}/assign")
async def ticket_assign(tid: str, body: AssignIn, u=Depends(current_user)):
    if u["role"] != "admin" or not can(u, "ticket"):
        raise HTTPException(403, "Permesso negato")
    t = await tk_access(tid, u)
    cur = (t.get("assegnato") or {}).get("id")
    if not u.get("is_super"):
        if body.userId == u["id"] and cur not in (None, u["id"]):
            raise HTTPException(400, "Il ticket è già in carico a un collega")
        if body.userId not in (u["id"], "") or (body.userId == "" and cur != u["id"]):
            raise HTTPException(403, "Solo il Master o chi ha accesso completo può riassegnare i ticket")
    val = None
    if body.userId:
        x = await db.users.find_one({"id": body.userId, "role": "admin", "active": {"$ne": False}}, {"_id": 0, "password_hash": 0})
        if not x:
            raise HTTPException(400, "Operatore non valido")
        val = {**who(x), "at": nowiso()}
    await db.tickets.update_one({"id": tid}, {"$set": {"assegnato": val}})
    if val and body.userId != u["id"]:
        await send_mail(x["email"], f"[Ticket #{t['num']}] Assegnato a te", f"Ciao {val['nome']},\n\n{u.get('nome') or u['email']} ti ha assegnato il ticket #{t['num']} \"{t['oggetto']}\".", tid)
    return {"ok": True, "assegnato": val}


@router.post("/tickets/{tid}/msg")
async def ticket_msg(tid: str, body: MsgIn, u=Depends(current_user)):
    t = await tk_access(tid, u)
    if not body.testo.strip():
        raise HTTPException(400, "Scrivi un messaggio")
    a = await db.affiliates.find_one({"id": t["affId"]}, {"_id": 0})
    ag, n = aff_name(a), t["num"]
    msg = {"da": "admin" if u["role"] == "admin" else "affiliato", "testo": body.testo.strip(), "at": nowiso()}
    if u["role"] == "admin":
        st = "in_lavorazione" if t["stato"] == "aperto" else t["stato"]
        upd = {"lettoAff": False, "lettoAdmin": True, "stato": st}
        if not t.get("assegnato"):
            upd["assegnato"] = {**who(u), "at": nowiso()}
        await db.tickets.update_one({"id": tid}, {"$push": {"messaggi": msg}, "$set": upd})
        await send_mail(a["email"], f"[Ticket #{n}] Nuova risposta dal supporto", f"Ciao {ag},\n\nil supporto ha risposto al ticket #{n} \"{t['oggetto']}\":\n\n{msg['testo']}\n\nStato attuale: {LBL[st]}", tid)
        await notify(t["affId"], f"Nuova risposta al ticket <b>#{n}</b>", "ticket", tid)
    else:
        reopen = t["stato"] == "chiuso"
        await db.tickets.update_one({"id": tid}, {"$push": {"messaggi": msg}, "$set": {"lettoAdmin": False, "lettoAff": True, "stato": "aperto" if reopen else t["stato"]}})
        extra = " – riaperto" if reopen else ""
        await tk_mail(t, f"[Ticket #{n}] Nuova risposta da {ag}{extra}", f"{ag} ha risposto al ticket #{n} \"{t['oggetto']}\":\n\n{msg['testo']}")
        await notify_admins(f"<b>{ag}</b> ha risposto al ticket <b>#{n}</b>{extra}", "ticket", tid)
    return {"ok": True}


@router.post("/tickets/{tid}/status")
async def ticket_status(tid: str, body: StatoIn, u=Depends(current_user)):
    t = await tk_access(tid, u)
    if body.stato not in LBL:
        raise HTTPException(400, "Stato non valido")
    a = await db.affiliates.find_one({"id": t["affId"]}, {"_id": 0})
    ag, n = aff_name(a), t["num"]
    if u["role"] == "affiliate":
        if body.stato != "chiuso":
            raise HTTPException(400, "Puoi solo segnare il ticket come risolto")
        await db.tickets.update_one({"id": tid}, {"$set": {"stato": "chiuso", "lettoAdmin": False}})
        await tk_mail(t, f"[Ticket #{n}] Segnato come risolto da {ag}", f"{ag} ha segnato come risolto il ticket #{n} \"{t['oggetto']}\".")
        await notify_admins(f"<b>{ag}</b> ha segnato come risolto il ticket <b>#{n}</b>", "ticket", tid)
    else:
        await db.tickets.update_one({"id": tid}, {"$set": {"stato": body.stato, "lettoAff": False}})
        await send_mail(a["email"], f"[Ticket #{n}] Stato aggiornato: {LBL[body.stato]}", f"Ciao {ag},\n\nil ticket #{n} \"{t['oggetto']}\" è ora nello stato: {LBL[body.stato]}.", tid)
        await notify(t["affId"], f"Ticket <b>#{n}</b>: stato aggiornato a {LBL[body.stato]}", "ticket", tid)
    return {"ok": True}


@router.post("/tickets/{tid}/reparto")
async def ticket_reparto(tid: str, body: RepIn, u=Depends(current_user)):
    if u["role"] != "admin" or not can(u, "ticket"):
        raise HTTPException(403, "Permesso negato")
    t = await tk_access(tid, u)
    if not await db.reparti.find_one({"id": body.reparto}):
        raise HTTPException(400, "Reparto non valido")
    if body.reparto == t.get("reparto"):
        return {"ok": True}
    await db.tickets.update_one({"id": tid}, {"$set": {"reparto": body.reparto, "lettoAdmin": False}})
    t["reparto"] = body.reparto
    rn = await rep_name(body.reparto)
    a = await db.affiliates.find_one({"id": t["affId"]}, {"_id": 0})
    await tk_mail(t, f"[Ticket #{t['num']}] Spostato nel reparto {rn}", f"Il ticket #{t['num']} \"{t['oggetto']}\" di {aff_name(a)} è stato spostato nel reparto {rn} da {u.get('nome') or u['email']}.")
    await notify_admins(f"Ticket <b>#{t['num']}</b> spostato nel reparto <b>{rn}</b>", "ticket", tid)
    return {"ok": True}

