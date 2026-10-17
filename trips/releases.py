"""Plain-language, per-release changelog shown on the public "Novità" page.

Newest first. Append one entry per release as part of the ``/release`` skill
workflow. Keep the notes non-technical Italian: 2-4 short bullet points a
non-developer would understand, one per user-visible change, condensed from
the GitHub release notes — not the raw commit list.
"""

from datetime import date

RELEASES: list[dict] = [
    {
        "version": "2026.12.1",
        "date": date(2026, 8, 7),
        "notes": [
            "La pianificazione dei giorni con l'AI non propone più pasti al ristorante se l'alloggio include colazione o pensione, mostrando chiaramente cosa è già compreso.",
            "Se non si scelge una foto di copertina durante la procedura guidata, ne viene selezionata una automaticamente, con un'indicazione che è stata scelta in automatico.",
            "Risolto un errore che poteva far perdere le date e le tappe inserite se la procedura guidata segnalava un errore di validazione.",
            "Corretto un problema che cancellava la data di cancellazione gratuita di un alloggio quando si salvava il modulo senza toccare quel campo.",
        ],
    },
    {
        "version": "2026.12",
        "date": date(2026, 8, 5),
        "notes": [
            "Novità: una nuova procedura guidata passo-passo per creare un viaggio da zero, con pianificazione automatica dei giorni tramite AI (opzionale) e ricerca dell'alloggio integrata.",
            "È possibile interrompere la procedura in qualsiasi momento e riprenderla in un secondo momento dalla homepage.",
        ],
    },
    {
        "version": "2026.11.2",
        "date": date(2026, 7, 28),
        "notes": [
            "La creazione di un alloggio parte ora, nei viaggi con più tappe, dalla scelta della tappa: città e date vengono già compilate, lasciando solo nome e indirizzo da inserire.",
            'Migliorata la disposizione della finestra "Trova un alloggio", più ordinata su computer e smartphone.',
            "Uniformato in tutto il sito il pulsante per chiudere le finestre popup.",
        ],
    },
    {
        "version": "2026.11.1",
        "date": date(2026, 7, 28),
        "notes": [
            "Risolto un errore che impediva di eliminare un viaggio con spese già registrate.",
            'Corretta l\'etichetta italiana del pulsante "Condividi", che in alcuni casi mostrava per errore "Quota".',
            "Risolto un testo che compariva per errore sulla mappa degli appuntamenti quando non c'era connessione.",
        ],
    },
    {
        "version": "2026.11",
        "date": date(2026, 7, 27),
        "notes": [
            "Novità: ricerca di alloggi per ogni tappa del viaggio direttamente dal sito, con il numero di adulti e bambini indicati a determinare l'occupazione.",
            "Si può scegliere il portale di prenotazione preferito (Booking.com, Expedia, Airbnb e altri).",
            "I partecipanti nominati possono ora essere indicati come adulti o bambini, con l'età per i più piccoli.",
        ],
    },
    {
        "version": "2026.10.4",
        "date": date(2026, 7, 25),
        "notes": [
            'Rimosso un link "Password dimenticata" duplicato nella pagina di accesso.',
            "Aggiornata la guida con un nuovo screenshot della pagina di accesso con il pulsante Google.",
        ],
    },
    {
        "version": "2026.10.3",
        "date": date(2026, 7, 24),
        "notes": [
            "Lavori interni di manutenzione all'infrastruttura del progetto, senza impatti visibili per chi usa il sito.",
            "Aggiornata la documentazione online del progetto.",
        ],
    },
    {
        "version": "2026.10.2",
        "date": date(2026, 7, 23),
        "notes": [
            "Novità: accesso con account Google, oltre a email e password.",
            "Controlli automatici aggiuntivi prima di ogni nuovo rilascio, per individuare link rotti prima che raggiungano il sito pubblico.",
        ],
    },
    {
        "version": "2026.10.1",
        "date": date(2026, 7, 21),
        "notes": [
            "I suggerimenti AI per l'itinerario giornaliero raggruppano ora le tappe in un'unica zona, per spostamenti più brevi e sensati.",
            "Migliorata la qualità dei suggerimenti AI, con maggiore attenzione a orari di apertura e vicinanza alla destinazione.",
            "Corrette alcune traduzioni italiane incomplete.",
        ],
    },
    {
        "version": "2026.10",
        "date": date(2026, 7, 20),
        "notes": [
            "Novità: tracciamento delle spese condivise del viaggio (appuntamenti, alloggi, trasferimenti), con divisione tra partecipanti e nuclei familiari e saldi calcolati automaticamente.",
            "Novità: generazione automatica via AI dell'itinerario di un intero giorno, con possibilità di rivedere e accettare le singole proposte prima di applicarle.",
            "Il sito si può ora installare come app e consultare viaggi e giorni anche senza connessione a internet.",
        ],
    },
    {
        "version": "2026.9.2",
        "date": date(2026, 7, 12),
        "notes": [
            "Aggiunto un limite giornaliero all'uso dei suggerimenti AI con chiave condivisa, per evitare che un collaboratore esaurisca la quota dell'organizzatore.",
            "Lavori interni di riorganizzazione del codice, senza impatti visibili per chi usa il sito.",
        ],
    },
    {
        "version": "2026.9.1",
        "date": date(2026, 7, 12),
        "notes": [
            "La chiave AI personale si può ora condividere con i collaboratori del viaggio, così tutto il gruppo può generare suggerimenti senza bisogno di una chiave propria.",
            "Novità: si può rigenerare il link di sincronizzazione del calendario se condiviso per errore, invalidando subito quello precedente.",
        ],
    },
    {
        "version": "2026.9",
        "date": date(2026, 7, 5),
        "notes": [
            "Novità: suggerimenti di viaggio generati dall'intelligenza artificiale (esperienze, pasti, alloggi), usando una propria chiave API personale (Google Gemini o Mistral AI).",
            "I suggerimenti tengono conto del meteo e dei luoghi già presenti nel viaggio, e si possono generare anche solo per una tappa o una tipologia specifica.",
            "La funzione va attivata esplicitamente dalle impostazioni del profilo.",
            'Corretto un errore di geocodifica per cui città omonime (es. "Roma") potevano risolversi nel paese sbagliato.',
        ],
    },
    {
        "version": "2026.8.6",
        "date": date(2026, 6, 29),
        "notes": [
            "Rifiniture dell'aspetto delle schede e delle finestre su smartphone, per un'esperienza più compatta e ordinata.",
            "Aggiornamenti tecnici di manutenzione e di sicurezza.",
        ],
    },
    {
        "version": "2026.8.5",
        "date": date(2026, 6, 24),
        "notes": [
            "Ulteriori interventi tecnici hanno reso più veloci la homepage e l'elenco e il dettaglio dei viaggi.",
            'Corretta un\'etichetta del menu su smartphone, ora coerente con quella su computer ("Impostazioni").',
        ],
    },
    {
        "version": "2026.8.4",
        "date": date(2026, 6, 20),
        "notes": [
            "Numerose correzioni emerse dai test con gli utenti: date, badge troppo lunghi, link alle indicazioni stradali, promemoria via email e altri piccoli dettagli dell'interfaccia.",
            'Rimosso il banner "da definire" che compariva senza motivo su esperienze e pasti.',
        ],
    },
    {
        "version": "2026.8.3",
        "date": date(2026, 6, 12),
        "notes": [
            "Novità: durante il viaggio arriva ogni giorno una mail di riepilogo con meteo, appuntamenti e trasferimenti della giornata (disattivabile dal profilo).",
            "Le email del sito arrivano ora con un nome mittente più chiaro e riconoscibile.",
            "L'avviso meteo pre-partenza arriva ora anche a chi collabora al viaggio, non solo a chi lo ha creato.",
        ],
    },
    {
        "version": "2026.8.2",
        "date": date(2026, 6, 11),
        "notes": [
            "Novità: ogni viaggio ha ora un proprio collegamento per sincronizzare automaticamente le date con il calendario del telefono o del computer.",
            "Tre giorni prima della partenza arriva una mail con le previsioni del tempo della destinazione.",
            "Novità: si possono allegare documenti (PDF, foto) al viaggio, agli alloggi e agli appuntamenti, con anteprima e accesso riservato a chi partecipa.",
            "Il PDF del viaggio è stato ridisegnato per essere più chiaro e utile anche offline.",
        ],
    },
    {
        "version": "2026.8.1",
        "date": date(2026, 6, 6),
        "notes": [
            "Novità: lista di cose da fare prima della partenza (valigie, documenti...) con possibilità di ricevere un promemoria via email.",
            "L'anteprima della lista nel dettaglio del viaggio mostra ora tutte le voci, con segno di spunta verde per quelle completate.",
        ],
    },
    {
        "version": "2026.8",
        "date": date(2026, 6, 4),
        "notes": [
            "Novità: puoi esportare l'intero viaggio in PDF, con tutti gli appuntamenti, gli alloggi, i trasferimenti e le note.",
            "Le esperienze e i pasti si possono ora spostare da un giorno all'altro con un semplice trascinamento, o con un pulsante dedicato su smartphone.",
            "La mappa del viaggio è stata ridisegnata con una ricerca più chiara e un pannello dedicato agli appuntamenti.",
            "Per i trasferimenti in auto, se non si indicano gli orari, viene calcolata una stima automatica della durata.",
        ],
    },
    {
        "version": "2026.7.5",
        "date": date(2026, 5, 16),
        "notes": [
            "Risolto un problema che impediva di riconoscere i link di Google Maps condivisi da smartphone.",
            "Il caricamento della foto di copertina da Unsplash non blocca più la creazione o la modifica del viaggio: avviene in background con un'anteprima temporanea.",
        ],
    },
    {
        "version": "2026.7.4",
        "date": date(2026, 5, 15),
        "notes": [
            "Novità: incollando un link di Google Maps nel modulo di creazione di un'esperienza, un pasto o un alloggio, i dati (nome, indirizzo, orari, telefono...) si compilano automaticamente.",
            "Nelle impostazioni del profilo, l'indirizzo di casa si può ora digitare con suggerimenti automatici.",
        ],
    },
    {
        "version": "2026.7.3",
        "date": date(2026, 5, 14),
        "notes": [
            "Se non è impostato un trasferimento di andata o ritorno, il sito calcola ora automaticamente la distanza da casa usando l'indirizzo nel profilo.",
            "È possibile nascondere le informazioni su durata e distanza dei trasferimenti tra le tappe, dalle impostazioni.",
            "Novità: puoi aggiungere etichette libere (tag) alle esperienze, con suggerimenti basati su quelle già usate nel viaggio.",
        ],
    },
    {
        "version": "2026.7.2",
        "date": date(2026, 5, 10),
        "notes": [
            "Risolti alcuni problemi di visualizzazione: il selettore della lingua, l'ordine delle tappe nella finestra di gestione e il campo note, ora senza limite di lunghezza.",
            "Corretto un errore che in alcuni casi impediva il corretto aggiornamento dello stato del viaggio.",
            "Il sito è diventato più rapido nell'elenco dei viaggi grazie a diverse ottimizzazioni interne.",
        ],
    },
    {
        "version": "2026.7.1",
        "date": date(2026, 5, 9),
        "notes": [
            "Novità: i viaggi possono ora avere più tappe/destinazioni, con il tempo di percorrenza stimato tra una tappa e l'altra.",
            "Si possono aggiungere esperienze e pasti anche senza assegnarli subito a un giorno specifico.",
            "Migliorata la scelta e il caricamento della foto di copertina del viaggio.",
        ],
    },
    {
        "version": "2026.7",
        "date": date(2026, 5, 3),
        "notes": [
            "Novità: creazione di esperienze e alloggi direttamente dalla mappa, con ricerca dei luoghi integrata.",
            "La pagina del viaggio è stata riorganizzata: una sezione dedicata a dove dormire e una, divisa per giorno, per le cose da fare, con possibilità di riordinarle con un semplice trascinamento.",
            "I partecipanti al viaggio hanno ora ruoli distinti (organizzatore, editor, ospite) visibili con colori diversi, e si possono invitare anche persone senza account.",
            "La mappa del viaggio mostra ora tutti i giorni insieme, con un colore diverso per ciascuno e una legenda.",
        ],
    },
    {
        "version": "2026.6.1",
        "date": date(2026, 4, 12),
        "notes": [
            "Il pulsante per modificare un viaggio è ora visibile anche nella pagina di dettaglio.",
            "Risolto un problema che impediva di salvare la lingua preferita nelle impostazioni del profilo.",
            "La documentazione del progetto ha una nuova casa online, con un aspetto coerente con quello del sito.",
        ],
    },
    {
        "version": "2026.6",
        "date": date(2026, 4, 9),
        "notes": [
            "Novità: ora puoi invitare altre persone a collaborare su un viaggio come co-editor, con badge colorati che mostrano chi ha aggiunto ogni elemento.",
            "Chi viene invitato riceve una mail di notifica scritta nella lingua che preferisce; se non ha ancora un account viene guidato nella registrazione.",
            'La homepage per i visitatori non registrati mostra ora una sezione "Come funziona" con una panoramica delle funzionalità.',
        ],
    },
    {
        "version": "2026.5.3",
        "date": date(2026, 3, 31),
        "notes": [
            "Numerosi interventi tecnici hanno reso il sito più rapido, riducendo il carico sul database nelle pagine principali.",
            "Ottimizzate anche le attività automatiche in background, come l'aggiornamento del meteo e la pulizia delle sessioni scadute.",
        ],
    },
    {
        "version": "2026.5.2",
        "date": date(2026, 3, 28),
        "notes": [
            "Risolto un problema che poteva impedire il corretto avvio del sito in produzione, legato al salvataggio delle immagini.",
            "Aggiornamenti tecnici alla gestione dei file caricati.",
        ],
    },
    {
        "version": "2026.5.1",
        "date": date(2026, 3, 28),
        "notes": [
            "Il modulo per il trasferimento in auto è stato semplificato: indicando il proprio indirizzo di casa nel profilo, partenza e arrivo vengono proposti automaticamente, con pulsanti di compilazione rapida.",
            "Per altri mezzi di trasporto (traghetto, bus...) è ora possibile indicare il tipo di veicolo.",
            "Le immagini caricate sono ora conservate in modo più sicuro, senza rischio di perdita a ogni aggiornamento del sito.",
        ],
    },
    {
        "version": "2026.5",
        "date": date(2026, 3, 26),
        "notes": [
            "Nel trasferimento in treno è ora disponibile un pulsante che porta direttamente allo stato del treno in tempo reale su viaggiatreno.it, oltre a link rapidi per la ricerca su Trainline e Trenitalia.",
            "Anche per i voli è disponibile un pulsante che apre lo stato del volo in tempo reale su FlightAware.",
            "Semplificati i moduli di treno e aereo, eliminando campi poco utilizzati.",
        ],
    },
    {
        "version": "2026.4.1",
        "date": date(2026, 3, 22),
        "notes": [
            "Le previsioni del tempo sono visibili anche nella vista mappa del giorno.",
            "Risolti alcuni problemi di visualizzazione su smartphone: etichette di stato e pulsanti ora più leggibili e completi di testo.",
            "Corrette alcune traduzioni italiane mancanti o duplicate.",
        ],
    },
    {
        "version": "2026.4",
        "date": date(2026, 3, 21),
        "notes": [
            "Novità: puoi condividere un viaggio con chiunque tramite un link sicuro, con scadenza configurabile (7/30/90 giorni o senza scadenza) e possibilità di revoca.",
            "Aggiunte le previsioni del tempo per i giorni del viaggio, visibili anche nella pagina condivisa.",
            "Cliccando sull'immagine o sul titolo di un viaggio nell'elenco si apre ora direttamente il dettaglio.",
        ],
    },
    {
        "version": "2026.3.3",
        "date": date(2026, 3, 18),
        "notes": [
            "Dopo aver creato il primo viaggio dalla guida introduttiva si viene ora portati direttamente all'elenco dei viaggi.",
            "Corretto il pulsante della guida introduttiva, che ora apre correttamente la finestra di creazione viaggio.",
        ],
    },
    {
        "version": "2026.3.2",
        "date": date(2026, 3, 5),
        "notes": [
            "Il numero di versione mostrato in fondo al sito si aggiorna ora automaticamente a ogni rilascio.",
            "Corretto un problema di configurazione interna che poteva impedire la corretta esecuzione delle attività pianificate (controllo stato viaggi, pulizia sessioni).",
        ],
    },
    {
        "version": "2026.3.1",
        "date": date(2026, 1, 25),
        "notes": [
            "Migliorata la connessione tra i trasferimenti di andata/ritorno e il primo o ultimo appuntamento o alloggio del viaggio, con icone per il mezzo di trasporto.",
            "Risolti piccoli problemi di interfaccia nelle finestre di modifica.",
        ],
    },
    {
        "version": "2026.3",
        "date": date(2026, 1, 23),
        "notes": [
            "Semplificato il sistema dei trasferimenti tra tappe, con collegamenti diretti a Google Maps.",
            "Chi non ha ancora creato un viaggio trova ora una guida introduttiva con indicazioni su come iniziare.",
            "Pubblicata la documentazione online del progetto, in italiano e inglese.",
        ],
    },
    {
        "version": "2026.2",
        "date": date(2026, 1, 12),
        "notes": [
            "I trasferimenti di andata e ritorno sono ora visibili sulla mappa del viaggio, con icone diverse per aereo, treno e auto.",
            "Inserendo i dati dell'andata, quelli del ritorno vengono ora precompilati automaticamente.",
        ],
    },
    {
        "version": "2026.1",
        "date": date(2026, 1, 8),
        "notes": [
            "Nuova gestione dei trasferimenti di andata e ritorno (aereo, treno...) con ricerca automatica di aeroporti e stazioni.",
            "Il profilo utente si è arricchito: avatar, valuta preferita, ordinamento dei viaggi e vista mappa predefinita.",
            "Aggiunto il cambio tema chiaro/scuro, con supporto al tema di sistema del dispositivo.",
        ],
    },
]
