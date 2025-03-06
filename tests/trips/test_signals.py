from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.django_db


class TestStaySignals:
    def test_update_stay_days_signal(self, user_factory, trip_factory, stay_factory):
        # Create user and trip
        user = user_factory()
        trip = trip_factory(
            author=user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
        )

        # Create stays
        stay1 = stay_factory()
        stay2 = stay_factory()

        # Get days created by trip signal
        day1, day2, day3 = trip.days.all()

        # Assign days to stay1
        day1.stay = stay1
        day1.save()
        day2.stay = stay1
        day2.save()

        # Verify days are assigned to stay1
        assert stay1.days.count() == 2

        # Assign day2 to stay2
        day2.stay = stay2
        day2.save()

        # Verify day2 was removed from stay1 and assigned to stay2
        assert stay1.days.count() == 1
        assert stay2.days.count() == 1
        assert stay1.days.first() == day1
        assert stay2.days.first() == day2
