# Esportazione e Sincronizzazione Calendario

Organize It può generare un **PDF offline** del tuo itinerario e un **feed iCal** dinamico a cui iscriverti da qualsiasi app di calendario. Entrambi sono disponibili dal menu **Condividi & Esporta** nell'intestazione del viaggio.

## Aprire il menu

Nella pagina di dettaglio del viaggio, clicca l'icona di condivisione nell'intestazione. Vedrai:

- **Link** — genera un link condivisibile in sola lettura (vedi [Collaborazione](collaboration.md))
- **PDF** — scarica un PDF offline del viaggio
- **Calendario** — apre il feed iCal per l'iscrizione

## Esportazione PDF

Il PDF è una versione completa e stampabile del tuo viaggio pensata per funzionare **offline** — perfetta da tenere sul telefono o stampare prima di partire.

### Cosa contiene

- Pagina di copertina con titolo, date, destinazione e immagine di copertina
- Itinerario giorno per giorno con tutti gli eventi in ordine
- Alloggi con indirizzo e check-in/check-out
- Trasferimenti principali (arrivo/partenza) con orari e dettagli
- Trasferimenti locali e tra alloggi
- Voci della [checklist](checklist.md) pre-partenza
- Link utili

### Allegati nel PDF

Ogni [allegato](attachments.md) ha un'opzione **Includi nel PDF**. Quando attivata, il file viene incorporato così lo hai anche offline. Utile per carte d'imbarco, voucher hotel e biglietti.

### Generare il PDF

1. Apri la pagina di dettaglio del viaggio
2. Clicca il menu **Condividi & Esporta**
3. Clicca **PDF**
4. Il file viene generato e scaricato automaticamente

!!! tip "Stampa o salva offline"
    Salva il PDF sul telefono prima di partire (es. nell'app File, in Note o nel tuo strumento read-later preferito). Funziona senza connessione e include ogni dettaglio rilevante.

!!! info "Sempre aggiornato"
    Il PDF viene generato al volo dai dati correnti del viaggio. Rigeneralo ogni volta che l'itinerario cambia.

## Sincronizzazione Calendario iCal

Il feed iCal trasforma ogni evento del tuo viaggio in voci di calendario leggibili da qualsiasi app di calendario moderna — Apple Calendar, Google Calendar, Outlook, Fastmail, Thunderbird, ecc.

### Come funziona

Ogni viaggio ha un **token calendario** univoco e non indovinabile. L'URL del feed contiene questo token:

```
https://<dominio>/ical/<calendar-token>/
```

Il token viene generato automaticamente alla creazione del viaggio. Chiunque abbia l'URL può leggere il feed, quindi trattalo come un link privato — e reimpostalo se condiviso per errore (vedi [Reimpostare il link](#reimpostare-il-link)).

### Iscriversi

1. Apri la pagina di dettaglio del viaggio
2. Clicca il menu **Condividi & Esporta**
3. Clicca **Calendario** — si apre una nuova scheda con l'URL del feed (l'autore del viaggio può invece aprire **Link calendario** per copiare l'URL e gestire il feed)
4. Copia l'URL
5. Nella tua app di calendario, aggiungi un'**iscrizione** (non un'importazione) usando l'URL:
    - **Apple Calendar**: File → Nuova iscrizione a calendario
    - **Google Calendar**: Altri calendari → Da URL
    - **Outlook**: Aggiungi calendario → Iscriviti dal web

### Cosa contiene

- Ogni [esperienza](experiences.md) e [pasto](meals.md) come evento di calendario
- Gli [alloggi](stays.md) come eventi multi-giorno
- I [trasferimenti principali](transfers.md) (arrivo, partenza) con i loro orari
- Località, note e un link al viaggio in Organize It

### Aggiornamenti automatici

Trattandosi di un'**iscrizione**, la tua app di calendario aggiorna periodicamente il feed. Qualsiasi modifica all'itinerario appare nel calendario entro minuti o ore, a seconda dell'intervallo di aggiornamento dell'app.

!!! warning "Non importare — iscriviti"
    Se *importi* il file, ottieni una fotografia statica che non si aggiorna. Usa sempre l'opzione *iscriviti* / *aggiungi da URL*.

### Reimpostare il link

Se l'URL del feed viene condiviso per errore, l'autore del viaggio può reimpostarlo:

1. Apri la pagina di dettaglio del viaggio
2. Clicca il menu **Condividi & Esporta**
3. Clicca **Link calendario**
4. Clicca **Reimposta link calendario**

La reimpostazione genera un nuovo token: il vecchio URL smette immediatamente di funzionare, le iscrizioni esistenti non si aggiornano più e viene mostrato un nuovo URL da condividere.

## Domande frequenti

### Posso avere calendari separati per giorno o per alloggio?

No. Il feed contiene tutti gli eventi di un viaggio. Usa i filtri o i colori della tua app di calendario per evidenziare elementi specifici.

### Il PDF include le mappe?

Include indirizzi e (dove disponibili) snippet statici di mappa per alloggi e eventi chiave. La navigazione mappa interattiva richiede l'app web.

### Gli allegati nel PDF sono incorporati o solo linkati?

Sono incorporati, così il PDF funziona completamente offline.

### Il mio calendario non si aggiorna — perché?

Le app di calendario aggiornano i feed secondo i loro tempi (in genere ogni 1–24 ore). La maggior parte ha un'opzione *Aggiorna* manuale se ti serve un aggiornamento immediato.
