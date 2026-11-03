# Iteration 2 retest: fixes from iteration_1 (lockout by email, input validation, notifications perms, materials, renew description)
import os
import re
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import dotenv_values

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = ("admin@alpimo.it", "Alpimo-Admin-2026")
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
env = dotenv_values("/app/backend/.env")
DB = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def blu():
    return login("blu@demo.it", "demo1234")


@pytest.fixture(scope="module")
def new_aff():
    em = f"test_it2_{uuid.uuid4().hex[:8]}@test.it"
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": em, "password": "Password123", "tipo": "persona", "contratto": True, "privacy": True})
    assert r.status_code == 200, r.text
    return r.json()["id"], s


# Auth lockout keyed by email
def test_lockout_by_email():
    em = f"test_lock_{uuid.uuid4().hex[:6]}@nowhere.it"
    codes = [requests.post(f"{API}/auth/login", json={"email": em, "password": "x"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429, codes
    # case-insensitive email shares counter
    assert requests.post(f"{API}/auth/login", json={"email": em.upper(), "password": "x"}).status_code == 429


def test_admin_login_still_ok():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
    assert r.status_code == 200 and r.json()["role"] == "admin"
    sc = r.headers.get("set-cookie", "").lower()
    assert "httponly" in sc


# Domain invalid date
def test_domain_invalid_date(admin, new_aff):
    aid, _ = new_aff
    r = admin.post(f"{API}/admin/affiliates/{aid}/domain", json={"scadenza": "not-a-date"})
    assert r.status_code == 400 and "Data" in r.json()["detail"]


# Renew description dd/mm/yyyy
def test_renew_description_format(admin, new_aff):
    aid, _ = new_aff
    assert admin.post(f"{API}/admin/affiliates/{aid}/domain", json={"scadenza": "2026-03-01"}).status_code == 200
    r = admin.post(f"{API}/admin/affiliates/{aid}/renew")
    assert r.status_code == 200 and r.json()["scadenza"] == "2027-03-01"
    p = DB.payments.find_one({"affId": aid, "kind": "rinnovo"})
    assert p and p["descrizione"].endswith("fino al 01/03/2027"), p and p["descrizione"]


# Payment bounds
@pytest.mark.parametrize("g", [0, -5])
def test_payment_confirm_giorni_bounds(admin, new_aff, g):
    aid, _ = new_aff
    r = admin.post(f"{API}/admin/affiliates/{aid}/payment", json={"confirm": True, "giorni": g})
    assert r.status_code == 422, r.status_code


@pytest.mark.parametrize("t", [0, -10])
def test_manual_payment_totale_bounds(admin, new_aff, t):
    aid, _ = new_aff
    r = admin.post(f"{API}/admin/payments", json={"affId": aid, "descrizione": "TEST bad", "totale": t})
    assert r.status_code == 422, r.status_code


# Email search special chars
@pytest.mark.parametrize("q", ["(", "[", "*", "+?"])
def test_emails_special_chars(admin, q):
    r = admin.get(f"{API}/admin/emails", params={"q": q})
    assert r.status_code == 200 and "items" in r.json()


# Courses: unknown done -> 404, premium unlocked bool
def test_course_done_unknown(blu):
    r = blu.post(f"{API}/aff/courses/nonexistent-xyz/done", json={"lid": "x"})
    assert r.status_code == 404, r.status_code


def test_courses_unlocked_is_bool():
    r = login("mario@demo.it", "demo1234").get(f"{API}/aff/courses")
    assert r.status_code == 200
    cs = r.json()
    assert all(isinstance(c["unlocked"], bool) for c in cs), [(c.get("titolo"), c["unlocked"]) for c in cs]
    prem = [c for c in cs if c.get("premium")]
    print("premium:", [(c["titolo"], c["unlocked"]) for c in prem])
    assert any(c["unlocked"] is False for c in prem) or not prem


# Materials download on deleted material
def test_material_deleted_download_noinc(admin, blu):
    f = admin.post(f"{API}/files", files={"file": ("b.pdf", PDF, "application/pdf")}).json()["id"]
    mid = admin.post(f"{API}/admin/materials", json={"titolo": "TEST mat it2", "categoria": "Brochure", "file": f}).json()["id"]
    assert admin.delete(f"{API}/admin/materials/{mid}").status_code == 200
    blu.post(f"{API}/aff/materials/{mid}/download")
    m = DB.materials.find_one({"id": mid})
    assert (m or {}).get("downloads", 0) == 0
    blu.post(f"{API}/aff/materials/nonexistent-{uuid.uuid4().hex}/download")
    assert DB.materials.count_documents({"id": {"$regex": "^nonexistent"}}) == 0


# Collaborator notification filtering
def test_collaborator_ticket_only_notifications(admin):
    em = f"test_collab_{uuid.uuid4().hex[:6]}@test.it"
    assert admin.post(f"{API}/admin/team", json={"nome": "TEST Collab", "email": em, "password": "Collab1234", "perms": ["ticket"]}).status_code == 200
    # ensure there are non-ticket admin notifications
    DB.notifications.insert_many([
        {"id": f"test-n-{uuid.uuid4().hex}", "to": "admin", "testo": "TEST pay", "view": "affiliato", "ref": None, "letto": False, "at": "2099-01-01T00:00:00"},
        {"id": f"test-n-{uuid.uuid4().hex}", "to": "admin", "testo": "TEST tick", "view": "ticket", "ref": None, "letto": False, "at": "2099-01-01T00:00:01"},
        {"id": f"test-n-{uuid.uuid4().hex}", "to": "admin", "testo": "TEST gen", "view": None, "ref": None, "letto": False, "at": "2099-01-01T00:00:02"},
    ])
    try:
        c = login(em, "Collab1234")
        ns = c.get(f"{API}/notifications").json()
        views = {n.get("view") for n in ns}
        print("collab views:", views)
        assert views <= {None, "ticket"}, views
        assert any(n["testo"] == "TEST tick" for n in ns) and any(n["testo"] == "TEST gen" for n in ns)
        assert not any(n["testo"] == "TEST pay" for n in ns)
        sup = admin.get(f"{API}/notifications").json()
        assert any(n["testo"] == "TEST pay" for n in sup)
        # read-all by collaborator must not mark the payment one as read
        c.post(f"{API}/notifications/read-all")
        assert DB.notifications.find_one({"testo": "TEST pay"})["letto"] is False
    finally:
        DB.notifications.delete_many({"testo": {"$in": ["TEST pay", "TEST tick", "TEST gen"]}})
        tid = next(x for x in admin.get(f"{API}/admin/team").json() if x["email"] == em)["id"]
        admin.put(f"{API}/admin/team/{tid}", json={"nome": "TEST Collab", "email": em, "perms": ["ticket"], "active": False})
