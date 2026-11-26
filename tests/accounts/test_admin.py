import pytest
from django.core import mail
from django.urls import reverse

from accounts.models import Notification
from tests.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_notification_model_str_and_defaults():
    sender = UserFactory(is_staff=True)
    recipient = UserFactory()
    n1 = Notification.objects.create(
        recipient=recipient,
        message="First notification message",
        created_by=sender,
    )
    n2 = Notification.objects.create(
        recipient=recipient,
        message="Second notification message",
        created_by=sender,
    )
    assert n1.is_read is False
    assert str(recipient) in str(n1)
    assert list(Notification.objects.all()) == [n2, n1]


def test_admin_block_and_unblock_users_actions(client):
    staff = UserFactory(is_staff=True, is_superuser=True, is_active=True)
    u1 = UserFactory(is_active=True)
    u2 = UserFactory(is_active=True)
    client.force_login(staff)

    changelist_url = reverse("admin:accounts_customuser_changelist")
    response = client.post(
        changelist_url,
        {
            "action": "block_users",
            "_selected_action": [str(u1.pk), str(u2.pk)],
        },
    )
    assert response.status_code == 302
    u1.refresh_from_db()
    u2.refresh_from_db()
    assert u1.is_active is False
    assert u2.is_active is False

    response = client.post(
        changelist_url,
        {
            "action": "unblock_users",
            "_selected_action": [str(u1.pk)],
        },
    )
    assert response.status_code == 302
    u1.refresh_from_db()
    u2.refresh_from_db()
    assert u1.is_active is True
    assert u2.is_active is False


def test_send_notification_and_email_denied_for_non_staff(client):
    user = UserFactory(is_staff=False, is_active=True)
    client.force_login(user)

    for url_name in (
        "admin:accounts_customuser_send_notification",
        "admin:accounts_customuser_send_email",
    ):
        response = client.get(reverse(url_name))
        assert response.status_code == 302
        assert reverse("admin:login") in response.url


def test_send_notification_empty_selection_redirects(client):
    staff = UserFactory(is_staff=True, is_superuser=True, is_active=True)
    client.force_login(staff)

    response = client.get(reverse("admin:accounts_customuser_send_notification"))
    assert response.status_code == 302
    assert reverse("admin:accounts_customuser_changelist") in response.url


def test_send_email_empty_selection_redirects(client):
    staff = UserFactory(is_staff=True, is_superuser=True, is_active=True)
    client.force_login(staff)

    response = client.get(reverse("admin:accounts_customuser_send_email"))
    assert response.status_code == 302
    assert reverse("admin:accounts_customuser_changelist") in response.url


def test_send_notification_action_and_view(client):
    staff = UserFactory(is_staff=True, is_superuser=True, is_active=True)
    u1 = UserFactory()
    u2 = UserFactory()
    client.force_login(staff)

    changelist_url = reverse("admin:accounts_customuser_changelist")
    action_resp = client.post(
        changelist_url,
        {
            "action": "send_notification_action",
            "_selected_action": [str(u1.pk), str(u2.pk)],
        },
    )
    send_url = reverse("admin:accounts_customuser_send_notification")
    assert action_resp.status_code == 302
    assert send_url in action_resp.url

    get_resp = client.get(send_url)
    assert get_resp.status_code == 200
    assert u1.email in get_resp.content.decode()

    post_resp = client.post(send_url, {"message": "Maintenance tonight"})
    assert post_resp.status_code == 302
    assert changelist_url in post_resp.url
    assert Notification.objects.filter(recipient=u1, created_by=staff).exists()
    assert Notification.objects.filter(recipient=u2, created_by=staff).exists()


def test_send_email_action_and_view(client):
    staff = UserFactory(is_staff=True, is_superuser=True, is_active=True)
    u1 = UserFactory(email="alice@example.com")
    u2 = UserFactory(email="bob@example.com")
    client.force_login(staff)

    changelist_url = reverse("admin:accounts_customuser_changelist")
    action_resp = client.post(
        changelist_url,
        {
            "action": "send_email_action",
            "_selected_action": [str(u1.pk), str(u2.pk)],
        },
    )
    send_url = reverse("admin:accounts_customuser_send_email")
    assert action_resp.status_code == 302
    assert send_url in action_resp.url

    get_resp = client.get(send_url)
    assert get_resp.status_code == 200
    assert "alice@example.com" in get_resp.content.decode()

    post_resp = client.post(
        send_url,
        {"subject": "Important update", "body": "Please check your trip."},
    )
    assert post_resp.status_code == 302
    assert changelist_url in post_resp.url
    assert len(mail.outbox) == 2
    assert {m.to[0] for m in mail.outbox} == {"alice@example.com", "bob@example.com"}


def test_profile_shows_only_unread_notifications_and_mark_read(client):
    user = UserFactory()
    other = UserFactory()
    unread = Notification.objects.create(recipient=user, message="Unread alert")
    read = Notification.objects.create(
        recipient=user, message="Already read", is_read=True
    )

    client.force_login(user)
    profile_resp = client.get(reverse("accounts:profile"))
    assert profile_resp.status_code == 200
    assert list(profile_resp.context["unread_notifications"]) == [unread]
    html = profile_resp.content.decode()
    assert "Unread alert" in html
    assert "Already read" not in html
    assert read.is_read is True

    mark_url = reverse("accounts:mark-notification-read", kwargs={"pk": unread.pk})
    assert client.get(mark_url).status_code == 405

    client.force_login(other)
    assert client.post(mark_url).status_code == 404
    unread.refresh_from_db()
    assert unread.is_read is False

    client.force_login(user)
    resp = client.post(mark_url)
    assert resp.status_code == 204
    unread.refresh_from_db()
    assert unread.is_read is True


def test_admin_link_visibility_for_staff_and_non_staff(client):
    admin_url = reverse("admin:index")
    regular = UserFactory(is_staff=False, is_active=True)
    staff = UserFactory(is_staff=True, is_active=True)

    client.force_login(regular)
    resp_regular = client.get(reverse("accounts:profile"))
    assert admin_url not in resp_regular.content.decode()

    client.force_login(staff)
    resp_staff = client.get(reverse("accounts:profile"))
    assert admin_url in resp_staff.content.decode()
