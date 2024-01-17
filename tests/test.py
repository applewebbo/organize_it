from test_plus.test import TestCase as PlusTestCase

from tests.accounts.factories import UserFactory


class TestCase(PlusTestCase):
    user_factory = UserFactory
