# Cleanup helper for iteration 3 test data (deletes only exact QA emails / QA company names created by the tests)
import sys
from pymongo import MongoClient
from dotenv import dotenv_values
e = dotenv_values("/app/backend/.env")
d = MongoClient(e["MONGO_URL"])[e["DB_NAME"]]
AFFS = ["qa-aff1@test.local", "qa-aff2@test.local"]
TEAM = ["qa-scoped@test.local", "qa-full@test.local"]
COMPS = ["QA Azienda Uno", "QA Azienda Due"]
for em in AFFS:
    u = d.users.find_one({"email": em, "role": "affiliate"})
    if u:
        aid = u["id"]
        tids = [t["id"] for t in d.tickets.find({"affId": aid}, {"id": 1})]
        d.notifications.delete_many({"ref": {"$in": tids}})
        for c in ("documents", "payments", "tickets", "progress"):
            d[c].delete_many({"affId": aid})
        d.notifications.delete_many({"$or": [{"to": aid}, {"ref": aid}]})
        d.affiliates.delete_one({"id": aid})
        d.users.delete_one({"id": aid})
        print("deleted aff", em)
if "team" in sys.argv:
    for em in TEAM:
        print("team", em, d.users.delete_one({"email": em, "role": "admin"}).deleted_count)
for n in COMPS:
    c = d.companies.find_one({"nome": n})
    if c:
        d.companies.delete_one({"id": c["id"]})
        d.users.update_many({"role": "admin"}, {"$pull": {"aziende": c["id"]}})
        print("deleted comp", n)
