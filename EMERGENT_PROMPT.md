# Specifiche per Emergent.sh – Portale Affiliati Agenzie di Viaggio

## Prompt da incollare

> Costruisci una web app full-stack (frontend React, backend FastAPI, database MongoDB, oppure lo stack che preferisci) chiamata **"Portale Affiliati – Rete Agenzie"**, in lingua italiana, completamente **responsive** (desktop, tablet, smartphone).
>
> Nel repository trovi `prototype/index.html`: è un **prototipo funzionante** in un unico file HTML che contiene già tutte le schermate, i testi, la grafica e i flussi. **Usalo come riferimento visivo e funzionale**: la versione che costruisci deve avere lo stesso aspetto (palette celeste scuro `#1b75b0` e arancione `#f07c1b`, sfondo sabbia `#f6f1e8`, font Fraunces per i titoli e Plus Jakarta Sans per il testo, illustrazioni stile viaggio con mare, montagne, sole e aereo) e le stesse funzioni.
>
> La differenza è che la versione definitiva deve avere **backend e database reali, login sicuro, invio reale delle email, archiviazione dei file su storage, job pianificati per le scadenze dei domini e notifiche**. Segui alla lettera le specifiche del file `EMERGENT_PROMPT.md`. Procedi per fasi (vedi "Piano di sviluppo") e fammi verificare ogni fase.

---

## 1. Ruoli

| Ruolo | Descrizione |
|---|---|
| **Affiliato** | Si registra, completa i dati, segue il percorso di apertura del sito, usa assistenza, corsi e materiali. |
| **Admin principale** (`super`) | Accesso completo, gestisce anche il team degli amministratori. |
| **Collaboratore admin** | Accede solo alle sezioni per cui ha il permesso. |

Permessi assegnabili ai collaboratori: `richieste`, `affiliati` (schede, documenti e pagamenti), `ticket`, `corsi`, `bacheca`, `materiali`, `scadenze`, `report` (report ed export), `email` (registro email), `impostazioni`. Il menu mostra solo le sezioni consentite e le API devono rifiutare (403) le operazioni non permesse.

## 2. Autenticazione e account

- Registrazione affiliato: tipo (persona fisica o azienda), email, password (minimo 8 caratteri) e conferma.
- Spunte obbligatorie: **contratto di affiliazione** e **informativa privacy**, con link che apre il testo. Spunta facoltativa: comunicazioni marketing. Salvare versione, data e ora di ogni consenso.
- **Verifica email**: dopo la registrazione si invia un codice di 6 cifre valido 24 ore. Finché l'email non è verificata l'affiliato vede solo la schermata di conferma, con il pulsante "Reinvia codice". L'admin può segnarla come verificata a mano.
- **Password dimenticata**: si inserisce l'email, arriva un codice di 6 cifre valido 30 minuti e si sceglie la nuova password. Non rivelare se l'email esiste.
- Password con hash (bcrypt o argon2), sessioni o JWT sicuri, limite ai tentativi di login.
- Gli account admin disattivati non possono accedere.
- **Riaccettazione termini**: se l'admin pubblica una nuova versione di contratto e privacy, al login successivo l'affiliato vede una schermata bloccante "Abbiamo aggiornato i termini" e deve riaccettarli.

## 3. Lato affiliato

Testata con banner illustrato (cielo, mare, montagne, aereo), "Benvenuto a bordo", nome dell'agenzia, URL e badge di stato. Sotto c'è un **itinerario in 6 tappe**: completate con la spunta, quella attuale con l'aereo arancione che pulsa, quelle future tratteggiate.

1. Dati · 2. Approvazione · 3. URL e logo · 4. Pagamento · 5. Realizzazione · 6. Consegna

Schede: **Il mio percorso · Documenti · Pagamenti · Bacheca · Materiali · Corsi · Assistenza**. Campanella notifiche in alto.

### 3.1 Il mio percorso
- **Dati affiliato**: se è una persona, nome e cognome con la possibilità di aggiungere altri affiliati; se è un'azienda, ragione sociale, P.IVA e referente (al posto dei nomi). Poi nome dell'agenzia, telefono, città e **fino a 3 URL desiderati** (normalizzati in minuscolo, senza `http`, `www` e `/`). Si può salvare una bozza o inviare la richiesta. Dopo l'invio i dati diventano di sola lettura; se la richiesta viene rifiutata si possono correggere e reinviare (viene mostrato il motivo del rifiuto).
- Per inviare la richiesta servono anche i **dati di fatturazione** completi (vedi 3.2).
- **Logo e URL** (dopo l'approvazione):
  - si mostrano le 3 proposte di logo caricate dall'admin e l'affiliato ne sceglie una;
  - un'anteprima a forma di browser mostra URL, logo scelto e nome dell'agenzia;
  - per ogni URL c'è uno stato: in verifica, disponibile o non disponibile;
  - l'affiliato sceglie l'**URL definitivo** solo tra quelli disponibili, con conferma (poi non si può cambiare);
  - se un URL non è disponibile, può proporne uno alternativo.
- **Pagamento** (compare solo dopo la scelta dell'URL definitivo):
  - box con i dati del bonifico presi dalle impostazioni: importo con IVA, intestatario, IBAN, banca, BIC, causale con `{agenzia}` e `{url}` sostituiti, termine e note, con pulsanti "Copia";
  - caricamento della ricevuta (PDF o immagine), che passa in stato "in verifica";
  - se l'admin la respinge, l'affiliato vede il motivo e ne carica un'altra.
- **Tempi di consegna** (dopo la conferma del pagamento): data prevista grande, giorni mancanti, barra di avanzamento e fasi (Pagamento ricevuto → Sviluppo in corso → Revisione e test → Consegnato).
- **Il tuo sito** (dopo la consegna), presentato come una **carta d'imbarco**:
  - URL Admin, Utente, Password Admin e Password sito, con pulsanti Mostra e Copia;
  - la password sito resta attiva finché il sito non viene messo online;
  - pulsante "Ho finito le modifiche: metti online", che invia una richiesta all'admin;
  - dominio con data di scadenza.
- Avvisi in home: comunicazione della bacheca non letta, documenti obbligatori mancanti, notifiche.

### 3.2 Documenti
- Tipi: Documento d'identità (obbligatorio), Codice fiscale o tessera sanitaria (obbligatorio), Visura camerale (obbligatoria solo per le aziende), Licenza agenzia di viaggi (facoltativa), Altro (facoltativo, anche più file).
- Upload di PDF o immagini fino a 10 MB. Stati: in verifica, approvato o rifiutato con motivo; un documento rifiutato si può ricaricare.
- **Dati di fatturazione** (sempre modificabili): intestatario, codice fiscale, P.IVA, codice SDI, PEC, indirizzo, CAP, città e provincia.
  - Controlli: CAP di 5 cifre, provincia di 2 lettere, CF di 16 caratteri (o 11 cifre), P.IVA di 11 cifre, SDI di 7 caratteri.
  - Persona: serve CF o P.IVA. Azienda: serve la P.IVA e almeno uno tra SDI e PEC.
- Riepilogo dei consensi (contratto, privacy, marketing) con data e ora e link ai testi; il consenso marketing si può revocare.

### 3.3 Pagamenti
- Riquadri: totale pagato (IVA inclusa), totale in verifica, numero di fatture.
- Tabella con data, descrizione, importo (imponibile più IVA), stato (pagato, in verifica, respinto), ricevuta e **fattura da scaricare** (oppure "In preparazione").
- Le voci comprendono: attivazione sito, corsi Premium, rinnovi dominio e pagamenti registrati a mano dall'admin.

### 3.4 Bacheca
Elenco delle comunicazioni dell'admin con immagine facoltativa, categoria (Novità, Promozione, Avviso, Evento), data e badge "In evidenza" o "Nuovo". Aprendo la scheda, le comunicazioni vengono segnate come lette.

### 3.5 Materiali
Griglia con filtri per categoria (Loghi e grafica, Brochure e cataloghi, Social media, Modulistica, Altro), anteprima di immagini, PDF e video, e **download**. Ogni download viene contato.

### 3.6 Corsi (Academy)
- **Visibile solo dopo che l'admin ha confermato il pagamento del sito e del dominio.** Prima compare una schermata con il lucchetto che spiega cosa manca: approvazione, scelta dell'URL e ricevuta, oppure ricevuta in verifica.
- Banner "Academy affiliati" con il riquadro "Continua da dove eri rimasto" e filtri Tutti, In corso, Completati, Premium.
- Card del corso: copertina (immagine, oppure colori e icona della categoria), categoria, badge Gratis o "★ Premium · prezzo", titolo, descrizione, durata, numero di video, livello e barra di avanzamento.
- Pagina del corso:
  - player video con l'elenco delle lezioni accanto, segnate come completate, attuale o bloccate;
  - "Segna come completato" e "Video successivo"; quando un video finisce viene segnato come completato in automatico;
  - al 100% compare il messaggio "Corso completato" e arriva una notifica all'admin.
- **Corsi Premium**: il primo video è un'anteprima gratuita, gli altri sono bloccati. Sotto c'è il box di pagamento con il prezzo del corso e il caricamento della ricevuta. Dopo la conferma dell'admin il corso si sblocca; se il pagamento viene rifiutato, l'affiliato vede il motivo.

### 3.7 Assistenza (ticket)
- Nuovo ticket con oggetto, priorità (bassa, media, alta) e descrizione. **Numero progressivo `T-0001`**.
- Conversazione a messaggi; l'affiliato può segnare il ticket come risolto, e se risponde a un ticket chiuso lo riapre.
- Stati: aperto, in lavorazione, chiuso. Nell'elenco i ticket non letti sono evidenziati.

## 4. Lato admin

Menu laterale blu notte con icone e contatori: Panoramica, Richieste, Affiliati, Ticket, Corsi, Bacheca, Materiali, Scadenze domini, Report, Registro email, Impostazioni.

- **Panoramica**:
  - banner con saluto in base all'ora e numero di attività;
  - riquadri: richieste in attesa, ricevute da verificare, siti in realizzazione, ticket aperti, alert domini;
  - elenco dei domini in scadenza con il pulsante "Rinnovo pagato";
  - lista **Da fare**: nuove richieste, ticket non letti, ricevute, acquisti di corsi, documenti da verificare, URL da verificare, loghi da caricare, richieste di messa online, consegne vicine.
  - Tutto è filtrato in base ai permessi.
- **Richieste**: affiliati in attesa con i dati completi e i pulsanti Accetta o Rifiuta (con motivo); registrati che non hanno ancora inviato i dati; richieste rifiutate.
- **Affiliati**: tabella con ricerca, stato, URL, scadenza del dominio ed export CSV.
- **Scheda affiliato**, con queste sezioni:
  - dati anagrafici;
  - verifica URL (Disponibile o Non disponibile);
  - **3 slot per caricare i loghi**, con evidenziato quello scelto dall'affiliato;
  - pagamento: vedi la ricevuta, poi Conferma (con i giorni lavorativi di consegna, 15 di default) oppure Respingi (con motivo);
  - tempi di consegna: data modificabile e avanzamento delle fasi;
  - accessi al sito: **Super Admin** (URL, utente, password, visibili solo all'admin) e **Admin affiliato** (URL, utente, password admin e password di sblocco del sito), con "Consegna all'affiliato" e "Metti online", che disattiva la password del sito;
  - scadenza dominio: data, promemoria e "Rinnovo pagato (+1 anno)", che annulla gli alert e salva lo storico;
  - fatturazione;
  - account e consensi;
  - documenti: apri, approva, rifiuta con motivo;
  - **pagamenti e fatture**: allega la fattura PDF a ogni voce pagata, con numerazione automatica `FT n/anno`, oppure registra un pagamento manuale;
  - avanzamento dei corsi;
  - ticket.
- **Ticket**: filtri Aperti, Chiusi, Tutti; risposte; cambio di stato; elenco delle email inviate per ogni ticket.
- **Corsi**:
  - card con iscritti, completati e acquisti;
  - acquisti Premium da verificare: vedi ricevuta, Conferma e sblocca, Rifiuta;
  - editor del corso: titolo, categoria, livello, descrizione, gratuito o Premium con prezzo, pubblicato sì/no, copertina;
  - **video**: titolo, durata, descrizione, upload del file MP4 oppure link YouTube, Vimeo o Drive; si possono riordinare ed eliminare;
  - quando si pubblica un corso nuovo, arriva una notifica a tutti gli affiliati con il pagamento confermato.
- **Bacheca**: crea, modifica ed elimina comunicazioni (titolo, categoria, testo, immagine, in evidenza, "invia anche per email") e vedi da quanti affiliati sono state lette.
- **Materiali**: upload con titolo, categoria, descrizione e file (PDF, immagini, ZIP, DOCX, PPTX, XLSX, CSV, MP4, TXT, fino a 50 MB), contatore dei download ed eliminazione.
- **Scadenze domini**: tabella ordinata per scadenza, chip dei promemoria (1 mese, 15, 7 e 1 giorno prima) e "Rinnovo pagato".
- **Report**:
  - incassi dell'anno (IVA inclusa) divisi per attivazioni, corsi, rinnovi e altro, più il totale in verifica;
  - grafico a barre mensile, con selettore dell'anno;
  - panoramica della rete;
  - **export CSV** (separatore `;`, BOM UTF-8 per Excel) di affiliati con fatturazione, pagamenti, scadenze e avanzamento corsi.
- **Registro email**: tutte le email inviate, con ricerca e testo completo.
- **Impostazioni**:
  - **Dati pagamento**: intestatario, IBAN (validato), banca, BIC, importo imponibile, IVA %, importo del rinnovo dominio, causale con `{agenzia}` e `{url}`, termine, note, con anteprima;
  - **Password affiliati**: imposta o genera una nuova password per un affiliato;
  - **Contratto e privacy**: testi modificabili e "Pubblica come nuova versione", che obbliga alla riaccettazione;
  - **Team admin** (solo per l'admin principale): aggiungi o modifica collaboratori con nome, email, password, permessi e attivo sì/no, con email delle credenziali;
  - **Generali**: email dell'admin per le notifiche, giorni di consegna predefiniti, cambio della propria password.

## 5. Email automatiche (invio reale)

Usa un servizio transazionale (Resend, Brevo, SendGrid o SMTP del dominio), con mittente configurabile tramite variabili d'ambiente. Ogni email inviata viene salvata anche nel Registro email.

| Evento | Destinatario |
|---|---|
| Registrazione: codice di verifica | Affiliato |
| Password dimenticata: codice | Utente |
| Nuovo ticket (con numero) | Admin **e** affiliato (conferma) |
| Risposta o cambio di stato del ticket da parte dell'admin | Affiliato |
| Risposta, riapertura o chiusura del ticket da parte dell'affiliato | Admin |
| Richiesta approvata o rifiutata | Affiliato |
| Pagamento del sito confermato (avvio lavori, data di consegna, corsi sbloccati) o respinto | Affiliato |
| Sito consegnato con le credenziali / sito online | Affiliato |
| Ricevuta di un corso caricata | Admin, più conferma all'affiliato |
| Corso sbloccato o pagamento rifiutato | Affiliato |
| Documento approvato o rifiutato | Affiliato |
| Fattura disponibile | Affiliato |
| Nuova comunicazione in bacheca (se selezionato) | Affiliati |
| Nuovo collaboratore admin (credenziali) | Collaboratore |
| **Scadenza dominio: 30, 15, 7 e 1 giorno prima** | **Admin** (ed eventualmente l'affiliato) |

## 6. Job pianificati

- **Una volta al giorno**: per ogni dominio con scadenza a 30, 15, 7 o 1 giorno invia l'email all'admin e crea una notifica. Non inviare due volte lo stesso promemoria. Quando il rinnovo è segnato come pagato, gli alert si annullano e la scadenza passa all'anno successivo.

## 7. Notifiche nel portale

Campanella con contatore e pannello delle ultime notifiche (cliccabili: portano al ticket, al corso, alla scheda o alla sezione) e "Segna tutte come lette". Notifiche per gli stessi eventi delle email, più: nuovo materiale, nuovo corso pubblicato, corso completato, documento caricato.

## 8. File e storage

Archivia su object storage (S3, Cloudflare R2 o lo storage di Emergent) e mai nel database: ricevute, loghi, documenti, fatture, copertine, immagini della bacheca, video dei corsi e materiali. Accesso solo con URL firmati o endpoint autenticati: un affiliato può vedere solo i propri file. Per i video dei corsi va bene anche l'incorporamento di YouTube o Vimeo (non in elenco).

## 9. Modello dati (indicativo)

- **users**: id, email, password_hash, role (`affiliate` o `admin`), is_super, nome, perms[], verified, active, created_at
- **affiliates**: user_id, tipo, persone[{nome,cognome}], azienda, piva, referente, nome_agenzia, telefono, citta, urls[{value,stato}], stato (bozza, in_attesa, accettata, rifiutata), nota_rifiuto, loghi[3], logo_scelto, url_definitivo, ricevuta, pagamento (nessuno, in_verifica, confermato, respinto), importo, consegna{inizio,giorni,data_prevista,fase}, credenziali{url,utente,password,password_sito}, super_admin{url,utente,password}, consegnato_at, richiesta_online, online_at, dominio{scadenza, storico[], promemoria_inviati[]}, fatturazione{…}, consensi{contratto,privacy,marketing}, timestamps
- **documents**: affiliate_id, tipo, file, stato, nota, uploaded_at
- **payments_extra / invoices**: affiliate_id, chiave della voce, numero, file, data
- **tickets**: numero, affiliate_id, oggetto, priorita, stato, messaggi[{da,testo,at}], letto_admin, letto_aff
- **courses**: titolo, categoria, livello, descrizione, premium, prezzo, pubblicato, copertina, lezioni[{id,titolo,durata,descrizione,video_file|url}]
- **course_progress**: affiliate_id, course_id, lezioni_fatte[], completato_at
- **course_purchases**: affiliate_id, course_id, stato, importo, ricevuta, nota
- **news**: titolo, categoria, testo, immagine, in_evidenza, letti_da[]
- **materials**: titolo, categoria, descrizione, file, downloads
- **notifications**: destinatario, testo, link, letto
- **email_log**: to, subject, body, sent_at, riferimento
- **settings**: pagamento{…}, legali{versione,contratto,privacy}, giorni_consegna, admin_email

Le credenziali dei siti (password admin e sito, super admin) vanno **cifrate a riposo**.

## 10. Piano di sviluppo consigliato

1. Autenticazione completa (registrazione, verifica email, reset password, ruoli e permessi) e invio email.
2. Percorso dell'affiliato: dati, fatturazione, approvazione, URL, loghi, pagamento, consegna, credenziali, messa online, scadenze dei domini con job giornaliero.
3. Ticket e notifiche.
4. Documenti, storico pagamenti e fatture, report ed export CSV.
5. Corsi (con sblocco dopo il pagamento), corsi Premium, bacheca e materiali.
6. Team admin e permessi, impostazioni, rifinitura grafica e responsive come nel prototipo.
