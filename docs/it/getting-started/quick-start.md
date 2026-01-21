# Guida Rapida

Inizia ad usare Organize It in 5 minuti!

## Cos'è Organize It?

Organize It è un'applicazione web progettata per aiutarti a pianificare e organizzare i tuoi viaggi. Che tu stia pianificando un weekend fuori porta o un'avventura di un mese, Organize It ti aiuta a tenere traccia di:

- **Alloggi** (Stays)
- **Attività** (Experiences)
- **Ristoranti** (Meals)
- **Trasporti** (Transfers)
- **Link e note importanti**

## Concetti Fondamentali

### Viaggi

Un **Viaggio** è il contenitore principale per i tuoi piani di viaggio. Ogni viaggio ha:

- Date di inizio e fine
- Un'immagine di copertina
- Una collezione di giorni (generati automaticamente dalle date)
- Eventi organizzati per giorno

### Giorni

I **Giorni** vengono creati automaticamente in base alle date del viaggio. Ogni giorno può contenere:

- Più eventi (esperienze, pasti, trasferimenti)
- Un alloggio (stay)

### Eventi

Gli **Eventi** sono le attività nel tuo itinerario. Ci sono quattro tipi:

1. **Stays** - Hotel, appartamenti, ostelli
2. **Experiences** - Musei, tour, passeggiate, attrazioni
3. **Meals** - Ristoranti, caffè, esperienze culinarie
4. **Transfers** - Voli, treni, noleggi auto, spostamenti tra luoghi

## Il Tuo Primo Viaggio in 5 Minuti

### Passo 1: Crea un Account

1. Vai su [http://localhost:8000](http://localhost:8000)
2. Clicca su **Registrati**
3. Inserisci email e password
4. Verifica la tua email (in sviluppo, controlla la console)
5. Effettua il login

### Passo 2: Crea il Tuo Primo Viaggio

1. Clicca su **Crea Nuovo Viaggio**
2. Compila i dettagli:
   - Nome viaggio (es. "Weekend a Roma")
   - Destinazione (es. "Roma, Italia")
   - Data inizio
   - Data fine
   - Opzionale: Aggiungi immagine di copertina o cerca su Unsplash
3. Clicca su **Salva**

I giorni verranno creati automaticamente per ogni data del viaggio!

### Passo 3: Aggiungi un Alloggio

1. Vai al tuo viaggio
2. Clicca su un giorno
3. Clicca su **Aggiungi Alloggio**
4. Inserisci i dettagli dell'alloggio:
   - Nome (es. "Hotel Colosseo")
   - Indirizzo
   - Orario check-in
   - Orario check-out
5. Clicca su **Salva**

!!! tip
    Gli alloggi possono coprire più giorni consecutivi. Basta impostare i giorni di inizio e fine!

### Passo 4: Aggiungi Attività

1. Clicca su **Aggiungi Esperienza**
2. Inserisci i dettagli:
   - Nome (es. "Visita al Colosseo")
   - Orario
   - Durata
   - Luogo
   - Note
3. Clicca su **Salva**

Ripeti per pasti e altre attività!

### Passo 5: Aggiungi Trasporti

1. Clicca su **Aggiungi Trasferimento**
2. Scegli il tipo di trasferimento:
   - **Arrivo** - Per raggiungere il primo alloggio
   - **Partenza** - Per lasciare l'ultimo alloggio
   - **Trasferimento tra Alloggi** - Spostamento tra sistemazioni
   - **Trasferimento Semplice** - Spostamento tra eventi
3. Compila i dettagli:
   - Mezzo di trasporto (volo, treno, auto, ecc.)
   - Orari di partenza e arrivo
   - Numero di conferma
4. Clicca su **Salva**

### Passo 6: Visualizza il Tuo Itinerario

Il tuo viaggio è ora organizzato! Puoi:

- Visualizzare tutti gli eventi in una timeline
- Vedere gli eventi organizzati per giorno
- Cliccare su qualsiasi evento per vedere i dettagli completi
- Modificare o eliminare eventi secondo necessità
- Contrassegnare i viaggi preferiti con una stella

## Cosa Fare Dopo?

Ora che hai configurato il tuo primo viaggio, esplora:

- [Tutorial Il Tuo Primo Viaggio](first-trip.md) - Una guida dettagliata passo-passo
- [Guida Utente](../user-guide/trips.md) - Documentazione approfondita
- [Domande Frequenti](../faq.md) - Domande comuni

## Suggerimenti e Trucchi

!!! tip "Usa Google Places"
    Abilita l'API Google Places per compilare automaticamente i dettagli di ristoranti e attrazioni

!!! tip "Integrazione Unsplash"
    Cerca su Unsplash immagini di copertina bellissime direttamente dal modulo viaggio

!!! tip "Stati del Viaggio"
    I viaggi aggiornano automaticamente il loro stato in base alle date:
    - **Non Iniziato** - Viaggi futuri
    - **Imminente** - In partenza entro 30 giorni
    - **In Corso** - Attualmente in svolgimento
    - **Completato** - Viaggi passati
    - **Archiviato** - Archiviati manualmente

!!! tip "Eventi Non Associati"
    Puoi creare eventi senza assegnarli a un giorno. Appariranno nella sezione "Eventi Non Associati" e potranno essere assegnati in seguito.

## Serve Aiuto?

- Consulta le [Domande Frequenti](../faq.md) per domande comuni
- Leggi la [Guida Utente](../user-guide/trips.md) dettagliata
- Segnala problemi su [GitHub](https://github.com/applewebbo/organize_it/issues)

Buona pianificazione! ✈️
