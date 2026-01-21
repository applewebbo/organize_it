# Installazione

Questa guida ti aiuterà a configurare Organize It sul tuo computer locale.

## Requisiti

Prima di iniziare, assicurati di avere installato:

- **Python 3.14 o superiore** - [Scarica Python](https://www.python.org/downloads/)
- **uv** - Gestore pacchetti Python moderno - [Installa uv](https://docs.astral.sh/uv/)
- **just** - Esecutore di comandi (opzionale ma consigliato) - [Installa just](https://github.com/casey/just)
- **Git** - Per clonare il repository

## Passi per l'Installazione

### 1. Clona il Repository

```bash
git clone https://github.com/applewebbo/organize_it.git
cd organize_it
```

### 2. Installa le Dipendenze

Usa `uv` per installare tutte le dipendenze del progetto:

```bash
just install
```

Oppure manualmente:

```bash
uv sync
```

!!! note
    Non usare mai `pip` con questo progetto - usa sempre `uv` per la gestione dei pacchetti.

### 3. Configurazione dell'Ambiente

Crea un file `.env` nella radice del progetto con la seguente configurazione:

```bash
# Impostazioni richieste
SECRET_KEY=your-secret-key-here
ENVIRONMENT=dev
DEBUG=True

# Chiavi API opzionali (per funzionalità avanzate)
MAPBOX_ACCESS_TOKEN=your-mapbox-token
GOOGLE_PLACES_API_KEY=your-google-places-key
UNSPLASH_ACCESS_KEY=your-unsplash-key
```

!!! tip "Genera una Secret Key"
    Puoi generare una chiave segreta sicura usando Python:
    ```bash
    python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    ```

### 4. Configurazione del Database

Esegui le migrazioni per configurare il database:

```bash
just migrate
```

Oppure manualmente:

```bash
uv run python manage.py migrate
```

### 5. Crea un Superutente (Opzionale)

Per accedere al pannello di amministrazione Django, crea un account superutente:

```bash
uv run python manage.py createsuperuser
```

### 6. Avvia il Server di Sviluppo

Avvia il server di sviluppo con la compilazione TailwindCSS:

```bash
just local
```

Oppure per lo stack completo con worker in background:

```bash
just serve
```

L'applicazione sarà disponibile su [http://localhost:8000](http://localhost:8000)

## Verifica

Per verificare che l'installazione sia corretta:

1. Visita [http://localhost:8000](http://localhost:8000) nel tuo browser
2. Dovresti vedere la homepage di Organize It
3. Prova a creare un account e ad effettuare il login

## Risoluzione Problemi

### Porta Già in Uso

Se la porta 8000 è già in uso, puoi specificare una porta diversa:

```bash
uv run python manage.py runserver 8080
```

### Problemi con il Database

Se riscontri problemi con il database, prova:

```bash
just clean
just fresh
```

Questo rimuoverà tutti i file temporanei e reinstallerà tutto da zero.

### Dipendenze Mancanti

Se vedi errori di import, assicurati che tutte le dipendenze siano installate:

```bash
just install
```

## Prossimi Passi

Una volta completata l'installazione, procedi con la [Guida Rapida](quick-start.md) per imparare ad usare Organize It.

## Strumenti di Sviluppo

Se hai intenzione di contribuire a Organize It, installa le dipendenze di sviluppo aggiuntive:

```bash
just update_all
```

Questo:
- Aggiornerà tutte le dipendenze
- Aggiornerà i pre-commit hooks
- Installerà gli strumenti di sviluppo (pytest, ruff, ecc.)

Per i test:

```bash
just test      # Esegue tutti i test
just ftest     # Esegue i test in parallelo (più veloce)
```

Per la qualità del codice:

```bash
just lint      # Esegue linting e formattazione
```
