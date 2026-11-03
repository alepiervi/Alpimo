from dotenv import load_dotenv
load_dotenv()

import os  # noqa: E402
import asyncio  # noqa: E402
import logging  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from core import db, hash_pw, uid, nowiso, add_biz, get_settings, init_storage, put_object, enc, PERMS  # noqa: E402
import routes_auth  # noqa: E402
import routes_common  # noqa: E402
import routes_aff  # noqa: E402
import routes_admin  # noqa: E402
from datetime import date, timedelta  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("alpimo")
app = FastAPI(title="Portale Affiliati Alpimo")
for r in (routes_auth.router, routes_common.router, routes_aff.router, routes_admin.router):
    app.include_router(r)
app.add_middleware(CORSMiddleware, allow_origins=os.environ["CORS_ORIGINS"].split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/")
async def root():
    return {"ok": True, "app": "Portale Affiliati"}


def logo_svg(name, style):
    pal = [["#1b75b0", "#f07c1b"], ["#123c5e", "#f5a03a"], ["#e06a10", "#1b75b0"]][style % 3]
    ini = "".join(w[0] for w in name.split() if len(w) > 2)[:2].upper() or "AV"
    marks = [f'<circle cx="60" cy="60" r="46" fill="{pal[0]}"/><path d="M22 74 Q60 44 98 74" stroke="{pal[1]}" stroke-width="7" fill="none" stroke-linecap="round"/><circle cx="60" cy="44" r="10" fill="{pal[1]}"/>',
             f'<rect x="16" y="16" width="88" height="88" rx="22" fill="{pal[0]}"/><text x="60" y="76" text-anchor="middle" font-family="Georgia,serif" font-size="44" font-weight="700" fill="{pal[1]}">{ini}</text>',
             f'<path d="M60 14 L104 96 L16 96 Z" fill="{pal[0]}"/><path d="M38 96 Q60 62 82 96" fill="{pal[1]}"/><circle cx="86" cy="34" r="9" fill="{pal[1]}"/>']
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 120"><rect width="340" height="120" fill="#fff"/>{marks[style]}'
            f'<text x="122" y="62" font-family="Georgia,serif" font-size="20" font-weight="700" fill="{pal[0]}">{name}</text>'
            f'<text x="123" y="84" font-family="Arial,sans-serif" font-size="11" letter-spacing="3" fill="{pal[1]}">AGENZIA VIAGGI</text></svg>').encode()


async def store(owner, name, data, ctype):
    path = f"{os.environ.get('APP_NAME', 'alpimo')}/seed/{owner}/{uid()}-{name}"
    try:
        res = put_object(path, data, ctype)
    except Exception as e:
        log.warning(f"seed storage failed: {e}")
        return None
    fid = uid()
    await db.files.insert_one({"id": fid, "path": res["path"], "name": name, "type": ctype, "size": len(data), "owner": owner, "uploader": "seed", "is_deleted": False, "created_at": nowiso()})
    return fid


async def seed_demo():
    from routes_auth import new_aff
    s = await get_settings()
    v, t = s["legali"]["versione"], nowiso()
    fatt = {"intestatario": "", "cf": "", "piva": "", "sdi": "", "pec": "", "indirizzo": "Via Roma 1", "cap": "00100", "citta": "Roma", "provincia": "RM"}

    async def add(email, **o):
        u = {"id": uid(), "email": email, "password_hash": hash_pw("demo1234"), "role": "affiliate", "is_super": False, "nome": "", "perms": [],
             "verified": True, "active": True, "created_at": t}
        await db.users.insert_one(u)
        a = new_aff(u["id"], email, o.pop("tipo", "persona"))
        a["consensi"] = {"contratto": {"versione": v, "at": t}, "privacy": {"versione": v, "at": t}, "marketing": {"value": False, "at": t}}
        a.update(o)
        await db.affiliates.insert_one(a)
        return a

    await add("sole@demo.it", tipo="azienda", azienda="Viaggi del Sole srl", piva="01234567890", referente="Anna Galli", nomeAgenzia="Viaggi del Sole",
              telefono="333 1112233", citta="Bari", stato="in_attesa", submittedAt=t,
              urls=[{"value": x, "stato": "da_verificare"} for x in ("viaggidelsole.it", "viaggidelsole.com", "viaggidelsoletour.it")],
              fatturazione={**fatt, "intestatario": "Viaggi del Sole srl", "piva": "01234567890", "sdi": "M5UXCR1"})
    m = await add("mario@demo.it", persone=[{"nome": "Mario", "cognome": "Rossi"}, {"nome": "Laura", "cognome": "Bianchi"}], nomeAgenzia="Rotte Mediterranee",
                  telefono="347 5556677", citta="Napoli", stato="accettata", submittedAt=t, decidedAt=t,
                  urls=[{"value": "rottemediterranee.it", "stato": "disponibile"}, {"value": "rottemediterranee.com", "stato": "non_disponibile"}, {"value": "rotte-mediterranee.it", "stato": "disponibile"}],
                  fatturazione={**fatt, "intestatario": "Mario Rossi", "cf": "RSSMRA80A01F839X"})
    loghi = [await store(m["id"], f"logo{i + 1}.svg", logo_svg("Rotte Mediterranee", i), "image/svg+xml") for i in range(3)]
    await db.affiliates.update_one({"id": m["id"]}, {"$set": {"loghi": loghi}})
    start = (date.today() - timedelta(days=360)).isoformat()
    b = await add("blu@demo.it", tipo="azienda", azienda="Blu Orizzonti snc", piva="04561237890", referente="Sara Conti", nomeAgenzia="Blu Orizzonti",
                  telefono="335 4443322", citta="Genova", stato="accettata", submittedAt=t, decidedAt=t, logoScelto=0, urlDefinitivo=0,
                  urls=[{"value": "bluorizzonti.it", "stato": "disponibile"}, {"value": "", "stato": "da_verificare"}, {"value": "", "stato": "da_verificare"}],
                  pagamento="confermato", pagamentoAt=t, consegnato=True, consegnatoAt=t,
                  consegna={"inizio": start, "giorni": 15, "dataPrevista": add_biz(start, 15), "fase": 3},
                  cred=enc({"url": "https://bluorizzonti.it/admin", "utente": "bluorizzonti", "password": "Bo!2026-adm", "passwordSito": "anteprima-blu"}),
                  superAdmin=enc({"url": "https://bluorizzonti.it/superadmin", "utente": "superadmin", "password": "SA#blu-77"}),
                  dominio={"scadenza": (date.today() + timedelta(days=6)).isoformat(), "storico": [], "inviati": [30, 15]},
                  fatturazione={**fatt, "intestatario": "Blu Orizzonti snc", "piva": "04561237890", "pec": "blu@pec.it"})
    bl = [await store(b["id"], f"logo{i + 1}.svg", logo_svg("Blu Orizzonti", i), "image/svg+xml") for i in range(3)]
    await db.affiliates.update_one({"id": b["id"]}, {"$set": {"loghi": bl}})
    await db.payments.insert_one({"id": uid(), "affId": b["id"], "kind": "attivazione", "descrizione": "Attivazione sito bluorizzonti.it", "imponibile": 990.0,
                                  "iva": 22.0, "totale": 1207.8, "stato": "pagato", "ricevuta": None, "nota": "", "at": t, "invoice": None})
    await db.courses.insert_many([
        {"id": uid(), "titolo": "Primi passi con il tuo sito", "categoria": "Sito", "livello": "Base", "descrizione": "Come accedere al pannello, aggiornare pagine, foto e offerte del tuo sito agenzia.",
         "premium": False, "prezzo": 0, "pubblicato": True, "copertina": None, "annunciato": True, "createdAt": t,
         "lezioni": [{"id": uid(), "titolo": "Benvenuto nell'Academy", "durata": "4 min", "descrizione": "Panoramica del percorso.", "file": None, "url": "https://www.youtube.com/watch?v=ysz5S6PUM-U"},
                     {"id": uid(), "titolo": "Il pannello di amministrazione", "durata": "8 min", "descrizione": "Dove trovare le funzioni principali.", "file": None, "url": "https://vimeo.com/76979871"}]},
        {"id": uid(), "titolo": "Social media per agenzie di viaggio", "categoria": "Marketing", "livello": "Intermedio", "descrizione": "Strategie pratiche per promuovere le tue offerte su Instagram e Facebook.",
         "premium": True, "prezzo": 149, "pubblicato": True, "copertina": None, "annunciato": True, "createdAt": t,
         "lezioni": [{"id": uid(), "titolo": "Anteprima: perché i social", "durata": "5 min", "descrizione": "Lezione gratuita.", "file": None, "url": "https://www.youtube.com/watch?v=ysz5S6PUM-U"},
                     {"id": uid(), "titolo": "Calendario editoriale", "durata": "12 min", "descrizione": "", "file": None, "url": "https://www.youtube.com/watch?v=ysz5S6PUM-U"},
                     {"id": uid(), "titolo": "Inserzioni a pagamento", "durata": "15 min", "descrizione": "", "file": None, "url": "https://www.youtube.com/watch?v=ysz5S6PUM-U"}]}])
    await db.news.insert_one({"id": uid(), "titolo": "Benvenuti nel nuovo portale affiliati", "categoria": "Novità", "testo": "Da oggi trovate qui documenti, pagamenti, corsi e assistenza in un unico posto.\nBuon viaggio!",
                              "immagine": None, "inEvidenza": True, "lettiDa": [], "at": t})
    await db.settings.update_one({"_id": "main"}, {"$set": {"pag.intestatario": "Rete Agenzie srl (esempio)", "pag.iban": "IT60 X054 2811 1010 0000 0123 456",
                                                          "pag.banca": "Banca di esempio", "pag.note": "Dati di esempio: modificali in Impostazioni > Dati pagamento."}})


async def startup_tasks():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.affiliates.create_index("id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.notifications.create_index([("to", 1), ("at", -1)])
    await db.email_log.create_index("at")
    s = await get_settings()
    em, pw = os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"]
    if not await db.users.find_one({"email": em}):
        await db.users.insert_one({"id": uid(), "email": em, "password_hash": hash_pw(pw), "role": "admin", "is_super": True, "nome": "Amministratore",
                                   "perms": PERMS, "verified": True, "active": True, "created_at": nowiso()})
    try:
        init_storage()
    except Exception as e:
        log.error(f"Storage init failed: {e}")
    if not s.get("seeded"):
        await db.settings.update_one({"_id": "main"}, {"$set": {"seeded": True}})
        await seed_demo()


async def scheduler():
    while True:
        try:
            await routes_admin.domain_job()
        except Exception as e:
            log.error(f"domain job: {e}")
        await asyncio.sleep(6 * 3600)


@app.on_event("startup")
async def startup():
    await startup_tasks()
    asyncio.create_task(scheduler())


@app.on_event("shutdown")
async def shutdown():
    from core import client
    client.close()


