---
# organize_it-yp6g
title: Pubblica documentazione su Read the Docs
status: todo
type: task
created_at: 2026-01-21T14:38:52Z
updated_at: 2026-01-21T14:38:52Z
---

Completare il setup e la pubblicazione della documentazione MkDocs su Read the Docs.

## Checklist

### Preparazione Repository
- [ ] Push del branch 2026.3 su GitHub
- [ ] Verifica che tutti i commit siano presenti sul remote

### Setup Read the Docs (da fare manualmente)
- [ ] Registrarsi/accedere su https://readthedocs.org
- [ ] Usare "Sign in with GitHub" per integrazione
- [ ] Importare il progetto organize_it dal repository GitHub
- [ ] Configurare nome progetto: "organize-it"
- [ ] Impostare default branch: main
- [ ] Verificare che .readthedocs.yaml sia rilevato correttamente

### Primo Build e Test
- [ ] Trigger del primo build da Read the Docs dashboard
- [ ] Monitorare i log del build per verificare successo
- [ ] Verificare che il build completi senza errori
- [ ] Testare la documentazione live su organize-it.readthedocs.io
- [ ] Verificare versione inglese (EN)
- [ ] Verificare versione italiana (IT)
- [ ] Testare la ricerca in entrambe le lingue
- [ ] Verificare il toggle dark/light mode

### Configurazione Avanzata (opzionale)
- [ ] Configurare default version (latest/stable)
- [ ] Verificare privacy level (Public)
- [ ] Verificare webhook GitHub sia configurato
- [ ] Testare build automatico con un push di test

### Merge su Main
- [ ] Verificare che tutto funzioni su branch 2026.3
- [ ] Eseguire just ftest per verificare test
- [ ] Checkout su main
- [ ] Rebase 2026.3 su main
- [ ] Push su main
- [ ] Verificare build automatico su Read the Docs

### Documentazione e Comunicazione
- [x] Aggiungere badge Read the Docs al README.md
- [x] Aggiornare README con link alla documentazione
- [ ] Considerare aggiungere link alla docs nell'app stessa

### Versioning (futuro)
- [ ] Quando pronto, creare primo tag (es. v1.0.0)
- [ ] Verificare che Read the Docs crei versione automaticamente
- [ ] Configurare "stable" version se necessario

## Note

- URL documentazione: https://organize-it.readthedocs.io
- Build automatico attivato via webhook GitHub
- Testing locale disponibile con: just docs-serve
- Tempo build stimato: 1-2 minuti
