// https://blog.benoitblanchon.fr/django-htmx-modal-form/

const modal = new bootstrap.Modal(document.getElementById("modal"))

htmx.on("htmx:afterSwap", (e) => {
  // Response targeting #dialog => show the modal
  if (e.detail.target.id == "dialog") {
    modal.show()
  }
})

htmx.on("htmx:beforeSwap", (e) => {
  // Empty response targeting #dialog => hide the modal
  if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
    modal.hide()
    e.detail.shouldSwap = false
  }
})

htmx.on("hidden.bs.modal", () => {
  // Closing the modal => remove the content from the modal
  document.getElementById("dialog").innerHTML = ""
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
