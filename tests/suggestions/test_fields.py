from suggestions.fields import EncryptedTextField


class TestEncryptedTextField:
    def test_get_prep_value_none_passthrough(self):
        field = EncryptedTextField()
        assert field.get_prep_value(None) is None

    def test_from_db_value_none_passthrough(self):
        field = EncryptedTextField()
        assert field.from_db_value(None, None, None) is None

    def test_encrypt_decrypt_round_trip(self):
        field = EncryptedTextField()
        stored = field.get_prep_value("secret-value")
        assert stored != "secret-value"
        assert field.from_db_value(stored, None, None) == "secret-value"
