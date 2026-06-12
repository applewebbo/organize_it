# Pre-departure Checklist

Every trip has a personal pre-departure checklist where you can track everything you need to do or pack before leaving. It is private to the trip and optionally reminded by email a few days before departure.

## What it is

The **Checklist** is a simple to-do list attached to a trip. Use it for:

- **Packing items** — passport, chargers, adapters, medication
- **Tasks** — book airport parking, stop mail delivery, water the plants
- **Logistics** — check-in online, print tickets, download offline maps
- **Last-minute reminders** — pay bills, set out-of-office reply

Items have only two states: open or completed. Progress is shown as a counter (e.g. `5 / 12`) on the trip detail page.

## Accessing the Checklist

A **Checklist** card appears on the trip detail page. The card shows the progress counter and a link to open the full checklist view.

Clicking the link opens the dedicated checklist page at `/trips/<id>/checklist/`.

## Managing items

### Add an item

1. Open the checklist page
2. Type the item in the input field
3. Click **Add** (or press Enter)

The item appears immediately at the bottom of the list.

### Mark as done

Click the checkbox next to the item. Completed items move to the bottom and appear with strikethrough.

### Edit or delete

Each item has inline actions to rename or remove it. Deletion is immediate.

## Email reminder

The trip author can configure an automatic email reminder so the checklist is not forgotten.

### Configure the reminder

On the checklist page, the **Email reminder** card lets you choose when to receive a reminder:

- **Off** — no email is sent
- **1 day before** departure
- **3 days before** departure
- **7 days before** departure
- **14 days before** departure
- **30 days before** departure

The setting is saved on the trip itself. Only the **author** of the trip can set it — collaborators can still see and edit checklist items.

### What you receive

The reminder email contains:

- The trip title and dates
- A summary of pending items (not completed yet)
- A direct link back to the checklist

The reminder is sent **once** per trip per day. If the trip has already departed or all items are completed, the reminder is skipped.

## Tips

!!! tip "Start early"
    Add items as soon as you create the trip — it is easier to think of what you need over several days than the night before departure.

!!! tip "Keep it actionable"
    Write items as actions ("buy adapter") rather than topics ("electronics") so it is clear when they are done.

!!! info "Collaboration"
    On shared trips, collaborators can add and complete items too, but only the **author** controls the email reminder.

## FAQ

### Are checklists shared between trips?

No. Each trip has its own independent checklist.

### Can I export or print the checklist?

The checklist is part of the [PDF export](export.md), so printing the trip PDF includes it.

### Why didn't I receive my reminder?

Make sure:

- The trip start date is still in the future
- You are the author of the trip
- The reminder is **not** set to *Off*
- Your email is verified

The reminder is also skipped if it would land after the trip has already started.
