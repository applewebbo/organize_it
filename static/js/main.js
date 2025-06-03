// Close the modal after successfully submitting the form
htmx.on("htmx:beforeSwap", (e) => {
  // Empty response targeting #dialog => hide the modal
  if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
    window.dispatchEvent(new Event('hide-modal'))
    e.detail.shouldSwap = false
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
