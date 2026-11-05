import os, uuid, json, random, hashlib, logging, asyncio
from datetime import datetime, timezone, timedelta, date
from email.message import EmailMessage
import bcrypt, jwt, requests, httpx, aiosmtplib
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request, Depends
from motor.motor_asyncio import AsyncIOMotorClient

log = logging.getLogger("alpimo")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
JWT_ALG = "HS256"
FERNET = Fernet(os.environ["CRED_KEY"].encode())
PERMS = ["richieste", "affiliati", "ticket", "corsi", "bacheca", "materiali", "scadenze", "report", "email", "impostazioni"]
NOP = {"_id": 0}


def now():
    return datetime.now(timezone.utc)


def nowiso():
    return now().isoformat()


def today():
    return date.today().isoformat()


def uid():
    return uuid.uuid4().hex[:12]


def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def check_pw(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def code6():
    return f"{random.SystemRandom().randint(0, 999999):06d}"


def enc(d: dict) -> str:
    return FERNET.encrypt(json.dumps(d).encode()).decode()


def dec(s) -> dict:
    if not s:
        return {}
    try:
        return json.loads(FERNET.decrypt(s.encode()).decode())
    except Exception:
        return {}


def add_biz(start: str, n: int) -> str:
    d = date.fromisoformat(start)
    k = 0
    while k < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            k += 1
    return d.isoformat()


def add_year(s: str) -> str:
    d = date.fromisoformat(s)
    try:
        return d.replace(year=d.year + 1).isoformat()
    except ValueError:
        return d.replace(year=d.year + 1, day=28).isoformat()


def days_to(s: str) -> int:
    return (date.fromisoformat(s) - date.today()).days


# ---------- JWT / auth ----------
def make_token(user_id, kind, minutes):
    p = {"sub": user_id, "type": kind, "exp": now() + timedelta(minutes=minutes)}
    return jwt.encode(p, os.environ["JWT_SECRET"], algorithm=JWT_ALG)


def set_auth_cookies(resp, user_id):
    resp.set_cookie("access_token", make_token(user_id, "access", 60), httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    resp.set_cookie("refresh_token", make_token(user_id, "refresh", 60 * 24 * 7), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    ah = request.headers.get("Authorization", "")
    if not token and ah.startswith("Bearer "):
        token = ah[7:]
    if not token:
        raise HTTPException(401, "Non autenticato")
    try:
        p = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Sessione scaduta")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token non valido")
    if p.get("type") != "access":
        raise HTTPException(401, "Token non valido")
    u = await db.users.find_one({"id": p["sub"]}, {"_id": 0, "password_hash": 0})
    if not u or not u.get("active", True):
        raise HTTPException(401, "Account non attivo")
    return await resolve_role(u)


async def resolve_role(u):
    if u.get("role") == "admin" and not u.get("is_super") and u.get("ruoloId"):
        r = await db.ruoli.find_one({"id": u["ruoloId"]}, {"_id": 0})
        if r:
            u["perms"], u["reparti"], u["ruoloNome"] = r.get("perms", []), r.get("reparti", []), r["nome"]
    return u


def tk_rep_q(u):
    if u.get("role") == "admin" and not u.get("is_super") and u.get("reparti"):
        return {"reparto": {"$in": u["reparti"]}}
    return {}


async def reparto_emails(rid):
    out = []
    for x in await db.users.find({"role": "admin", "active": {"$ne": False}, "is_super": {"$ne": True}}, {"_id": 0, "password_hash": 0}).to_list(500):
        x = await resolve_role(x)
        if rid in (x.get("reparti") or []) and "ticket" in (x.get("perms") or []):
            out.append(x["email"])
    return out


async def affiliate_user(u=Depends(current_user)):
    if u["role"] != "affiliate":
        raise HTTPException(403, "Solo affiliati")
    if not u.get("verified"):
        raise HTTPException(403, "Email non verificata")
    return u


async def admin_user(u=Depends(current_user)):
    if u["role"] != "admin":
        raise HTTPException(403, "Solo amministratori")
    return u


def can(u, perm):
    return u.get("role") == "admin" and (u.get("is_super") or perm in (u.get("perms") or []))


def need(perm):
    async def dep(u=Depends(admin_user)):
        if not can(u, perm):
            raise HTTPException(403, "Permesso negato")
        return u
    return dep


async def super_user(u=Depends(admin_user)):
    if not u.get("is_super"):
        raise HTTPException(403, "Solo l'amministratore principale")
    return u


# ---------- settings ----------
DEF_CONTRATTO = """CONTRATTO DI AFFILIAZIONE (testo di esempio)

1. Oggetto: la Rete fornisce all'Affiliato la realizzazione del sito della propria agenzia di viaggi, il dominio e i servizi di supporto.
2. Corrispettivo: l'Affiliato versa l'importo indicato nel portale tramite bonifico.
3. Durata: il servizio ha durata annuale e si rinnova con il pagamento del dominio.
4. Obblighi: l'Affiliato fornisce dati veritieri e i documenti richiesti.

Modifica questo testo da Impostazioni > Contratto e privacy."""
DEF_PRIVACY = """INFORMATIVA PRIVACY (testo di esempio)

I dati personali sono trattati per gestire il rapporto di affiliazione, la fatturazione e l'assistenza, nel rispetto del Regolamento UE 2016/679 (GDPR).
L'interessato può esercitare i diritti di accesso, rettifica e cancellazione scrivendo all'amministratore.

Modifica questo testo da Impostazioni > Contratto e privacy."""


def def_settings():
    return {"_id": "main", "giorni": 15, "adminEmail": os.environ.get("ADMIN_EMAIL", ""),
            "pag": {"intestatario": "", "iban": "", "banca": "", "bic": "", "importo": "990", "iva": "22", "rinnovo": "120",
                    "causale": "Attivazione sito {agenzia} - {url}", "scadenza": "Entro 7 giorni dalla scelta dell'URL", "note": ""},
            "legali": {"versione": 1, "contratto": DEF_CONTRATTO, "privacy": DEF_PRIVACY, "at": nowiso()}}


async def get_settings():
    s = await db.settings.find_one({"_id": "main"})
    if not s:
        s = def_settings()
        await db.settings.insert_one(s)
    s.pop("_id", None)
    return s


async def next_seq(name):
    r = await db.counters.find_one_and_update({"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
    return r["seq"]


# ---------- notifications ----------
async def notify(to, testo, view=None, ref=None):
    await db.notifications.insert_one({"id": uid(), "to": to, "testo": testo, "view": view, "ref": ref, "letto": False, "at": nowiso()})


async def notify_admins(testo, view=None, ref=None):
    await notify("admin", testo, view, ref)


# ---------- email: Aruba SMTP first, Brevo fallback ----------
PUBLIC = {"base": ""}


def html_body(body):
    import html as h
    logo = f"<div style='padding:6px 0 14px'><img src='{PUBLIC['base']}/logo-alpimo.png' alt='Alpimo' width='180' style='display:block;width:180px;height:auto'></div>" if PUBLIC["base"] else ""
    return "<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.5;color:#14263b'>" + logo + h.escape(body).replace("\n", "<br>") + "</div>"


async def _aruba(to, subject, body):
    user, pw = os.environ.get("ARUBA_SMTP_USER"), os.environ.get("ARUBA_SMTP_PASSWORD")
    if not (user and pw):
        raise RuntimeError("Aruba non configurato")
    port = int(os.environ.get("ARUBA_SMTP_PORT", "465"))
    m = EmailMessage()
    m["From"] = f"{os.environ.get('MAIL_FROM_NAME', '')} <{user}>"
    m["To"], m["Subject"] = to, subject
    m.set_content(body)
    m.add_alternative(html_body(body), subtype="html")
    await aiosmtplib.send(m, hostname=os.environ.get("ARUBA_SMTP_HOST", "smtps.aruba.it"), port=port, username=user, password=pw,
                          use_tls=port == 465, start_tls=port != 465, timeout=20)


async def _brevo(to, subject, body):
    key = os.environ.get("BREVO_API_KEY")
    sender = os.environ.get("BREVO_SENDER_EMAIL") or os.environ.get("ARUBA_SMTP_USER")
    if not (key and sender):
        raise RuntimeError("Brevo non configurato")
    payload = {"sender": {"email": sender, "name": os.environ.get("MAIL_FROM_NAME", "")}, "to": [{"email": to}],
               "subject": subject, "textContent": body, "htmlContent": html_body(body)}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post("https://api.brevo.com/v3/smtp/email", json=payload, headers={"api-key": key, "accept": "application/json"})
        r.raise_for_status()


async def _deliver(log_id, to, subject, body):
    errors = []
    for name, fn in (("aruba", _aruba), ("brevo", _brevo)):
        try:
            await fn(to, subject, body)
            await db.email_log.update_one({"id": log_id}, {"$set": {"status": "inviata", "provider": name, "errors": errors}})
            return
        except Exception as e:
            errors.append(f"{name}: {str(e)[:160]}")
    st = "non_configurato" if all("non configurato" in e for e in errors) else "errore"
    await db.email_log.update_one({"id": log_id}, {"$set": {"status": st, "errors": errors}})


async def send_mail(to, subject, body, ref=None):
    if not to:
        return
    lid = uid()
    await db.email_log.insert_one({"id": lid, "to": to, "subject": subject, "body": body + "\n\n— Rete Agenzie Alpimo", "ref": ref, "at": nowiso(), "status": "in_invio"})
    asyncio.create_task(_deliver(lid, to, subject, body + "\n\n— Rete Agenzie Alpimo"))


async def admin_email():
    return (await get_settings()).get("adminEmail") or os.environ.get("ADMIN_EMAIL")


def email_status():
    return {"aruba": bool(os.environ.get("ARUBA_SMTP_USER") and os.environ.get("ARUBA_SMTP_PASSWORD")),
            "brevo": bool(os.environ.get("BREVO_API_KEY"))}


# ---------- object storage ----------
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_skey = None


def init_storage(force=False):
    global _skey
    if _skey and not force:
        return _skey
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    r.raise_for_status()
    _skey = r.json()["storage_key"]
    return _skey


def put_object(path, data, ctype):
    for attempt in (0, 1):
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(attempt == 1), "Content-Type": ctype}, data=data, timeout=300)
        if r.status_code == 404 and attempt == 0:
            continue
        r.raise_for_status()
        return r.json()


def get_object(path):
    for attempt in (0, 1):
        r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(attempt == 1)}, timeout=120)
        if r.status_code == 404 and attempt == 0:
            continue
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "application/octet-stream")


async def file_info(fid):
    if not fid:
        return None
    return await db.files.find_one({"id": fid, "is_deleted": False}, {"_id": 0, "id": 1, "name": 1, "type": 1, "size": 1})


def aff_name(a):
    if not a:
        return ""
    if a.get("nomeAgenzia"):
        return a["nomeAgenzia"]
    if a.get("tipo") == "azienda" and a.get("azienda"):
        return a["azienda"]
    p = (a.get("persone") or [{}])[0]
    return (f"{p.get('nome', '')} {p.get('cognome', '')}").strip() or a.get("email", "")


def url_def(a):
    i = a.get("urlDefinitivo")
    if i is None:
        return ""
    return (a.get("urls") or [{}] * 3)[i].get("value", "")


def itd(iso):
    return date.fromisoformat(iso[:10]).strftime("%d/%m/%Y") if iso else ""


def scope_all(u):
    return bool(u.get("is_super") or u.get("tutteAziende"))


def aff_q(u):
    return {} if scope_all(u) else {"aziendaId": {"$in": u.get("aziende") or []}}


async def scope_ids(u):
    if scope_all(u):
        return None
    return {a["id"] for a in await db.affiliates.find(aff_q(u), {"_id": 0, "id": 1}).to_list(10000)}


async def pag_for(a):
    s = await get_settings()
    if a and a.get("aziendaId"):
        c = await db.companies.find_one({"id": a["aziendaId"]}, {"_id": 0})
        if c and (c.get("pag") or {}).get("iban"):
            return {**s["pag"], **{k: v for k, v in c["pag"].items() if v}}
    return s["pag"]
