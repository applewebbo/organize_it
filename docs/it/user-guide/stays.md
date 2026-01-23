# Alloggi

Gli alloggi rappresentano le tue sistemazioni durante il viaggio - hotel, appartamenti, ostelli o qualsiasi luogo dove passerai la notte.

## Cos'è un Alloggio?

Un **Alloggio** è una sistemazione che copre uno o più giorni consecutivi nel tuo viaggio. Gli alloggi possono includere:

- Hotel
- Appartamenti/Airbnb
- Ostelli
- Pensioni
- Affitti per vacanze
- Case di amici o familiari

## Creare un Alloggio

### Dalla Vista Giorno

1. Vai al giorno in cui inizia l'alloggio
2. Clicca **Aggiungi Alloggio**
3. Compila i dettagli dell'alloggio
4. Clicca **Salva**

### Dalla Panoramica Viaggio

1. Trova la sezione del giorno
2. Clicca **Aggiungi Alloggio** nella card di quel giorno
3. Compila i dettagli
4. Salva

![Form Alloggio](../../assets/screenshots/stay-form.png)
*Il form di creazione alloggio*

## Campi Alloggio

### Campi Obbligatori

**Nome**
- Il nome della sistemazione
- Esempio: "Hotel Forum Roma", "Appartamento di Sara", "Hilton Downtown"
- Massimo 100 caratteri

**Indirizzo**
- Indirizzo completo
- Esempio: "Via Tor de' Conti, 25, 00184 Roma, Italia"
- Utilizzato per geocodifica e visualizzazione mappa
- Massimo 200 caratteri

**Giorno Inizio**
- Il primo giorno del tuo alloggio
- Esempio: Giorno 1

**Giorno Fine**
- L'ultimo giorno del tuo alloggio
- Deve essere uguale o successivo al giorno di inizio
- Esempio: Giorno 3

### Campi Opzionali

**Orario Check-in**
- Quando puoi accedere alla sistemazione
- Esempio: 15:00, 14:00
- Visualizzato solo il primo giorno

**Orario Check-out**
- Quando devi lasciare la sistemazione
- Esempio: 11:00, 12:00
- Visualizzato solo l'ultimo giorno

**Città**
- Nome della città
- Compilato automaticamente durante la geocodifica
- Massimo 100 caratteri

**Numero di Telefono**
- Numero di contatto per la sistemazione
- Esempio: "+39 06 1234 5678"
- Può essere compilato automaticamente tramite arricchimento Google Places
- Massimo 50 caratteri

**Sito Web**
- URL del sito web della sistemazione
- Esempio: "https://www.hotelforum.com"
- Può essere compilato automaticamente tramite arricchimento Google Places

**Data Cancellazione**
- Ultima data per cancellazione gratuita
- Promemoria utile per flessibilità prenotazione
- Esempio: 1 marzo 2025

**Numero Conferma**
- Riferimento prenotazione o codice conferma
- Esempio: "HTL123456", "ABC-2025-0314"

**Note**
- Informazioni aggiuntive
- Esempio: "Colazione gratuita inclusa. Piscina al 5° piano. Check-out posticipato concordato."
- Massimo 500 caratteri

## Alloggi Multi-Giorno

Gli alloggi possono coprire più giorni consecutivi, il che è tipico per la maggior parte delle sistemazioni.

### Come Funzionano gli Alloggi Multi-Giorno

Quando crei un alloggio dal Giorno 1 al Giorno 3:
- L'alloggio appare nei Giorni 1, 2 e 3
- L'orario di check-in viene mostrato il Giorno 1
- L'orario di check-out viene mostrato il Giorno 3
- Lo stesso oggetto alloggio è collegato a tutti i giorni coperti

### Esempio

```
Viaggio: Weekend Roma (14-16 Mar)

Giorno 1 - Venerdì, 14 Mar
├─ Alloggio: Hotel Forum Roma
│  └─ Check-in: 15:00

Giorno 2 - Sabato, 15 Mar
├─ Alloggio: Hotel Forum Roma

Giorno 3 - Domenica, 16 Mar
├─ Alloggio: Hotel Forum Roma
   └─ Check-out: 11:00
```

### Modificare la Durata dell'Alloggio

Per estendere o accorciare un alloggio:

1. Modifica l'alloggio
2. Cambia il campo **Giorno Fine**
3. Salva

L'alloggio apparirà automaticamente (o verrà rimosso) dai giorni interessati.

## Più Alloggi in Un Viaggio

Se ti sposti tra diverse sistemazioni durante il viaggio, crea alloggi separati:

### Esempio: Due Hotel

```
Giorno 1-2: Hotel a Roma
Giorno 3-4: Hotel a Firenze
Giorno 5: Hotel a Venezia
```

Ogni alloggio:
1. Ha le proprie date
2. Ha la propria posizione
3. Viene mostrato nei giorni appropriati
4. Ha orari di check-in/out separati

!!! tip "Pianifica Check-out e Check-in"
    Lascia tempo sufficiente tra il check-out da un alloggio e il check-in al successivo. Aggiungi un trasferimento tra di essi se necessario.

## Posizione e Mappe

### Geocodifica

Quando inserisci un indirizzo, Organize It automaticamente:

1. Converte l'indirizzo in coordinate (latitudine/longitudine)
2. Determina la città
3. Valida la posizione

Questo abilita:
- Visualizzazione mappa
- Calcoli distanza
- Funzionalità basate sulla posizione

### Visualizzazione su Mappa

Gli alloggi vengono visualizzati sulle mappe in:
- Vista dettaglio giorno
- Mappa panoramica viaggio (se implementata)
- Timeline eventi con marcatori posizione

!!! info "Precisione Geocodifica"
    Per risultati ottimali, usa indirizzi completi con nome via, numero civico, codice postale e paese.

## Arricchimento Google Places

Organize It può compilare automaticamente i dettagli dell'alloggio usando l'API Google Places.

### Cos'è l'Arricchimento?

L'arricchimento recupera automaticamente:
- URL sito web ufficiale
- Numero di telefono
- Orari di apertura (se applicabile)
- Dati aggiuntivi del luogo

### Come Arricchire un Alloggio

1. Crea o modifica un alloggio con un indirizzo valido
2. Clicca il pulsante **Arricchisci**
3. Il sistema cerca su Google Places l'indirizzo
4. Seleziona il risultato corretto
5. I dettagli vengono compilati automaticamente

!!! note "Chiave API Richiesta"
    L'arricchimento Google Places richiede una chiave API configurata. Controlla con l'amministratore se questa funzionalità non è disponibile.

### Campi Dati Arricchiti

Dopo l'arricchimento:
- ✅ `place_id` - Identificatore Google Places
- ✅ `website` - Sito web ufficiale
- ✅ `phone_number` - Numero di contatto
- ✅ `opening_hours` - Orari reception (se disponibile)
- ✅ flag `enriched` impostato a true

## Gestire gli Alloggi

### Modificare un Alloggio

1. Clicca sulla card alloggio
2. Clicca **Modifica**
3. Modifica qualsiasi campo
4. Clicca **Salva**

Le modifiche si applicano a tutti i giorni coperti dall'alloggio.

### Eliminare un Alloggio

1. Clicca sulla card alloggio
2. Clicca **Elimina**
3. Conferma eliminazione

!!! warning "Impatto Eliminazione"
    Eliminare un alloggio lo rimuove da tutti i giorni a cui era assegnato. Questa azione non può essere annullata.

### Spostare un Alloggio in Giorni Diversi

1. Modifica l'alloggio
2. Cambia **Giorno Inizio** e/o **Giorno Fine**
3. Salva

L'alloggio si sposterà al nuovo intervallo di giorni.

## Best Practice

### Informazioni Prenotazione

✅ **Includi**:
- Numeri di conferma
- Date di cancellazione
- Richieste speciali (check-in anticipato, check-out posticipato)
- Note importanti (parcheggio, colazione, servizi)

### Indirizzi Completi

✅ **Indirizzo corretto**:
```
Via Tor de' Conti, 25
00184 Roma, Italia
```

❌ **Indirizzo incompleto**:
```
Hotel Forum Roma
```

Gli indirizzi completi consentono una corretta geocodifica e visualizzazione mappa.

### Orari Check-in/out

- Includi sempre gli orari di check-in e check-out
- Imposta promemoria se hai bisogno di check-in anticipato o check-out posticipato
- Annota gli orari standard nel campo Note
- Esempio nota: "Check-in standard 15:00, richiesto check-in anticipato alle 12:00"

### Usare le Note in Modo Efficace

Le note utili includono:
- Istruzioni parcheggio
- Password WiFi (se conosciute in anticipo)
- Servizi (piscina, palestra, colazione)
- Accordi speciali
- Nome persona di contatto
- Numeri telefono di riserva

Esempio:
```
Parcheggio gratuito nel parcheggio posteriore. WiFi: hotelguest / password123.
Piscina aperta 7am-10pm. Buffet colazione 7-10am incluso.
Contatto: Marco (reception) +39 123 456 7890
```

## Visualizzazione Alloggio

### Sulle Card Giorno

Mostra:
- Nome alloggio
- Orario check-in (solo primo giorno)
- Orario check-out (solo ultimo giorno)
- Indicatore "In soggiorno" (giorni intermedi)

### Sulla Pagina Dettaglio Giorno

Mostra:
- Informazioni complete alloggio
- Indirizzo con mappa
- Orari check-in/out
- Tutte le note e dettagli
- Azioni modifica/elimina

### Sulle Mappe

Mostra:
- Marcatore pin nella posizione alloggio
- Nome alloggio al passaggio mouse
- Clicca per visualizzare dettagli completi

## Domande Frequenti

### Posso avere più alloggi nello stesso giorno?

No, ogni giorno può avere solo un alloggio. Se stai cambiando sistemazione a metà giornata, assegna un alloggio a quel giorno e l'altro al giorno successivo. Usa un trasferimento per rappresentare lo spostamento.

### Cosa succede se elimino un giorno che ha un alloggio?

Se accorci un viaggio ed elimini giorni, l'alloggio verrà adattato:
- Se vengono eliminati solo giorni intermedi: L'alloggio diventa non consecutivo (non raccomandato, modifica manualmente)
- Se viene eliminato l'ultimo giorno: La data fine alloggio si sposta al nuovo ultimo giorno
- Se vengono eliminati tutti i giorni: L'alloggio viene rimosso

### Posso creare un alloggio che non appartiene ad alcun giorno?

No, gli alloggi devono sempre essere assegnati ad almeno un giorno (giorno inizio e giorno fine).

### Come gestisco check-in e check-out nello stesso giorno?

Imposta sia **Giorno Inizio** che **Giorno Fine** allo stesso giorno. Questo rappresenta un soggiorno di una notte dove fai check-in e check-out nello stesso giorno di calendario (es. Giorno 3).

### Posso aggiungere più posizioni per un alloggio?

No, ogni alloggio ha un indirizzo. Se hai prenotazioni multiple in strutture diverse, crea voci alloggio separate.

### Perché il mio indirizzo non viene geocodificato correttamente?

Prova:
- Aggiungere più dettagli (numero civico, codice postale, paese)
- Usare il formato indirizzo ufficiale da Google Maps
- Controllare errori di battitura
- Usare traslitterazioni inglesi per indirizzi non latini

### Posso allegare documenti a un alloggio?

Attualmente gli allegati documenti non sono supportati. Puoi:
- Aggiungere link alle email di conferma (tramite Link Viaggio)
- Aggiungere numeri di conferma nel campo
- Aggiungere URL file nelle note

## Guide Correlate

- [Giorni](days.md) - Comprendere l'organizzazione giorni
- [Viaggi](trips.md) - Gestire viaggi
- [Trasferimenti](transfers.md) - Spostarsi tra alloggi
- [Esperienze](experiences.md) - Attività vicino al tuo alloggio

---

**Prossimo**: Scopri come [aggiungere esperienze ai tuoi giorni](experiences.md)
