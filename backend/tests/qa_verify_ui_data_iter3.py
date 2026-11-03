# Re-runs iteration 3 scope checks against data created through the UI (companies/team/affiliates already exist)
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import test_iter3_companies_scope as T

d = T.DB
S = T.S
S["a1"] = d.users.find_one({"email": T.AFF1[0]})["id"]
S["a2"] = d.users.find_one({"email": T.AFF2[0]})["id"]
S["c1"] = d.companies.find_one({"nome": "QA Azienda Uno"})["id"]
S["c2"] = d.companies.find_one({"nome": "QA Azienda Due"})["id"]
S["t1"] = d.tickets.find_one({"affId": S["a1"]})["id"]
S["t2"] = d.tickets.find_one({"affId": S["a2"]})["id"]
S["master"] = d.users.find_one({"is_master": True})["id"]
adm = T.login(*T.QA_ADMIN)
for name in ["test_06_aff_me_pag", "test_07_company_without_iban_fallback", "test_10_team_email_no_password", "test_11_scoped_affiliates",
             "test_12_scoped_tickets", "test_13_scoped_dashboard_report_exports_emails", "test_14_scoped_notifications",
             "test_15_scoped_forbidden", "test_16_full_user", "test_17_csv_company_column"]:
    fn = getattr(T, name)
    try:
        fn(adm) if fn.__code__.co_argcount else fn()
        print("PASS", name)
    except AssertionError as e:
        print("FAIL", name, str(e)[:300])
m = T.login(*T.AFF1).get(f"{T.API}/aff/me").json()["pag"]
print("aff1 pag:", m)
