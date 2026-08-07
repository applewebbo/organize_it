# Procedura Guidata

La **procedura guidata** è un modo alternativo di creare un viaggio. Invece di compilare un unico modulo, ti accompagna in tre passaggi: i dati del viaggio con le sue tappe, una pianificazione AI giorno per giorno facoltativa e una ricerca alloggi facoltativa.

È pensata per i viaggi che non hai ancora organizzato. Se sai già esattamente cosa vuoi, la [procedura standard](trips.md#creare-un-viaggio) è più rapida.

## Prima di Iniziare

!!! warning "Richiede una chiave AI personale"
    La procedura guidata è disponibile solo per gli utenti che hanno configurato **una propria chiave API per l'AI** nel profilo. Se non ce l'hai, il pulsante **Crea un nuovo viaggio** apre direttamente il modulo standard e l'opzione guidata non compare.

    Una chiave condivisa con te dall'autore di un viaggio non è sufficiente: la procedura richiede una chiave personale.

    Entrambi i provider supportati hanno un **piano gratuito**: crea una chiave su [Google AI Studio](https://aistudio.google.com/apikey) o nella [console Mistral](https://console.mistral.ai/api-keys/), poi incollala in **Impostazioni Account → Suggerimenti AI**. Le istruzioni passo passo sono in [Ottenere una Chiave API Gratuita](suggestions.md#ottenere-una-chiave-api-gratuita).

## Avviare la Procedura

1. Nella home, clicca **Crea un nuovo viaggio**
2. Scegli **Procedura guidata** dal menu a tendina

L'altra voce, **Procedura standard**, apre la classica finestra con il modulo unico.

![Menu di creazione viaggio](../assets/screenshots/wizard-entry-dropdown.png)
*La scelta tra procedura standard e guidata*

## Passaggio 1: Dati Base

È l'unico passaggio obbligatorio: è quello che crea il viaggio.

![Passaggio dati base](../assets/screenshots/wizard-basics.png)
*Il passaggio Dati base con due tappe*

Compila:

- **Titolo** — il nome del viaggio (max 100 caratteri)
- **Data di inizio** e **Data di fine**
- **Tappe** — una o più destinazioni, ciascuna con un numero di notti

### Le Tappe

Una **tappa** è una destinazione in cui dormi, con il numero di notti che vi trascorri. Aggiungi una riga per ogni destinazione:

- Clicca **Aggiungi tappa** per inserire una riga
- Clicca l'icona del cestino per rimuoverne una (la prima tappa non è eliminabile)
- La **prima tappa è la destinazione principale** del viaggio ed è quella che compare sulla card

Il contatore accanto al titolo *Tappe* mostra `notti usate / durata del viaggio` e diventa verde quando i due valori coincidono.

!!! warning "Le notti devono corrispondere alla durata"
    La somma delle notti di tutte le tappe deve essere uguale alla durata del viaggio. Un viaggio dal 1 all'8 giugno dura **7 notti**, quindi `Roma 4 + Firenze 3` è valido, mentre `Roma 4 + Firenze 2` viene rifiutato con *"Le notti delle tappe devono corrispondere alla durata del viaggio."*

    Ogni tappa richiede inoltre una destinazione e almeno una notte.

### Come le Tappe Diventano Giorni

Quando clicchi **Avanti**, il viaggio e i suoi giorni vengono creati e ogni tappa viene assegnata a un blocco di giorni consecutivi in base alle sue notti.

L'**ultima tappa assorbe il giorno di partenza**, perché un viaggio ha sempre un giorno in più rispetto alle notti. Con `Roma 4 + Firenze 3` su 8 giorni:

| Giorni | Tappa |
|--------|-------|
| 1–4 | Roma |
| 5–8 | Firenze |

Ogni giorno porta con sé la destinazione della propria tappa, che è ciò che usano la pianificazione AI e le previsioni meteo.

!!! info "Qui la bozza viene salvata"
    Da questo momento il viaggio esiste come **bozza**. Se chiudi il browser puoi riprenderla dalla home: non perdi nulla.

## Passaggio 2: Pianificazione AI

Facoltativo. L'AI propone un piano per l'intero viaggio in una sola volta e decidi tu, giorno per giorno, cosa tenere.

![Passaggio pianificazione AI](../assets/screenshots/wizard-ai-step.png)
*Il passaggio di pianificazione AI prima della generazione*

1. Se vuoi, scrivi delle **note per l'AI** (max 500 caratteri) — ad esempio *"in viaggio con due bambini, niente musei al pomeriggio"*
2. Clicca **Genera itinerario**
3. Rivedi i giorni proposti

Ogni giorno è una card che mostra il numero del giorno, la sua destinazione, il numero di tappe e l'elenco delle fermate proposte con la durata stimata. Le fermate hanno un'icona che ne indica il tipo: forchetta e coltello per i pasti, segnaposto per le esperienze.

![Risultati della pianificazione AI](../assets/screenshots/wizard-ai-results.png)
*Un itinerario generato pronto da rivedere, con il giorno 3 deselezionato per non applicarlo*

### Tenere e Scartare

- Ogni giorno con almeno una fermata è **selezionato di default**
- Deseleziona i giorni che non vuoi
- I giorni senza fermate proposte sono mostrati ma non selezionabili
- Clicca **Rigenera** per chiedere un piano completamente nuovo (ignora il risultato in cache)
- Clicca **Tieni i giorni selezionati** per applicarli

Le fermate tenute vengono **aggiunte** al rispettivo giorno: nulla di già presente viene sostituito. I giorni scartati restano semplicemente vuoti, pronti per essere compilati in seguito.

!!! tip "Puoi saltarlo del tutto"
    Clicca **Salta questo passaggio** per andare direttamente ai soggiorni. Potrai comunque usare la pianificazione AI più avanti, un giorno alla volta, dalla pagina del viaggio — vedi [Suggerimenti AI](suggestions.md).

### Se la Generazione Fallisce

Il passaggio degrada in modo controllato e ti permette sempre di proseguire:

| Messaggio | Significato |
|-----------|-------------|
| *La pianificazione AI non è ancora configurata* | La chiave API manca o non è valida — viene mostrato un link alle impostazioni AI |
| *Hai raggiunto il limite di utilizzo del provider AI* | La quota del tuo provider è esaurita: riprova più tardi |
| *Hai raggiunto il limite giornaliero di generazioni AI* | È stato raggiunto il limite giornaliero dell'app: riprova domani |
| *Qualcosa è andato storto…* | Qualsiasi altro errore — spesso basta riprovare |

## Passaggio 3: Soggiorni

Facoltativo. Per ogni tappa del viaggio puoi cercare un alloggio per le date esatte di quella tappa.

![Passaggio soggiorni](../assets/screenshots/wizard-stays.png)
*Il passaggio Soggiorni, una riga per tappa*

Ogni riga mostra la destinazione della tappa e il suo intervallo di date. Clicca **Cerca** per aprire la ricerca alloggi di quella tappa, precompilata con destinazione e date. Vedi la [guida agli Alloggi](stays.md) per il funzionamento della ricerca.

!!! info "Qui non viene registrata alcuna prenotazione"
    La ricerca apre un servizio esterno di prenotazione. Nulla viene salvato automaticamente nel viaggio: aggiungi il soggiorno a Organize It dopo aver prenotato.

Se la ricerca alloggi non è configurata sulla tua istanza, il passaggio mostra *"La ricerca degli alloggi non è al momento disponibile."* e puoi semplicemente concludere.

Clicca **Fine** per completare la procedura e arrivare al tuo viaggio.

## Immagine di Copertina

Se non hai fornito un'immagine di copertina durante la procedura, ne viene **selezionata una automaticamente** da Unsplash in base alla destinazione principale nel momento in cui clicchi **Fine**.

Le copertine selezionate automaticamente riportano una piccola bacchetta magica in alto a sinistra dell'immagine, così puoi distinguerle da quelle scelte da te.

![Badge copertina selezionata dall'AI](../assets/screenshots/wizard-ai-cover-badge.png)
*Il badge che identifica una copertina selezionata automaticamente*

La selezione avviene in background, quindi l'immagine potrebbe comparire qualche secondo dopo il caricamento della pagina. Se non viene trovata una foto adatta, viene mostrato il consueto segnaposto. Puoi sostituire la copertina in qualsiasi momento [modificando il viaggio](trips.md#cambiare-unimmagine).

## Bozze: Riprendere, Scartare, Uscire

Un viaggio creato con la procedura guidata resta una **bozza** finché non clicchi **Fine**.

### Riprendere

Una bozza non completata compare come card nella home e nella lista viaggi, contrassegnata dal badge **Bozza**:

![Card della bozza](../assets/screenshots/wizard-draft-card.png)
*Una bozza non completata nella home*

- **Continua** riapre la procedura al passaggio in cui l'avevi lasciata
- **Scarta** elimina la bozza e tutto il suo contenuto

!!! warning "Una sola bozza alla volta"
    La home mostra una sola bozza. Completala o scartala prima di avviare un'altra procedura guidata.

### Uscire dalla Procedura

Se clicchi un link che ti porta fuori dalla procedura, compare una finestra di conferma. Il testo dipende da quanto sei andato avanti:

- **Prima di aver inviato i dati base**: *"Non hai ancora salvato nulla: uscendo perderai i dati inseriti."*
- **Dopo la creazione della bozza**: *"La bozza è salvata. Potrai riprenderla in seguito dalla home."*

Scegli **Rimani** per tornare indietro oppure **Esci** per proseguire.

### Annullare

- Nel passaggio Dati base, **Annulla** riporta alla home senza creare nulla
- In seguito, **Scarta** sulla card della bozza elimina il viaggio in bozza, i suoi giorni e gli eventi eventualmente aggiunti dall'AI

!!! danger "Scartare è definitivo"
    Scartare una bozza elimina il viaggio e tutto il suo contenuto. Non è possibile annullare l'operazione.

## Guidata o Standard?

| | Procedura guidata | Procedura standard |
|---|---|---|
| Richiede una chiave AI personale | Sì | No |
| Più destinazioni | Sì, come tappe | Una sola destinazione |
| Itinerario AI | Tutto il viaggio in una volta | Un giorno alla volta, in seguito |
| Ricerca alloggi | Per tappa, durante la procedura | Dalla pagina del viaggio |
| Immagine di copertina | Automatica se omessa | La scegli tu |
| Ideale per | Un viaggio ancora da organizzare | Un viaggio di cui conosci già i dettagli |

Entrambe producono un viaggio ordinario: nulla di ciò che crea la procedura guidata si comporta diversamente in seguito.

## Domande Frequenti

### Perché non vedo l'opzione della procedura guidata?

Non hai configurato una chiave API personale per l'AI. Aggiungine una dal profilo — vedi [Suggerimenti AI](suggestions.md).

### Posso modificare le tappe dopo aver concluso?

Non come tappe. Una volta completata la procedura il viaggio è un viaggio ordinario: modifichi la destinazione di ogni giorno singolarmente dalla pagina di dettaglio.

### Il passaggio AI sovrascrive quello che c'è già?

No. Le fermate tenute vengono aggiunte al rispettivo giorno insieme a ciò che è già presente.

### Cosa succede se chiudo il browser a metà procedura?

Non perdi nulla, purché tu abbia completato il passaggio Dati base. La bozza ti aspetta nella home.

### Posso tornare a un passaggio precedente?

Non direttamente. Uscendo e riprendendo, la bozza si riapre al passaggio più avanzato raggiunto. Per modificare i dati base, concludi la procedura e modifica il viaggio normalmente.

## Guide Correlate

- [Viaggi](trips.md) - Creazione e gestione standard dei viaggi
- [Suggerimenti AI](suggestions.md) - Pianificazione AI per singolo giorno e chiavi API
- [Alloggi](stays.md) - Soggiorni e ricerca prenotazioni
- [Giorni](days.md) - Organizzazione dei giorni e destinazioni

---

**Prossimo**: Scopri come [organizzare il viaggio per giorni](days.md)
