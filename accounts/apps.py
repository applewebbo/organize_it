from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    # Disambiguates from allauth.account's own "Accounts" app label in the
    # admin sidebar, which otherwise renders as a duplicate-looking group.
    verbose_name = _("Users")
