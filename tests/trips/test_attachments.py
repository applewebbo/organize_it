import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from pytest_django.asserts import assertTemplateUsed

from tests.test import TestCase
from tests.trips.factories import (
    ExperienceFactory,
    MainTransferFactory,
    MealFactory,
    StayFactory,
    TripFactory,
)
from trips.models import Attachment, TripCollaboration

pytestmark = pytest.mark.django_db


def _file(name="doc.pdf", size=1024, content_type="application/pdf"):
    return SimpleUploadedFile(name, b"x" * size, content_type=content_type)


class TestAttachmentModel:
    def test_create_for_trip(self):
        trip = TripFactory()
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="boarding.pdf",
            mime_type="application/pdf",
            size=1024,
            uploaded_by=trip.author,
        )
        assert att.content_object == trip
        assert att.include_in_pdf is False

    def test_create_for_stay(self):
        stay = StayFactory()
        trip = TripFactory()
        att = Attachment.objects.create(
            content_object=stay,
            file=_file(),
            original_name="voucher.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=trip.author,
        )
        assert att.content_type == ContentType.objects.get_for_model(stay)

    def test_max_size_2mb_rejected(self):
        trip = TripFactory()
        big = _file(size=2 * 1024 * 1024 + 1)
        att = Attachment(
            content_object=trip,
            file=big,
            original_name="big.pdf",
            mime_type="application/pdf",
            size=big.size,
            uploaded_by=trip.author,
        )
        with pytest.raises(ValidationError):
            att.full_clean()

    def test_disallowed_mime_rejected(self):
        trip = TripFactory()
        att = Attachment(
            content_object=trip,
            file=_file(name="a.exe", content_type="application/octet-stream"),
            original_name="a.exe",
            mime_type="application/octet-stream",
            size=10,
            uploaded_by=trip.author,
        )
        with pytest.raises(ValidationError):
            att.full_clean()

    def test_max_count_per_trip_is_5(self):
        trip = TripFactory()
        for _i in range(5):
            Attachment.objects.create(
                content_object=trip,
                file=_file(),
                original_name="ok.pdf",
                mime_type="application/pdf",
                size=10,
                uploaded_by=trip.author,
            )
        sixth = Attachment(
            content_object=trip,
            file=_file(),
            original_name="extra.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=trip.author,
        )
        with pytest.raises(ValidationError):
            sixth.full_clean()

    @pytest.mark.parametrize("factory", [StayFactory, ExperienceFactory, MealFactory])
    def test_max_count_per_sub_entity_is_2(self, factory):
        trip = TripFactory()
        kwargs = {"trip": trip} if factory is not StayFactory else {}
        obj = factory(**kwargs)
        author = trip.author
        for _i in range(2):
            Attachment.objects.create(
                content_object=obj,
                file=_file(),
                original_name="ok.pdf",
                mime_type="application/pdf",
                size=10,
                uploaded_by=author,
            )
        third = Attachment(
            content_object=obj,
            file=_file(),
            original_name="extra.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=author,
        )
        with pytest.raises(ValidationError):
            third.full_clean()

    def test_max_count_for_main_transfer_is_2(self):
        trip = TripFactory()
        mt = MainTransferFactory(trip=trip, direction=1)
        for _i in range(2):
            Attachment.objects.create(
                content_object=mt,
                file=_file(),
                original_name="ok.pdf",
                mime_type="application/pdf",
                size=10,
                uploaded_by=trip.author,
            )
        third = Attachment(
            content_object=mt,
            file=_file(),
            original_name="extra.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=trip.author,
        )
        with pytest.raises(ValidationError):
            third.full_clean()

    def test_is_image_helper(self):
        trip = TripFactory()
        img = Attachment(
            content_object=trip,
            file=_file(name="x.jpg", content_type="image/jpeg"),
            original_name="x.jpg",
            mime_type="image/jpeg",
            size=10,
            uploaded_by=trip.author,
        )
        assert img.is_image is True
        assert img.is_pdf is False

    def test_str(self):
        trip = TripFactory()
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="boarding.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=trip.author,
        )
        assert str(att) == "boarding.pdf"

    def test_is_pdf_helper(self):
        trip = TripFactory()
        pdf = Attachment(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=trip.author,
        )
        assert pdf.is_pdf is True
        assert pdf.is_image is False


def _ct(obj):
    return ContentType.objects.get_for_model(obj).pk


class AttachmentUploadView(TestCase):
    def test_owner_can_upload_to_trip(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={
                    "object_id": trip.pk,
                    "file": _file(),
                    "include_in_pdf": "on",
                },
            )
        assert response.status_code == 204
        att = Attachment.objects.get(content_type__pk=_ct(trip), object_id=trip.pk)
        assert att.original_name == "doc.pdf"
        assert att.include_in_pdf is True
        assert att.uploaded_by == user

    def test_collaborator_can_upload(self):
        owner = self.make_user("owner")
        collab = self.make_user("collab")
        trip = TripFactory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        with self.login(collab):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={"object_id": trip.pk, "file": _file()},
            )
        assert response.status_code == 204
        assert Attachment.objects.filter(object_id=trip.pk).exists()

    def test_non_member_gets_404(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={"object_id": trip.pk, "file": _file()},
            )
        self.response_404(response)

    def test_oversize_returns_400(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={
                    "object_id": trip.pk,
                    "file": _file(size=2 * 1024 * 1024 + 1),
                },
            )
        assert response.status_code == 400
        assert not Attachment.objects.exists()

    def test_invalid_extension_returns_400(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        bad = SimpleUploadedFile(
            "x.exe", b"123", content_type="application/octet-stream"
        )
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={"object_id": trip.pk, "file": bad},
            )
        assert response.status_code == 400

    def test_count_limit_returns_400(self):
        user = self.make_user("user")
        trip = TripFactory(author=user)
        stay = StayFactory()
        day = trip.days.first()
        day.stay = stay
        day.save()
        for _i in range(2):
            Attachment.objects.create(
                content_object=stay,
                file=_file(),
                original_name="ok.pdf",
                mime_type="application/pdf",
                size=10,
                uploaded_by=user,
            )
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="stay",
                data={"object_id": stay.pk, "file": _file()},
            )
        assert response.status_code == 400

    def test_invalid_category_returns_404(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="bogus",
                data={"object_id": trip.pk, "file": _file()},
            )
        self.response_404(response)

    def test_object_from_other_trip_returns_404(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        other_trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={"object_id": other_trip.pk, "file": _file()},
            )
        self.response_404(response)

    def test_missing_object_id_returns_400(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={"file": _file()},
            )
        assert response.status_code == 400


class AttachmentDeleteView(TestCase):
    def test_owner_can_delete(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.post("trips:attachment-delete", pk=att.pk)
        assert response.status_code == 204
        assert not Attachment.objects.filter(pk=att.pk).exists()

    def test_non_member_cannot_delete(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=owner,
        )
        with self.login(other):
            response = self.post("trips:attachment-delete", pk=att.pk)
        self.response_404(response)
        assert Attachment.objects.filter(pk=att.pk).exists()


class AttachmentStreamView(TestCase):
    def test_owner_can_stream(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.get("trips:attachment-stream", pk=att.pk)
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        response.close()

    def test_non_member_cannot_stream(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=owner,
        )
        with self.login(other):
            response = self.get("trips:attachment-stream", pk=att.pk)
        self.response_404(response)

    def test_anonymous_cannot_stream(self):
        owner = self.make_user("owner")
        trip = TripFactory(author=owner)
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=owner,
        )
        response = self.get("trips:attachment-stream", pk=att.pk)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_collaborator_can_stream(self):
        owner = self.make_user("owner")
        collab = self.make_user("collab")
        trip = TripFactory(author=owner)
        TripCollaboration.objects.create(
            trip=trip, user=collab, color="blue", added_by=owner
        )
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=owner,
        )
        with self.login(collab):
            response = self.get("trips:attachment-stream", pk=att.pk)
        assert response.status_code == 200
        response.close()

    def test_stream_for_stay_attachment(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        stay = StayFactory()
        day = trip.days.first()
        day.stay = stay
        day.save()
        att = Attachment.objects.create(
            content_object=stay,
            file=_file(),
            original_name="v.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.get("trips:attachment-stream", pk=att.pk)
        assert response.status_code == 200
        response.close()


class AttachmentPreviewView(TestCase):
    def test_owner_gets_preview_modal(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        att = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="x.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.get("trips:attachment-preview", pk=att.pk)
        self.response_200(response)
        assertTemplateUsed(response, "trips/attachments/preview-modal.html")


class AttachmentsCardView(TestCase):
    def test_card_loads_with_trip_and_subentity_attachments(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        stay = StayFactory()
        day = trip.days.first()
        day.stay = stay
        day.save()
        event = ExperienceFactory(trip=trip)
        mt = MainTransferFactory(trip=trip, direction=1)
        for obj in (trip, stay, event, mt):
            Attachment.objects.create(
                content_object=obj,
                file=_file(),
                original_name="x.pdf",
                mime_type="application/pdf",
                size=10,
                uploaded_by=user,
            )
        with self.login(user):
            response = self.get("trips:attachments-card", trip_pk=trip.pk)
        self.response_200(response)
        assertTemplateUsed(response, "trips/includes/attachments-card.html")
        assert response.context["total_count"] == 4

    def test_card_404_for_non_member(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get("trips:attachments-card", trip_pk=trip.pk)
        self.response_404(response)


class AttachmentUploadModalView(TestCase):
    def test_owner_can_get_upload_modal_trip(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="trip",
            )
        self.response_200(response)
        assertTemplateUsed(response, "trips/attachments/upload-modal.html")
        assert len(response.context["targets"]) == 1

    def test_modal_shows_targets_for_stays(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        stay = StayFactory()
        day = trip.days.first()
        day.stay = stay
        day.save()
        with self.login(user):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="stay",
            )
        self.response_200(response)
        assert response.context["targets"][0][0] == stay.pk

    def test_non_member_modal_404(self):
        owner = self.make_user("owner")
        other = self.make_user("other")
        trip = TripFactory(author=owner)
        with self.login(other):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="trip",
            )
        self.response_404(response)

    def test_modal_filters_targets_by_object_id(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        mt1 = MainTransferFactory(trip=trip, direction=1)
        MainTransferFactory(trip=trip, direction=2)
        with self.login(user):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="main",
                data={"object_id": mt1.pk},
            )
        self.response_200(response)
        targets = response.context["targets"]
        assert len(targets) == 1
        assert targets[0][0] == mt1.pk

    def test_modal_404_for_unknown_object_id(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        MainTransferFactory(trip=trip, direction=1)
        with self.login(user):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="main",
                data={"object_id": 999999},
            )
        self.response_404(response)

    def test_modal_404_for_invalid_category(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="bogus",
            )
        self.response_404(response)


class AttachmentMissingCoverage(TestCase):
    def test_modal_404_for_non_int_object_id(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get(
                "trips:attachment-upload-modal",
                trip_pk=trip.pk,
                category="trip",
                data={"object_id": "abc"},
            )
        self.response_404(response)

    def test_upload_without_file_returns_400(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="trip",
                data={"object_id": trip.pk},
            )
        assert response.status_code == 400

    def test_upload_to_main_transfer(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        mt = MainTransferFactory(trip=trip, direction=1)
        with self.login(user):
            response = self.post(
                "trips:attachment-upload",
                trip_pk=trip.pk,
                category="main",
                data={"object_id": mt.pk, "file": _file()},
            )
        assert response.status_code == 204
        assert Attachment.objects.filter(object_id=mt.pk).exists()

    def test_card_for_empty_trip(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        with self.login(user):
            response = self.get("trips:attachments-card", trip_pk=trip.pk)
        self.response_200(response)
        assert response.context["total_count"] == 0

    def test_preview_title_for_stay(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        stay = StayFactory(name="Hotel Test")
        day = trip.days.first()
        day.stay = stay
        day.save()
        att = Attachment.objects.create(
            content_object=stay,
            file=_file(),
            original_name="v.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.get("trips:attachment-preview", pk=att.pk)
        assert response.context["title"] == "Hotel Test"

    def test_preview_title_for_main_transfer(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        mt = MainTransferFactory(trip=trip, direction=1)
        att = Attachment.objects.create(
            content_object=mt,
            file=_file(),
            original_name="v.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.get("trips:attachment-preview", pk=att.pk)
        assert mt.get_direction_display() in response.context["title"]

    def test_preview_title_for_event(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        event = ExperienceFactory(trip=trip)
        att = Attachment.objects.create(
            content_object=event,
            file=_file(),
            original_name="v.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            response = self.get("trips:attachment-preview", pk=att.pk)
        assert event.name in response.context["title"]

    def test_preview_title_with_multiple_siblings_shows_index(self):
        user = self.make_user("owner")
        trip = TripFactory(author=user)
        att1 = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="a.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        att2 = Attachment.objects.create(
            content_object=trip,
            file=_file(),
            original_name="b.pdf",
            mime_type="application/pdf",
            size=10,
            uploaded_by=user,
        )
        with self.login(user):
            r1 = self.get("trips:attachment-preview", pk=att1.pk)
            r2 = self.get("trips:attachment-preview", pk=att2.pk)
        assert "1" in r1.context["title"]
        assert "2" in r2.context["title"]
