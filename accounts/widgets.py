from django import forms
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class AvatarRadioSelect(forms.RadioSelect):
    """Custom widget to display avatar choices as radio buttons with images"""

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(attrs or {}, {"name": name})
        output = ['<div class="grid grid-cols-4 gap-4">']

        for i, (option_value, option_label) in enumerate(self.choices):
            if option_value:  # Skip empty choice
                option_id = f"{attrs.get('id', 'id_avatar')}_{i}"
                image_url = static(f"img/avatars/{option_value}")
                checked_class = (
                    "border-primary bg-primary/10"
                    if option_value == value
                    else "border-base-300"
                )
                # Safe: only generating checked attribute string, no user input
                checked_attr = mark_safe(  # nosec B703 B308
                    'checked="checked"' if option_value == value else ""
                )

                output.append(
                    format_html(
                        '<label for="{}" class="cursor-pointer">'
                        '<div class="flex flex-col items-center gap-2 p-3 border rounded-lg hover:border-primary transition-colors {}">'
                        '<input type="radio" name="{}" value="{}" class="radio radio-primary radio-sm" id="{}" {}>'
                        '<img src="{}" alt="{}" class="w-10 h-10 object-contain">'
                        # '<span class="text-xs text-center">{}</span>'
                        "</div>"
                        "</label>",
                        option_id,
                        checked_class,
                        name,
                        option_value,
                        option_id,
                        checked_attr,
                        image_url,
                        option_label,
                        # option_label,
                    )
                )

        output.append("</div>")
        # Safe: all HTML generated via format_html which escapes user input
        return mark_safe("\n".join(output))  # nosec B703 B308
