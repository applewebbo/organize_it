from django.db import connection
from test_plus.test import TestCase as PlusTestCase

from tests.accounts.factories import UserFactory


class TestCase(PlusTestCase):
    user_factory = UserFactory

    def tearDown(self):
        # Close the DB connection to prevent ResourceWarning
        connection.close()
        super().tearDown()
