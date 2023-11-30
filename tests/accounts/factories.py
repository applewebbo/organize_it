import factory
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    email = factory.Sequence(lambda n: "user_%d@test.com" % n)
