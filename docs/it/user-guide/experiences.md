# Esperienze

Le esperienze sono attività, attrazioni e cose che pianifichi di fare durante il viaggio. Rappresentano i momenti memorabili che rendono speciale il tuo viaggio.

## Cos'è un'Esperienza?

Un'**Esperienza** è qualsiasi attività pianificata durante il viaggio, come:

- Visite a musei
- Tour e passeggiate guidate
- Visite a parchi
- Attività all'aperto
- Sport e ricreazione
- Spettacoli e performance
- Shopping
- Qualsiasi altra attrazione o attività

## Creare un'Esperienza

### Dalla Vista Giorno

1. Vai a un giorno specifico
2. Clicca **Aggiungi Esperienza**
3. Compila i dettagli dell'esperienza
4. Clicca **Salva**

### Dalla Panoramica Viaggio

1. Trova la sezione del giorno
2. Clicca **Aggiungi Esperienza**
3. Completa il modulo
4. Salva

## Campi Esperienza

### Campi Obbligatori

**Nome**
- Il nome dell'attività o attrazione
- Esempio: "Tour del Colosseo", "Museo del Louvre", "Crociera sulla Senna"
- Massimo 100 caratteri

**Orario Inizio**
- Quando inizia l'esperienza
- Esempio: 09:30, 14:00, 16:30
- Utilizzato per ordinamento timeline e rilevamento sovrapposizioni

**Orario Fine**
- Quando termina l'esperienza
- Deve essere successivo all'orario di inizio
- Esempio: 11:30, 16:00, 18:30
- La durata viene calcolata automaticamente

**Tipo Esperienza**
- Categoria dell'esperienza
- Opzioni:
  - **Museum** - Musei, gallerie, mostre
  - **Park** - Parchi, giardini, spazi all'aperto
  - **Walk** - Tour a piedi, passeggiate auto-guidate
  - **Sport** - Attività sportive, avventure all'aperto
  - **Other** - Tutto il resto

### Campi Opzionali

**Indirizzo**
- Posizione dell'esperienza
- Esempio: "Piazza del Colosseo, 1, 00184 Roma, Italia"
- Utilizzato per geocodifica e visualizzazione mappa
- Massimo 200 caratteri

**Città**
- Nome città
- Compilato automaticamente durante geocodifica
- Massimo 100 caratteri

**Note**
- Informazioni aggiuntive
- Esempio: "Biglietto salta-fila. Punto di incontro: ingresso principale. Porta documento per sconto studenti."
- Massimo 500 caratteri

**Numero Conferma**
- Riferimento prenotazione
- Esempio: "TOUR123456", "COL202503141600"

**Prezzo**
- Costo dell'esperienza (se applicabile)
- Esempio: "25€", "$50", "Gratuito con pass città"

**Giorno**
- In quale giorno avviene questa esperienza
- Può essere lasciato vuoto per creare un'esperienza "non associata"

## Tipi di Esperienza

### Museum
- Gallerie d'arte
- Musei di storia
- Centri scientifici
- Mostre
- Siti culturali

**Esempi**:
- "Musei Vaticani e Cappella Sistina"
- "British Museum"
- "MoMA - Mostra Arte Moderna"

### Park
- Parchi nazionali
- Parchi cittadini
- Giardini botanici
- Riserve naturali
- Punti panoramici all'aperto

**Esempi**:
- "Picnic a Central Park"
- "Giardini di Villa Borghese"
- "Sentiero Escursionistico Yosemite"

### Walk
- Tour a piedi (guidati o auto-guidati)
- Passeggiate storiche
- Tour architettonici
- Esplorazioni di quartiere

**Esempi**:
- "Passeggiata Fontana di Trevi e Piazza di Spagna"
- "Free Walking Tour - Centro Storico"
- "Tour Street Art - Brooklyn"

### Sport
- Escursionismo
- Ciclismo
- Sport acquatici
- Sci/snowboard
- Attività avventurose

**Esempi**:
- "Tour Mountain Bike"
- "Gita Snorkeling"
- "Beach Volley"

### Other
- Shopping
- Spettacoli/performance
- Corsi/workshop
- Spa/benessere
- Tutto ciò che non rientra nelle altre categorie

**Esempi**:
- "Opera alla Scala"
- "Corso di Cucina - Pasta Tradizionale"
- "Shopping al Souk"

## Gestione del Tempo

### Calcolo Durata

La durata viene calcolata automaticamente dagli orari di inizio e fine:

```
Orario Inizio: 14:00
Orario Fine: 16:30
Durata: 2 ore 30 minuti
```

### Sovrapposizioni Orarie

Il sistema rileva quando le esperienze si sovrappongono con altri eventi:

!!! warning "Sovrapposizione Rilevata"
    Esperienza alle 16:00-18:00 si sovrappone con Pasto alle 17:30

**Sovrapposizioni comuni**:
- Esperienza sconfina nella prenotazione pasto
- Esperienze consecutive senza tempo di viaggio
- Esperienza in conflitto con orari trasferimento

**Soluzioni**:
- Regola orari inizio/fine
- Riordina eventi
- Dividi esperienze lunghe in più sessioni
- Lascia tempo cuscinetto tra eventi

### Pianificare Durate Realistiche

✅ **Buone pratiche**:
- Visita museo: 2-3 ore
- Tour a piedi: 2-4 ore
- Visita parco: 1-2 ore
- Shopping veloce: 1 ora
- Spettacolo/performance: Durata effettiva + 30 min cuscinetto

❌ **Troppo ottimistico**:
- Museo importante: 30 minuti (troppo breve)
- Tour a piedi: 6 ore senza pause
- Consecutivi senza tempo di viaggio

## Posizione e Mappe

### Geocodifica

Inserisci un indirizzo completo per abilitare:
- Visualizzazione pin sulla mappa
- Calcoli distanza
- Raggruppamento eventi vicini
- Stime tempo di viaggio

**Formato indirizzo migliore**:
```
Piazza del Colosseo, 1
00184 Roma, Italia
```

### Visualizzazione su Mappa

Le esperienze appaiono su:
- Mappe timeline giorno
- Mappe panoramica viaggio
- Clustering posizioni (più eventi nella stessa area)

!!! tip "Raggruppa Esperienze Vicine"
    Pianifica esperienze nello stesso quartiere insieme per minimizzare tempo di viaggio.

## Arricchimento Google Places

Compila automaticamente dettagli esperienza usando Google Places.

### Come Arricchire

1. Crea un'esperienza con un indirizzo valido
2. Clicca pulsante **Arricchisci**
3. Il sistema cerca su Google Places
4. Seleziona il risultato corretto
5. I dettagli si compilano automaticamente:
   - Sito web ufficiale
   - Numero di telefono
   - Orari di apertura
   - Place ID

### Quando Usare l'Arricchimento

✅ **Utile per**:
- Attrazioni popolari con listing Google
- Musei con siti web ufficiali
- Attività verificate
- Luoghi con orari specifici

❌ **Non utile per**:
- Passeggiate auto-guidate
- Attività all'aperto generiche
- Eventi senza posizioni fisse
- Luoghi non listati

## Gestire le Esperienze

### Modificare un'Esperienza

1. Clicca sulla card esperienza
2. Clicca **Modifica**
3. Modifica qualsiasi campo
4. Clicca **Salva**

### Eliminare un'Esperienza

1. Clicca sulla card esperienza
2. Clicca **Elimina**
3. Conferma eliminazione

!!! warning
    L'eliminazione è permanente e non può essere annullata.

### Spostare in Un Altro Giorno

1. Modifica l'esperienza
2. Cambia il campo **Giorno**
3. Salva

L'esperienza si sposta nel giorno selezionato.

### Creare Esperienze Non Associate

A volte vuoi pianificare attività senza assegnarle a un giorno specifico:

1. Crea un'esperienza
2. Lascia il campo **Giorno** vuoto o imposta su "Nessuno"
3. Salva

L'esperienza appare nella sezione "Eventi Non Associati". Assegnala a un giorno più tardi quando finalizzi il programma.

## Best Practice

### Ricerca e Pianificazione

✅ **Prima di aggiungere**:
- Controlla orari di apertura
- Verifica se serve prenotazione
- Leggi recensioni
- Controlla posizione su mappa
- Conferma prezzi di ammissione

### Aggiungere Informazioni Complete

**Buon esempio**:
```
Nome: Tour Colosseo e Foro Romano
Tipo: Museum
Orario: 09:00 - 12:30
Indirizzo: Piazza del Colosseo, 1, 00184 Roma, Italia
Note: Biglietto combinato salta-fila. Punto incontro: ingresso principale.
       Include audioguida. Indossa scarpe comode. Porta acqua.
Conferma: COL-TOUR-2025-0314
```

**Esempio incompleto** (più difficile da usare):
```
Nome: Colosseo
Tipo: Museum
Orario: 09:00 - 10:00
```

### Usare le Note in Modo Efficace

Ottime note includono:
- Dettagli punto di incontro
- Cosa portare
- Istruzioni speciali
- Informazioni accessibilità
- Codice abbigliamento
- Sconti studenti/anziani
- Politica cancellazione

**Esempio**:
```
Punto incontro: Cancello principale, cerca guida con ombrello rosso.
Porta: Passaporto per sconto studenti, borraccia, crema solare.
Nota: Prima domenica del mese ingresso gratuito ma molto affollato.
Alternativa: Prenota giovedì sera per meno folla.
```

### Bilanciare il Tuo Giorno

Non sovra-pianificare:

❌ **Troppo pieno**:
```
08:00-10:00 Museo A
10:30-12:30 Museo B
13:00-15:00 Museo C
15:30-17:30 Museo D
18:00-20:00 Museo E
```

✅ **Ben bilanciato**:
```
09:00-12:00 Museo A (attrazione principale)
12:00-13:30 Pausa pranzo
14:00-16:00 Tour a piedi
16:00-17:00 Tempo libero / caffè
19:00 Cena
```

## Scenari Speciali

### Esperienze Giornata Intera

Per attività giornata intera:
- Imposta orario inizio: 09:00
- Imposta orario fine: 18:00
- Nota: "Tour giornata intera con pranzo incluso"

### Esperienze Multi-Parte

Se un'esperienza ha più sessioni:

**Opzione 1**: Crea un'esperienza lunga
```
Nome: Tour Città Guidato (Mattina e Pomeriggio)
Orario: 09:00 - 17:00
Note: Pausa pranzo 12:00-13:00 (non incluso)
```

**Opzione 2**: Crea esperienze separate
```
Esperienza 1: Tour Città - Sessione Mattina (09:00-12:00)
Esperienza 2: Tour Città - Sessione Pomeriggio (13:00-17:00)
```

### Attività Dipendenti dal Meteo

Aggiungi note di contingenza:
```
Note: Attività all'aperto. Controlla previsioni meteo.
       Backup: Visita museo se piove (vedi Eventi Non Associati)
```

### Orari Flessibili

Per esperienze senza orari rigidi:
```
Nome: Esplora Quartiere Montmartre
Orario: 14:00 - 17:00 (approssimativo)
Note: Esplorazione auto-guidata. Nessun programma fisso.
       Visita Sacré-Cœur prima delle 18:00.
```

## Domande Frequenti

### Posso avere più esperienze nello stesso orario?

Sì, ma il sistema ti avviserà delle sovrapposizioni orarie. Potrebbe essere intenzionale (gruppo che si divide) o un errore (necessità di riprogrammare).

### Come marco un'esperienza come completata?

Attualmente non c'è uno stato "completato". Questa funzionalità è pianificata per versioni future.

### Posso aggiungere foto a un'esperienza?

Gli allegati foto per eventi sono pianificati per una versione futura.

### Posso duplicare un'esperienza?

Non c'è ancora una funzione di duplicazione integrata. Dovrai creare una nuova esperienza manualmente.

### Posso impostare esperienze ricorrenti?

No, ogni esperienza deve essere creata individualmente. Se hai attività giornaliere (es. corsa mattutina), creane una per ogni giorno.

### Come gestisco le prenotazioni?

Aggiungi dettagli prenotazione in:
- Campo Numero Conferma
- Campo Note (ora, email conferma, ecc.)
- Sezione Link (aggiungi URL prenotazione)

### E se non conosco ancora l'orario esatto?

Imposta orari approssimativi e aggiungi una nota:
```
Note: Orario TBD - confermerò 1 giorno prima
```

Aggiorna l'orario una volta confermato.

### Posso collegare esperienze insieme?

Non direttamente. Usa le note per riferimenti ad esperienze correlate:
```
Note: Parte 1 del tour Vaticano. Vedi anche "Cappella Sistina" (Giorno 2)
```

## Guide Correlate

- [Giorni](days.md) - Comprendere l'organizzazione giorni
- [Pasti](meals.md) - Aggiungere prenotazioni ristoranti
- [Trasferimenti](transfers.md) - Viaggiare tra esperienze
- [Viaggi](trips.md) - Gestione complessiva viaggio

---

**Prossimo**: Scopri come [aggiungere pasti al tuo itinerario](meals.md)
