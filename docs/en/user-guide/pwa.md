# Install & Offline

Organize It is a **Progressive Web App (PWA)**. You can install it on your phone, tablet, or desktop so it opens in its own window like a native app, and trips you have already opened stay readable when you lose connectivity.

## Installing the App

Installation happens through your browser — there is no app store.

### On a phone or tablet

- **Android (Chrome/Edge)**: open Organize It, then tap the browser menu and choose **Install app** / **Add to Home screen**.
- **iPhone/iPad (Safari)**: open Organize It, tap the **Share** button, then **Add to Home Screen**.

### On desktop

In Chrome or Edge, look for the **install icon** in the address bar (or use the browser menu → **Install Organize It**). The app then opens in its own standalone window.

Once installed, Organize It uses its own icon and launches full-screen without the browser chrome.

## Working Offline

Organize It registers a **service worker** that caches the pages and assets you visit. This means:

- **Trips you have already opened stay available** offline. You can reopen the app without a connection and still read them.
- If you navigate somewhere that hasn't been cached while offline, a friendly **offline page** is shown instead of a browser error.
- Where a **map** would normally appear, an offline **placeholder** is shown, since map tiles need a live connection.

!!! info "Offline is read-only"
    Offline support is meant for **consulting** trips you already loaded — for example checking your itinerary at the airport. Changes still need a connection to be saved, and you will always see the latest data once you are back online.

!!! tip "The service worker only runs in production"
    To keep local development responsive, the offline service worker is active on the live site, not on a local `DEBUG` server.

## Related Guides

- [Export & Calendar Sync](export.md) - Download a PDF or subscribe via iCal for full offline access
- [Trips](trips.md) - Creating and managing trips

---

**Next**: Learn about the [FAQ](../faq.md)
