from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core import db, uid, super_user, PERMS

router = APIRouter(prefix="/api/admin")


class RepartoIn(BaseModel):
    nome: str
    ordine: int = 0


class RuoloIn(BaseModel):
    nome: str
    perms: List[str] = []
    reparti: List[str] = []


async def valid_reps(L):
    ok = {r["id"] for r in await db.reparti.find({}, {"_id": 0, "id": 1}).to_list(100)}
    return [x for x in L if x in ok]


@router.post("/reparti")
async def rep_new(body: RepartoIn, u=Depends(super_user)):
    if not body.nome.strip():
        raise HTTPException(400, "Inserisci il nome del reparto")
    r = {"id": uid(), "nome": body.nome.strip(), "ordine": body.ordine}
    await db.reparti.insert_one(dict(r))
    return r


@router.put("/reparti/{rid}")
async def rep_upd(rid: str, body: RepartoIn, u=Depends(super_user)):
    if not body.nome.strip():
        raise HTTPException(400, "Inserisci il nome del reparto")
    r = await db.reparti.update_one({"id": rid}, {"$set": {"nome": body.nome.strip(), "ordine": body.ordine}})
    if not r.matched_count:
        raise HTTPException(404, "Reparto non trovato")
    return {"ok": True}


@router.delete("/reparti/{rid}")
async def rep_del(rid: str, u=Depends(super_user)):
    if await db.tickets.count_documents({"reparto": rid}):
        raise HTTPException(400, "Ci sono ticket in questo reparto: spostali prima di eliminarlo")
    await db.reparti.delete_one({"id": rid})
    await db.ruoli.update_many({}, {"$pull": {"reparti": rid}})
    await db.users.update_many({}, {"$pull": {"reparti": rid}})
    return {"ok": True}


@router.get("/ruoli")
async def ruoli(u=Depends(super_user)):
    L = await db.ruoli.find({}, {"_id": 0}).sort("nome", 1).to_list(100)
    for r in L:
        r["utenti"] = await db.users.count_documents({"ruoloId": r["id"]})
    return L


async def ruolo_fields(body):
    if not body.nome.strip():
        raise HTTPException(400, "Inserisci il nome del ruolo")
    return {"nome": body.nome.strip(), "perms": [p for p in body.perms if p in PERMS], "reparti": await valid_reps(body.reparti)}


@router.post("/ruoli")
async def ruolo_new(body: RuoloIn, u=Depends(super_user)):
    r = {"id": uid(), **(await ruolo_fields(body))}
    await db.ruoli.insert_one(dict(r))
    return r


@router.put("/ruoli/{rid}")
async def ruolo_upd(rid: str, body: RuoloIn, u=Depends(super_user)):
    r = await db.ruoli.update_one({"id": rid}, {"$set": await ruolo_fields(body)})
    if not r.matched_count:
        raise HTTPException(404, "Ruolo non trovato")
    return {"ok": True}


@router.delete("/ruoli/{rid}")
async def ruolo_del(rid: str, u=Depends(super_user)):
    if await db.users.count_documents({"ruoloId": rid}):
        raise HTTPException(400, "Il ruolo è assegnato ad alcuni utenti: cambia prima il loro ruolo")
    await db.ruoli.delete_one({"id": rid})
    return {"ok": True}
