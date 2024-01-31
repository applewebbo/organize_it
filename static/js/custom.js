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
