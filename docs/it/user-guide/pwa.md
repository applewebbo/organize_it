# Installazione e Offline

Organize It è una **Progressive Web App (PWA)**. Puoi installarla su telefono, tablet o desktop così si apre in una finestra propria come un'app nativa, e i viaggi che hai già aperto restano consultabili anche quando perdi la connessione.

## Installare l'App

L'installazione avviene tramite il browser — non c'è nessuno store.

### Su telefono o tablet

- **Android (Chrome/Edge)**: apri Organize It, poi tocca il menu del browser e scegli **Installa app** / **Aggiungi a schermata Home**.
- **iPhone/iPad (Safari)**: apri Organize It, tocca il pulsante **Condividi**, poi **Aggiungi alla schermata Home**.

### Su desktop

In Chrome o Edge, cerca l'**icona di installazione** nella barra degli indirizzi (oppure usa il menu del browser → **Installa Organize It**). L'app si aprirà in una finestra propria e indipendente.

Una volta installata, Organize It usa la propria icona e si avvia a schermo intero senza gli elementi del browser.

## Lavorare Offline

Organize It registra un **service worker** che memorizza nella cache le pagine e le risorse che visiti. Questo significa che:

- **I viaggi che hai già aperto restano disponibili** offline. Puoi riaprire l'app senza connessione e continuare a consultarli.
- Se, mentre sei offline, navighi verso qualcosa che non è stato messo in cache, viene mostrata una **pagina offline** amichevole al posto dell'errore del browser.
- Dove normalmente comparirebbe una **mappa**, viene mostrato un **segnaposto** offline, perché le tessere delle mappe richiedono una connessione attiva.

!!! info "L'offline è in sola lettura"
    Il supporto offline serve a **consultare** i viaggi già caricati — ad esempio controllare l'itinerario in aeroporto. Le modifiche richiedono comunque una connessione per essere salvate e vedrai sempre i dati più recenti una volta tornato online.

!!! tip "Il service worker è attivo solo in produzione"
    Per mantenere reattivo lo sviluppo locale, il service worker offline è attivo sul sito online, non su un server locale in `DEBUG`.

## Guide Correlate

- [Esportazione e Sincronizzazione Calendario](export.md) - Scarica un PDF o abbonati via iCal per l'accesso offline completo
- [Viaggi](trips.md) - Creare e gestire i viaggi

---

**Prossimo**: Consulta le [FAQ](../faq.md)
