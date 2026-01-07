// Close the modal after successfully submitting the form
htmx.on("htmx:beforeSwap", (e) => {
  // Empty response targeting #dialog => hide the modal
  if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
    window.dispatchEvent(new Event('hide-modal'))
    e.detail.shouldSwap = false
  }
})

// Re-initialize Alpine.js after HTMX OOB swaps
htmx.on("htmx:oobAfterSwap", (e) => {
  // Re-initialize Alpine on the OOB swapped element
  if (window.Alpine && e.detail.target) {
    Alpine.initTree(e.detail.target)
  }
})

// Show success/error messages from HTMX triggers
document.body.addEventListener("showMessage", (e) => {
  const { type, message } = e.detail

  // Get or create toast container (matching includes/messages.html style)
  let toastContainer = document.querySelector(".toast.toast-top.toast-center")
  if (!toastContainer) {
    toastContainer = document.createElement("div")
    toastContainer.className = "toast toast-top toast-center"
    document.getElementById("messages")?.appendChild(toastContainer) || document.body.appendChild(toastContainer)
  }

  // Create alert element matching includes/messages.html structure
  const alertDiv = document.createElement("div")
  alertDiv.setAttribute("role", "alert")
  alertDiv.setAttribute("x-data", "{ show: true }")
  alertDiv.setAttribute("x-show", "show")
  alertDiv.setAttribute("x-cloak", "")

  const alertClass = type === "success" ? "alert-success" : type === "error" ? "alert-error" : "alert-info"
  alertDiv.className = `alert alert-soft ${alertClass}`

  alertDiv.innerHTML = `
    <i class="ph-bold ph-info i-md"></i>
    <span class="sr-only">Info</span>
    <div class="flex gap-6 items-center text-sm font-medium">
      ${message}
      <button type="button"
              class="btn btn-xs btn-outline"
              @click="show = false"
              aria-label="Close">
        <span class="sr-only">Close</span>
        Close
      </button>
    </div>
  `

  toastContainer.appendChild(alertDiv)

  // Initialize Alpine on the new element
  if (window.Alpine) {
    Alpine.initTree(alertDiv)
  }

  // Auto-remove after 4 seconds (matching the template)
  setTimeout(() => {
    alertDiv.remove()
  }, 4000)
})


// LeafletJs Map
function createMap(bounds) {
  let map = L.map('map').fitBounds(bounds);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  return map
}

// Global functions for autocomplete (accessible from HTMX-loaded content)
window.setAirportFieldsFromButton = function(button, fieldType = 'origin') {
    console.log('setAirportFieldsFromButton called:', { fieldType });

    // Get the parent <li> element which contains the data attributes
    const listItem = button.closest('li');
    if (!listItem) {
        console.error('Could not find parent list item');
        return;
    }

    const name = listItem.dataset.airportName || "";
    const iata = listItem.dataset.airportIata || "";
    // Convert comma to dot for float fields
    const lat = (listItem.dataset.airportLat || "").replace(',', '.');
    const lon = (listItem.dataset.airportLon || "").replace(',', '.');

    console.log('Values extracted from dataset:', { name, iata, lat, lon });

    // Get the native value setter to avoid triggering events
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;

    // Determine which fields to fill based on fieldType parameter
    if (fieldType === 'origin') {
        const originAirport = document.getElementById("id_origin_airport");
        const originIata = document.getElementById("id_origin_iata");
        const originLat = document.getElementById("id_origin_latitude");
        const originLon = document.getElementById("id_origin_longitude");

        console.log('Origin fields found:', { originAirport, originIata, originLat, originLon });

        if (originAirport) nativeInputValueSetter.call(originAirport, name);
        if (originIata) nativeInputValueSetter.call(originIata, iata);
        if (originLat) nativeInputValueSetter.call(originLat, lat);
        if (originLon) nativeInputValueSetter.call(originLon, lon);

        console.log('Origin fields populated:', {
            airport: originAirport?.value,
            iata: originIata?.value,
            lat: originLat?.value,
            lon: originLon?.value
        });
    } else {
        const destAirport = document.getElementById("id_destination_airport");
        const destIata = document.getElementById("id_destination_iata");
        const destLat = document.getElementById("id_destination_latitude");
        const destLon = document.getElementById("id_destination_longitude");

        console.log('Destination fields found:', { destAirport, destIata, destLat, destLon });

        if (destAirport) nativeInputValueSetter.call(destAirport, name);
        if (destIata) nativeInputValueSetter.call(destIata, iata);
        if (destLat) nativeInputValueSetter.call(destLat, lat);
        if (destLon) nativeInputValueSetter.call(destLon, lon);

        console.log('Destination fields populated:', {
            airport: destAirport?.value,
            iata: destIata?.value,
            lat: destLat?.value,
            lon: destLon?.value
        });
    }

    // Clear autocomplete results
    const resultsDiv = document.getElementById(`${fieldType}-airport-results`);
    if (resultsDiv) resultsDiv.innerHTML = '';
};

window.setStationFieldsFromButton = function(button, fieldType = 'origin') {
    console.log('setStationFieldsFromButton called:', { fieldType });

    // Get the parent <li> element which contains the data attributes
    const listItem = button.closest('li');
    if (!listItem) {
        console.error('Could not find parent list item');
        return;
    }

    const name = listItem.dataset.stationName || "";
    const stationId = listItem.dataset.stationId || "";
    // Convert comma to dot for float fields
    const lat = (listItem.dataset.stationLat || "").replace(',', '.');
    const lon = (listItem.dataset.stationLon || "").replace(',', '.');

    console.log('Values extracted from dataset:', { name, stationId, lat, lon });

    // Get the native value setter to avoid triggering events
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;

    // Determine which fields to fill based on fieldType parameter
    if (fieldType === 'origin') {
        const originStation = document.getElementById("id_origin_station");
        const originStationId = document.getElementById("id_origin_station_id");
        const originLat = document.getElementById("id_origin_latitude");
        const originLon = document.getElementById("id_origin_longitude");

        console.log('Origin station fields found:', { originStation, originStationId, originLat, originLon });

        if (originStation) nativeInputValueSetter.call(originStation, name);
        if (originStationId) nativeInputValueSetter.call(originStationId, stationId);
        if (originLat) nativeInputValueSetter.call(originLat, lat);
        if (originLon) nativeInputValueSetter.call(originLon, lon);

        console.log('Origin station fields populated:', {
            station: originStation?.value,
            stationId: originStationId?.value,
            lat: originLat?.value,
            lon: originLon?.value
        });
    } else {
        const destStation = document.getElementById("id_destination_station");
        const destStationId = document.getElementById("id_destination_station_id");
        const destLat = document.getElementById("id_destination_latitude");
        const destLon = document.getElementById("id_destination_longitude");

        console.log('Destination station fields found:', { destStation, destStationId, destLat, destLon });

        if (destStation) nativeInputValueSetter.call(destStation, name);
        if (destStationId) nativeInputValueSetter.call(destStationId, stationId);
        if (destLat) nativeInputValueSetter.call(destLat, lat);
        if (destLon) nativeInputValueSetter.call(destLon, lon);

        console.log('Destination station fields populated:', {
            station: destStation?.value,
            stationId: destStationId?.value,
            lat: destLat?.value,
            lon: destLon?.value
        });
    }

    // Clear autocomplete results
    const resultsDiv = document.getElementById(`${fieldType}-station-results`);
    if (resultsDiv) resultsDiv.innerHTML = '';
};

if (window.Alpine) {
    Alpine.data("autocompleteForm", () => ({
        geocodeTimer: null,
        addressFilled: false,
        nameFilled: false,
        airportFilled: false,
        stationFilled: false,
        checkAndTrigger() {
            clearTimeout(this.geocodeTimer);
            if (this.$refs.name.value && this.$refs.city.value) {
                this.geocodeTimer = setTimeout(() => {
                    this.$refs.name.dispatchEvent(new CustomEvent("trigger-geocode"));
                }, 500);
            }
        },
        setFields(nameId, addressId) {
            const name = document.getElementById(nameId)?.textContent || "";
            const address = document.getElementById(addressId)?.textContent || "";
            document.getElementById("id_name").value = name;
            document.getElementById("id_address").value = address;
            this.nameFilled = true;
            this.addressFilled = true;
            setTimeout(() => {
                this.nameFilled = false;
                this.addressFilled = false;
            }, 500);
        }
    }));

    Alpine.data("overlapChecker", () => ({
        checkOverlap() {
            const startTime = this.$refs.startTime.value;
            const duration = this.$refs.duration.value;
            if (startTime && duration) {
                const endTime = new Date(`2000-01-01T${startTime}`);
                endTime.setMinutes(endTime.getMinutes() + parseInt(duration));
                const endTimeStr = endTime.toTimeString().slice(0, 5);
                htmx.ajax("GET", this.$root.dataset.overlapUrl, {
                    target: "#overlap-warning",
                    values: { start_time: startTime, end_time: endTimeStr }
                });
            }
        }
    }));

    console.log("Alpine components loaded");
}
