/*
 * Organize It service worker.
 *
 * Strategy:
 *  - Static assets (/static/, /media/): cache-first with background refresh.
 *  - Navigations and HTMX GET fragments (trip detail, day, checklist,
 *    attachments cards): network-first, falling back to the cached copy and,
 *    for full-page navigations, to the offline page.
 *  - Only successful, same-origin GET responses are cached, so authenticated
 *    pages stay per-device and login redirects are never stored.
 *
 * Push notifications are intentionally out of scope for now. The push /
 * notificationclick handlers below are left as documented stubs so webpush can
 * be enabled later without reworking the caching logic.
 */

const CACHE_VERSION = "organize-it-v1";
const OFFLINE_URL = "/offline/";
const PRECACHE_URLS = [OFFLINE_URL];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_VERSION)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting()),
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((names) =>
                Promise.all(
                    names
                        .filter((name) => name.startsWith("organize-it-") && name !== CACHE_VERSION)
                        .map((name) => caches.delete(name)),
                ),
            )
            .then(() => self.clients.claim()),
    );
});

function isCacheableResponse(response) {
    return response && response.status === 200 && response.type === "basic" && !response.redirected;
}

// A handled empty response for uncacheable sub-resources that fail while
// offline (e.g. the browser's automatic /favicon.ico request). Returning this
// instead of Response.error() keeps the console free of "network error
// response" warnings.
function offlineResponse() {
    return new Response("", { status: 503, statusText: "Offline" });
}

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }
    try {
        const response = await fetch(request);
        if (isCacheableResponse(response)) {
            const cache = await caches.open(CACHE_VERSION);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        // Never surface an unhandled rejection: fall back to a handled response.
        return offlineResponse();
    }
}

async function networkFirst(request) {
    const cache = await caches.open(CACHE_VERSION);
    try {
        const response = await fetch(request);
        if (isCacheableResponse(response)) {
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await cache.match(request);
        if (cached) {
            return cached;
        }
        if (request.mode === "navigate") {
            const offline = await cache.match(OFFLINE_URL);
            if (offline) {
                return offline;
            }
        }
        return offlineResponse();
    }
}

// Requests the service worker must not intercept: cross-origin, non-GET, the
// dev live-reload endpoint and any Server-Sent Events stream (long-lived
// connections whose periodic reconnects would otherwise flood with errors).
function shouldBypass(request, url) {
    return (
        request.method !== "GET" ||
        url.origin !== self.location.origin ||
        url.pathname.startsWith("/__reload__/") ||
        (request.headers.get("accept") || "").includes("text/event-stream")
    );
}

self.addEventListener("fetch", (event) => {
    const { request } = event;
    const url = new URL(request.url);
    if (shouldBypass(request, url)) {
        return;
    }
    if (url.pathname.startsWith("/static/") || url.pathname.startsWith("/media/")) {
        event.respondWith(cacheFirst(request));
        return;
    }
    event.respondWith(networkFirst(request));
});

/*
 * Future webpush support (currently disabled). Uncomment and wire VAPID keys
 * to enable push notifications without touching the caching strategy above.
 *
 * self.addEventListener("push", (event) => { ... });
 * self.addEventListener("notificationclick", (event) => { ... });
 */
