# Alpimo – Portale Affiliati Agenzie di Viaggio

Piattaforma per gestire gli affiliati che aprono il sito della propria agenzia di viaggi: registrazione, scelta di dominio e logo, pagamenti, consegna del sito, assistenza tramite ticket, documenti, fatture, bacheca, materiali e corsi di formazione (Academy).

## Contenuto del repository

| Percorso | Cosa contiene |
|---|---|
| `prototype/index.html` | **Prototipo funzionante** in un unico file HTML: tutte le schermate e i flussi, lato affiliato e lato admin. |
| `EMERGENT_PROMPT.md` | **Specifiche complete e prompt da usare su Emergent.sh** per costruire la versione definitiva con database, email reali e archivio file. |

## Provare il prototipo

Apri `prototype/index.html` con un browser (doppio clic sul file). Non serve installare niente.

La barra scura in alto ("Modalità prova") permette di entrare subito nei vari ruoli:

| Ruolo | Email | Password |
|---|---|---|
| Amministratore principale | admin@demo.it | admin |
| Collaboratore (permessi limitati) | supporto@demo.it | demo |
| Affiliato approvato, in attesa di pagamento | mario@demo.it | demo |
| Affiliato con sito consegnato | blu@demo.it | demo |
| Affiliato con ricevuta in verifica | isole@demo.it | demo |

"Reimposta dati" riporta tutto agli esempi iniziali.

### Limiti del prototipo (da risolvere nella versione definitiva)
- I dati sono salvati **nel browser** (localStorage e IndexedDB): non sono condivisi tra dispositivi o utenti diversi.
- Le **email non partono davvero**: vengono generate e mostrate nel "Registro email" dell'admin. I codici di verifica e di reset password sono mostrati a schermo.
- I file (documenti, fatture, video, materiali) restano nel browser di chi li carica.
- I video YouTube/Vimeo non possono essere incorporati nel player.

## Funzionalità

**Lato affiliato:** registrazione con verifica email e accettazione di contratto e privacy · password dimenticata · percorso in 6 tappe (Dati → Approvazione → URL e logo → Pagamento → Realizzazione → Consegna) · dati anagrafici con più affiliati o azienda · fino a 3 URL proposti · scelta tra 3 loghi con anteprima · URL definitivo · box pagamento con IBAN e upload della ricevuta · tempi di consegna con fasi · credenziali del sito a stile "carta d'imbarco" · richiesta di messa online · documenti · dati di fatturazione · storico pagamenti e fatture · bacheca · materiali da scaricare · corsi video con avanzamento e corsi Premium a pagamento (disponibili solo dopo la conferma del pagamento del sito) · ticket numerati · notifiche.

**Lato admin:** panoramica con attività da fare · richieste da accettare o rifiutare · scheda completa dell'affiliato · verifica URL · caricamento dei 3 loghi · conferma dei pagamenti · fasi di consegna · credenziali Super Admin e Admin · messa online · scadenze dei domini con avvisi a 30, 15, 7 e 1 giorno · ticket · corsi e video · bacheca · materiali · documenti · fatture · report incassi ed export CSV · registro email · impostazioni (dati di pagamento, password affiliati, contratto e privacy, team admin con permessi, generali).

## Sviluppo con Emergent.sh

1. Collega questo repository a Emergent.
2. Apri `EMERGENT_PROMPT.md` e incolla in Emergent il blocco "Prompt da incollare", poi chiedigli di leggere tutto il file come specifica.
3. Indica a Emergent di usare `prototype/index.html` come riferimento per grafica, testi e flussi.
