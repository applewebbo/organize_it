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


// LeafletJs Map
function createMap(bounds) {
  let map = L.map('map').fitBounds(bounds);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  return map
}

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
        },
        setAirportFields(nameId, iataId, latId, lonId, fieldType = 'origin') {
            const name = document.getElementById(nameId)?.textContent || "";
            const iata = document.getElementById(iataId)?.textContent || "";
            const lat = document.getElementById(latId)?.textContent || "";
            const lon = document.getElementById(lonId)?.textContent || "";

            // Determine which fields to fill based on fieldType parameter
            if (fieldType === 'origin') {
                const originAirport = document.getElementById("id_origin_airport");
                const originIata = document.getElementById("id_origin_iata");
                const originLat = document.getElementById("id_origin_latitude");
                const originLon = document.getElementById("id_origin_longitude");

                if (originAirport) originAirport.value = name;
                if (originIata) originIata.value = iata;
                if (originLat) originLat.value = lat;
                if (originLon) originLon.value = lon;
            } else {
                const destAirport = document.getElementById("id_destination_airport");
                const destIata = document.getElementById("id_destination_iata");
                const destLat = document.getElementById("id_destination_latitude");
                const destLon = document.getElementById("id_destination_longitude");

                if (destAirport) destAirport.value = name;
                if (destIata) destIata.value = iata;
                if (destLat) destLat.value = lat;
                if (destLon) destLon.value = lon;
            }

            this.airportFilled = true;
            setTimeout(() => {
                this.airportFilled = false;
            }, 500);
        },
        setStationFields(nameId, stationIdElementId, latId, lonId, fieldType = 'origin') {
            const name = document.getElementById(nameId)?.textContent || "";
            const stationId = document.getElementById(stationIdElementId)?.textContent || "";
            const lat = document.getElementById(latId)?.textContent || "";
            const lon = document.getElementById(lonId)?.textContent || "";

            // Determine which fields to fill based on fieldType parameter
            if (fieldType === 'origin') {
                const originStation = document.getElementById("id_origin_station");
                const originStationId = document.getElementById("id_origin_station_id");
                const originLat = document.getElementById("id_origin_latitude");
                const originLon = document.getElementById("id_origin_longitude");

                if (originStation) originStation.value = name;
                if (originStationId) originStationId.value = stationId;
                if (originLat) originLat.value = lat;
                if (originLon) originLon.value = lon;
            } else {
                const destStation = document.getElementById("id_destination_station");
                const destStationId = document.getElementById("id_destination_station_id");
                const destLat = document.getElementById("id_destination_latitude");
                const destLon = document.getElementById("id_destination_longitude");

                if (destStation) destStation.value = name;
                if (destStationId) destStationId.value = stationId;
                if (destLat) destLat.value = lat;
                if (destLon) destLon.value = lon;
            }

            this.stationFilled = true;
            setTimeout(() => {
                this.stationFilled = false;
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
