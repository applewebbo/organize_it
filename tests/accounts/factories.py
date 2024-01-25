import factory
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

CustomUser = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    # set a simple password and automatically verify email address for populate_trips command
    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        if not create:
            return
        obj.set_password("1234")
        EmailAddress.objects.create(
            user=obj, email=obj.email, primary=True, verified=True
        )
        obj.save()

    email = factory.Sequence(lambda n: "user_%d@test.com" % n)
