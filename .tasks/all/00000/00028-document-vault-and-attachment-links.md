---
id: 0000000028
slug: document-vault-and-attachment-links
title: Document vault and attachment links
labels: []
created: '2026-06-07T10:19:16.254+02:00'
updated: '2026-06-10T15:48:00.000+02:00'
---

## Description

Allow uploading documents (PDFs, images) to Stays, Transfers, and Events, and show view links.
---

## Task Comments

| Commented At | Comment |
| --- | --- |
| 2026-06-09T15:32:07.934+02:00 | Linked to Codeberg issue #340. Single Attachment model w/ GenericForeignKey; PDF+images <=2MB; 5/Trip, 2/Stay-Event-MainTransfer; protected streaming view; HTMX modals; include_in_pdf flag merges into export. |
| 2026-06-09T15:32:07.971+02:00 | Status changed from ready to in-progress |
| 2026-06-10T15:48:00.000+02:00 | Status changed from in-progress to done. Implementation complete; pending release. Fasi 3-5 completate (UI 4 card affiancate, modal con selector entità, bottoni dedicati su transfer/stay, preview con embed/download, classe custom .btn-stay-card, traduzioni IT 'Documenti'→'Allegati'). PDF export integration skipped per richiesta utente. |
| 2026-06-09T15:49:57.079+02:00 | Progress 2026-06-09:
- Fase 1 DONE: pypdf aggiunto, modello Attachment (GenericForeignKey, validators mime/size 2MB, limite count 5 Trip / 2 Stay-Event-MainTransfer, helpers is_pdf/is_image), migration 0039_attachment, 11 model tests verdi.
- Fase 2 DONE: trips/views/attachments.py con attachment_upload/delete/stream/preview, helpers permessi (author + collaborators), URL registrate, template preview-modal.html (iframe PDF / img). 23 test verdi totali in test_attachments.py.
- TODO Fase 3: UI sezione Documenti nelle detail (trip-detail, stay, event, main-transfer) + modal upload HTMX + lista allegati.
- TODO Fase 4: integrazione PDF export con include_in_pdf (merge via pypdf, immagini come pagine extra).
- TODO Fase 5: traduzioni IT/EN, lint, ftest, commit 'for #340', label release.
- Branch: 2026.8.2 (release branch).
- Codeberg issue: #340.
- Modifiche non committate. |
