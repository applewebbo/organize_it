# Previsioni Meteo e Promemoria

Organize It mostra le previsioni meteo per il tuo viaggio e ti invia un'email di promemoria qualche giorno prima della partenza, così puoi preparare i bagagli di conseguenza.

## Widget meteo sul viaggio

Quando il tuo viaggio diventa **Imminente** (data di inizio entro 7 giorni) o **In Corso**, appare un widget meteo nella pagina di dettaglio del viaggio e su ogni card giornaliera. Mostra:

- **Temperature massime/minime giornaliere** in °C
- **Icona delle condizioni meteo** (sole, nuvole, pioggia, neve, ecc.)
- **Previsione giorno per giorno** per i giorni a venire del viaggio

Le previsioni vengono recuperate periodicamente in background, così sono fresche senza rallentare la pagina.

## Email di promemoria meteo

Tre giorni prima della partenza, l'autore del viaggio riceve un'email automatica con il **riepilogo delle previsioni** per il viaggio.

### Quando viene inviata

- **3 giorni** prima della data di inizio del viaggio
- Solo **una volta** per viaggio (un flag viene memorizzato dopo l'invio)
- Solo se l'autore ha le funzioni meteo abilitate sul profilo

### Cosa contiene

- Titolo e date del viaggio
- Previsioni giorno per giorno con temperature massime/minime e condizioni
- Un link diretto al viaggio

L'email è localizzata: italiano per gli utenti che hanno l'italiano come lingua dell'account, inglese altrimenti. Le temperature sono sempre in °C.

### Disattivare il promemoria

Il promemoria è legato alla preferenza **Mostra meteo** del profilo. Disattiva questa opzione per smettere di ricevere email meteo per tutti i tuoi viaggi.

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

No, solo l'**autore** del viaggio lo riceve.

### Da dove vengono i dati delle previsioni?

Dal provider meteo configurato sul backend. L'accuratezza dipende dal provider e dalla distanza dalla destinazione — le previsioni a breve termine (1–3 giorni) sono generalmente affidabili, mentre quelle a lungo termine sono solo indicative.
