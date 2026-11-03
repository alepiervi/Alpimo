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
- P1: date picker in formato italiano; streaming video con range
- Fatto (03/11/2026): video MP4 dei corsi protetti lato server (Premium solo dopo acquisto confermato; tutti i video solo con pagamento sito confermato e corso pubblicato)
- P2: suddividere routes_admin.py; job domini idempotente su più repliche
