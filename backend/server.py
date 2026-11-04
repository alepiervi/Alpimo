from dotenv import load_dotenv
load_dotenv()

import os  # noqa: E402
import json  # noqa: E402
import asyncio  # noqa: E402
import logging  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from core import db, hash_pw, uid, nowiso, get_settings, init_storage, PERMS  # noqa: E402
import routes_auth  # noqa: E402
import routes_common  # noqa: E402
import routes_aff  # noqa: E402
import routes_admin  # noqa: E402
import routes_team  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("alpimo")
GUIDE_SEED = os.path.join(os.path.dirname(__file__), "seed_guides.json")
app = FastAPI(title="Portale Affiliati Alpimo")
for r in (routes_auth.router, routes_common.router, routes_aff.router, routes_admin.router, routes_team.router):
    app.include_router(r)
app.add_middleware(CORSMiddleware, allow_origins=os.environ["CORS_ORIGINS"].split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/")
async def root():
    return {"ok": True, "app": "Portale Affiliati"}


async def seed_demo():
    t = nowiso()
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


async def startup_tasks():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.affiliates.create_index("id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.notifications.create_index([("to", 1), ("at", -1)])
    await db.email_log.create_index("at")
    s = await get_settings()
    em, pw = os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"]
    if not await db.users.find_one({"role": "admin"}):
        await db.users.insert_one({"id": uid(), "email": em, "password_hash": hash_pw(pw), "role": "admin", "is_super": True, "is_master": True, "tutteAziende": True, "nome": "Amministratore",
                                   "perms": PERMS, "verified": True, "active": True, "created_at": nowiso()})
    try:
        init_storage()
    except Exception as e:
        log.error(f"Storage init failed: {e}")
    if not s.get("seeded"):
        await db.settings.update_one({"_id": "main"}, {"$set": {"seeded": True}})
        await seed_demo()
    if not await db.reparti.count_documents({}):
        await db.reparti.insert_many([{"id": uid(), "nome": n, "ordine": i} for i, n in enumerate(["Amministrazione", "Travel", "IT · Sito internet", "IT · Email"])])
    if not await db.guides.count_documents({}) and os.path.exists(GUIDE_SEED):
        data = json.load(open(GUIDE_SEED))
        for f in data["files"]:
            if not await db.files.find_one({"id": f["id"]}):
                await db.files.insert_one(f)
        if data["guides"]:
            await db.guides.insert_many(data["guides"])


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


