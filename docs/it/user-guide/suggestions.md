# Suggerimenti AI

Organize It può suggerire luoghi da visitare, dove mangiare e dove alloggiare per il tuo viaggio tramite un provider AI. I suggerimenti sono personalizzati in base alla destinazione, alle tue preferenze di viaggio e a ciò che hai già pianificato, e ogni risultato è ancorato a un luogo reale tramite Google Places.

!!! info "Funzione opzionale (Bring Your Own Key)"
    I suggerimenti AI sono **disattivati di default** e richiedono la **tua chiave API** di un provider supportato. Non viene generato nulla finché non attivi la funzione e configuri una chiave nel tuo profilo.

## Come Funziona

1. Attivi i suggerimenti AI e aggiungi la tua chiave API nelle **Impostazioni Account**.
2. In un viaggio, apri il pannello **Suggerimenti AI** e premi **Genera**.
3. L'AI propone luoghi in base a destinazione, preferenze, piani esistenti e meteo.
4. Ogni proposta viene **ancorata** a un luogo reale (indirizzo, coordinate, orari) tramite Google Places.
5. Esamini le card dei risultati e **aggiungi** quelle che ti interessano al viaggio.

## Attivare i Suggerimenti AI

1. Vai alla pagina **Impostazioni Account**
2. Individua la card **Suggerimenti AI**
3. Attiva l'interruttore **Abilita suggerimenti AI**
4. Compaiono il provider, la chiave API e i campi delle preferenze

Finché l'interruttore è disattivato, le impostazioni AI e le funzioni AI nell'app restano nascoste.

### Scegliere un Provider e Aggiungere una Chiave

Sono supportati due provider:

- **Google Gemini**
- **Mistral AI**

Seleziona il tuo provider, incolla la chiave API rilasciata da quel provider e clicca **Salva**.

![Impostazioni suggerimenti AI](../assets/screenshots/ai-settings.png)
*Le impostazioni dei suggerimenti AI, con provider, chiave, condivisione e preferenze*

!!! info "La tua chiave è memorizzata in modo sicuro"
    La chiave API è **cifrata a riposo** e non viene mai mostrata in chiaro. Una volta salvato, il campo resta mascherato: lascialo vuoto per mantenere la chiave attuale, oppure digitane una nuova per sostituirla. Se cambi provider, devi inserire la chiave del nuovo provider.

!!! warning "L'uso incide sulla tua quota"
    Ogni generazione chiama il provider usando la **tua** chiave API, quindi consuma la **tua** quota (e gli eventuali costi associati). I risultati vengono memorizzati in cache per evitare chiamate inutili.

## Preferenze dei Suggerimenti

Le preferenze impostate una volta nelle **Impostazioni Account** vengono riutilizzate a ogni generazione, così non devi reinserirle ogni volta.

| Campo | Scopo |
|-------|-------|
| **In viaggio come** | Solo, coppia, famiglia con bambini o gruppo di amici |
| **Stile di viaggio** | Mete imperdibili, bilanciato o fuori dai percorsi turistici |
| **Tipi di attività preferiti** | Orienta le esperienze verso i tipi che preferisci (musei, passeggiate, sport, …) |
| **Interessi / temi** | Storia, arte, natura, vita notturna, shopping, cibo locale, relax |
| **Preferenza alimentare** | Nessuna preferenza, vegetariana, vegana o senza glutine |
| **Tipo di cucina** | Nessuna preferenza, tradizionale locale, street food o internazionale |
| **Budget** | Basso, medio o alto |
| **Area di ricerca** | In città, città e dintorni o includi gite di un giorno |
| **Numero di suggerimenti** | Quanti risultati richiedere per generazione (3–15, default 8) |
| **Note** | Indicazioni libere, es. "abbiamo l'auto, evitare lunghe code, preferire locali aperti fino a tardi" |

## Generare Suggerimenti in un Viaggio

I suggerimenti AI si trovano nella vista **mappa** del viaggio.

### Desktop

1. Apri il viaggio e vai alla vista mappa
2. Nel pannello laterale, passa alla scheda **Suggerimenti AI** (accanto a **Cerca**)
3. Facoltativamente, restringi l'ambito con i selettori **tappa/città** e **tipo**
4. Premi **Genera**

![Suggerimenti AI sulla mappa del viaggio](../assets/screenshots/ai-suggestions.jpg)
*I suggerimenti generati nel pannello mappa, con i pin numerati corrispondenti sulla mappa*

### Mobile

Su schermi più piccoli la stessa funzione si apre come **modale** dalla pagina del viaggio, con l'identico flusso di generazione e le stesse card dei risultati.

### Delimitare una Generazione

- **Tappa / città** — per viaggi con più destinazioni, genera suggerimenti per una singola tappa. I risultati (e il contesto sottostante) sono centrati sui giorni di quella tappa.
- **Tipo** — limita i risultati solo a **esperienze**, **pasti** o **alloggi**.
- **Note** — puoi aggiungere note estemporanee per una singola generazione, oltre alle preferenze salvate.

### Genera vs. Rigenera

- **Genera** produce un nuovo set di risultati la prima volta.
- **Rigenera** compare in seguito e **ignora la cache** per richiedere un set completamente nuovo (consumando di nuovo la quota).

!!! tip "I risultati sono in cache"
    Una generazione viene memorizzata in cache per **24 ore** e i tuoi ultimi risultati restano disponibili per **48 ore**. Riaprendo il pannello o il modale vengono rimostrati gli ultimi risultati **senza** consumare quota: paghi solo quando premi Genera/Rigenera.

## Esaminare e Aggiungere i Suggerimenti

Ogni suggerimento è mostrato come card con:

- Un'**icona del tipo** (esperienza, pasto o alloggio) coerente con i pin della mappa dell'app
- Il **nome** del luogo e una breve **descrizione**
- L'**indirizzo** e la **città** risolti da Google Places
- La possibilità di caricare i **dettagli su richiesta** (sito web, telefono, orari di apertura)

Per aggiungere un luogo, clicca **Aggiungi** sulla sua card. Viene creato come **Esperienza**, **Pasto** o **Alloggio** e compare tra gli elementi non assegnati del viaggio, pronto per essere assegnato a un giorno. La card accettata viene sostituita da un messaggio di conferma.

!!! info "Nessun duplicato"
    I luoghi già presenti nel viaggio vengono **nascosti** dai risultati e i luoghi esistenti del viaggio vengono forniti all'AI affinché eviti di proporre cose già pianificate.

### Ancoraggio ai Luoghi Reali

Ogni proposta viene confrontata con **Google Places** per associare indirizzo, coordinate e ID luogo reali. Le proposte non abbinabili — o che risolvono a un luogo fuori dall'**area di ricerca** scelta — vengono scartate, così le card puntano sempre a un locale reale e correttamente localizzato.

## Pianificare un Intero Giorno

Oltre a suggerire singoli luoghi, Organize It può proporre un **itinerario completo per un singolo giorno** — un insieme ordinato di tappe (esperienze, pasti) che si incastrano tra loro.

1. In un viaggio, apri il giorno da pianificare e premi **Pianifica giornata** (il pulsante nell'intestazione del giorno).
2. Nel modale, aggiungi facoltativamente delle **note per questo giorno**, poi premi **Pianifica giornata** per generare.
3. Esamina le **tappe** proposte. Ognuna ha una casella — deseleziona ciò che non vuoi.
4. Premi **Applica giornata** per aggiungere le tappe selezionate al giorno.

### Scegliere una Strategia

Se il giorno **ha già degli eventi**, scegli come il piano deve trattarli:

- **Aggiungi agli eventi esistenti** — mantieni ciò che c'è e aggiungi le nuove tappe accanto.
- **Scollega gli eventi esistenti** — gli eventi attuali vengono spostati nell'elenco non assegnati quando applichi il piano, liberando il giorno per le nuove tappe.
- **Elimina gli eventi esistenti** — gli eventi attuali vengono eliminati quando applichi il piano.

!!! info "Niente cambia finché non applichi"
    La generazione si limita a proporre un itinerario. Gli eventi esistenti vengono scollegati o eliminati **solo quando premi Applica giornata** e solo per la strategia scelta.

!!! warning "La generazione usa la tua quota"
    Come per i suggerimenti di luoghi, pianificare un giorno chiama il tuo provider AI con la tua chiave e viene conteggiato sulla tua quota e sul limite giornaliero.

## Condividere la Chiave con i Collaboratori

Se hai creato un viaggio e aggiunto [collaboratori](collaboration.md), puoi permettere loro di generare suggerimenti AI usando la **tua** chiave quando non ne hanno configurata una propria.

1. Nelle **Impostazioni Account**, sotto **Suggerimenti AI**, attiva **Condividi la chiave API con i collaboratori**
2. I collaboratori dei viaggi che hai creato possono ora generare suggerimenti con la tua chiave

Come viene risolta la chiave per un collaboratore:

- Se il collaboratore ha una **chiave propria**, viene sempre usata quella.
- Altrimenti, se l'autore del viaggio ha **condiviso** la propria chiave, viene usata quella dell'autore.
- Se nessuna delle due è disponibile, la generazione non è possibile.

!!! info "Avviso di chiave condivisa"
    Quando un collaboratore si affida alla chiave condivisa dell'autore, un avviso una tantum lo informa. Può ignorarlo e non verrà più mostrato per quel viaggio.

!!! warning "L'uso condiviso è a tuo carico"
    Con la condivisione attiva, le generazioni dei collaboratori consumano la **tua** quota del provider. Disattiva l'interruttore in qualsiasi momento per interrompere la condivisione.

## Domande Frequenti

### Devo pagare Organize It per usare i suggerimenti AI?

No. La funzione usa il **tuo** account e la **tua** chiave del provider (Bring Your Own Key). Eventuali costi o quote riguardano te e il tuo provider AI.

### Quali provider posso usare?

Google **Gemini** e **Mistral AI**.

### Dove viene memorizzata la mia chiave API?

Cifrata a riposo nel database. Non viene mai mostrata in chiaro né scritta nei log.

### Perché ho ottenuto meno risultati di quelli richiesti?

Alcune proposte non possono essere ancorate a un luogo reale, o cadono fuori dall'area di ricerca, e vengono scartate. L'app richiede più candidati per compensare, ma il numero finale può comunque essere inferiore.

### I collaboratori possono vedere la mia chiave?

No. La condivisione permette loro di **usare** la tua chiave per generare suggerimenti; la chiave stessa non viene mai mostrata.

## Guide Correlate

- [Esperienze](experiences.md) - Attività e attrazioni
- [Pasti](meals.md) - Ristoranti e ristorazione
- [Alloggi](stays.md) - Sistemazioni
- [Collaborazione](collaboration.md) - Lavorare a un viaggio con altri

---

**Prossimo**: Scopri come [collaborare a un viaggio](collaboration.md)
