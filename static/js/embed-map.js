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

function buildPopupHtml(item, color, iconClass, groupLabel) {
  const headerPills = [];
  if (groupLabel) {
    headerPills.push(
      `<span class="embed-popup-pill" style="background:${esc(color)}">` +
        `<i class="ph-bold ${esc(iconClass)}" aria-hidden="true"></i>${esc(groupLabel)}</span>`
    );
  }
  if (item.badge) {
    headerPills.push(`<span class="embed-popup-badge">${esc(item.badge)}</span>`);
  }

  const rows = [];
  if (item.address) {
    rows.push(
      `<div class="embed-popup-row"><i class="ph-bold ph-map-pin" aria-hidden="true"></i><span>${esc(item.address)}</span></div>`
    );
  }
  if (item.start_time || item.duration) {
    const parts = [item.start_time, item.duration].filter(Boolean).map(esc);
    rows.push(
      `<div class="embed-popup-row"><i class="ph-bold ph-timer" aria-hidden="true"></i><span>${parts.join(" · ")}</span></div>`
    );
  }
  if (item.check_in || item.check_out) {
    const stayTimes = [
      item.check_in ? `Check-in ${esc(item.check_in)}` : "",
      item.check_out ? `Check-out ${esc(item.check_out)}` : "",
    ].filter(Boolean);
    rows.push(
      `<div class="embed-popup-row"><i class="ph-bold ph-clock" aria-hidden="true"></i><span>${stayTimes.join(" · ")}</span></div>`
    );
  }
  if (item.phone) {
    rows.push(
      `<div class="embed-popup-row"><i class="ph-bold ph-phone" aria-hidden="true"></i><span>${esc(item.phone)}</span></div>`
    );
  }

  return (
    `<div class="embed-popup">` +
    (headerPills.length ? `<div class="embed-popup-header">${headerPills.join("")}</div>` : "") +
    `<div class="embed-popup-title">${esc(item.name)}</div>` +
    (rows.length ? `<div class="embed-popup-details">${rows.join("")}</div>` : "") +
    `</div>`
  );
}

function addMarker(layer, item, color, iconClass, markersById, onSelect, groupLabel) {
  const marker = new Marker([item.lat, item.lng], {
    icon: makeCircleIcon(color, iconClass),
  });
  marker.bindPopup(buildPopupHtml(item, color, iconClass, groupLabel), { maxWidth: 280 });
  marker.bindTooltip(esc(item.tooltip || item.name), {
    direction: "bottom",
    offset: [0, 10],
  });
  if (item.id && markersById) {
    markersById.set(item.id, marker);
  }
  if (item.id && onSelect) {
    marker.on("click", () => onSelect(item.id));
  }
  layer.addLayer(marker);
  return marker;
}

function renderTripMap(map, data, container) {
  const wrapper = container.closest("[data-embed-map-wrapper]") || container.parentElement;
  const cluster = new MarkerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
  }).addTo(map);

  const markersById = new Map();
  const markerEntries = [];
  let selectedDay = "all";
  let selectedType = "all";

  const setActiveItem = (id) => {
    if (!wrapper) return;
    wrapper.querySelectorAll(".embed-map-item.is-active").forEach((el) => {
      el.classList.remove("is-active");
    });
    if (!id) return;
    const itemEl = wrapper.querySelector(`.embed-map-item[data-map-item-id="${CSS.escape(id)}"]`);
    if (itemEl) {
      itemEl.classList.add("is-active");
    }
  };

  const onMarkerClick = (id) => setActiveItem(id);

  const registerMarker = (item, color, iconClass, group, kind, groupLabel) => {
    const marker = addMarker(cluster, item, color, iconClass, markersById, onMarkerClick, groupLabel);
    markerEntries.push({ marker, group, kind });
  };

  (data.stays || []).forEach((stay) => {
    registerMarker(stay, "#6b7280", "ph-bed", "stays", "stay", data.stay_label || "");
  });

  (data.days || []).forEach((day) => {
    const group = `day-${day.number}`;
    (day.events || []).forEach((ev) => {
      const iconClass = ev.kind === "meal" ? "ph-fork-knife" : "ph-images";
      registerMarker(ev, day.color, iconClass, group, ev.kind, day.label);
    });
  });

  (data.unassigned || []).forEach((ev) => {
    const iconClass = ev.kind === "meal" ? "ph-fork-knife" : "ph-images";
    registerMarker(ev, "#9ca3af", iconClass, "unassigned", ev.kind, data.unassigned_label || "");
  });

  if (data.bounds) {
    map.fitBounds(new LatLngBounds(data.bounds), { padding: [30, 30], maxZoom: 15 });
  }

  if (wrapper) {
    wrapper.querySelectorAll("[data-day-color]").forEach((label) => {
      label.style.color = label.dataset.dayColor;
    });

    wrapper.querySelectorAll(".embed-map-item[data-map-item-id]").forEach((itemEl) => {
      if (itemEl.dataset.mapWired) return;
      itemEl.dataset.mapWired = "1";
      const activate = () => {
        const id = itemEl.dataset.mapItemId;
        setActiveItem(id);
        const marker = markersById.get(id);
        if (!marker) return;
        cluster.zoomToShowLayer(marker, () => {
          map.setView(marker.getLatLng(), Math.max(map.getZoom(), 15), { animate: true });
          marker.openPopup();
        });
      };
      itemEl.addEventListener("click", activate);
      itemEl.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
    });

    const getTargetGroup = () =>
      selectedDay === "unassigned" ? "unassigned" : `day-${selectedDay}`;

    const matchesFilters = (group, kind) => {
      const targetGroup = getTargetGroup();
      const dayOk = selectedDay === "all" || group === targetGroup;
      const typeOk = selectedType === "all" || kind === selectedType;
      return dayOk && typeOk;
    };

    const updateVisibleList = () => {
      const bounds = map.getBounds();
      let totalVisible = 0;

      wrapper.querySelectorAll("[data-embed-map-group]").forEach((groupEl) => {
        const groupName = groupEl.dataset.embedMapGroup;

        let groupVisibleCount = 0;
        groupEl.querySelectorAll(".embed-map-item[data-map-item-id]").forEach((itemEl) => {
          const marker = markersById.get(itemEl.dataset.mapItemId);
          const visible =
            matchesFilters(groupName, itemEl.dataset.mapItemKind) &&
            Boolean(marker && bounds.contains(marker.getLatLng()));
          itemEl.classList.toggle("hidden", !visible);
          if (!visible) {
            itemEl.classList.remove("is-active");
          } else {
            groupVisibleCount += 1;
            totalVisible += 1;
          }
        });

        groupEl.classList.toggle("hidden", groupVisibleCount === 0);
      });

      const emptyEl = wrapper.querySelector("[data-embed-map-empty]");
      if (emptyEl) {
        emptyEl.classList.toggle("hidden", totalVisible > 0);
      }
    };

    const syncFilterButtons = (selector, attr, activeValue) => {
      wrapper.querySelectorAll(selector).forEach((btn) => {
        const isActive = btn.dataset[attr] === activeValue;
        btn.classList.toggle("btn-primary", isActive);
        btn.classList.toggle("btn-soft", !isActive);
        btn.setAttribute("aria-pressed", isActive ? "true" : "false");
      });
    };

    const applyFilters = () => {
      syncFilterButtons("[data-day-filter]", "dayFilter", selectedDay);
      syncFilterButtons("[data-type-filter]", "typeFilter", selectedType);

      cluster.clearLayers();
      const visibleLatLngs = [];
      markerEntries.forEach(({ marker, group, kind }) => {
        if (matchesFilters(group, kind)) {
          cluster.addLayer(marker);
          visibleLatLngs.push(marker.getLatLng());
        }
      });

      if (visibleLatLngs.length === 1) {
        map.setView(visibleLatLngs[0], 15, { animate: true });
      } else if (visibleLatLngs.length > 1) {
        map.fitBounds(new LatLngBounds(visibleLatLngs), { padding: [30, 30], maxZoom: 15 });
      }

      updateVisibleList();
    };

    wrapper.querySelectorAll("[data-day-filter]").forEach((btn) => {
      if (btn.dataset.dayFilterWired) return;
      btn.dataset.dayFilterWired = "1";
      btn.addEventListener("click", () => {
        selectedDay = btn.dataset.dayFilter || "all";
        selectedType = "all";
        applyFilters();
      });
    });

    wrapper.querySelectorAll("[data-type-filter]").forEach((btn) => {
      if (btn.dataset.typeFilterWired) return;
      btn.dataset.typeFilterWired = "1";
      btn.addEventListener("click", () => {
        selectedType = btn.dataset.typeFilter || "all";
        selectedDay = "all";
        applyFilters();
      });
    });

    map.on("moveend", updateVisibleList);
    updateVisibleList();
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
    renderTripMap(map, data, container);
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
