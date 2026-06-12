# Weather Forecast & Reminder

Organize It shows a weather forecast for your trip and sends you an email reminder a few days before departure, so you can pack accordingly.

## Weather widget on the trip

When your trip becomes **Impending** (start date within 7 days) or **In Progress**, a weather widget appears on the trip detail page and on each day card. It shows:

- **Daily high/low temperatures** in °C
- **Weather condition icon** (sun, cloud, rain, snow, etc.)
- **Per-day forecast** for the upcoming days of the trip

The forecast is fetched periodically in the background, so it is fresh without slowing down the page.

## Weather email reminder

Three days before departure, the trip **author and all registered collaborators** receive an automatic **weather forecast email** summarising the conditions expected during the trip.

### When it is sent

- **3 days** before the trip's start date
- Only **once** per trip (a flag is stored after sending)
- Sent to every eligible recipient in a single message (author in `To`, collaborators in `Bcc` so addresses are not exposed)

### Who receives it

- The trip **author**
- All **accepted collaborators** with a registered account on Organize It

A recipient is included only if:

- their email address is **verified**, and
- their profile preference **Show weather** is enabled

If the author has the preference disabled but a collaborator has it enabled, the email is still sent to that collaborator. Participants added by name or email only (without an account) are not included.

### What it contains

- The trip title and dates
- A day-by-day forecast with high/low temperatures and condition
- A direct link to the trip

The email is localised in the **author's language** for all recipients (single render, single send). Temperatures are always shown in °C.

### Disabling the reminder

The reminder is tied to the **Show weather** preference in your profile. Disable that option to stop receiving weather emails for all your trips, whether you are the author or a collaborator.

!!! info "One trip at a time"
    There is no per-trip switch yet. If you want a profile-wide off, use the profile setting. A per-trip toggle is on the roadmap.

## Tips

!!! tip "Use the forecast for packing"
    Pair the weather reminder with the [checklist](checklist.md). When the email arrives, open the checklist and add (or check) items like *umbrella*, *sunscreen*, *jacket* based on the forecast.

!!! tip "Check the day-by-day widget on the road"
    Once the trip starts, the per-day weather widget gives you a quick view to plan outdoor activities or shift them around if needed.

## FAQ

### Why didn't I receive the email?

The reminder is skipped if:

- The trip start date is not exactly 3 days away when the daily task runs
- The reminder has already been sent for this trip
- Weather is disabled on your profile
- Your email address is not verified

### Can collaborators receive the reminder?

Yes. Every accepted collaborator with a verified email and the **Show weather** preference enabled receives the same email as the author. The author is shown in the `To` field; collaborators are added in `Bcc` so addresses are not disclosed.

### Where does the forecast data come from?

From the configured weather provider on the backend. Accuracy depends on the provider and the distance to the destination — short-term forecasts (1–3 days) are typically reliable, while longer-range ones are indicative only.

## Daily digest email

While the trip is **in progress**, you receive a **daily summary email** for the current day with:

- Trip title and "Day X of N" header
- **Weather forecast** for the day (max/min)
- **Events** scheduled for today, in chronological order
- **Stay** check-in / check-out notices
- **Main transfers** (arrival on day 1, departure on the last day)
- A direct link to the trip

The email is sent **once per day** to the trip author and to every accepted **collaborator** with a verified email address. The author is in the `To` field; collaborators are added in `Bcc`.

### Opt-out

Open your **profile** and turn off **Daily digest email**. The setting is per user: you stop receiving the digest for every trip you author or collaborate on.

### When the email is not sent

- The trip is not in progress (status `IN_PROGRESS` or `IMPENDING` on the first day)
- The digest has already been sent for the day (idempotent)
- Your email address is not verified
- You disabled **Daily digest email** in your profile
