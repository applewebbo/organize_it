from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class TransportModeRadioSelect(forms.RadioSelect):
    """Custom widget to display transport mode choices as radio buttons with Phosphor icons"""

    TRANSPORT_ICONS = {
        "driving": "ph-car",
        "walking": "ph-person-simple-walk",
        "bicycling": "ph-bicycle",
        "transit": "ph-train",
    }

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(attrs or {}, {"name": name})
        # Use Alpine.js to manage selected state
        initial_value = value or "driving"
        output = [
            format_html(
                '<div class="grid grid-cols-2 gap-2 sm:grid-cols-4" x-data="{{ selected: \'{}\' }}">',
                initial_value,
            )
        ]

        for i, (option_value, option_label) in enumerate(self.choices):
            if option_value:  # pragma: no branch  # Skip empty choice
                option_id = f"{attrs.get('id', 'id_transport_mode')}_{i}"
                icon_class = self.TRANSPORT_ICONS.get(option_value, "ph-question")
                is_checked = option_value == value

                # Safe: only generating checked attribute string, no user input
                checked_attr = mark_safe(  # nosec B703 B308
                    'checked="checked"' if is_checked else ""
                )

                output.append(
                    format_html(
                        '<label for="{}" class="cursor-pointer">'
                        '<div class="flex flex-col items-center gap-1.5 p-3 border-2 rounded-lg transition-colors"'
                        " :class=\"selected === '{}' ? 'border-primary bg-primary/10' : 'border-base-300 hover:border-primary'\">"
                        '<input type="radio" name="{}" value="{}" class="sr-only" id="{}" {} '
                        'x-model="selected">'
                        '<i class="ph-bold {} text-2xl" aria-hidden="true"></i>'
                        '<span class="text-xs font-medium text-center">{}</span>'
                        "</div>"
                        "</label>",
                        option_id,
                        option_value,
                        name,
                        option_value,
                        option_id,
                        checked_attr,
                        icon_class,
                        option_label,
                    )
                )

        output.append("</div>")
        # Safe: all HTML generated via format_html which escapes user input
        return mark_safe("\n".join(output))  # nosec B703 B308
