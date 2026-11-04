# Iteration 4: ticket departments (reparti), reusable team roles (ruoli), reparto-scoped ticket visibility/notifications/emails.
# Needs env MASTER_EMAIL / MASTER_PW (never stored in file). Tests run in order and share state S; test_99 cleans up.
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"
ME, MP = os.environ.get("MASTER_EMAIL"), os.environ.get("MASTER_PW")
TAG = uuid.uuid4().hex[:6]
S = {"tickets": {}}
ORIG = {"Amministrazione", "Travel", "IT · Sito internet", "IT · Email"}


def sess(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s, r.json()


@pytest.fixture(scope="module")
def master():
    if not (ME and MP):
        pytest.skip("no master creds")
    return sess(ME, MP)[0]


# --- reparti seed
def test_01_reparti_seeded(master):
    r = master.get(f"{BASE}/reparti")
    assert r.status_code == 200
    L = r.json()
    names = {x["nome"] for x in L}
    assert ORIG <= names, names
    S["rep"] = {x["nome"]: x["id"] for x in L}
    assert all("_id" not in x for x in L)


# --- reparto CRUD
def test_02_reparto_create_rename(master):
    r = master.post(f"{BASE}/admin/reparti", json={"nome": f"TEST_Rep_{TAG}", "ordine": 9})
    assert r.status_code == 200, r.text
    S["newrep"] = r.json()["id"]
    assert master.post(f"{BASE}/admin/reparti", json={"nome": "  "}).status_code == 400
    r = master.put(f"{BASE}/admin/reparti/{S['newrep']}", json={"nome": f"TEST_Rep2_{TAG}", "ordine": 9})
    assert r.status_code == 200
    names = {x["id"]: x["nome"] for x in master.get(f"{BASE}/reparti").json()}
    assert names[S["newrep"]] == f"TEST_Rep2_{TAG}"
    assert master.put(f"{BASE}/admin/reparti/nope", json={"nome": "x"}).status_code == 404


# --- ruoli CRUD
def test_03_ruolo_create_edit(master):
    it = S["rep"]["IT · Sito internet"]
    r = master.post(f"{BASE}/admin/ruoli", json={"nome": f"TEST_RuoloIT_{TAG}", "perms": ["ticket", "bogus"], "reparti": [it, "bogus"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["perms"] == ["ticket"] and d["reparti"] == [it]
    S["ruolo"] = d["id"]
    r = master.put(f"{BASE}/admin/ruoli/{S['ruolo']}", json={"nome": f"TEST_RuoloIT2_{TAG}", "perms": ["ticket"], "reparti": [it]})
    assert r.status_code == 200
    L = master.get(f"{BASE}/admin/ruoli").json()
    me = [x for x in L if x["id"] == S["ruolo"]][0]
    assert me["nome"] == f"TEST_RuoloIT2_{TAG}" and me["utenti"] == 0


# --- team users with role and custom
def test_04_team_with_role(master):
    S["it_email"], S["it_pw"] = f"test_it_{TAG}@test.local", "TestIT-2026!"
    r = master.post(f"{BASE}/admin/team", json={"nome": f"TEST IT {TAG}", "email": S["it_email"], "password": S["it_pw"], "ruoloId": S["ruolo"], "tutteAziende": True})
    assert r.status_code == 200, r.text
    T = master.get(f"{BASE}/admin/team").json()
    u = [x for x in T if x["email"] == S["it_email"]][0]
    S["it_id"] = u["id"]
    assert u["ruoloNome"] == f"TEST_RuoloIT2_{TAG}"
    assert u["perms"] == ["ticket"] and u["reparti"] == [S["rep"]["IT · Sito internet"]]
    assert "password_hash" not in u
    assert master.post(f"{BASE}/admin/team", json={"nome": "x", "email": f"bad_{TAG}@test.local", "password": "Abcdefgh1", "ruoloId": "nope"}).status_code == 400


def test_05_team_custom(master):
    S["cu_email"] = f"test_cu_{TAG}@test.local"
    tr = S["rep"]["Travel"]
    r = master.post(f"{BASE}/admin/team", json={"nome": f"TEST CU {TAG}", "email": S["cu_email"], "password": "TestCU-2026!", "perms": ["ticket", "email"], "reparti": [tr, "bogus"], "tutteAziende": True})
    assert r.status_code == 200, r.text
    u = [x for x in master.get(f"{BASE}/admin/team").json() if x["email"] == S["cu_email"]][0]
    S["cu_id"] = u["id"]
    assert set(u["perms"]) == {"ticket", "email"} and u["reparti"] == [tr] and not u.get("ruoloNome")


def test_06_login_resolves_role():
    s, u = sess(S["it_email"], S["it_pw"])
    assert u["perms"] == ["ticket"] and u["ruoloNome"].startswith("TEST_RuoloIT2")
    assert u["reparti"] == [S["rep"]["IT · Sito internet"]]
    assert s.get(f"{BASE}/admin/affiliates").status_code == 403
    S["it_s"] = s


# --- affiliate tickets with reparto
def test_07_affiliate_tickets():
    s = requests.Session()
    S["aff_email"] = f"test_aff_{TAG}@test.local"
    r = s.post(f"{BASE}/auth/register", json={"email": S["aff_email"], "password": "TestAff-2026!", "contratto": True, "privacy": True})
    assert r.status_code == 200, r.text
    S["aff_id"] = r.json()["id"]
    S["aff_s"] = s
    r = s.post(f"{BASE}/tickets", json={"oggetto": "TEST no rep", "testo": "x"})
    assert r.status_code == 400 and "Scegli il reparto" in r.text
    assert s.post(f"{BASE}/tickets", json={"oggetto": "TEST bad rep", "testo": "x", "reparto": "nope"}).status_code == 400
    for key, rid in (("it", S["rep"]["IT · Sito internet"]), ("amm", S["rep"]["Amministrazione"]), ("new", S["newrep"])):
        r = s.post(f"{BASE}/tickets", json={"oggetto": f"TEST {key}", "testo": "descr", "reparto": rid, "priorita": "media"})
        assert r.status_code == 200, r.text
        assert r.json()["reparto"] == rid
        S["tickets"][key] = r.json()["id"]
    L = s.get(f"{BASE}/tickets").json()
    assert len(L) == 3


# --- visibility per reparto
def test_08_it_user_visibility(master):
    L = S["it_s"].get(f"{BASE}/tickets").json()
    ids = {t["id"] for t in L}
    assert S["tickets"]["it"] in ids
    assert S["tickets"]["amm"] not in ids and S["tickets"]["new"] not in ids
    assert all(t["reparto"] == S["rep"]["IT · Sito internet"] for t in L)
    assert S["it_s"].get(f"{BASE}/tickets/{S['tickets']['it']}").status_code == 200
    assert S["it_s"].get(f"{BASE}/tickets/{S['tickets']['amm']}").status_code == 404
    assert S["it_s"].post(f"{BASE}/tickets/{S['tickets']['amm']}/msg", json={"testo": "x"}).status_code == 404
    mids = {t["id"] for t in master.get(f"{BASE}/tickets").json()}
    assert set(S["tickets"].values()) <= mids


def test_09_it_user_notifications():
    N = S["it_s"].get(f"{BASE}/notifications").json()
    refs = {n.get("ref") for n in N if n.get("view") == "ticket"}
    assert S["tickets"]["amm"] not in refs and S["tickets"]["new"] not in refs
    assert S["tickets"]["it"] in refs
    assert all(n.get("view") in (None, "ticket") for n in N)


def test_10_emails_to_reparto(master):
    time.sleep(2)
    items = master.get(f"{BASE}/admin/emails", params={"ref": S["tickets"]["it"]}).json()["items"]
    tos = {e["to"] for e in items}
    assert S["it_email"] in tos, tos
    assert S["aff_email"] in tos
    items2 = master.get(f"{BASE}/admin/emails", params={"ref": S["tickets"]["amm"]}).json()["items"]
    assert S["it_email"] not in {e["to"] for e in items2}
    assert all(e["status"] in ("non_configurato", "inviata", "errore", "in_invio") for e in items)


# --- delete reparto blocked, move ticket
def test_11_reparto_delete_blocked_and_move(master):
    r = master.delete(f"{BASE}/admin/reparti/{S['newrep']}")
    assert r.status_code == 400 and "ticket" in r.text.lower()
    r = master.post(f"{BASE}/tickets/{S['tickets']['new']}/reparto", json={"reparto": S["rep"]["IT · Sito internet"]})
    assert r.status_code == 200
    assert master.get(f"{BASE}/tickets/{S['tickets']['new']}").json()["reparto"] == S["rep"]["IT · Sito internet"]
    assert master.post(f"{BASE}/tickets/{S['tickets']['new']}/reparto", json={"reparto": "nope"}).status_code == 400
    # now IT user sees moved ticket and was emailed
    assert S["it_s"].get(f"{BASE}/tickets/{S['tickets']['new']}").status_code == 200
    r = master.delete(f"{BASE}/admin/reparti/{S['newrep']}")
    assert r.status_code == 200
    assert S["newrep"] not in {x["id"] for x in master.get(f"{BASE}/reparti").json()}
    S["newrep_deleted"] = True


def test_12_it_user_moves_out():
    r = S["it_s"].post(f"{BASE}/tickets/{S['tickets']['new']}/reparto", json={"reparto": S["rep"]["Travel"]})
    assert r.status_code == 200
    assert S["it_s"].get(f"{BASE}/tickets/{S['tickets']['new']}").status_code == 404
    # affiliate cannot move
    assert S["aff_s"].post(f"{BASE}/tickets/{S['tickets']['it']}/reparto", json={"reparto": S["rep"]["Travel"]}).status_code == 403


def test_13_custom_user_travel_only():
    s, u = sess(S["cu_email"], "TestCU-2026!")
    ids = {t["id"] for t in s.get(f"{BASE}/tickets").json()}
    assert S["tickets"]["new"] in ids and S["tickets"]["it"] not in ids and S["tickets"]["amm"] not in ids


def test_14_role_delete_blocked(master):
    r = master.delete(f"{BASE}/admin/ruoli/{S['ruolo']}")
    assert r.status_code == 400
    assert any(x["id"] == S["ruolo"] for x in master.get(f"{BASE}/admin/ruoli").json())


def test_15_non_super_forbidden():
    assert S["it_s"].get(f"{BASE}/admin/ruoli").status_code == 403
    assert S["it_s"].post(f"{BASE}/admin/reparti", json={"nome": "x"}).status_code == 403


def test_99_cleanup(master):
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    if S.get("aff_id"):
        assert master.delete(f"{BASE}/admin/affiliates/{S['aff_id']}").status_code == 200
    if not S.get("newrep_deleted") and S.get("newrep"):
        master.delete(f"{BASE}/admin/reparti/{S['newrep']}")

    async def go():
        from dotenv import dotenv_values
        env = dotenv_values("/app/backend/.env")
        db = AsyncIOMotorClient(env["MONGO_URL"])[env["DB_NAME"]]
        ids = [x for x in (S.get("it_id"), S.get("cu_id")) if x]
        await db.users.delete_many({"id": {"$in": ids}})
        await db.email_log.delete_many({"to": {"$in": [S.get("it_email"), S.get("cu_email")]}})
        await db.login_attempts.delete_many({"identifier": {"$in": [f"login:{S.get('it_email')}", f"login:{S.get('cu_email')}"]}})
    asyncio.run(go())
    if S.get("ruolo"):
        assert master.delete(f"{BASE}/admin/ruoli/{S['ruolo']}").status_code == 200
    names = {x["nome"] for x in master.get(f"{BASE}/reparti").json()}
    assert ORIG <= names
