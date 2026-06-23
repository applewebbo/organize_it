# Export & Calendar Sync

Organize It can produce an **offline PDF** of your itinerary and a live **iCal feed** you can subscribe to from any calendar app. Both are available from the **Share & Export** menu on the trip header.

## Opening the menu

On the trip detail page, click the share icon in the trip header. You will see:

- **Link** — generate a read-only shareable link (see [Collaboration](collaboration.md))
- **PDF** — download an offline PDF of the trip
- **Calendar** — open the iCal feed for subscription

## PDF Export

The PDF is a complete, printable version of your trip designed to work **offline** — perfect to keep on your phone or print before leaving.

### What's included

- Cover page with trip title, dates, destination and cover image
- Day-by-day itinerary with all events in order
- Stays with address and check-in/check-out
- Main transfers (arrival/departure) with times and details
- Pre-departure [checklist](checklist.md) items
- Useful links

### Attachments in the PDF

Each [attachment](attachments.md) has an **Include in PDF** toggle. When enabled, the file is embedded so you have it offline too. Useful for boarding passes, hotel vouchers and tickets.

### Generating the PDF

1. Open the trip detail page
2. Click the **Share & Export** menu
3. Click **PDF**
4. The file is generated and downloaded automatically

!!! tip "Print or save offline"
    Save the PDF on your phone before leaving (e.g. to a Files app, Notes, or your favourite read-later tool). It works without connectivity and includes every relevant detail.

!!! info "Always up to date"
    The PDF is rendered on demand from current trip data. Generate it again any time the itinerary changes.

## iCal Calendar Sync

The iCal feed turns every event of your trip into calendar entries that any modern calendar app can read — Apple Calendar, Google Calendar, Outlook, Fastmail, Thunderbird, etc.

### How it works

Each trip has a unique, unguessable **calendar token**. The feed URL contains this token:

```
https://<your-org-domain>/ical/<calendar-token>/
```

The token is generated automatically when the trip is created and stays stable. Anyone with the URL can read the feed, so treat it like a private link.

### Subscribing

1. Open the trip detail page
2. Click the **Share & Export** menu
3. Click **Calendar** — a new tab opens with the feed URL
4. Copy the URL
5. In your calendar app, add a **subscription** (not an import) using the URL:
    - **Apple Calendar**: File → New Calendar Subscription
    - **Google Calendar**: Other calendars → From URL
    - **Outlook**: Add calendar → Subscribe from web

### What's included

- Each [experience](experiences.md) and [meal](meals.md) as a calendar event
- [Stays](stays.md) as multi-day events
- [Main transfers](transfers.md) (arrival, departure) with their times
- Location, notes and a link back to the trip in Organize It

### Automatic updates

Because it is a **subscription**, your calendar app refreshes the feed periodically. Any change to the itinerary appears in your calendar within minutes or hours, depending on the calendar app's refresh interval.

!!! warning "Don't import — subscribe"
    If you *import* the file, you get a one-time snapshot that won't update. Always use the *subscribe* / *add by URL* option.

### Revoking access

To revoke the feed, contact your trip administrator. A future release will let you rotate the calendar token directly from the trip settings.

## FAQ

### Can I have separate calendars per day or per stay?

No. The feed contains all events of one trip. Use your calendar app's filtering or colour settings if you want to highlight specific items.

### Does the PDF include maps?

It includes addresses and (where available) static map snippets for stays and key events. Live map navigation requires the web app.

### Are attachments in the PDF embedded or linked?

They are embedded so the PDF works fully offline.

### My calendar doesn't refresh — why?

Calendar apps refresh feeds on their own schedule (typically every 1–24 hours). Most apps have a manual *Refresh* option you can trigger if you need an immediate update.
