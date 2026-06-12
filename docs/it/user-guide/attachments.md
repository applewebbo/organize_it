# Documenti e Allegati

Organize It include un **archivio documenti** che ti permette di allegare PDF e immagini a un viaggio. Biglietti, voucher hotel, prenotazioni museo, polizze assicurative — tienili insieme al viaggio così sono sempre a portata di click.

## Cosa puoi allegare

### Tipi di file consentiti

- **PDF** (`application/pdf`)
- **JPEG** (`image/jpeg`)
- **PNG** (`image/png`)
- **WebP** (`image/webp`)

### Limite di dimensione

Ogni file può essere fino a **2 MB**.

!!! tip "Comprimi prima di caricare"
    Per PDF multi-pagina (es. carte d'imbarco) puoi comprimere il file o suddividerlo in PDF per singola tratta.

### Limiti di quantità

Per mantenere l'archivio ordinato, ci sono limiti di file allegabili a ciascun elemento:

| Allegato a | Max file |
| --- | --- |
| Viaggio (documenti generali) | 5 |
| Trasferimento principale (arrivo/partenza) | 2 |
| Alloggio | 2 |
| Evento (esperienza / pasto) | 2 |

## La card Allegati

Una card **Documenti** appare nella pagina di dettaglio del viaggio. Raggruppa i caricamenti per categoria:

- **Viaggio** — documenti generali non legati a uno specifico elemento (assicurazione, visto, guida turistica)
- **Come Arrivare** — allegati sui trasferimenti principali di arrivo/partenza (carte d'imbarco, biglietti treno)
- **Dove Dormire** — allegati sugli alloggi (voucher hotel, istruzioni appartamento)
- **Eventi** — allegati sulle singole esperienze e pasti (biglietti museo, prenotazione ristorante)

Ogni categoria mostra un totale e l'elenco dei file con il nome originale e una miniatura (per le immagini) o un'icona PDF.

## Caricare un file

1. Nella pagina di dettaglio del viaggio, trova la card **Documenti**
2. Clicca il pulsante di upload per la categoria desiderata
3. Nel modale, scegli:
   - L'**elemento di destinazione** (a quale trasferimento / alloggio / evento appartiene il file — non serve per la categoria *Viaggio*)
   - Il **file** da caricare
4. Conferma

L'elenco si aggiorna automaticamente. Il nome originale del file viene mantenuto e mostrato nella card.

## Visualizzare un file

Clicca un allegato per aprire l'anteprima:

- Le **immagini** si aprono in un modale di anteprima
- I **PDF** si aprono in una nuova scheda del browser (usando il visualizzatore PDF nativo)

I file vengono serviti solo agli utenti che hanno accesso al viaggio — l'URL contiene l'ID dell'allegato e l'accesso è verificato a ogni richiesta.

## Eliminare un file

Usa l'azione di eliminazione accanto all'allegato. Il file viene rimosso immediatamente, sia dal database sia dallo storage.

## Includere allegati nell'esportazione PDF

Ogni allegato ha un'opzione **Includi nel PDF**. Quando attivata, il file viene incorporato (o referenziato) nell'[esportazione PDF](export.md) offline, così lo hai sempre con te anche senza connessione.

!!! info "Perché un'opzione?"
    Non tutti i file ha senso includerli nel PDF stampato. Un PDF assicurativo grande aggiunge peso, mentre una singola immagine di carta d'imbarco è perfetta da incorporare.

## Consigli

!!! tip "Dai nomi chiari ai file"
    Il nome originale viene mantenuto. Rinominare `IMG_2934.jpg` in `carta-imbarco-roma.jpg` prima del caricamento rende l'archivio molto più leggibile.

!!! tip "Allega vicino alla fonte"
    Un biglietto del museo allegato all'**evento** Colosseo è più facile da trovare dello stesso file perso tra i documenti generali del viaggio.

!!! warning "Dati sensibili"
    Gli allegati risiedono sul server. Evita di caricare scansioni di passaporto o altri documenti altamente sensibili se non strettamente necessario.

## Domande frequenti

### Posso caricare documenti Word o fogli di calcolo?

No — sono accettati solo formati PDF e immagine. Esporta il documento come PDF prima di caricarlo.

### Cosa succede se supero il limite di 2 MB?

Comprimi il file. Per le foto, riduci a circa 1600 px sul lato lungo; per i PDF, usa un'opzione "comprimi" o "riduci dimensione" nel tuo strumento PDF.

### I collaboratori possono caricare file?

Sì — i collaboratori del viaggio possono caricare, vedere ed eliminare allegati.

### Gli allegati sono inclusi nel feed iCal?

No. Il [feed iCal](export.md) contiene solo gli eventi in programma. Gli allegati fanno parte dell'esportazione PDF.
