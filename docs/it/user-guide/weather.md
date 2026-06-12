# Previsioni Meteo e Promemoria

Organize It mostra le previsioni meteo per il tuo viaggio e ti invia un'email di promemoria qualche giorno prima della partenza, così puoi preparare i bagagli di conseguenza.

## Widget meteo sul viaggio

Quando il tuo viaggio diventa **Imminente** (data di inizio entro 7 giorni) o **In Corso**, appare un widget meteo nella pagina di dettaglio del viaggio e su ogni card giornaliera. Mostra:

- **Temperature massime/minime giornaliere** in °C
- **Icona delle condizioni meteo** (sole, nuvole, pioggia, neve, ecc.)
- **Previsione giorno per giorno** per i giorni a venire del viaggio

Le previsioni vengono recuperate periodicamente in background, così sono fresche senza rallentare la pagina.

## Email di promemoria meteo

Tre giorni prima della partenza, l'**autore del viaggio e tutti i collaboratori registrati** ricevono un'email automatica con il **riepilogo delle previsioni** per il viaggio.

### Quando viene inviata

- **3 giorni** prima della data di inizio del viaggio
- Solo **una volta** per viaggio (un flag viene memorizzato dopo l'invio)
- Inviata a tutti i destinatari idonei in un unico messaggio (autore in `A`, collaboratori in `Ccn` così gli indirizzi non vengono esposti)

### Chi la riceve

- L'**autore** del viaggio
- Tutti i **collaboratori accettati** con un account registrato su Organize It

Un destinatario viene incluso solo se:

- il suo indirizzo email è **verificato**, e
- la preferenza di profilo **Mostra meteo** è attiva

Se l'autore ha la preferenza disattivata ma un collaboratore l'ha attiva, l'email viene comunque inviata a quel collaboratore. I partecipanti aggiunti solo per nome o email (senza un account) non vengono inclusi.

### Cosa contiene

- Titolo e date del viaggio
- Previsioni giorno per giorno con temperature massime/minime e condizioni
- Un link diretto al viaggio

L'email è localizzata nella **lingua dell'autore** per tutti i destinatari (singolo rendering, singolo invio). Le temperature sono sempre in °C.

### Disattivare il promemoria

Il promemoria è legato alla preferenza **Mostra meteo** del profilo. Disattiva questa opzione per smettere di ricevere email meteo per tutti i tuoi viaggi, sia come autore sia come collaboratore.

!!! info "Un viaggio alla volta"
    Non c'è ancora un interruttore per singolo viaggio. Se vuoi disattivare a livello globale, usa l'impostazione del profilo. Un'opzione per singolo viaggio è in roadmap.

## Consigli

!!! tip "Usa le previsioni per i bagagli"
    Abbina il promemoria meteo alla [checklist](checklist.md). Quando arriva l'email, apri la checklist e aggiungi (o spunta) voci come *ombrello*, *crema solare*, *giacca* in base alle previsioni.

!!! tip "Controlla il widget giornaliero durante il viaggio"
    Una volta iniziato il viaggio, il widget meteo per ogni giorno ti dà una visione rapida per pianificare attività all'aperto o spostarle se necessario.

## Domande frequenti

### Perché non ho ricevuto l'email?

Il promemoria viene saltato se:

- La data di inizio del viaggio non è esattamente a 3 giorni quando gira il task giornaliero
- Il promemoria è già stato inviato per questo viaggio
- Il meteo è disattivato sul tuo profilo
- L'indirizzo email non è verificato

### I collaboratori ricevono il promemoria?

Sì. Ogni collaboratore accettato con email verificata e preferenza **Mostra meteo** attiva riceve la stessa email dell'autore. L'autore appare nel campo `A`; i collaboratori vengono aggiunti in `Ccn` così gli indirizzi non vengono divulgati.

### Da dove vengono i dati delle previsioni?

Dal provider meteo configurato sul backend. L'accuratezza dipende dal provider e dalla distanza dalla destinazione — le previsioni a breve termine (1–3 giorni) sono generalmente affidabili, mentre quelle a lungo termine sono solo indicative.

## Email riepilogo giornaliero

Mentre il viaggio è **in corso**, ricevi un'**email di riepilogo giornaliera** per il giorno corrente con:

- Titolo del viaggio e intestazione "Giorno X di N"
- **Previsioni meteo** del giorno (max/min)
- **Eventi** programmati per oggi, in ordine cronologico
- **Alloggio**: avvisi di check-in / check-out
- **Trasferimenti principali** (arrivo il giorno 1, partenza l'ultimo giorno)
- Un link diretto al viaggio

L'email viene inviata **una volta al giorno** all'autore del viaggio e a ogni **collaboratore** accettato con email verificata. L'autore è nel campo `A`; i collaboratori vengono aggiunti in `Ccn`.

### Disattivazione

Apri il tuo **profilo** e disattiva **Email riepilogo giornaliero**. L'impostazione è per utente: smetti di ricevere il riepilogo per ogni viaggio in cui sei autore o collaboratore.

### Quando l'email non viene inviata

- Il viaggio non è in corso (stato `IN_PROGRESS` oppure `IMPENDING` il primo giorno)
- Il riepilogo è già stato inviato per la giornata (idempotente)
- L'indirizzo email non è verificato
- Hai disattivato **Email riepilogo giornaliero** nel profilo
