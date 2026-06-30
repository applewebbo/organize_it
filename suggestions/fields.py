from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the configured field-encryption key."""
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())


class EncryptedTextField(models.TextField):
    """TextField that transparently encrypts its value at rest with Fernet.

    The plaintext lives only in memory; the database always stores the
    encrypted token. Used for BYOK AI credentials, which must never be
    persisted, logged or exposed in clear.
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        return _get_fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _get_fernet().decrypt(value.encode()).decode()
