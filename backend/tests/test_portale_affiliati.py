# Regression tests: Portale Affiliati (auth, draft flow, admin workflow, docs, tickets, courses, bacheca, materiali, report, settings, team, security)
import os
import re
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = ("admin@alpimo.it", "Alpimo-Admin-2026")
DEMO_PW = "demo1234"
S = {}  # shared state across ordered tests
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return s


def upload(sess, name, data, ctype, owner=None):
    d = {"owner": owner} if owner else {}
    r = sess.post(f"{API}/files", files={"file": (name, data, ctype)}, data=d)
    return r


def latest_code(admin, to, subject):
    for _ in range(10):
        r = admin.get(f"{API}/admin/emails", params={"q": to})
        assert r.status_code == 200
        for e in r.json()["items"]:
            if e["to"] == to and e["subject"] == subject:
                m = re.search(r"\b(\d{6})\b", e["body"])
                if m:
                    return m.group(1), e
        time.sleep(1)
    pytest.fail(f"No email '{subject}' for {to}")


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)


# ---------- Auth ----------
class TestAuth:
    def test_admin_login_cookies(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
        assert r.status_code == 200
        assert r.json()["role"] == "admin" and r.json()["is_super"] is True
        sc = r.headers.get("set-cookie", "").lower()
        assert "access_token" in sc and "httponly" in sc and "samesite=none" in sc

    def test_affiliate_logins_and_me(self):
        for e in ("sole@demo.it", "mario@demo.it", "blu@demo.it"):
            s = login(e, DEMO_PW)
            me = s.get(f"{API}/auth/me").json()
            assert me["email"] == e and me["role"] == "affiliate"
            assert me["termsOutdated"] is False

    def test_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": "mario@demo.it", "password": "wrong-pw"})
        assert r.status_code == 401

    def test_bruteforce_lockout(self):
        em = f"test_lock_{uuid.uuid4().hex[:6]}@nowhere.it"
        codes = [requests.post(f"{API}/auth/login", json={"email": em, "password": "x"}).status_code for _ in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429, codes

    def test_bcrypt_hash_and_cred_encrypted(self):
        from pymongo import MongoClient
        from dotenv import dotenv_values
        env = dotenv_values("/app/backend/.env")
        db = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
        assert db.users.find_one({"email": ADMIN[0]})["password_hash"].startswith("$2b$")
        blu = db.affiliates.find_one({"email": "blu@demo.it"})
        assert isinstance(blu["cred"], str) and "Bo!2026" not in blu["cred"]

    def test_unauth_me(self):
        assert requests.get(f"{API}/auth/me").status_code == 401


# ---------- Register + verify + forgot/reset + draft submit ----------
class TestRegisterFlow:
    def test_register_requires_consents(self):
        r = requests.post(f"{API}/auth/register", json={"email": "x_test@test.it", "password": "Password123", "contratto": False, "privacy": True})
        assert r.status_code == 400

    def test_register_and_verify(self, admin):
        em = f"test_{uuid.uuid4().hex[:8]}@test.it"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={"email": em, "password": "Password123", "tipo": "persona", "contratto": True, "privacy": True})
        assert r.status_code == 200 and r.json()["verified"] is False
        assert s.get(f"{API}/aff/me").status_code == 403  # not verified
        assert s.post(f"{API}/auth/verify", json={"code": "000000"}).status_code == 400
        assert s.post(f"{API}/auth/resend").status_code == 200
        code, mail = latest_code(admin, em, "Il tuo codice di verifica")
        assert mail["status"] in ("non_configurato", "in_invio", "errore", "inviata", "inviato")
        print("email status:", mail["status"])
        assert s.post(f"{API}/auth/verify", json={"code": code}).status_code == 200
        assert s.get(f"{API}/auth/me").json()["verified"] is True
        S.update(new_email=em, new_sess=s)

    def test_forgot_reset(self, admin):
        em = S["new_email"]
        assert requests.post(f"{API}/auth/forgot", json={"email": em}).status_code == 200
        code, _ = latest_code(admin, em, "Codice per reimpostare la password")
        assert requests.post(f"{API}/auth/reset", json={"email": em, "code": "111111", "password": "NewPass1234"}).status_code == 400
        assert requests.post(f"{API}/auth/reset", json={"email": em, "code": code, "password": "NewPass1234"}).status_code == 200
        S["new_sess"] = login(em, "NewPass1234")

    def test_profile_billing_submit(self):
        s = S["new_sess"]
        r = s.put(f"{API}/aff/profile", json={"tipo": "persona", "persone": [{"nome": "Test", "cognome": "User"}], "nomeAgenzia": "TEST Agenzia",
                                              "telefono": "3330000000", "citta": "Roma", "urls": [f"test{uuid.uuid4().hex[:6]}.it", "", ""]})
        assert r.status_code == 200
        # submit without billing -> 400
        r = s.post(f"{API}/aff/submit")
        assert r.status_code == 400 and "fatturazione" in r.json()["detail"]
        bad = {"intestatario": "Test", "indirizzo": "Via 1", "cap": "123", "citta": "Roma", "provincia": "RMA", "cf": "ABC", "piva": "12", "sdi": "12"}
        r = s.put(f"{API}/aff/billing", json=bad)
        d = r.json()["detail"]
        assert r.status_code == 400 and "CAP" in d and "Provincia" in d and "Codice fiscale" in d and "P.IVA" in d and "SDI" in d
        r = s.put(f"{API}/aff/billing", json={"intestatario": "Test", "indirizzo": "Via 1", "cap": "00100", "citta": "Roma", "provincia": "RM"})
        assert r.status_code == 400 and "codice fiscale o la P.IVA" in r.json()["detail"]
        r = s.put(f"{API}/aff/billing", json={"intestatario": "Test", "indirizzo": "Via 1", "cap": "00100", "citta": "Roma", "provincia": "rm", "cf": "rssmra80a01f839x"})
        assert r.status_code == 200
        f = s.get(f"{API}/aff/me").json()["aff"]["fatturazione"]
        assert f["provincia"] == "RM" and f["cf"] == "RSSMRA80A01F839X"
        r = s.post(f"{API}/aff/submit")
        assert r.status_code == 200
        me = s.get(f"{API}/aff/me").json()["aff"]
        assert me["stato"] == "in_attesa"
        S["new_id"] = me["id"]
        S["new_url"] = me["urls"][0]["value"]

    def test_admin_reject_then_resubmit_accept(self, admin):
        aid, s = S["new_id"], S["new_sess"]
        assert any(r["id"] == aid and r["stato"] == "in_attesa" for r in admin.get(f"{API}/admin/affiliates").json())
        assert admin.post(f"{API}/admin/affiliates/{aid}/decide", json={"accept": False, "nota": ""}).status_code == 400
        assert admin.post(f"{API}/admin/affiliates/{aid}/decide", json={"accept": False, "nota": "Dati incompleti TEST"}).status_code == 200
        me = s.get(f"{API}/aff/me").json()["aff"]
        assert me["stato"] == "rifiutata" and me["nota"] == "Dati incompleti TEST"
        assert s.put(f"{API}/aff/profile", json={"tipo": "persona", "persone": [{"nome": "Test", "cognome": "User2"}], "nomeAgenzia": "TEST Agenzia",
                                                 "telefono": "3330000000", "citta": "Roma", "urls": [S["new_url"], "", ""]}).status_code == 200
        assert s.post(f"{API}/aff/submit").status_code == 200
        assert admin.post(f"{API}/admin/affiliates/{aid}/decide", json={"accept": True}).status_code == 200
        assert s.get(f"{API}/aff/me").json()["aff"]["stato"] == "accettata"


# ---------- Full admin workflow on new affiliate (logos, URL, receipt, payment, cred, deliver, online) ----------
class TestWorkflow:
    def test_logos_url_receipt(self, admin):
        aid, s = S["new_id"], S["new_sess"]
        for i in range(3):
            r = upload(admin, f"logo{i}.png", PNG, "image/png")
            assert r.status_code == 200, r.text
            assert admin.post(f"{API}/admin/affiliates/{aid}/logo", json={"idx": i, "file": r.json()["id"]}).status_code == 200
        assert s.post(f"{API}/aff/logo", json={"idx": 2}).status_code == 200
        assert s.post(f"{API}/aff/url-final", json={"idx": 0}).status_code == 400  # not disponibile yet
        assert admin.post(f"{API}/admin/affiliates/{aid}/url", json={"idx": 0, "stato": "disponibile"}).status_code == 200
        assert s.post(f"{API}/aff/url-final", json={"idx": 0}).status_code == 200
        f = upload(s, "ricevuta.pdf", PDF, "application/pdf")
        assert f.status_code == 200
        assert s.post(f"{API}/aff/receipt", json={"file": f.json()["id"]}).status_code == 200
        me = s.get(f"{API}/aff/me").json()["aff"]
        assert me["pagamento"] == "in_verifica" and me["logoScelto"] == 2
        S["receipt_file"] = f.json()["id"]
        assert s.get(f"{API}/aff/courses").status_code == 403

    def test_confirm_payment_cred_deliver_online(self, admin):
        aid, s = S["new_id"], S["new_sess"]
        assert admin.get(f"{API}/files/{S['receipt_file']}").status_code == 200
        assert admin.post(f"{API}/admin/affiliates/{aid}/payment", json={"confirm": True, "giorni": 10}).status_code == 200
        me = s.get(f"{API}/aff/me").json()["aff"]
        assert me["pagamento"] == "confermato" and me["consegna"]["giorni"] == 10 and me["consegna"]["dataPrevista"]
        assert s.get(f"{API}/aff/courses").status_code == 200
        assert s.post(f"{API}/aff/logo", json={"idx": 1}).status_code == 400
        assert admin.post(f"{API}/admin/affiliates/{aid}/deliver").status_code == 400  # no creds yet
        assert me["cred"] == {}
        cred = {"url": "https://x.it/admin", "utente": "u1", "password": "p1", "passwordSito": "ps"}
        assert admin.post(f"{API}/admin/affiliates/{aid}/cred", json={"cred": cred, "superAdmin": {"url": "https://x.it/sa", "utente": "sa", "password": "sp"}}).status_code == 200
        assert s.get(f"{API}/aff/me").json()["aff"]["cred"] == {}  # not delivered yet
        assert admin.get(f"{API}/admin/affiliates/{aid}").json()["superAdmin"]["utente"] == "sa"
        assert admin.post(f"{API}/admin/affiliates/{aid}/consegna", json={"fase": 2, "dataPrevista": "2026-12-31"}).status_code == 200
        assert admin.post(f"{API}/admin/affiliates/{aid}/deliver").status_code == 200
        me = s.get(f"{API}/aff/me").json()["aff"]
        assert me["consegnato"] is True and me["cred"]["password"] == "p1" and "superAdmin" not in me
        assert s.post(f"{API}/aff/request-online").status_code == 200
        assert admin.post(f"{API}/admin/affiliates/{aid}/online").status_code == 200
        me = s.get(f"{API}/aff/me").json()["aff"]
        assert me["online"] is True and me["richiestaOnline"] is False

    def test_domain_renew_invoice_manual_payment(self, admin):
        aid, s = S["new_id"], S["new_sess"]
        assert admin.post(f"{API}/admin/affiliates/{aid}/domain", json={"scadenza": "2026-03-01"}).status_code == 200
        r = admin.post(f"{API}/admin/affiliates/{aid}/renew")
        assert r.status_code == 200 and r.json()["scadenza"] == "2027-03-01"
        pays = s.get(f"{API}/aff/payments").json()
        assert any(p["kind"] == "rinnovo" and p["stato"] == "pagato" for p in pays)
        att = next(p for p in pays if p["kind"] == "attivazione")
        assert att["stato"] == "pagato"
        inv = upload(admin, "fattura.pdf", PDF, "application/pdf").json()["id"]
        r = admin.post(f"{API}/admin/payments/{att['id']}/invoice", json={"file": inv})
        assert r.status_code == 200 and re.fullmatch(r"FT \d+/\d{4}", r.json()["numero"])
        att = next(p for p in s.get(f"{API}/aff/payments").json() if p["kind"] == "attivazione")
        assert att["invoice"]["numero"] == r.json()["numero"]
        assert s.get(f"{API}/files/{inv}?dl=1").status_code == 200
        S["invoice_file"] = inv
        assert admin.post(f"{API}/admin/payments", json={"affId": aid, "descrizione": "TEST manuale", "totale": 122}).status_code == 200
        assert any(p["descrizione"] == "TEST manuale" for p in s.get(f"{API}/aff/payments").json())

    def test_invalid_domain_date(self, admin):
        r = admin.post(f"{API}/admin/affiliates/{S['new_id']}/domain", json={"scadenza": "not-a-date"})
        assert r.status_code == 400, f"got {r.status_code}"


# ---------- Documents ----------
class TestDocs:
    def test_doc_upload_reject_reupload_approve(self, admin):
        s, aid = S["new_sess"], S["new_id"]
        assert upload(s, "virus.exe", b"MZ", "application/octet-stream").status_code == 400
        assert upload(s, "big.pdf", b"0" * (10 * 1024 * 1024 + 10), "application/pdf").status_code == 400
        f = upload(s, "id.pdf", PDF, "application/pdf").json()["id"]
        assert s.post(f"{API}/aff/docs", json={"tipo": "identita", "file": f}).status_code == 200
        d = next(x for x in s.get(f"{API}/aff/docs").json() if x["tipo"] == "identita")
        assert admin.post(f"{API}/admin/docs/{d['id']}", json={"approve": False, "nota": ""}).status_code == 400
        assert admin.post(f"{API}/admin/docs/{d['id']}", json={"approve": False, "nota": "Illeggibile"}).status_code == 200
        d = next(x for x in s.get(f"{API}/aff/docs").json() if x["tipo"] == "identita")
        assert d["stato"] == "rifiutato" and d["nota"] == "Illeggibile"
        f2 = upload(s, "id2.png", PNG, "image/png").json()["id"]
        assert s.post(f"{API}/aff/docs", json={"tipo": "identita", "file": f2}).status_code == 200
        d = next(x for x in s.get(f"{API}/aff/docs").json() if x["tipo"] == "identita")
        assert d["stato"] == "in_verifica"
        assert admin.post(f"{API}/admin/docs/{d['id']}", json={"approve": True}).status_code == 200
        assert s.post(f"{API}/aff/docs", json={"tipo": "identita", "file": f2}).status_code == 400
        S["doc_file"] = f2


# ---------- Tickets ----------
class TestTickets:
    def test_ticket_lifecycle(self, admin):
        s = S["new_sess"]
        r = s.post(f"{API}/tickets", json={"oggetto": "TEST problema", "priorita": "alta", "testo": "Aiuto"})
        assert r.status_code == 200 and re.fullmatch(r"T-\d{4}", r.json()["num"])
        tid = r.json()["id"]
        t = next(x for x in admin.get(f"{API}/tickets").json() if x["id"] == tid)
        assert t["lettoAdmin"] is False
        assert admin.post(f"{API}/tickets/{tid}/msg", json={"testo": "Risposta"}).status_code == 200
        full = admin.get(f"{API}/tickets/{tid}").json()
        assert full["stato"] == "in_lavorazione" and len(full["emails"]) >= 2
        assert s.post(f"{API}/tickets/{tid}/status", json={"stato": "aperto"}).status_code == 400
        assert s.post(f"{API}/tickets/{tid}/status", json={"stato": "chiuso"}).status_code == 200
        assert s.post(f"{API}/tickets/{tid}/msg", json={"testo": "Ancora"}).status_code == 200
        assert s.get(f"{API}/tickets/{tid}").json()["stato"] == "aperto"
        S["ticket"] = tid

    def test_admin_cannot_open_ticket(self, admin):
        assert admin.post(f"{API}/tickets", json={"oggetto": "x", "testo": "y"}).status_code == 403


# ---------- Notifications ----------
class TestNotifications:
    def test_notifs_read_all(self, admin):
        s = S["new_sess"]
        L = s.get(f"{API}/notifications").json()
        assert len(L) > 0
        assert s.post(f"{API}/notifications/read-all").status_code == 200
        assert all(n["letto"] for n in s.get(f"{API}/notifications").json())
        assert len(admin.get(f"{API}/notifications").json()) > 0


# ---------- Courses ----------
class TestCourses:
    def test_locked_for_sole(self):
        assert login("sole@demo.it", DEMO_PW).get(f"{API}/aff/courses").status_code == 403

    def test_free_and_premium(self, admin):
        s = S["new_sess"]
        cs = s.get(f"{API}/aff/courses").json()
        free = next(c for c in cs if not c["premium"])
        prem = next(c for c in cs if c["premium"])
        assert not prem["unlocked"] and prem["lezioni"][0]["locked"] is False and prem["lezioni"][1]["locked"] is True and prem["lezioni"][1]["url"] is None
        for l in free["lezioni"]:
            assert s.post(f"{API}/aff/courses/{free['id']}/done", json={"lid": l["id"]}).status_code == 200
        c = s.get(f"{API}/aff/courses/{free['id']}").json()
        assert c["progress"] == 100 and c["completatoAt"]
        assert s.post(f"{API}/aff/courses/{prem['id']}/done", json={"lid": prem["lezioni"][1]["id"]}).status_code == 400
        f = upload(s, "corso.pdf", PDF, "application/pdf").json()["id"]
        assert s.post(f"{API}/aff/courses/{prem['id']}/buy", json={"file": f}).status_code == 200
        assert s.post(f"{API}/aff/courses/{prem['id']}/buy", json={"file": f}).status_code == 400
        p = next(x for x in admin.get(f"{API}/admin/course-purchases").json() if x["affId"] == S["new_id"] and x["ref"] == prem["id"])
        assert p["stato"] == "in_verifica"
        assert admin.post(f"{API}/admin/course-purchases/{p['id']}", json={"confirm": True}).status_code == 200
        c = s.get(f"{API}/aff/courses/{prem['id']}").json()
        assert c["unlocked"] is True and all(not l["locked"] for l in c["lezioni"])

    def test_done_invalid_course(self):
        r = S["new_sess"].post(f"{API}/aff/courses/nonexistent/done", json={"lid": "x"})
        assert r.status_code in (400, 404), f"got {r.status_code}"

    def test_admin_course_crud(self, admin):
        r = admin.post(f"{API}/admin/courses", json={"titolo": "TEST Corso", "lezioni": [{"titolo": "L1", "url": "https://youtu.be/abc"}, {"titolo": "L2"}]})
        cid = r.json()["id"]
        c = next(x for x in admin.get(f"{API}/admin/courses").json() if x["id"] == cid)
        assert len(c["lezioni"]) == 2 and c["pubblicato"] is False
        assert all(x["id"] != cid for x in S["new_sess"].get(f"{API}/aff/courses").json())
        les = list(reversed(c["lezioni"]))
        assert admin.put(f"{API}/admin/courses/{cid}", json={"titolo": "TEST Corso", "lezioni": les, "pubblicato": True}).status_code == 200
        ac = S["new_sess"].get(f"{API}/aff/courses/{cid}").json()
        assert ac["lezioni"][0]["titolo"] == "L2"
        assert admin.delete(f"{API}/admin/courses/{cid}").status_code == 200


# ---------- Bacheca / Materiali ----------
class TestNewsMaterials:
    def test_news(self, admin):
        s = S["new_sess"]
        r = admin.post(f"{API}/admin/news", json={"titolo": "TEST news", "testo": "ciao", "inEvidenza": True, "email": False})
        nid = r.json()["id"]
        assert s.get(f"{API}/aff/me").json()["newsUnread"] >= 1
        n = next(x for x in s.get(f"{API}/aff/news").json() if x["id"] == nid)
        assert n["letto"] is False
        s.post(f"{API}/aff/news/read")
        assert s.get(f"{API}/aff/me").json()["newsUnread"] == 0
        an = next(x for x in admin.get(f"{API}/admin/news").json() if x["id"] == nid)
        assert an["letti"] == 1 and an["tot"] >= 4
        assert admin.delete(f"{API}/admin/news/{nid}").status_code == 200

    def test_materials(self, admin):
        s = S["new_sess"]
        f = upload(admin, "brochure.pdf", PDF, "application/pdf").json()["id"]
        mid = admin.post(f"{API}/admin/materials", json={"titolo": "TEST mat", "categoria": "Brochure", "file": f}).json()["id"]
        m = next(x for x in s.get(f"{API}/aff/materials").json() if x["id"] == mid)
        assert m["categoria"] == "Brochure" and m["downloads"] == 0
        s.post(f"{API}/aff/materials/{mid}/download")
        assert s.get(f"{API}/files/{f}").status_code == 200
        assert next(x for x in admin.get(f"{API}/admin/materials").json() if x["id"] == mid)["downloads"] == 1
        assert admin.delete(f"{API}/admin/materials/{mid}").status_code == 200
        assert all(x["id"] != mid for x in s.get(f"{API}/aff/materials").json())


# ---------- Report / export / emails / domains ----------
class TestReport:
    def test_report(self, admin):
        r = admin.get(f"{API}/admin/report", params={"year": 2026}).json()
        assert r["year"] == 2026 and len(r["months"]) == 12 and r["totale"] > 0

    @pytest.mark.parametrize("kind", ["affiliati", "pagamenti", "scadenze", "corsi"])
    def test_exports(self, admin, kind):
        r = admin.get(f"{API}/admin/export/{kind}")
        assert r.status_code == 200 and r.content.startswith(b"\xef\xbb\xbf") and ";" in r.text.splitlines()[0]

    def test_emails_search_and_domains(self, admin):
        r = admin.get(f"{API}/admin/emails", params={"q": "verifica"}).json()
        assert len(r["items"]) > 0 and all("verifica" in (e["subject"] + e["to"]).lower() for e in r["items"])
        print("email statuses:", {e["status"] for e in r["items"]})
        d = admin.get(f"{API}/admin/domains").json()
        assert any(x["email"] == "blu@demo.it" for x in d)

    def test_emails_search_special_chars(self, admin):
        r = admin.get(f"{API}/admin/emails", params={"q": "("})
        assert r.status_code == 200, f"got {r.status_code}"


# ---------- Settings / Team ----------
class TestSettingsTeam:
    def test_iban_validation(self, admin):
        s = admin.get(f"{API}/admin/settings").json()
        pag = dict(s["pag"])
        assert admin.put(f"{API}/admin/settings", json={"pag": {**pag, "iban": "XX12"}}).status_code == 400
        assert admin.put(f"{API}/admin/settings", json={"pag": pag}).status_code == 200

    def test_set_affiliate_password(self, admin):
        assert admin.post(f"{API}/admin/affiliates/{S['new_id']}/password", json={"password": "short"}).status_code == 400
        assert admin.post(f"{API}/admin/affiliates/{S['new_id']}/password", json={"password": "AdminSet123"}).status_code == 200
        S["new_sess"] = login(S["new_email"], "AdminSet123")

    def test_team_collaborator(self, admin):
        em = f"test_collab_{uuid.uuid4().hex[:6]}@test.it"
        assert admin.post(f"{API}/admin/team", json={"nome": "TEST Collab", "email": em, "password": "Collab1234", "perms": ["ticket"]}).status_code == 200
        c = login(em, "Collab1234")
        assert c.get(f"{API}/admin/report").status_code == 403
        assert c.get(f"{API}/admin/team").status_code == 403
        assert c.get(f"{API}/tickets").status_code == 200
        tid = next(x for x in admin.get(f"{API}/admin/team").json() if x["email"] == em)["id"]
        assert admin.put(f"{API}/admin/team/{tid}", json={"nome": "TEST Collab", "email": em, "perms": ["ticket"], "active": False}).status_code == 200
        assert requests.post(f"{API}/auth/login", json={"email": em, "password": "Collab1234"}).status_code == 403
        assert c.get(f"{API}/tickets").status_code == 401

    def test_change_password(self):
        s = S["new_sess"]
        assert s.post(f"{API}/auth/change-password", json={"old": "bad", "new": "Whatever123"}).status_code == 400
        assert s.post(f"{API}/auth/change-password", json={"old": "AdminSet123", "new": "Final12345"}).status_code == 200


# ---------- Security ----------
class TestSecurity:
    def test_cross_affiliate_access(self):
        sole = login("sole@demo.it", DEMO_PW)
        assert sole.get(f"{API}/files/{S['invoice_file']}").status_code == 403
        assert sole.get(f"{API}/files/{S['doc_file']}").status_code == 403
        assert sole.get(f"{API}/tickets/{S['ticket']}").status_code == 403
        assert sole.post(f"{API}/tickets/{S['ticket']}/msg", json={"testo": "hack"}).status_code == 403

    def test_affiliate_no_admin(self):
        s = login("mario@demo.it", DEMO_PW)
        for p in ("/admin/report", "/admin/affiliates", "/admin/emails", "/admin/settings", "/admin/team"):
            assert s.get(f"{API}{p}").status_code == 403, p
