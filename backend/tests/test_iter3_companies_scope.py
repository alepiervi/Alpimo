# Iteration 3: companies (per-company bank data), scoped admins (aziende), full-access team users, master protection
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import dotenv_values

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
QA_ADMIN = ("qa-admin@test.local", "QaAdmin-2026")
AFF1 = ("qa-aff1@test.local", "QaAff-2026")
AFF2 = ("qa-aff2@test.local", "QaAff-2026")
SCOPED = ("qa-scoped@test.local", "QaScoped-2026")
FULL = ("qa-full@test.local", "QaFull-2026")
env = dotenv_values("/app/backend/.env")
DB = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
S = {}  # shared state across ordered tests


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    return login(*QA_ADMIN)


@pytest.fixture(scope="module", autouse=True)
def save_restore_settings():
    S["orig_pag"] = DB.settings.find_one({"_id": "main"})["pag"]
    yield
    # restore default payment to empty bank fields
    s = login(*QA_ADMIN)
    pag = dict(S["orig_pag"])
    for k in ("intestatario", "iban", "banca", "note"):
        pag[k] = ""
    s.put(f"{API}/admin/settings", json={"pag": pag})


# ---- Companies CRUD ----
def test_01_create_companies(admin):
    r = admin.post(f"{API}/admin/companies", json={"nome": "QA Azienda Uno", "pag": {"iban": "IT60X0542811101000000123456", "intestatario": "QA Uno srl", "importo": "500", "iva": "22"}})
    assert r.status_code == 200, r.text
    S["c1"] = r.json()["id"]
    r = admin.post(f"{API}/admin/companies", json={"nome": "QA Azienda Due", "pag": {}})
    assert r.status_code == 200
    S["c2"] = r.json()["id"]
    L = admin.get(f"{API}/admin/companies").json()
    c1 = next(c for c in L if c["id"] == S["c1"])
    assert c1["pag"]["iban"] == "IT60X0542811101000000123456" and c1["pag"]["intestatario"] == "QA Uno srl"


def test_02_company_validation_and_edit(admin):
    assert admin.post(f"{API}/admin/companies", json={"nome": " ", "pag": {}}).status_code == 400
    assert admin.post(f"{API}/admin/companies", json={"nome": "QA bad", "pag": {"iban": "XX"}}).status_code == 400
    r = admin.put(f"{API}/admin/companies/{S['c2']}", json={"nome": "QA Azienda Due", "pag": {"banca": "QA Banca"}})
    assert r.status_code == 200
    assert admin.put(f"{API}/admin/companies/nonexist", json={"nome": "QA x", "pag": {}}).status_code == 404


def test_03_default_payment(admin):
    pag = dict(S["orig_pag"], iban="IT02L1234512345123456789012", intestatario="QA Default")
    assert admin.put(f"{API}/admin/settings", json={"pag": pag}).status_code == 200


def test_04_register_affiliates():
    for key, (e, p) in (("a1", AFF1), ("a2", AFF2)):
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={"email": e, "password": p, "contratto": True, "privacy": True})
        assert r.status_code == 200, r.text
        assert r.json()["verified"] is True
        S[key] = r.json()["id"]


def test_05_assign_company(admin):
    r = admin.post(f"{API}/admin/affiliates/{S['a1']}/internal", json={"aziendaId": S["c1"], "registrar": "QA Reg"})
    assert r.status_code == 200
    assert admin.post(f"{API}/admin/affiliates/{S['a2']}/internal", json={"aziendaId": "nope"}).status_code == 400
    a = admin.get(f"{API}/admin/affiliates/{S['a1']}").json()
    assert a["aziendaId"] == S["c1"]
    assert admin.delete(f"{API}/admin/companies/{S['c1']}").status_code == 400


def test_06_aff_me_pag():
    m1 = login(*AFF1).get(f"{API}/aff/me").json()
    assert m1["pag"]["iban"] == "IT60X0542811101000000123456" and m1["pag"]["intestatario"] == "QA Uno srl" and m1["pag"]["importo"] == "500"
    assert "aziendaId" not in m1["aff"] and "registrar" not in m1["aff"]
    m2 = login(*AFF2).get(f"{API}/aff/me").json()
    assert m2["pag"]["iban"] == "IT02L1234512345123456789012" and m2["pag"]["intestatario"] == "QA Default"


def test_07_company_without_iban_fallback(admin):
    admin.post(f"{API}/admin/affiliates/{S['a2']}/internal", json={"aziendaId": S["c2"], "registrar": ""})
    m2 = login(*AFF2).get(f"{API}/aff/me").json()
    assert m2["pag"]["iban"] == "IT02L1234512345123456789012"
    admin.post(f"{API}/admin/affiliates/{S['a2']}/internal", json={"aziendaId": None, "registrar": ""})


def test_08_tickets_for_both():
    for k, cred in (("t1", AFF1), ("t2", AFF2)):
        r = login(*cred).post(f"{API}/tickets", json={"oggetto": f"QA ticket {k}", "testo": "QA"})
        assert r.status_code == 200, r.text
        S[k] = r.json().get("id")


# ---- Team ----
def test_09_create_team_users(admin):
    r = admin.post(f"{API}/admin/team", json={"nome": "QA Scoped", "email": SCOPED[0], "password": SCOPED[1],
                                              "perms": ["affiliati", "ticket", "report", "email", "impostazioni"], "aziende": [S["c1"]]})
    assert r.status_code == 200, r.text
    r = admin.post(f"{API}/admin/team", json={"nome": "QA Full", "email": FULL[0], "password": FULL[1], "full": True})
    assert r.status_code == 200, r.text
    T = admin.get(f"{API}/admin/team").json()
    sc = next(t for t in T if t["email"] == SCOPED[0])
    fu = next(t for t in T if t["email"] == FULL[0])
    assert sc["is_super"] is False and sc["aziende"] == [S["c1"]] and not sc["tutteAziende"]
    assert fu["is_super"] is True
    S["master"] = next((t["id"] for t in T if t.get("is_master")), None)
    assert S["master"], "no master flagged"


def test_10_team_email_no_password(admin):
    L = admin.get(f"{API}/admin/emails", params={"q": SCOPED[0]}).json()["items"]
    assert L
    for e in L + admin.get(f"{API}/admin/emails", params={"q": FULL[0]}).json()["items"]:
        assert SCOPED[1] not in e["body"] and FULL[1] not in e["body"]


def test_11_scoped_affiliates():
    s = login(*SCOPED)
    ids = [a["id"] for a in s.get(f"{API}/admin/affiliates").json()]
    assert ids == [S["a1"]]
    assert s.get(f"{API}/admin/affiliates/{S['a2']}").status_code == 404
    assert s.get(f"{API}/admin/affiliates/{S['a1']}").status_code == 200
    assert s.post(f"{API}/admin/affiliates/{S['a2']}/internal", json={"aziendaId": S["c1"]}).status_code == 404
    assert s.post(f"{API}/admin/affiliates/{S['a1']}/internal", json={"aziendaId": S["c2"]}).status_code == 403


def test_12_scoped_tickets():
    s = login(*SCOPED)
    L = s.get(f"{API}/tickets").json()
    tids = {t["id"] for t in L}
    assert S["t1"] in tids and S["t2"] not in tids
    assert all(t["affId"] == S["a1"] for t in L)
    assert s.get(f"{API}/tickets/{S['t2']}").status_code == 404
    assert s.get(f"{API}/tickets", params={"affId": S["a2"]}).json() and all(t["affId"] == S["a1"] for t in s.get(f"{API}/tickets", params={"affId": S["a2"]}).json())


def test_13_scoped_dashboard_report_exports_emails():
    s = login(*SCOPED)
    d = s.get(f"{API}/admin/dashboard").json()
    assert all(t["id"] in (S["a1"], S["t1"]) for t in d["todo"]), d["todo"]
    assert d["kpi"]["ticket"] == 1
    c = s.get(f"{API}/admin/counts").json()
    assert c["ticket"] <= 1
    rep = s.get(f"{API}/admin/report").json()
    assert rep["rete"]["affiliati"] == 1
    csv = s.get(f"{API}/admin/export/affiliati").text
    assert AFF1[0] in csv and AFF2[0] not in csv and "piervincenzi" not in csv
    assert "Azienda affiliante" in csv and "QA Azienda Uno" in csv
    em = s.get(f"{API}/admin/emails").json()["items"]
    assert all(e["to"] == AFF1[0] for e in em)


def test_14_scoped_notifications():
    s = login(*SCOPED)
    N = s.get(f"{API}/notifications").json()
    refs = {n.get("ref") for n in N}
    assert S["a2"] not in refs and S["t2"] not in refs
    assert S["a1"] in refs or S["t1"] in refs


def test_15_scoped_forbidden():
    s = login(*SCOPED)
    assert s.put(f"{API}/admin/settings", json={"giorni": 15}).status_code == 403
    assert s.post(f"{API}/admin/legal", json={"contratto": "x", "privacy": "y", "nuovaVersione": False}).status_code == 403
    assert s.get(f"{API}/admin/team").status_code == 403
    assert s.post(f"{API}/admin/companies", json={"nome": "QA hack", "pag": {}}).status_code == 403
    cs = s.get(f"{API}/admin/companies").json()
    assert [c["id"] for c in cs] == [S["c1"]]


def test_16_full_user():
    s = login(*FULL)
    ids = {a["id"] for a in s.get(f"{API}/admin/affiliates").json()}
    assert S["a1"] in ids and S["a2"] in ids
    assert s.get(f"{API}/admin/team").status_code == 200
    r = s.put(f"{API}/admin/team/{S['master']}", json={"nome": "x", "email": "x@x.it", "active": False})
    assert r.status_code == 403
    m = DB.users.find_one({"id": S["master"]})
    assert m["active"] is True and m.get("is_super") is True


def test_17_csv_company_column(admin):
    csv = admin.get(f"{API}/admin/export/affiliati").text
    line = next(l for l in csv.splitlines() if AFF1[0] in l)
    assert "QA Azienda Uno" in line


def test_99_cleanup(admin):
    for k in ("a1", "a2"):
        if S.get(k):
            assert admin.delete(f"{API}/admin/affiliates/{S[k]}").status_code == 200
            assert admin.get(f"{API}/admin/affiliates/{S[k]}").status_code == 404
    for k in ("c1", "c2"):
        if S.get(k):
            assert admin.delete(f"{API}/admin/companies/{S[k]}").status_code == 200
