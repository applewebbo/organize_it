# Documents & Attachments

Organize It includes a **document vault** that lets you attach PDFs and images to a trip. Tickets, hotel vouchers, museum reservations, insurance cards — keep them with the trip so they are one click away.

## What you can attach

### Allowed file types

- **PDF** (`application/pdf`)
- **JPEG** (`image/jpeg`)
- **PNG** (`image/png`)
- **WebP** (`image/webp`)

### Size limit

Each file can be up to **2 MB**.

!!! tip "Compress before upload"
    For multi-page PDFs (e.g. boarding passes) you can compress the file or split it into per-leg PDFs.

### Quantity limits

To keep the vault tidy, there are limits on how many files you can attach to each item:

| Attached to | Max files |
| --- | --- |
| Trip (general documents) | 5 |
| Main transfer (arrival/departure) | 2 |
| Stay | 2 |
| Event (experience / meal) | 2 |

## The Attachments card

A **Documents** card appears on the trip detail page. It groups your uploads by category:

- **Trip** — general documents not tied to a specific item (insurance, visa, travel guide)
- **How to Get There** — attachments on the arrival/departure main transfers (boarding passes, train tickets)
- **Where to Sleep** — attachments on stays (hotel voucher, apartment instructions)
- **Events** — attachments on individual experiences and meals (museum tickets, restaurant reservation)

Each category shows a total count and lists the files with their original filename and a thumbnail (for images) or PDF icon.

## Uploading a file

1. On the trip detail page, find the **Documents** card
2. Click the upload button for the desired category
3. In the modal, choose:
   - The **target item** (which transfer / stay / event the file belongs to — not needed for the *Trip* category)
   - The **file** to upload
4. Confirm

The list refreshes automatically. The original filename is kept and shown in the card.

## Viewing a file

Click an attachment to open the preview:

- **Images** open in a preview modal
- **PDFs** open in a new browser tab (using the browser's native PDF viewer)

Files are served only to users who can access the trip — the URL contains the attachment ID and access is checked on every request.

## Deleting a file

Use the delete action next to the attachment. The file is removed immediately, both from the database and from storage.

## Including attachments in the PDF export

Each attachment has a toggle **Include in PDF**. When enabled, the file is embedded (or referenced) in the offline [PDF export](export.md) so you always have it with you, even without connectivity.

!!! info "Why a toggle?"
    Not every file makes sense to include in the printed PDF. Large insurance PDFs add weight, while a single boarding pass image is perfect to embed.

## Tips

!!! tip "Name your files clearly"
    The original filename is preserved. Renaming `IMG_2934.jpg` to `boarding-pass-rome.jpg` before upload makes the vault much easier to scan.

!!! tip "Attach close to the source"
    A museum ticket attached to the Colosseum **event** is easier to find than the same file lost in the general Trip documents.

!!! warning "Sensitive data"
    Attachments live on the server. Avoid uploading passport scans or other highly sensitive documents unless strictly necessary.

## FAQ

### Can I upload Word documents or spreadsheets?

No — only PDF and image formats are accepted. Export the document as PDF before uploading.

### What if I hit the 2 MB limit?

Compress the file. For photos, resize to ~1600 px on the long side; for PDFs, use a "compress" or "reduce size" option in your PDF tool.

### Can collaborators upload files?

Yes — collaborators on the trip can upload, view, and delete attachments.

### Are attachments included in the iCal feed?

No. The [iCal feed](export.md) only contains schedule events. Attachments are part of the PDF export.
