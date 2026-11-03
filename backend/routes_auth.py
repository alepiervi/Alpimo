from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
from datetime import timedelta
import os
import jwt
from core import (db, email_status, nowiso, now, code6, sha, send_mail, get_settings, uid, hash_pw, check_pw, notify_admins,
                  set_auth_cookies, current_user, JWT_ALG)

router = APIRouter(prefix="/api/auth")


def new_aff(user_id, email, tipo):
    return {"id": user_id, "email": email, "tipo": tipo, "persone": [{"nome": "", "cognome": ""}], "azienda": "", "piva": "", "referente": "",
            "nomeAgenzia": "", "telefono": "", "citta": "", "urls": [{"value": "", "stato": "da_verificare"} for _ in range(3)],
            "stato": "bozza", "nota": "", "submittedAt": None, "decidedAt": None, "loghi": [None, None, None], "logoScelto": None,
            "urlDefinitivo": None, "ricevuta": None, "pagamento": "nessuno", "notaPagamento": "", "pagamentoAt": None, "consegna": None,
            "cred": None, "superAdmin": None, "consegnato": False, "consegnatoAt": None, "richiestaOnline": False, "online": False,
            "onlineAt": None, "dominio": {"scadenza": "", "storico": [], "inviati": []}, "fatturazione": {}, "consensi": {}, "createdAt": nowiso()}


class RegisterIn(BaseModel):
    email: str
    password: str
    tipo: str = "persona"
    contratto: bool
    privacy: bool
    marketing: bool = False


class LoginIn(BaseModel):
    email: str
    password: str


class CodeIn(BaseModel):
    code: str


class EmailIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    email: str
    code: str
    password: str


class PwIn(BaseModel):
    old: str
    new: str


def public_user(u):
    return {k: u.get(k) for k in ("id", "email", "role", "is_super", "nome", "perms", "verified", "active")}


async def send_verify(u):
    c = code6()
    await db.codes.delete_many({"user_id": u["id"], "kind": "verify"})
    await db.codes.insert_one({"user_id": u["id"], "kind": "verify", "hash": sha(c), "exp": (now() + timedelta(hours=24)).isoformat(), "tries": 0})
    await send_mail(u["email"], "Il tuo codice di verifica", f"Benvenuto nel Portale Affiliati!\n\nIl tuo codice di verifica è: {c}\n\nIl codice è valido 24 ore.", "verify")


async def check_code(user_id, kind, code):
    rec = await db.codes.find_one({"user_id": user_id, "kind": kind})
    if not rec or rec["exp"] < nowiso() or rec["tries"] >= 5:
        raise HTTPException(400, "Codice scaduto o non valido: richiedine uno nuovo")
    if rec["hash"] != sha(code.strip()):
        await db.codes.update_one({"_id": rec["_id"]}, {"$inc": {"tries": 1}})
        raise HTTPException(400, "Codice errato")
    await db.codes.delete_one({"_id": rec["_id"]})


@router.post("/register")
async def register(body: RegisterIn, response: Response):
    email = body.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Email non valida")
    if len(body.password) < 8:
        raise HTTPException(400, "La password deve avere almeno 8 caratteri")
    if not (body.contratto and body.privacy):
        raise HTTPException(400, "Devi accettare contratto e informativa privacy")
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email già registrata")
    s = await get_settings()
    v, t = s["legali"]["versione"], nowiso()
    mail_on = any(email_status().values())

    u = {"id": uid(), "email": email, "password_hash": hash_pw(body.password), "role": "affiliate", "is_super": False, "nome": "",
         "perms": [], "verified": not mail_on, "active": True, "created_at": t}
    await db.users.insert_one(u)
    a = new_aff(u["id"], email, "azienda" if body.tipo == "azienda" else "persona")
    a["consensi"] = {"contratto": {"versione": v, "at": t}, "privacy": {"versione": v, "at": t}, "marketing": {"value": body.marketing, "at": t}}
    await db.affiliates.insert_one(a)
    if mail_on:
        await send_verify(u)
    await notify_admins(f"Nuova registrazione: <b>{email}</b>", "affiliato", u["id"])
    set_auth_cookies(response, u["id"])
    return public_user(u)


@router.post("/login")
async def login(body: LoginIn, response: Response):
    email = body.email.strip().lower()
    ident = f"login:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5 and att.get("until", "") > nowiso():
        raise HTTPException(429, "Troppi tentativi: riprova tra 15 minuti")
    u = await db.users.find_one({"email": email})
    if not u or not check_pw(body.password, u["password_hash"]):
        cnt = (att or {}).get("count", 0) + 1
        await db.login_attempts.update_one({"identifier": ident}, {"$set": {"count": cnt, "until": (now() + timedelta(minutes=15)).isoformat()}}, upsert=True)
        raise HTTPException(401, "Email o password non corretti")
    if not u.get("active", True):
        raise HTTPException(403, "Account disattivato")
    await db.login_attempts.delete_many({"identifier": ident})
    set_auth_cookies(response, u["id"])
    return public_user(u)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    t = request.cookies.get("refresh_token")
    try:
        p = jwt.decode(t or "", os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
        assert p.get("type") == "refresh"
    except Exception:
        raise HTTPException(401, "Sessione scaduta")
    u = await db.users.find_one({"id": p["sub"]})
    if not u or not u.get("active", True):
        raise HTTPException(401, "Account non attivo")
    set_auth_cookies(response, u["id"])
    return {"ok": True}


@router.get("/me")
async def me(u=Depends(current_user)):
    out = public_user(u)
    if u["role"] == "affiliate":
        s = await get_settings()
        a = await db.affiliates.find_one({"id": u["id"]}, {"_id": 0}) or {}
        c = a.get("consensi", {})
        out["termsOutdated"] = (c.get("contratto") or {}).get("versione", 0) < s["legali"]["versione"]
    return out


@router.post("/verify")
async def verify(body: CodeIn, u=Depends(current_user)):
    await check_code(u["id"], "verify", body.code)
    await db.users.update_one({"id": u["id"]}, {"$set": {"verified": True}})
    return {"ok": True}


@router.post("/resend")
async def resend(u=Depends(current_user)):
    if not u.get("verified"):
        await send_verify(u)
    return {"ok": True}


@router.post("/forgot")
async def forgot(body: EmailIn):
    u = await db.users.find_one({"email": body.email.strip().lower()})
    if u and u.get("active", True):
        c = code6()
        await db.codes.delete_many({"user_id": u["id"], "kind": "reset"})
        await db.codes.insert_one({"user_id": u["id"], "kind": "reset", "hash": sha(c), "exp": (now() + timedelta(minutes=30)).isoformat(), "tries": 0})
        await send_mail(u["email"], "Codice per reimpostare la password", f"Hai chiesto di reimpostare la password.\n\nIl tuo codice è: {c}\n\nÈ valido 30 minuti. Se non sei stato tu, ignora questa email.", "reset")
    return {"ok": True}


@router.post("/reset")
async def reset(body: ResetIn):
    if len(body.password) < 8:
        raise HTTPException(400, "La password deve avere almeno 8 caratteri")
    u = await db.users.find_one({"email": body.email.strip().lower()})
    if not u:
        raise HTTPException(400, "Codice scaduto o non valido")
    await check_code(u["id"], "reset", body.code)
    await db.users.update_one({"id": u["id"]}, {"$set": {"password_hash": hash_pw(body.password)}})
    return {"ok": True}


@router.post("/accept-terms")
async def accept_terms(u=Depends(current_user)):
    s = await get_settings()
    v, t = s["legali"]["versione"], nowiso()
    await db.affiliates.update_one({"id": u["id"]}, {"$set": {"consensi.contratto": {"versione": v, "at": t}, "consensi.privacy": {"versione": v, "at": t}}})
    return {"ok": True}


@router.post("/change-password")
async def change_password(body: PwIn, u=Depends(current_user)):
    full = await db.users.find_one({"id": u["id"]})
    if not check_pw(body.old, full["password_hash"]):
        raise HTTPException(400, "Password attuale errata")
    if len(body.new) < 8:
        raise HTTPException(400, "La nuova password deve avere almeno 8 caratteri")
    await db.users.update_one({"id": u["id"]}, {"$set": {"password_hash": hash_pw(body.new)}})
    return {"ok": True}


@router.get("/legal")
async def legal():
    s = await get_settings()
    return s["legali"]
