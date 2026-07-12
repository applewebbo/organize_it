from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from trips.models import (
    MainTransfer,
    MainTransferConnection,
)
from trips.widgets import TransportModeRadioSelect


class MainTransferBaseForm(forms.ModelForm):
    """
    Base form for MainTransfer - common fields for all transport types.
    Must be extended by type-specific forms.
    """

    direction = forms.ChoiceField(
        choices=MainTransfer.Direction.choices,
        label=_("Direction"),
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = MainTransfer
        fields = [
            "direction",
            "start_time",
            "end_time",
            "notes",
        ]
        labels = {
            "start_time": _("Departure Time"),
            "end_time": _("Arrival Time"),
            "notes": _("Notes"),
        }
        help_texts = {
            "start_time": "",
            "end_time": "",
            "notes": "",
        }
        widgets = {
            "start_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "end_time": forms.TimeInput(
                attrs={"type": "time", "class": "input input-bordered"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "textarea textarea-bordered", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop("trip", None)
        kwargs.pop("home_address", None)  # Consumed by car/other subforms; ignored here
        super().__init__(*args, **kwargs)
        self.fields["start_time"].required = True
        self.fields["end_time"].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.trip:  # pragma: no cover
            instance.trip = self.trip

        # Save type-specific data in JSONField
        type_specific_data = self.get_type_specific_data()
        if type_specific_data:  # pragma: no cover
            instance.type_specific_data = type_specific_data

        if commit:  # pragma: no cover
            instance.save()

        return instance

    def get_type_specific_data(self):
        """
        Override in child forms to populate type_specific_data.
        Returns a dict with type-specific fields.
        """
        return {}


class FlightMainTransferForm(MainTransferBaseForm):
    """Form for flight main transfers with airport autocomplete"""

    # Airport fields (autocomplete with CSV lookup)
    origin_airport = forms.CharField(
        label=_("Departure Airport"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by name or IATA code (e.g., FCO, Rome)"),
                "autocomplete": "off",
                "data-autocomplete-type": "airport",
            }
        ),
        help_text=_("Search for airport by name, city, or IATA code"),
    )

    origin_iata = forms.CharField(
        max_length=10, required=False, widget=forms.HiddenInput()
    )

    origin_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    origin_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    destination_airport = forms.CharField(
        label=_("Arrival Airport"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by name or IATA code"),
                "autocomplete": "off",
                "data-autocomplete-type": "airport",
            }
        ),
        help_text=_("Search for airport by name, city, or IATA code"),
    )

    destination_iata = forms.CharField(
        max_length=10, required=False, widget=forms.HiddenInput()
    )

    destination_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    destination_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    # Flight-specific fields
    flight_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Flight Number"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "AZ1234"}
        ),
    )

    terminal = forms.CharField(
        max_length=10,
        required=False,
        label=_("Terminal"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "T1"}
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_airport",
            "origin_iata",
            "origin_latitude",
            "origin_longitude",
            "destination_airport",
            "destination_iata",
            "destination_latitude",
            "destination_longitude",
        ]

    def __init__(self, *args, **kwargs):
        autocomplete = kwargs.pop("autocomplete", True)
        super().__init__(*args, **kwargs)

        # Add HTMX attributes for airport autocomplete (similar to EventForm geocode)
        if autocomplete:
            search_url_origin = f"{reverse('trips:search-airports')}?field_type=origin"
            search_url_dest = (
                f"{reverse('trips:search-airports')}?field_type=destination"
            )
            origin_htmx_attrs = {
                "hx-post": search_url_origin,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#origin-airport-results",
                "hx-vals": "js:{airport_query: (event && event.target) ? event.target.value : this.value}",
            }
            dest_htmx_attrs = {
                "hx-post": search_url_dest,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#destination-airport-results",
                "hx-vals": "js:{airport_query: (event && event.target) ? event.target.value : this.value}",
            }
            self.fields["origin_airport"].widget.attrs.update(origin_htmx_attrs)
            self.fields["destination_airport"].widget.attrs.update(dest_htmx_attrs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_airport"].initial = self.instance.origin_name
            self.fields["origin_iata"].initial = self.instance.origin_code
            self.fields["destination_airport"].initial = self.instance.destination_name
            self.fields["destination_iata"].initial = self.instance.destination_code

            # Populate type-specific fields
            if self.instance.type_specific_data:
                self.fields["flight_number"].initial = self.instance.flight_number
                self.fields["terminal"].initial = self.instance.terminal

        # Pre-fill from arrival if this is a new departure
        if (
            self.trip
            and not self.instance.pk
            and self.initial.get("direction") == MainTransfer.Direction.DEPARTURE
        ):
            arrival = MainTransfer.objects.filter(
                trip=self.trip,
                direction=MainTransfer.Direction.ARRIVAL,
                type=MainTransfer.Type.PLANE,
            ).first()

            if arrival:
                # Invert origin ↔ destination
                self.fields["origin_airport"].initial = arrival.destination_name
                self.fields["origin_iata"].initial = arrival.destination_code
                self.fields["origin_latitude"].initial = arrival.destination_latitude
                self.fields["origin_longitude"].initial = arrival.destination_longitude

                self.fields["destination_airport"].initial = arrival.origin_name
                self.fields["destination_iata"].initial = arrival.origin_code
                self.fields["destination_latitude"].initial = arrival.origin_latitude
                self.fields["destination_longitude"].initial = arrival.origin_longitude

                # Set flag for message display
                self.prefilled_from_arrival = True

    def clean(self):
        cleaned_data = super().clean()

        # Use coordinate values from hidden fields (populated by autocomplete JS)
        origin_lat = cleaned_data.get("origin_latitude")
        origin_lon = cleaned_data.get("origin_longitude")
        dest_lat = cleaned_data.get("destination_latitude")
        dest_lon = cleaned_data.get("destination_longitude")

        # Store coordinates for save() method
        if origin_lat and origin_lon:
            self._origin_coords = (origin_lat, origin_lon)
        if dest_lat and dest_lon:
            self._destination_coords = (dest_lat, dest_lon)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Populate model fields
        instance.type = MainTransfer.Type.PLANE
        instance.origin_code = self.cleaned_data["origin_iata"]
        instance.origin_name = self.cleaned_data["origin_airport"]
        instance.destination_code = self.cleaned_data["destination_iata"]
        instance.destination_name = self.cleaned_data["destination_airport"]

        # Coordinates from CSV
        if hasattr(self, "_origin_coords"):
            instance.origin_latitude, instance.origin_longitude = self._origin_coords
        if hasattr(self, "_destination_coords"):
            (
                instance.destination_latitude,
                instance.destination_longitude,
            ) = self._destination_coords

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        """Populate flight-specific fields in JSONField"""
        data = {}

        if self.cleaned_data.get("flight_number"):
            data["flight_number"] = self.cleaned_data["flight_number"]
        if self.cleaned_data.get("terminal"):
            data["terminal"] = self.cleaned_data["terminal"]

        return data


class TrainMainTransferForm(MainTransferBaseForm):
    """Form for train main transfers with station autocomplete"""

    # Station fields (autocomplete with CSV lookup)
    origin_station = forms.CharField(
        label=_("Departure Station"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by station name"),
                "autocomplete": "off",
                "data-autocomplete-type": "station",
            }
        ),
        help_text=_("Search for train station by name"),
    )

    origin_station_id = forms.CharField(
        max_length=20, required=False, widget=forms.HiddenInput()
    )

    origin_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    origin_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    destination_station = forms.CharField(
        label=_("Arrival Station"),
        max_length=200,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Search by station name"),
                "autocomplete": "off",
                "data-autocomplete-type": "station",
            }
        ),
        help_text=_("Search for train station by name"),
    )

    destination_station_id = forms.CharField(
        max_length=20, required=False, widget=forms.HiddenInput()
    )

    destination_latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    destination_longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    train_number = forms.CharField(
        max_length=20,
        required=False,
        label=_("Train Number"),
        widget=forms.TextInput(
            attrs={"class": "input input-bordered", "placeholder": "FR9612"}
        ),
        help_text=_(
            "Optional. If provided, enables direct train status lookup on Viaggiatreno."
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_station",
            "origin_station_id",
            "origin_latitude",
            "origin_longitude",
            "destination_station",
            "destination_station_id",
            "destination_latitude",
            "destination_longitude",
        ]

    def __init__(self, *args, **kwargs):
        autocomplete = kwargs.pop("autocomplete", True)
        super().__init__(*args, **kwargs)

        # Add HTMX attributes for station autocomplete (similar to EventForm geocode)
        if autocomplete:
            search_url_origin = f"{reverse('trips:search-stations')}?field_type=origin"
            search_url_dest = (
                f"{reverse('trips:search-stations')}?field_type=destination"
            )
            origin_htmx_attrs = {
                "hx-post": search_url_origin,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#origin-station-results",
                "hx-vals": "js:{station_query: (event && event.target) ? event.target.value : this.value}",
            }
            dest_htmx_attrs = {
                "hx-post": search_url_dest,
                "hx-trigger": "keyup delay:500ms",
                "hx-target": "#destination-station-results",
                "hx-vals": "js:{station_query: (event && event.target) ? event.target.value : this.value}",
            }
            self.fields["origin_station"].widget.attrs.update(origin_htmx_attrs)
            self.fields["destination_station"].widget.attrs.update(dest_htmx_attrs)

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_station"].initial = self.instance.origin_name
            # Note: station_id is stored in origin_code field (reusing)
            self.fields["origin_station_id"].initial = self.instance.origin_code
            self.fields["destination_station"].initial = self.instance.destination_name
            self.fields[
                "destination_station_id"
            ].initial = self.instance.destination_code
            if self.instance.type_specific_data:
                self.fields["train_number"].initial = self.instance.train_number

        # Pre-fill from arrival if this is a new departure
        if (
            self.trip
            and not self.instance.pk
            and self.initial.get("direction") == MainTransfer.Direction.DEPARTURE
        ):
            arrival = MainTransfer.objects.filter(
                trip=self.trip,
                direction=MainTransfer.Direction.ARRIVAL,
                type=MainTransfer.Type.TRAIN,
            ).first()

            if arrival:
                # Invert origin ↔ destination
                self.fields["origin_station"].initial = arrival.destination_name
                self.fields["origin_station_id"].initial = arrival.destination_code
                self.fields["origin_latitude"].initial = arrival.destination_latitude
                self.fields["origin_longitude"].initial = arrival.destination_longitude

                self.fields["destination_station"].initial = arrival.origin_name
                self.fields["destination_station_id"].initial = arrival.origin_code
                self.fields["destination_latitude"].initial = arrival.origin_latitude
                self.fields["destination_longitude"].initial = arrival.origin_longitude

                # Set flag for message display
                self.prefilled_from_arrival = True

    def clean(self):
        cleaned_data = super().clean()

        # Use coordinate values from hidden fields (populated by autocomplete JS)
        origin_lat = cleaned_data.get("origin_latitude")
        origin_lon = cleaned_data.get("origin_longitude")
        dest_lat = cleaned_data.get("destination_latitude")
        dest_lon = cleaned_data.get("destination_longitude")

        # Store coordinates for save() method
        if origin_lat and origin_lon:
            self._origin_coords = (origin_lat, origin_lon)
        if dest_lat and dest_lon:
            self._destination_coords = (dest_lat, dest_lon)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Populate model fields
        instance.type = MainTransfer.Type.TRAIN
        # Note: Reusing origin_code/destination_code fields to store station IDs for trains
        instance.origin_code = self.cleaned_data["origin_station_id"]
        instance.origin_name = self.cleaned_data["origin_station"]
        instance.destination_code = self.cleaned_data["destination_station_id"]
        instance.destination_name = self.cleaned_data["destination_station"]

        # Coordinates from CSV
        if hasattr(self, "_origin_coords"):
            instance.origin_latitude, instance.origin_longitude = self._origin_coords
        if hasattr(self, "_destination_coords"):
            (
                instance.destination_latitude,
                instance.destination_longitude,
            ) = self._destination_coords

        if commit:
            instance.save()

        return instance

    def get_type_specific_data(self):
        data = {}
        if self.cleaned_data.get("train_number"):
            data["train_number"] = self.cleaned_data["train_number"]
        return data


class CarMainTransferForm(MainTransferBaseForm):
    """Form for car main transfers with geocoding"""

    origin_address = forms.CharField(
        label=_("Departure Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address (street, city, country)"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    destination_address = forms.CharField(
        label=_("Arrival Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address (street, city, country)"),
            }
        ),
        help_text=_("Full address for geocoding"),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_address",
            "destination_address",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.pop("autocomplete", None)
        home_address = kwargs.pop("home_address", "")
        super().__init__(*args, **kwargs)
        self.fields["start_time"].required = False
        self.fields["end_time"].required = False

        # Populate fields if editing
        if self.instance and self.instance.pk:
            self.fields["origin_address"].initial = self.instance.origin_address
            self.fields[
                "destination_address"
            ].initial = self.instance.destination_address
        else:
            # Pre-fill origin with home address for arrival, destination for departure
            direction = self.initial.get("direction")
            if home_address:
                if direction == MainTransfer.Direction.ARRIVAL:
                    self.fields["origin_address"].initial = home_address
                elif direction == MainTransfer.Direction.DEPARTURE:
                    self.fields["destination_address"].initial = home_address

            # Pre-fill from arrival if this is a new departure
            if self.trip and direction == MainTransfer.Direction.DEPARTURE:
                arrival = MainTransfer.objects.filter(
                    trip=self.trip,
                    direction=MainTransfer.Direction.ARRIVAL,
                    type=MainTransfer.Type.CAR,
                ).first()
                if arrival:
                    self.fields["origin_address"].initial = arrival.destination_address
                    self.fields["destination_address"].initial = arrival.origin_address
                    self.prefilled_from_arrival = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = MainTransfer.Type.CAR
        instance.origin_address = self.cleaned_data["origin_address"]
        instance.destination_address = self.cleaned_data["destination_address"]

        if commit:  # pragma: no cover
            instance.save()

        return instance


class OtherMainTransferForm(MainTransferBaseForm):
    """Form for other transport types (ferry, bus, taxi, etc.) with free vehicle type"""

    vehicle_type = forms.CharField(
        label=_("Vehicle type"),
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("e.g. Ferry to Venice, Flixbus to Milan"),
            }
        ),
    )

    # Address fields (geocoding like events)
    origin_address = forms.CharField(
        label=_("Departure Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address or location name"),
            }
        ),
    )

    destination_address = forms.CharField(
        label=_("Arrival Location"),
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered",
                "placeholder": _("Full address or location name"),
            }
        ),
    )

    class Meta(MainTransferBaseForm.Meta):
        fields = MainTransferBaseForm.Meta.fields + [
            "origin_address",
            "destination_address",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.pop("autocomplete", None)
        kwargs.pop("home_address", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["origin_address"].initial = self.instance.origin_address
            self.fields[
                "destination_address"
            ].initial = self.instance.destination_address
            self.fields["vehicle_type"].initial = self.instance.type_specific_data.get(
                "vehicle_type", ""
            )

    def get_type_specific_data(self):
        vehicle_type = self.cleaned_data.get("vehicle_type", "")
        return {"vehicle_type": vehicle_type} if vehicle_type else {}

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.type = MainTransfer.Type.OTHER
        instance.origin_address = self.cleaned_data["origin_address"]
        instance.destination_address = self.cleaned_data["destination_address"]
        type_specific_data = self.get_type_specific_data()
        if type_specific_data:
            instance.type_specific_data = type_specific_data

        if commit:  # pragma: no cover
            instance.save()

        return instance


# ============================================================================
# MainTransferConnection Forms
# ============================================================================


class MainTransferConnectionForm(forms.ModelForm):
    """Form for creating a MainTransferConnection (auto-populates main_transfer and destination)"""

    class Meta:
        model = MainTransferConnection
        fields = ["transport_mode", "notes"]
        labels = {
            "transport_mode": _("Transport Mode"),
            "notes": _("Notes"),
        }
        widgets = {
            "transport_mode": TransportModeRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Notes")}),
        }

    def __init__(self, *args, **kwargs):
        self.main_transfer = kwargs.pop("main_transfer", None)
        self.destination = kwargs.pop("destination", None)
        self.destination_type = kwargs.pop("destination_type", None)

        # Create instance with main_transfer and destination already set to avoid validation errors
        if "instance" not in kwargs and self.main_transfer and self.destination:
            if self.destination_type == "event":
                kwargs["instance"] = MainTransferConnection(
                    main_transfer=self.main_transfer, event=self.destination
                )
            else:
                kwargs["instance"] = MainTransferConnection(
                    main_transfer=self.main_transfer, stay=self.destination
                )

        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields[
            "transport_mode"
        ].choices = MainTransferConnection.TransportMode.choices

        self.helper.layout = Layout(
            Field("transport_mode", wrapper_class="col-span-full"),
            Field("notes", wrapper_class="col-span-full"),
        )


class MainTransferConnectionEditForm(forms.ModelForm):
    """Form for editing an existing MainTransferConnection"""

    class Meta:
        model = MainTransferConnection
        fields = ["transport_mode", "notes"]
        labels = {
            "transport_mode": _("Transport Mode"),
            "notes": _("Notes"),
        }
        widgets = {
            "transport_mode": TransportModeRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": _("Notes")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_tag = False

        self.fields[
            "transport_mode"
        ].choices = MainTransferConnection.TransportMode.choices

        self.helper.layout = Layout(
            Field("transport_mode", wrapper_class="col-span-full"),
            Field("notes", wrapper_class="col-span-full"),
        )
