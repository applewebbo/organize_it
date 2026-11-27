/**
 * embed-map.js
 * Leaflet 2.0 + MarkerCluster ES module for embedded trip-events and per-day maps
 * (replaces Folium iframes). Handles HTMX swap lifecycle and Alpine x-show resizes.
 */

import { DivIcon, FeatureGroup, LatLngBounds, LeafletMap, Marker, TileLayer } from "leaflet";
import { MarkerClusterGroup } from "leaflet.markercluster";

const TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}";
const TILE_ATTR =
  '&copy; <a href="https://www.esri.com">Esri</a> &mdash; Esri, DeLorme, NAVTEQ';

const DAY_PIN_COLORS = {
  experience: "#10b981",
  meal: "#f59e0b",
  stay: "#0ea5e9",
  transfer: "#ef4444",
};

const DAY_PIN_ICONS = {
  experience: "ph-ticket",
  meal: "ph-fork-knife",
  stay: "ph-bed",
};

const instances = new WeakMap();

function esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function makeCircleIcon(color, iconClass) {
  return new DivIcon({
    className: "",
    html:
      `<div style="background:${color};width:30px;height:30px;border-radius:50%;` +
      `display:flex;align-items:center;justify-content:center;` +
      `border:2px solid rgba(255,255,255,0.85);box-shadow:0 2px 5px rgba(0,0,0,0.35)">` +
      `<i class="ph-bold ${iconClass}" style="color:#fff;font-size:13px;line-height:1"></i>` +
      `</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -15],
  });
}

function addMarker(layer, item, color, iconClass) {
  const marker = new Marker([item.lat, item.lng], {
    icon: makeCircleIcon(color, iconClass),
  });
  marker.bindPopup(esc(item.name));
  marker.bindTooltip(esc(item.tooltip || item.name));
  layer.addLayer(marker);
}

function renderTripMap(map, data) {
  const cluster = new MarkerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
  }).addTo(map);

  (data.stays || []).forEach((stay) => {
    addMarker(cluster, stay, "#6b7280", "ph-bed");
  });

  (data.days || []).forEach((day) => {
    (day.events || []).forEach((ev) => {
      const iconClass = ev.kind === "meal" ? "ph-fork-knife" : "ph-map-pin";
      addMarker(cluster, ev, day.color, iconClass);
    });
  });

  (data.unassigned || []).forEach((ev) => {
    const iconClass = ev.kind === "meal" ? "ph-fork-knife" : "ph-map-pin";
    addMarker(cluster, ev, "#9ca3af", iconClass);
  });

  if (data.bounds) {
    map.fitBounds(new LatLngBounds(data.bounds), { padding: [30, 30], maxZoom: 15 });
  }
}

function renderDayMap(map, data) {
  const group = new FeatureGroup().addTo(map);

  (data.markers || []).forEach((item) => {
    const color = DAY_PIN_COLORS[item.kind] || DAY_PIN_COLORS.experience;
    const iconClass = item.icon ? `ph-${item.icon}` : (DAY_PIN_ICONS[item.kind] || "ph-map-pin");
    addMarker(group, item, color, iconClass);
  });

  if (data.bounds) {
    map.fitBounds(new LatLngBounds(data.bounds), { maxZoom: 15 });
  }
}

function destroyMap(container) {
  const entry = instances.get(container);
  if (!entry) return;
  entry.observer.disconnect();
  entry.map.remove();
  instances.delete(container);
}

function cleanupEmbedMaps(root) {
  if (!root || !root.querySelectorAll) return;
  if (root.matches?.("[data-embed-map]")) {
    destroyMap(root);
  }
  root.querySelectorAll("[data-embed-map]").forEach(destroyMap);
}

function initEmbedMap(container) {
  destroyMap(container);

  const scriptEl = container.querySelector('script[type="application/json"]');
  const canvas = container.querySelector(".embed-map-canvas");
  if (!scriptEl || !canvas) return;

  let data;
  try {
    data = JSON.parse(scriptEl.textContent);
  } catch (e) {
    console.error("embed-map: failed to parse map JSON", e);
    return;
  }
  if (!data) return;

  const map = new LeafletMap(canvas);
  new TileLayer(TILE_URL, { maxZoom: 19, attribution: TILE_ATTR }).addTo(map);

  if (data.mode === "trip") {
    renderTripMap(map, data);
  } else if (data.mode === "day") {
    renderDayMap(map, data);
  }

  const observer = new ResizeObserver(() => {
    if (canvas.offsetWidth > 0 && canvas.offsetHeight > 0) {
      map.invalidateSize();
    }
  });
  observer.observe(canvas);

  instances.set(container, { map, observer });
}

function initEmbedMaps(root = document) {
  if (!root || !root.querySelectorAll) return;
  if (root.matches?.("[data-embed-map]")) {
    initEmbedMap(root);
  }
  root.querySelectorAll("[data-embed-map]").forEach(initEmbedMap);
}

function resolveTarget(event) {
  const target = event.detail?.ctx?.target;
  if (typeof target === "string") return document.querySelector(target);
  return target || event.target || document;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initEmbedMaps(document));
} else {
  initEmbedMaps(document);
}

document.addEventListener("htmx:before:swap", (event) => {
  cleanupEmbedMaps(resolveTarget(event));
});

document.addEventListener("htmx:after:swap", (event) => {
  initEmbedMaps(resolveTarget(event));
});
