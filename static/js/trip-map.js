/**
 * trip-map.js
 * Leaflet map for the unified trip map view.
 *
 * Initial markers come from <script id="map-initial-data" type="application/json">,
 * populated server-side. This avoids any DOM data-* parsing issues.
 *
 * Sidebar items still use data-* attributes for click → fly-to interaction.
 * Search results use data-* attributes (they are swapped by HTMX).
 */

(function () {
  "use strict";

  let map = null;
  let searchLayer = null;
  let eventsLayer = null;

  // Destination name → [lat, lng] for stage dropdown → refocus (issue #370)
  let stageCoords = {};

  // Index: "name|lat|lng" → Leaflet marker, for sidebar-click → popup
  const eventMarkerIndex = new Map();

  const DEFAULT_CENTER = [45.0703, 7.6869];
  const DEFAULT_ZOOM = 5;

  const PIN_COLORS = {
    search: "#6366f1",
    experience: "#10b981",
    meal: "#f59e0b",
    stay: "#0ea5e9",
  };

  /* ── Helpers ────────────────────────────────────────────────────── */
  function esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }

  function popup(name, address) {
    return `<strong>${esc(name)}</strong>${address ? `<br><small>${esc(address)}</small>` : ""}`;
  }

  const KIND_ICON = {
    stay: "ph-bed",
    experience: "ph-ticket",
    meal: "ph-fork-knife",
  };

  // Search result marker: numbered pin
  function makeIcon(color, label) {
    const inner = label != null
      ? `<span style="transform:rotate(45deg);font-size:10px;font-weight:700;line-height:1">${label}</span>`
      : "";
    return L.divIcon({
      className: "",
      html: `<div style="width:28px;height:28px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:${color};display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.35);color:#fff;font-size:13px;">${inner}</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 28],
      popupAnchor: [0, -30],
    });
  }

  // Trip event marker: type icon + day number (stays show only icon, no day number)
  function makeEventIcon(color, kind, dayIndex) {
    const iconClass = KIND_ICON[kind] || "ph-map-pin";
    const showDay = kind !== "stay" && dayIndex > 0;
    const inner = showDay
      ? `<div style="transform:rotate(45deg);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px">` +
        `<i class="ph-bold ${iconClass}" style="font-size:11px;line-height:1"></i>` +
        `<span style="font-size:11px;font-weight:700;line-height:1">${dayIndex}</span>` +
        `</div>`
      : `<i class="ph-bold ${iconClass}" style="font-size:13px;line-height:1;transform:rotate(45deg)"></i>`;
    return L.divIcon({
      className: "",
      html: `<div style="width:32px;height:32px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:${color};display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,.35);color:#fff">` +
            inner +
            `</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
      popupAnchor: [0, -34],
    });
  }

  function markerKey(name, lat, lng) {
    return `${name}|${lat}|${lng}`;
  }

  function highlightItem(item) {
    document.querySelectorAll(".map-sidebar-item.is-active")
      .forEach((el) => el.classList.remove("is-active"));
    if (item) item.classList.add("is-active");
  }

  /* ── Init ───────────────────────────────────────────────────────── */
  function initMap() {
    if (map) return;
    const el = document.getElementById("trip-map");
    if (!el) return;

    map = L.map("trip-map", { center: DEFAULT_CENTER, zoom: DEFAULT_ZOOM });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    searchLayer = L.featureGroup().addTo(map);
    eventsLayer = L.featureGroup().addTo(map);

    // Load initial trip events from embedded JSON (reliable, no DOM parsing)
    const dataEl = document.getElementById("map-initial-data");
    if (dataEl) {
      try {
        const items = JSON.parse(dataEl.textContent);
        buildEventsFromData(items);
      } catch (e) {
        console.error("trip-map: failed to parse map-initial-data", e);
      }
    }

    // Load stage coordinates for the dropdown → refocus interaction
    const stageEl = document.getElementById("stage-coords-data");
    if (stageEl) {
      try {
        stageCoords = JSON.parse(stageEl.textContent) || {};
      } catch (e) {
        console.error("trip-map: failed to parse stage-coords-data", e);
      }
    }

    // Wire sidebar item clicks (data-* attributes for fly-to)
    wireSidebarClicks();
    // Wire stage dropdowns (search + AI tabs) → refocus the map
    wireStageSelects();
  }

  /* ── Stage dropdown → refocus map ───────────────────────────────── */
  function focusStage(destination) {
    if (!map) return;
    if (!destination) {
      // "— all stages —": fit back to every event marker
      const bounds = eventsLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
      }
      return;
    }
    // Fit tightly to the stage's own markers so events spread out and use the
    // available space, rather than centring at a fixed (wide) zoom.
    const points = [];
    eventsLayer.eachLayer((m) => {
      if (m.stageName === destination) points.push(m.getLatLng());
    });
    if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points), { padding: [60, 60], maxZoom: 16 });
    } else if (points.length === 1) {
      map.setView(points[0], 15, { animate: true });
    } else {
      // No markers for this stage: fall back to its derived centre point.
      const coords = stageCoords[destination];
      if (coords) map.setView(coords, 14, { animate: true });
    }
  }

  function wireStageSelects() {
    document
      .querySelectorAll("select[name='stage_destination']:not([data-wired])")
      .forEach((sel) => {
        sel.dataset.wired = "1";
        sel.addEventListener("change", () => focusStage(sel.value));
      });
  }

  /* ── Build events layer from data array ─────────────────────────── */
  function buildEventsFromData(items) {
    eventsLayer.clearLayers();
    eventMarkerIndex.clear();
    const bounds = [];

    items.forEach((item) => {
      const { lat, lng, name, address, kind } = item;
      if (!lat || !lng) return;

      const color = PIN_COLORS[kind] || PIN_COLORS.experience;
      const marker = L.marker([lat, lng], { icon: makeEventIcon(color, kind, item.day_index) })
        .bindPopup(popup(name, address), { autoPan: false });
      marker.stageName = item.stage || null;

      // Clicking a marker highlights matching sidebar item
      marker.on("click", () => {
        marker.openPopup();
        const sidebarItem = findSidebarItem(name, lat, lng);
        if (sidebarItem) highlightItem(sidebarItem);
      });

      eventsLayer.addLayer(marker);
      eventMarkerIndex.set(markerKey(name, lat, lng), marker);
      bounds.push([lat, lng]);
    });

    if (bounds.length === 1) {
      map.setView(bounds[0], 14);
    } else if (bounds.length > 1) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40], maxZoom: 15 });
    }

    map.invalidateSize();
  }

  /* ── Find matching sidebar item by name + coords ─────────────────── */
  function findSidebarItem(name, lat, lng) {
    for (const item of document.querySelectorAll("[data-role='trip-event']")) {
      if (
        item.dataset.name === name &&
        Math.abs(parseFloat(item.dataset.lat) - lat) < 0.00001 &&
        Math.abs(parseFloat(item.dataset.lng) - lng) < 0.00001
      ) {
        return item;
      }
    }
    return null;
  }

  /* ── Wire sidebar item clicks (pan to coords + open popup) ──────── */
  function wireSidebarClicks() {
    document.querySelectorAll("[data-role='trip-event']:not([data-wired])").forEach((item) => {
      item.dataset.wired = "1";
      item.addEventListener("click", () => {
        highlightItem(item);
        const lat = parseFloat(item.dataset.lat);
        const lng = parseFloat(item.dataset.lng);
        if (!isNaN(lat) && !isNaN(lng)) {
          const marker = eventsLayer.getLayers().find((m) => {
            const p = m.getLatLng();
            return Math.abs(p.lat - lat) < 0.00001 && Math.abs(p.lng - lng) < 0.00001;
          });
          if (marker) {
            map.setView([lat, lng], Math.max(map.getZoom(), 14), { animate: false });
            marker.openPopup();
          }
        }
      });
    });
  }

  /* ── Search results layer (from HTMX swapped DOM) ───────────────── */
  function rebuildSearchLayer() {
    if (!map || !searchLayer) return;
    searchLayer.clearLayers();

    const items = document.querySelectorAll("[data-role='place-result']");
    const bounds = [];

    items.forEach((item, idx) => {
      const lat = parseFloat(item.dataset.lat);
      const lng = parseFloat(item.dataset.lng);
      if (isNaN(lat) || isNaN(lng)) return;

      const num = idx + 1;

      // Add number badge to sidebar item
      if (!item.querySelector(".place-num-badge")) {
        const badge = document.createElement("span");
        badge.className = "place-num-badge";
        badge.style.cssText = "display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:#6366f1;color:#fff;font-size:11px;font-weight:700;flex-shrink:0";
        badge.textContent = num;
        item.querySelector("div.flex").prepend(badge);
      }

      const marker = L.marker([lat, lng], { icon: makeIcon(PIN_COLORS.search, num) })
        .bindPopup(popup(item.dataset.name, item.dataset.address), { autoPan: false });

      marker.on("click", () => { highlightItem(item); marker.openPopup(); });
      item.addEventListener("mouseenter", () => marker.openPopup());
      item.addEventListener("click", () => {
        highlightItem(item);
        map.setView([lat, lng], 16, { animate: false });
        marker.openPopup();
      });

      searchLayer.addLayer(marker);
      bounds.push([lat, lng]);
    });

    if (bounds.length === 1) {
      map.setView(bounds[0], 16);
    } else if (bounds.length > 1) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [40, 40], maxZoom: 16 });
    }
    map.invalidateSize();
  }

  /* ── Rebuild events layer after HTMX swap ────────────────────────── */
  function rebuildEventsLayer() {
    if (!map || !eventsLayer) return;

    // Re-read JSON data from the embedded script tag
    const dataEl = document.getElementById("map-initial-data");
    if (dataEl) {
      try {
        const items = JSON.parse(dataEl.textContent);
        buildEventsFromData(items);
      } catch (e) {
        console.error("trip-map: failed to rebuild events layer", e);
      }
    }
    wireSidebarClicks();
  }

  /* ── HTMX wiring ─────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", initMap);

  document.body.addEventListener("htmx:afterSwap", (event) => {
    const id = event.detail.target?.id;
    if (id === "search-results-panel") rebuildSearchLayer();
    if (id === "events-panel") {
      // After adding an event, update the JSON and rebuild
      // (the JSON is embedded server-side; a full page reload would refresh it,
      //  but for HTMX swap we rebuild from the existing JSON)
      wireSidebarClicks();
    }
  });

  window.tripMap = { initMap, rebuildSearchLayer, rebuildEventsLayer };
})();
