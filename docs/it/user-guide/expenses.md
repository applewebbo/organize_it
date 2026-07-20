# Spese Condivise

Organize It può tenere traccia di chi ha pagato cosa durante un viaggio e dividere le spese condivise tra i partecipanti. Calcola **chi deve cosa a chi** con il minor numero di trasferimenti e gestisce anche le famiglie, dove la quota dei bambini viene addebitata ai genitori.

!!! info "Attivabile per viaggio"
    La divisione delle spese è **disattivata di default** in ogni viaggio. Attivala dalla card **Spese** quando vuoi iniziare a tracciare i costi — finché non la attivi non viene calcolato nulla.

## Come Funziona

1. **Attivi** la divisione delle spese in un viaggio dalla card **Spese**.
2. **Configuri** i partecipanti: scegli la valuta del viaggio, raggruppi coppie/famiglie in **nuclei famigliari** e segni i **bambini**.
3. Chiunque abbia accesso in modifica **aggiunge le spese** — libere oppure collegate a un alloggio, un evento o un trasferimento — e sceglie con chi dividerle.
4. Organize It calcola i **saldi** e mostra i **regolamenti semplificati** (chi deve pagare chi) nel modale delle spese.

## Attivare la Divisione delle Spese

1. Apri un viaggio e trova la card **Spese**.
2. Attiva l'interruttore **Attiva divisione spese** nell'intestazione della card.

![La card Spese](../assets/screenshots/expenses-card.png)

La prima volta che attivi la funzione, la valuta del viaggio viene impostata automaticamente dalla valuta preferita del tuo profilo. Potrai cambiarla in seguito nelle impostazioni delle spese.

!!! info "I dati vengono conservati"
    Disattivando di nuovo l'interruttore, tutte le spese e la configurazione restano salvate. La card mostra solo un invito a riattivare e nessun saldo viene visualizzato finché non la riattivi.

## Configurare i Partecipanti

Apri le **impostazioni spese** (l'icona a ingranaggio sulla card Spese) per configurare il viaggio.

![Impostazioni spese con un nucleo famigliare](../assets/screenshots/expense-settings.png)

!!! warning "Aggiungi prima le persone"
    I partecipanti provengono dalla sezione **Chi partecipa** del viaggio. Aggiungi prima tutti lì — l'autore e ogni collaboratore, comprese le persone "solo nome" senza account — e compariranno automaticamente nelle impostazioni delle spese.

### Valuta del Viaggio

Scegli un'unica valuta per tutto il viaggio (EUR, USD o GBP). Tutti gli importi e i saldi sono mostrati in questa valuta.

### Nuclei Famigliari

Un **nucleo famigliare** raggruppa le persone che condividono un unico portafoglio — tipicamente una coppia o una famiglia. Trascina il chip di un partecipante su un nucleo per assegnarlo, oppure riportalo su **Non assegnati** per staccarlo.

Un nucleo è trattato come **un'unica entità**: i debiti *interni* si annullano e i regolamenti sono mostrati per nucleo anziché per persona. Quando aggiungi una spesa, l'intero nucleo compare come **singola scelta** per chi ha pagato e con chi dividere (vedi sotto).

!!! tip "Mobile"
    Su schermi piccoli il drag & drop è sostituito da un **selettore di nucleo** su ogni chip partecipante.

### Bambini

Segna un partecipante come **bambino** per indicare che la sua quota va addebitata agli adulti del suo nucleo anziché a lui stesso:

- Con **due adulti** nel nucleo, la quota del bambino è divisa 50/50 tra loro.
- Con **un solo adulto**, quell'adulto copre l'intera quota del bambino.

!!! warning "Assegna i bambini a un nucleo"
    Un bambino che non è in un nucleo con almeno un adulto mantiene la propria quota e il modale delle spese mostra un avviso. Metti sempre i bambini in un nucleo con un genitore, così il loro costo viene attribuito correttamente.

## Aggiungere una Spesa

Ci sono due modi per registrare un costo.

### Spese Libere

Dalla card **Spese**, scegli **Aggiungi spesa** e compila descrizione, importo, data, chi ha **pagato** e con chi **dividerla**. **Pagato da** è precompilato con te e puoi cambiarlo. Bisogna selezionare almeno un'entità.

![Form Aggiungi spesa](../assets/screenshots/expense-form.png)

!!! tip "I nuclei famigliari sono un'unica scelta"
    Dove hai un nucleo famigliare, esso compare come **singola opzione** sia in **Pagato da** sia in **Dividi tra** — scegli il nucleo invece dei singoli membri. Dividere con un nucleo addebita una quota uguale a **ciascun** membro, e un pagamento del nucleo viene accreditato all'intero nucleo.

### Costi Collegati a un Alloggio, Evento o Trasferimento

Su un alloggio, un'esperienza, un pasto o un trasferimento principale, usa **Aggiungi costo** per collegare una spesa direttamente a quell'elemento. La data è impostata di default al giorno dell'elemento (o all'inizio/fine del viaggio per i trasferimenti di andata/ritorno). L'elemento collegato mostra il suo costo nel viaggio e nella vista di dettaglio.

!!! info "Le spese collegate sopravvivono alla cancellazione"
    Se in seguito elimini l'alloggio, l'evento o il trasferimento a cui una spesa era collegata, la **spesa viene conservata** come costo libero, così i saldi restano corretti.

## Regole di Divisione

Ogni spesa è divisa **equamente** tra i partecipanti con cui l'hai condivisa. Gli importi sono divisi al centesimo e gli eventuali centesimi residui vengono distribuiti in modo deterministico, così le quote sommano sempre esattamente al totale. La quota di una persona le viene addebitata solo se è inclusa nella divisione.

## Saldi e Regolamenti

Apri il modale **Spese** (il pulsante **Dettagli** sulla card) per vedere tutto in tre schede:

- **Saldi** — l'insieme minimo di regolamenti tra portafogli ("A paga B") più un dettaglio per portafoglio di quanto ciascuna entità ha pagato e deve. Qui compare un avviso se un bambino non è assegnato.
- **Spese** — l'elenco completo delle spese per data, con azioni di modifica ed eliminazione.
- **Totali** — totali **per giorno**, più il totale del viaggio.

![Modale dettaglio spese con i saldi](../assets/screenshots/expenses-modal.png)

La card Spese mostra il totale del viaggio e il **tuo** saldo personale (quanto devi o quanto ti devono).

!!! info "Debiti semplificati"
    I regolamenti usano il minor numero di trasferimenti (stile Splitwise): invece che tutti paghino tutti, Organize It compensa il tutto nel minor numero di trasferimenti "A paga B", con somma sempre pari a zero.

## Rimuovere un Collaboratore

Se un collaboratore che ha già uno storico spese viene rimosso dal viaggio, le sue spese vengono **conservate** e il partecipante viene semplicemente disattivato (mostrato in grigio), così i saldi restano accurati. Un collaboratore senza spese viene rimosso completamente.

## Guide Correlate

- [Collaborazione](collaboration.md) - Aggiungere partecipanti a un viaggio
- [Alloggi](stays.md) - Sistemazioni a cui collegare i costi
- [Esperienze](experiences.md) - Attività a cui collegare i costi
- [Pasti](meals.md) - Ristoranti a cui collegare i costi

---

**Prossimo**: Scopri i [trasferimenti](transfers.md)
