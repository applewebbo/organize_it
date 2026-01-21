# Giorni

I giorni sono le unità organizzative del tuo viaggio. Vengono generati automaticamente in base alle date di inizio e fine del viaggio e contengono tutti gli eventi pianificati per ogni giorno specifico.

## Cos'è un Giorno?

Un **Giorno** rappresenta un singolo giorno del calendario all'interno del tuo viaggio. Ogni giorno:

- Ha un **numero** (Giorno 1, Giorno 2, ecc.)
- Ha una **data specifica** (es. Venerdì, 14 marzo 2025)
- Contiene **eventi** (esperienze, pasti, trasferimenti)
- Può avere **un alloggio** (sistemazione)
- È **generato automaticamente** dalle date del viaggio

## Come Vengono Creati i Giorni

I giorni vengono creati e gestiti automaticamente dal sistema in base alle date del viaggio.

### Generazione Automatica

Quando crei un viaggio con:
- **Data Inizio**: 14 marzo 2025 (Venerdì)
- **Data Fine**: 16 marzo 2025 (Domenica)

Il sistema crea automaticamente:
- **Giorno 1**: Venerdì, 14 marzo 2025
- **Giorno 2**: Sabato, 15 marzo 2025
- **Giorno 3**: Domenica, 16 marzo 2025

!!! info "Non Puoi Creare Manualmente i Giorni"
    I giorni non possono essere creati, modificati o eliminati manualmente. Vengono sempre generati automaticamente dalle date di inizio e fine del viaggio.

### Aggiornare i Giorni

I giorni si aggiornano automaticamente quando:

#### Estendere il Viaggio
**Prima**: 3 giorni (14-16 Mar)
**Modifica**: Data fine al 18 Mar
**Risultato**: 2 nuovi giorni creati (Giorno 4, Giorno 5)

#### Accorciare il Viaggio
**Prima**: 5 giorni (14-18 Mar)
**Modifica**: Data fine al 16 Mar
**Risultato**: I giorni 4 e 5 vengono eliminati

!!! warning "Perdita di Dati"
    Quando i giorni vengono eliminati, tutti gli eventi su quei giorni diventano "non associati" e devono essere riassegnati o eliminati.

#### Cambiare la Data di Inizio
**Prima**: I giorni iniziano il 14 Mar
**Modifica**: Data inizio al 15 Mar
**Risultato**: Tutti i giorni si spostano in avanti, il Giorno 1 è ora il 15 Mar

## Struttura del Giorno

### Numero del Giorno

Ogni giorno ha un numero sequenziale che parte da 1:
- Giorno 1 = Primo giorno del viaggio
- Giorno 2 = Secondo giorno del viaggio
- Giorno 3 = Terzo giorno del viaggio
- ecc.

Il numero del giorno non cambia mai a meno che tu non modifichi le date del viaggio.

### Data del Giorno

Ogni giorno corrisponde a una data del calendario specifica:
- Il Giorno 1 potrebbe essere "Venerdì, 14 marzo 2025"
- Il Giorno 2 potrebbe essere "Sabato, 15 marzo 2025"

La data viene visualizzata insieme al numero del giorno per chiarezza.

### Eventi in un Giorno

Ogni giorno può contenere più eventi:

- **Esperienze**: Musei, tour, passeggiate, attrazioni
- **Pasti**: Colazione, pranzo, cena, spuntini
- **Trasferimenti**: Arrivo, partenza, spostamenti tra luoghi

Gli eventi vengono visualizzati in ordine cronologico in base al loro orario di inizio.

### Alloggio in un Giorno

Ogni giorno può avere **un alloggio (stay)** associato:

- Gli alloggi possono coprire più giorni consecutivi
- Lo stesso alloggio appare su tutti i giorni che copre
- Esempio: Un hotel di 3 notti dal Giorno 1 al Giorno 3 appare nei Giorni 1, 2 e 3

## Visualizzare i Giorni

### Dalla Panoramica Viaggio

La pagina dettaglio viaggio mostra tutti i giorni in ordine:

1. Intestazione giorno (numero + data)
2. Informazioni alloggio (se assegnato)
3. Tutti gli eventi per quel giorno
4. Pulsanti azione rapida (Aggiungi Esperienza, Aggiungi Pasto, ecc.)

### Vista Dettaglio Giorno

Clicca su un giorno per visualizzare:

- Timeline completa degli eventi
- Dettagli eventi con espandi/comprimi
- Avvisi sovrapposizione (se gli eventi sono in conflitto)
- Navigazione al giorno precedente/successivo
- Azioni rapide per aggiungere eventi

### Navigazione Giorno

Quando visualizzi un giorno, puoi:
- Cliccare **← Giorno Precedente** per tornare indietro
- Cliccare **Giorno Successivo →** per andare avanti
- Cliccare il titolo del viaggio per tornare alla panoramica viaggio

!!! tip "Navigazione con Tastiera"
    Usa i tasti freccia per navigare tra i giorni (se implementato in futuro)

## Eventi all'Interno dei Giorni

### Vista Timeline

Gli eventi vengono visualizzati in ordine cronologico:

```
Giorno 1 - Venerdì, 14 marzo 2025
─────────────────────────────────
Alloggio: Hotel Forum Roma (Check-in: 15:00)

08:00 - Volo per Roma (Arrivo)
12:00 - Treno per hotel (Trasferimento)
16:00 - Tour del Colosseo (Esperienza)
19:30 - Trattoria da Enzo (Pasto)
```

### Eventi Sovrapposti

Il sistema rileva quando gli eventi si sovrappongono nel tempo:

!!! warning "Conflitto di Orario"
    Esperienza alle 16:00-18:00 si sovrappone con Pasto alle 17:30

Rivedi e regola gli orari degli eventi per evitare conflitti.

### Eventi Non Associati

Gli eventi senza assegnazione a un giorno appaiono in una sezione speciale "Eventi Non Associati" in fondo alla pagina viaggio. Puoi:

1. Modificare l'evento
2. Assegnarlo a un giorno specifico
3. Salvare

## Gestire Eventi per Giorno

### Aggiungere Eventi a un Giorno

Dalla vista giorno o panoramica viaggio:

1. Trova il giorno a cui vuoi aggiungere
2. Clicca il pulsante "Aggiungi" appropriato:
   - **Aggiungi Esperienza** - per attività
   - **Aggiungi Pasto** - per ristoranti
   - **Aggiungi Trasferimento** - per trasporti
   - **Aggiungi Alloggio** - per sistemazioni

3. Compila i dettagli dell'evento
4. L'evento appartiene automaticamente a quel giorno

### Spostare Eventi tra Giorni

Per spostare un evento da un giorno a un altro:

1. Clicca sull'evento per aprire i dettagli
2. Clicca **Modifica**
3. Cambia il campo **Giorno** in un giorno diverso
4. Clicca **Salva**

L'evento ora appare nel nuovo giorno.

### Rimuovere Eventi da un Giorno

Per rimuovere un evento:

**Opzione 1: Elimina permanentemente**
1. Clicca sull'evento
2. Clicca **Elimina**
3. Conferma l'eliminazione

**Opzione 2: Dissocia (mantieni ma non assegnare)**
1. Modifica l'evento
2. Imposta il giorno su "Nessuno" o "Non Associato"
3. Salva

L'evento si sposta nella sezione "Eventi Non Associati".

## Opzioni di Visualizzazione Giorno

### Vista Compatta (Panoramica Viaggio)

Mostra:
- Numero e data del giorno
- Numero di eventi
- Nome alloggio (se presente)
- Pulsanti azione rapida

### Vista Espansa (Dettaglio Giorno)

Mostra:
- Timeline completa
- Tutti i dettagli eventi
- Orari e durate eventi
- Descrizioni e note eventi
- Avvisi sovrapposizione

## Best Practice

### Pianificare per Giorno

✅ **Fai**:
- Raggruppa eventi correlati insieme
- Lascia tempo cuscinetto tra eventi
- Considera il tempo di viaggio tra luoghi
- Controlla le sovrapposizioni di orario

❌ **Non fare**:
- Sovra-pianificare giorni con eventi consecutivi
- Dimenticare di considerare i pasti
- Ignorare il tempo di viaggio
- Saltare i periodi di riposo

### Pianificazione Realistica

Un giorno ben pianificato potrebbe apparire così:

```
Giorno 2 - Sabato
─────────────────
09:00 - Colazione in hotel
10:00 - Visita museo (2 ore)
13:00 - Pranzo (1.5 ore)
15:00 - Tour a piedi (2 ore)
18:00 - Tempo libero / riposo
20:00 - Prenotazione cena
```

Nota:
- ✅ Pasti inclusi
- ✅ Durate eventi ragionevoli
- ✅ Tempo cuscinetto tra eventi
- ✅ Tempo libero per spontaneità

### Gestire Alloggi Multi-Giorno

Quando un alloggio copre più giorni:

1. Imposta il giorno di inizio e fine dell'alloggio
2. L'alloggio appare su tutti i giorni coperti
3. L'orario di check-in viene mostrato il primo giorno
4. L'orario di check-out viene mostrato l'ultimo giorno

Esempio:
```
Giorno 1: Hotel ABC (Check-in: 15:00)
Giorno 2: Hotel ABC (in soggiorno)
Giorno 3: Hotel ABC (Check-out: 11:00)
```

## Statistiche Giorno

Ogni giorno può visualizzare:

- **Eventi totali**: Numero di attività pianificate
- **Orario primo evento**: Quando inizia il tuo giorno
- **Orario ultimo evento**: Quando finisce il tuo giorno
- **Tempo libero**: Spazi nel programma

!!! tip "Bilancia i Tuoi Giorni"
    Un buon mix di attività e tempo libero rende il viaggio più piacevole.

## Domande Frequenti

### Posso creare giorni personalizzati?

No, i giorni sono sempre generati automaticamente dalle date del viaggio. Se hai bisogno di un giorno extra, estendi la data di fine del viaggio.

### Cosa succede agli eventi quando elimino un giorno?

Gli eventi sui giorni eliminati diventano "non associati" e appaiono nella sezione Eventi Non Associati. Puoi riassegnarli ad altri giorni o eliminarli.

### Posso riordinare i giorni?

No, i giorni sono sempre in ordine cronologico in base alla data. Non puoi riordinarli manualmente.

### Un giorno può non avere eventi?

Sì, i giorni non richiedono eventi. Potresti avere giorni di riposo o giorni con piani spontanei.

### Posso rinominare i giorni?

No, i giorni sono nominati automaticamente "Giorno 1", "Giorno 2", ecc. Il sistema mostra sia il numero che la data del calendario.

### Posso aggiungere note a un giorno specifico?

Attualmente le note vengono aggiunte ai singoli eventi, non ai giorni stessi. Aggiungi una nota a un evento o alloggio per informazioni specifiche del giorno.

### Come vedo tutti gli eventi di oggi?

Quando visualizzi un viaggio durante le date del viaggio, il giorno corrente è evidenziato. Cliccaci sopra per vedere tutti gli eventi.

### Posso stampare l'itinerario di un giorno?

La stampa di giorno/viaggio è pianificata per una versione futura. Per ora puoi usare la funzione di stampa del browser nella pagina dettaglio giorno.

## Guide Correlate

- [Viaggi](trips.md) - Comprendere il contenitore viaggio
- [Alloggi](stays.md) - Aggiungere sistemazioni ai giorni
- [Esperienze](experiences.md) - Pianificare attività per ogni giorno
- [Pasti](meals.md) - Programmare pasti durante il giorno
- [Trasferimenti](transfers.md) - Gestire trasporti tra giorni

---

**Prossimo**: Scopri come [aggiungere alloggi ai tuoi giorni](stays.md)
