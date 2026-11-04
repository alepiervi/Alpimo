# PRD – Portale Affiliati Alpimo (Rete Agenzie)

## Problema originale
"Costruisci il progetto che trovi all'interno di GitHub https://github.com/alepiervi/Alpimo. Per le Email usiamo Aruba, ma dammi possibilità di mettere anche Brevo per sicurezza."
Specifiche: /app/EMERGENT_PROMPT.md · riferimento grafico: /app/prototype/index.html

## Scelte utente
- Email: Aruba SMTP principale, Brevo riserva automatica · credenziali inserite più avanti
- Consegna unica di tutto il portale · admin di default admin@alpimo.it

## Architettura
- Backend FastAPI + MongoDB (core.py, routes_auth/aff/admin/common.py, server.py con seed + job domini ogni 6h)
- Frontend React + Vite (styles.css copiato dal prototipo, palette #1b75b0/#f07c1b, Fraunces + Plus Jakarta Sans)
- Auth JWT in cookie httpOnly (access + refresh), bcrypt, blocco 5 tentativi per email, ruoli affiliato/admin/collaboratore con permessi (403 lato API)
- File su Emergent Object Storage, download autenticato (affiliato solo i propri file + pubblici)
- Credenziali siti cifrate (Fernet, CRED_KEY)
- Email: send_mail → Aruba SMTP (smtps.aruba.it:465) → fallback Brevo API; tutte salvate nel Registro email con stato

## Implementato (03/11/2026)
- Registrazione con verifica email (codice 6 cifre 24h), reset password (30 min), consensi versionati, riaccettazione termini
- Percorso affiliato 6 tappe: dati/più affiliati/azienda, 3 URL, fatturazione validata, invio richiesta, loghi, URL definitivo, URL alternativo, pagamento IBAN + ricevuta, tempi di consegna, carta d'imbarco credenziali, messa online
- Documenti, pagamenti/fatture (FT n/anno), bacheca, materiali con contatore, Academy (gate pagamento, Premium con anteprima e ricevuta), ticket T-0001, notifiche
- Admin: panoramica/da fare, richieste, affiliati + scheda completa, ticket, corsi + editor + acquisti, bacheca, materiali, scadenze domini (30/15/7/1), report + CSV, registro email, impostazioni (pagamento, password affiliati, legali, team, generali)
- Test: iteration_1 (34/38 → bug corretti), iteration_2 100%

## Backlog
- P0: inserire credenziali ARUBA_SMTP_USER / ARUBA_SMTP_PASSWORD e BREVO_API_KEY / BREVO_SENDER_EMAIL (email ora solo registrate)
- P1: streaming video con range
- Fatto (03/11/2026): video MP4 dei corsi protetti lato server (Premium solo dopo acquisto confermato; tutti i video solo con pagamento sito confermato e corso pubblicato)
- P2: suddividere routes_admin.py; job domini idempotente su più repliche

## 03/11/2026 – aggiornamento
- Rimossi tutti i dati di prova (affiliati demo, collaboratori test, admin di prova, materiali/corsi/news TEST, IBAN di esempio); il seed non crea più affiliati demo né IBAN di esempio
- Unico admin: account privato del titolare (password non registrata nei file); email notifiche admin impostata sul suo indirizzo
- Date in formato gg/mm/aaaa ovunque (campi di modifica con validazione, visualizzazione, email)
- Verifica email affiliati sospesa finché Aruba/Brevo non sono configurati (registrazione = verificato); riparte automaticamente per le nuove registrazioni appena una credenziale email è presente
- Logo + URL definitivo scelti => proposte non scelte eliminate (sceltaFinale), scelta bloccata
- Dati interni admin: azienda affiliante e piattaforma acquisto dominio (in lista, scadenze, export CSV; nascosti all affiliato)
- Eliminazione affiliato (admin, permesso affiliati) con conferma scrivendo ELIMINA: cancella account, dati, documenti, pagamenti, ticket, corsi, notifiche, file
- Aziende (Impostazioni > Aziende, solo accesso completo): ogni azienda ha dati pagamento propri (campi vuoti = predefinito); affiliato assegnato in Dati interni
- Utenti admin con visibilita per azienda (tutte / selezionate) + permessi; Master (is_master) protetto; utenti "Accesso completo come il Master" (is_super)
- Email creazione utente team non contiene piu la password
- Sezione Guide (menu admin, tutto il team): 16 guide con 34 passaggi, 29 screenshot reali e 4 video registrati (tour, URL/pagamento, ticket, approvazione); editor guide per accesso completo; seed automatico da backend/seed_guides.json in nuovi ambienti
- Script di cattura in /root/guide_*.py (playwright in /root/pwenv) per rigenerare screenshot/video

## 2026-06 — Guida contestuale
- Pulsante "Guida" in ogni sezione admin (campo `sezioni` sulle guide), apre la guida in finestra con schede se ce ne sono piu di una. Assegnazione sezioni modificabile nell editor guide.
- Tipologia sito (Base/Plus/Completo) nei Dati interni della scheda admin, colonna+filtro lista Affiliati, export CSV, report "Siti per tipologia". Nascosta agli affiliati, non incide sul prezzo.
- Ticket per reparti (collection reparti, seed Amministrazione/Travel/IT · Sito internet/IT · Email; Master li gestisce in Impostazioni > Ruoli e reparti). Affiliato sceglie reparto, admin lo sposta (POST /api/tickets/{id}/reparto). Ruoli riutilizzabili (collection ruoli: perms+reparti, user.ruoloId risolto in core.resolve_role). Utenti con reparti vedono solo quei ticket (tk_rep_q) anche in counts/dashboard/scheda/registro email; email ticket ad admin generale + utenti del reparto. Rotte in backend/routes_team.py.
- Known: notifiche admin condivise (segnare letto vale per tutti) - da separare per utente.
- Presa in carico ticket (campo assegnato {id,nome,at}; POST /api/tickets/{id}/assign). Risposta admin su ticket libero = auto-assegnazione. Riassegnare solo is_super. Nascosto agli affiliati.
