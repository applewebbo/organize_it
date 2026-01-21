# Domande Frequenti (FAQ)

Domande e risposte comuni sull'uso di Organize It.

## Domande Generali

### Cos'è Organize It?

Organize It è un'applicazione web progettata per aiutarti a pianificare e organizzare viaggi. Ti permette di:

- Creare itinerari di viaggio dettagliati
- Gestire sistemazioni (alloggi)
- Pianificare attività e attrazioni (esperienze)
- Programmare prenotazioni ristoranti (pasti)
- Tracciare trasporti (trasferimenti)
- Mantenere tutte le informazioni del viaggio in un unico posto

### Organize It è gratuito?

Sì, Organize It è attualmente gratuito. Non ci sono abbonamenti o livelli premium.

### Cosa rende Organize It diverso da altri pianificatori di viaggio?

Organize It si concentra su:

- **Organizzazione giorno per giorno**: Gli eventi sono automaticamente organizzati per giorno
- **Aggiornamenti stato automatici**: Gli stati del viaggio si aggiornano in base alle date
- **Rilevamento conflitti orari**: Avvisa quando gli eventi si sovrappongono
- **Alloggi multi-giorno**: Le sistemazioni possono estendersi su più giorni
- **Assegnazione eventi flessibile**: Crea eventi prima di assegnarli a giorni specifici
- **UI bella**: Interfaccia pulita e moderna costruita con TailwindCSS

### Posso usare Organize It per viaggi di lavoro?

Sì! Organize It funziona per qualsiasi tipo di viaggio:

- Vacanze leisure
- Viaggi di lavoro
- Weekend
- Tour multi-città
- Viaggi on the road
- Conferenze ed eventi

### Quanti viaggi posso creare?

Non c'è limite al numero di viaggi che puoi creare.

### Posso usare Organize It offline?

Attualmente, Organize It richiede una connessione internet. Il supporto offline è pianificato per una versione futura.

## Domande Account

### Ho bisogno di un account per usare Organize It?

Sì, devi creare un account per usare Organize It. Questo assicura che i tuoi viaggi siano salvati in sicurezza.

### Come creo un account?

1. Clicca **Registrati**
2. Inserisci il tuo indirizzo email
3. Crea una password (minimo 8 caratteri)
4. Verifica la tua email
5. Accedi

### Supportate il login social (Google, Facebook)?

Attualmente, è supportata solo l'autenticazione email/password. Il login social potrebbe essere aggiunto in una versione futura.

### Non ho ricevuto l'email di verifica. Cosa devo fare?

Controlla:

- **Cartella Spam/Posta indesiderata**: Le email di verifica a volte vengono filtrate
- **Indirizzo email**: Assicurati di averlo digitato correttamente
- **Attendi qualche minuto**: La consegna email può essere ritardata

Se ancora mancante, prova:
- Richiedi una nuova email di verifica (se disponibile)
- Contatta il supporto per assistenza

### Posso cambiare il mio indirizzo email?

Il cambio indirizzo email non è attualmente supportato tramite UI. Contatta il supporto se devi cambiare la tua email.

### Posso cambiare la mia password?

Sì:

1. Accedi al tuo account
2. Vai a **Profilo** o **Impostazioni Account**
3. Clicca **Cambia Password**
4. Inserisci password attuale e nuova
5. Salva

### Come elimino il mio account?

L'eliminazione account non è attualmente disponibile tramite UI. Contatta il supporto per richiedere l'eliminazione account.

### I miei dati sono sicuri?

Sì. Organize It usa:

- Archiviazione password crittografata
- Connessioni HTTPS sicure
- Best practice di sicurezza Django
- Aggiornamenti di sicurezza regolari

## Domande Viaggi

### Come creo un viaggio?

1. Clicca **Crea Nuovo Viaggio** dalla homepage
2. Compila:
   - Nome viaggio
   - Destinazione
   - Date inizio e fine
   - Opzionale: Descrizione, immagine copertina
3. Clicca **Salva**

I giorni sono generati automaticamente in base alle tue date.

### Posso creare viaggi senza date specifiche?

No, le date inizio e fine sono obbligatorie. I giorni sono auto-generati da queste date, e il sistema di stato dipende da esse.

### Posso modificare un viaggio dopo averlo creato?

Sì:

1. Naviga al viaggio
2. Clicca **Modifica Viaggio**
3. Modifica qualsiasi campo
4. Salva

!!! info
    Cambiare le date rigenererà i giorni. Gli eventi saranno riassegnati al giorno corrispondente più vicino.

### Cosa succede se cambio le date del viaggio?

**Estendere il viaggio**: Vengono creati nuovi giorni.

**Accorciare il viaggio**: I giorni extra sono eliminati. Gli eventi sui giorni eliminati diventano "non associati."

**Cambiare data inizio**: Tutti i giorni si spostano. Gli eventi rimangono sullo stesso numero di giorno.

### Posso eliminare un viaggio?

Sì:

1. Vai alla pagina dettaglio viaggio
2. Clicca **Elimina Viaggio**
3. Conferma eliminazione

!!! danger
    Eliminare un viaggio rimuove permanentemente tutti i giorni, eventi e alloggi. Questo non può essere annullato.

### Come funzionano gli stati del viaggio?

Gli stati si aggiornano automaticamente in base alle date:

- **Non Iniziato**: La data di inizio è a più di 7 giorni
- **Imminente**: La data di inizio è entro 7 giorni
- **In Corso**: Tra date inizio e fine
- **Completato**: Dopo la data di fine
- **Archiviato**: Archiviato manualmente (rimane in questo stato)

### Come archivio un viaggio?

1. Naviga al viaggio
2. Clicca **Archivia**
3. Lo stato viaggio diventa "Archiviato"

I viaggi archiviati sono nascosti dalla lista viaggi principale. Usa il filtro per visualizzare viaggi archiviati.

### Posso condividere viaggi con altri?

La condivisione viaggi non è attualmente supportata ma è pianificata per una versione futura.

### Posso duplicare un viaggio?

La duplicazione viaggi non è attualmente supportata ma è pianificata per una versione futura.

### Posso esportare il mio viaggio?

L'esportazione viaggi (PDF, calendario ICS) è pianificata per una versione futura.

### Posso aggiungere co-viaggiatori a un viaggio?

La collaborazione multi-utente sui viaggi è pianificata per una versione futura.

### Come aggiungo un'immagine di copertina?

**Carica la tua**:
1. Modifica viaggio
2. Clicca **Carica Immagine**
3. Seleziona file immagine
4. Salva

**Usa Unsplash**:
1. Modifica viaggio
2. Clicca **Cerca Unsplash**
3. Cerca immagini
4. Seleziona un'immagine
5. Clicca **Usa Questa Foto**
6. Salva

### Quali formati immagine sono supportati?

Formati supportati: JPG, PNG, WebP

Dimensione massima file: 2MB

Aspect ratio raccomandato: 16:9 o 4:3 (orizzontale)

## Domande Eventi

### Cosa sono gli "eventi non associati"?

Gli eventi non associati sono eventi (esperienze, pasti, trasferimenti) che non sono stati assegnati a un giorno specifico.

**Usi**:
- Pianificare attività prima di finalizzare il programma
- Creare una wishlist di opzioni
- Memorizzare piani di riserva

**Assegnare a un giorno**:
1. Modifica l'evento
2. Seleziona un giorno
3. Salva

### Posso spostare un evento a un giorno diverso?

Sì:

1. Clicca sull'evento
2. Clicca **Modifica**
3. Cambia il campo **Giorno**
4. Salva

### Cosa succede quando gli eventi si sovrappongono?

Il sistema rileva conflitti orari e visualizza un avviso. Rivedi gli eventi sovrapposti e:

- Aggiusta gli orari
- Riordina eventi
- Rimuovi/elimina conflitti

### Posso creare eventi ricorrenti?

No, ogni evento deve essere creato individualmente. Gli eventi ricorrenti non sono attualmente supportati.

### Come elimino un evento?

1. Clicca sull'evento
2. Clicca **Elimina**
3. Conferma

!!! warning
    L'eliminazione è permanente.

### Posso aggiungere foto agli eventi?

Gli allegati foto agli eventi sono pianificati per una versione futura.

### Posso allegare file o documenti?

Gli allegati file diretti non sono attualmente supportati. Puoi:

- Aggiungere link a email di conferma (Link Viaggio)
- Memorizzare numeri conferma nei campi evento
- Aggiungere URL nelle note

### Posso contrassegnare eventi come completati?

Il tracciamento completamento eventi è pianificato per una versione futura.

### Come riordino gli eventi all'interno di un giorno?

Gli eventi sono automaticamente ordinati per ora inizio. Per riordinare:

1. Modifica orari evento
2. Aggiusta ora inizio alla posizione desiderata
3. Salva

### Posso scambiare orari evento?

Attualmente, devi modificare manualmente entrambi gli eventi per scambiare orari. Una funzione di scambio è pianificata per una versione futura.

## Domande Alloggi

### Posso avere più alloggi nello stesso giorno?

No, ogni giorno può avere solo un alloggio. Se stai cambiando sistemazione a metà giornata, assegna un alloggio a quel giorno e il prossimo alloggio al giorno seguente.

### Come funzionano gli alloggi multi-giorno?

Imposta **Giorno Inizio** e **Giorno Fine**. L'alloggio appare su tutti i giorni in quel range.

Esempio:
- Giorno Inizio: Giorno 1
- Giorno Fine: Giorno 3
- Risultato: L'alloggio appare sui Giorni 1, 2 e 3

### Posso cambiare la durata di un alloggio?

Sì:

1. Modifica l'alloggio
2. Cambia **Giorno Inizio** o **Giorno Fine**
3. Salva

L'alloggio si aggiorna automaticamente per apparire sui giorni corretti.

### Cos'è l'arricchimento Google Places?

L'arricchimento auto-compila i dettagli alloggio usando l'API Google Places:

- Sito web ufficiale
- Numero di telefono
- Orari di apertura
- Dati aggiuntivi

**Per arricchire**:
1. Crea/modifica alloggio con indirizzo valido
2. Clicca **Arricchisci**
3. Seleziona risultato corretto
4. I dati si auto-compilano

### Perché il mio indirizzo non viene geocodificato correttamente?

Prova:

- Aggiungere indirizzo completo (numero civico, codice postale, paese)
- Usare formato ufficiale da Google Maps
- Controllare errori di battitura
- Usare traslitterazioni inglesi per indirizzi non latini

## Domande Trasferimenti

### Quali sono i diversi tipi di trasferimenti?

1. **Trasferimenti Principali**: Arrivo e partenza (voli, treni da/verso destinazione)
2. **Trasferimenti tra Alloggi**: Spostamento tra sistemazioni
3. **Trasferimenti Semplici**: Spostamento tra eventi nello stesso giorno

### Devo aggiungere trasferimenti per ogni spostamento?

No. Aggiungi trasferimenti solo quando:

- Posizioni/quartieri diversi
- Pianificazione trasporto specifico necessaria
- Informazioni tempo/percorso importanti

Salta per:
- Stesso edificio
- Posizioni adiacenti
- Percorsi pedonali ovvi

### Come funziona l'integrazione Google Maps?

I trasferimenti semplici auto-generano URL Google Maps basati su:

- Indirizzi eventi
- Modalità trasporto selezionata

Clicca il link per aprire indicazioni in Google Maps.

### Posso tracciare viaggi multi-tratta?

**Opzione 1**: Un trasferimento con note dettagliate
```
Note: Viaggio multi-tratta:
      1. Roma → Firenze (treno, 2h)
      2. Sosta Firenze (1h)
      3. Firenze → Venezia (treno, 2h)
```

**Opzione 2**: Eventi separati per ogni tratta (se pernottamenti tra)

## Domande Tecniche

### Quali browser sono supportati?

Organize It funziona meglio su browser moderni:

✅ **Pienamente supportati**:
- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

⚠️ **Potrebbero avere problemi**:
- Internet Explorer (non supportato)
- Versioni browser più vecchie

### C'è un'app mobile?

Attualmente, non c'è un'app mobile nativa. Tuttavia, l'interfaccia web è mobile-responsive e funziona su smartphone e tablet.

Un'app mobile dedicata potrebbe essere sviluppata in futuro.

### Posso usare Organize It sul mio telefono?

Sì! L'interfaccia web è mobile-responsive:

1. Apri il tuo browser mobile
2. Naviga all'URL di Organize It
3. Accedi
4. Usa normalmente

**Suggerimento**: Aggiungi alla schermata home per esperienza tipo app:
- **iOS**: Safari → Condividi → Aggiungi a Home
- **Android**: Chrome → Menu → Aggiungi a Home

### Organize It funziona offline?

Attualmente, no. È richiesta una connessione internet.

Il supporto offline (funzionalità Progressive Web App) è pianificato per una versione futura.

### Cosa succede ai miei dati se il server va giù?

I tuoi dati sono archiviati in sicurezza in un database e backuppati regolarmente. Le interruzioni temporanee non influenzano i tuoi dati.

### Posso esportare i miei dati?

L'esportazione dati è pianificata per una versione futura. I formati di esportazione includeranno probabilmente:

- JSON (tutti i dati)
- PDF (itinerario stampabile)
- ICS (formato calendario)

### Come segnalo un bug?

Segnala bug su GitHub:

1. Visita [https://github.com/applewebbo/organize_it/issues](https://github.com/applewebbo/organize_it/issues)
2. Clicca **New Issue**
3. Descrivi il bug:
   - Cosa hai fatto
   - Cosa ti aspettavi
   - Cosa è effettivamente successo
   - Screenshot se rilevanti
4. Invia

### Come richiedo una funzionalità?

Richiedi funzionalità su GitHub Issues:

1. Visita [https://github.com/applewebbo/organize_it/issues](https://github.com/applewebbo/organize_it/issues)
2. Clicca **New Issue**
3. Descrivi la funzionalità:
   - Cosa vuoi fare
   - Perché sarebbe utile
   - Come immagini funzioni
4. Invia

### Organize It è open source?

Controlla il repository GitHub per informazioni sulla licenza: [https://github.com/applewebbo/organize_it](https://github.com/applewebbo/organize_it)

### Posso contribuire a Organize It?

I contributi sono benvenuti! Controlla il repository per:

- Linee guida contribuzione
- Istruzioni setup sviluppo
- Issue aperti su cui lavorare

## Domande Privacy & Dati

### Quali dati raccogliete?

Organize It raccoglie:

- **Dati account**: Email, password (crittografata)
- **Dati viaggio**: Tutte le informazioni viaggio, evento, alloggio che crei
- **Dati utilizzo**: Analitiche base (se abilitate)

### Condividete i miei dati con terze parti?

I tuoi dati viaggio sono privati e non condivisi con terze parti eccetto:

- **Mapbox**: Per geocodifica indirizzi (nessuna info personale)
- **Google Places**: Per arricchimento (nessuna info personale)
- **Unsplash**: Per download foto (requisiti attribuzione)

### Altri utenti possono vedere i miei viaggi?

No. I tuoi viaggi sono privati e visibili solo a te (fino all'implementazione funzionalità condivisione).

### Per quanto tempo conservate i miei dati?

I dati sono conservati finché il tuo account è attivo. Se elimini il tuo account, i dati sono rimossi permanentemente.

### Posso scaricare tutti i miei dati?

L'esportazione/download dati è pianificato per una versione futura.

## Risoluzione Problemi

### Non riesco ad accedere. Cosa devo fare?

Controlla:

1. **Email**: Assicurati indirizzo email corretto
2. **Password**: Verifica password (sensibile a maiuscole/minuscole)
3. **Caps Lock**: Assicurati Caps Lock sia spento
4. **Browser**: Prova un browser diverso
5. **Cookie**: Assicurati cookie siano abilitati

Se ancora impossibile accedere, usa "Password Dimenticata" per reimpostare.

### Gli eventi non appaiono sulla mappa

Possibili cause:

- **Nessun indirizzo**: L'evento deve avere un indirizzo valido
- **Geocodifica fallita**: L'indirizzo non può essere convertito in coordinate
- **Problema API**: Servizio Mapbox temporaneamente non disponibile

**Soluzione**:
- Aggiungi indirizzo completo con codice postale e paese
- Modifica e ri-salva l'evento
- Controlla formato indirizzo

### Non riesco a caricare un'immagine

Controlla:

- **Dimensione file**: Deve essere sotto 2MB
- **Formato file**: Deve essere JPG, PNG o WebP
- **Browser**: Prova un browser diverso
- **Connessione**: Assicurati internet stabile

**Soluzione**:
- Comprimi immagini grandi
- Converti in formato supportato
- Prova ricerca Unsplash invece

### La pagina non si carica

Prova:

1. Aggiorna la pagina (F5 o Cmd+R)
2. Pulisci cache browser
3. Prova modalità incognito/privata
4. Controlla connessione internet
5. Prova un browser diverso

Se il problema persiste, il server potrebbe essere temporaneamente giù. Riprova più tardi o segnala il problema su GitHub.

## Hai Ancora Domande?

Non trovi risposta alla tua domanda?

- **Controlla la Guida Utente**: Documentazione dettagliata per tutte le funzionalità
- **GitHub Issues**: Cerca issue esistenti o creane uno nuovo
- **Contatta Supporto**: Email supporto (se disponibile)

---

**Link Utili**:

- [Guida Primi Passi](getting-started/installation.md)
- [Guida Utente](user-guide/trips.md)
- [Repository GitHub](https://github.com/applewebbo/organize_it)
