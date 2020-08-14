from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_time
from django.utils.timezone import make_aware
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase

from argus.auth.models import User
from argus.incident.models import (
    Incident,
    IncidentTagRelation,
    SourceSystem,
    SourceSystemType,
    Tag,
)
from argus.incident.serializers import IncidentSerializer
from argus.notificationprofile.models import (
    Filter,
    NotificationProfile,
    TimeRecurrence,
    Timeslot,
)


class MockIncidentData:
    # Define member variables, to avoid warnings
    user = None
    nav1 = None
    zabbix1 = None
    incident1 = None
    incident2 = None
    tagstr1 = "object=1"
    tagstr2 = "object=2"
    tagstr3 = "location=Oslo"

    def init_mock_data(self):
        self.user = User.objects.create(username="asdf")

        nav_type = SourceSystemType.objects.create(name="nav")
        zabbix_type = SourceSystemType.objects.create(name="zabbix")

        self.nav1 = SourceSystem.objects.create(
            name="Gløshaugen", type=nav_type, user=User.objects.create(username="nav.glos.no"),
        )
        self.zabbix1 = SourceSystem.objects.create(
            name="Gløshaugen", type=zabbix_type, user=User.objects.create(username="zabbix.glos.no"),
        )

        self.incident1 = Incident.objects.create(start_time=timezone.now(), source=self.nav1, source_incident_id="123",)
        self.incident2 = Incident.objects.get(pk=self.incident1.pk)
        self.incident2.pk = None  # clones incident1
        self.incident2.source = self.zabbix1
        self.incident2.save()

        self.tag1 = Tag.objects.create_from_tag(self.tagstr1)
        self.tag2 = Tag.objects.create_from_tag(self.tagstr2)
        self.tag3 = Tag.objects.create_from_tag(self.tagstr3)

        IncidentTagRelation.objects.create(tag=self.tag1, incident=self.incident1, added_by=self.user)
        IncidentTagRelation.objects.create(tag=self.tag3, incident=self.incident1, added_by=self.user)
        IncidentTagRelation.objects.create(tag=self.tag2, incident=self.incident2, added_by=self.user)
        IncidentTagRelation.objects.create(tag=self.tag3, incident=self.incident2, added_by=self.user)


def set_time(timestamp: datetime, new_time: str):
    new_time = parse_time(new_time)
    return timestamp.replace(
        hour=new_time.hour, minute=new_time.minute, second=new_time.second, microsecond=new_time.microsecond,
    )


class ModelTests(TestCase, MockIncidentData):
    def setUp(self):
        super().init_mock_data()
        self.monday_datetime = make_aware(parse_datetime("2019-11-25 00:00"))

        self.timeslot1 = Timeslot.objects.create(user=self.user, name="Test")
        self.recurrence1 = TimeRecurrence.objects.create(
            timeslot=self.timeslot1,
            days={TimeRecurrence.Day.MONDAY},
            start=parse_time("00:30:00"),
            end=parse_time("00:30:01"),
        )
        self.recurrence2 = TimeRecurrence.objects.create(
            timeslot=self.timeslot1,
            days={TimeRecurrence.Day.MONDAY},
            start=parse_time("00:30:03"),
            end=parse_time("00:31"),
        )
        self.recurrence_all_day = TimeRecurrence.objects.create(
            timeslot=self.timeslot1,
            days={TimeRecurrence.Day.TUESDAY},
            start=TimeRecurrence.DAY_START,
            end=TimeRecurrence.DAY_END,
        )

    def test_time_recurrence(self):
        # Test set_time() helper function
        self.assertEqual(
            parse_datetime("2000-01-01 10:00"), set_time(parse_datetime("2000-01-01 00:00"), "10:00"),
        )

        self.assertEqual(self.monday_datetime.strftime("%A"), "Monday")

        self.assertFalse(self.recurrence1.timestamp_is_within(set_time(self.monday_datetime, "00:29:01")))
        self.assertTrue(self.recurrence1.timestamp_is_within(set_time(self.monday_datetime, "00:30:00")))
        self.assertTrue(self.recurrence1.timestamp_is_within(set_time(self.monday_datetime, "00:30:01")))
        self.assertFalse(self.recurrence1.timestamp_is_within(set_time(self.monday_datetime, "00:30:02")))

    def test_timeslot(self):
        self.assertTrue(self.timeslot1.timestamp_is_within_time_recurrences(set_time(self.monday_datetime, "00:30:01")))
        self.assertFalse(
            self.timeslot1.timestamp_is_within_time_recurrences(set_time(self.monday_datetime, "00:30:02"))
        )
        self.assertTrue(self.timeslot1.timestamp_is_within_time_recurrences(set_time(self.monday_datetime, "00:30:03")))

    def test_source_fits(self):
        filter1 = Filter.objects.create(
            user=self.user, name="Filter1", filter_string="{" f'"sourceSystemIds": [{self.nav1.pk}]' "}",
        )
        filter2 = Filter.objects.create(
            user=self.user, name="Filter2", filter_string="{" f'"sourceSystemIds": [{self.zabbix1.pk}]' "}",
        )

        self.assertTrue(filter1.source_system_fits(self.incident1))

    def test_tags_fit(self):
        filter1 = Filter.objects.create(
            user=self.user, name="Filter1", filter_string="{" f'"tags": []' "}",
        )
        filter2 = Filter.objects.create(
            user=self.user, name="Filter2", filter_string="{" f'"tags": ["object=1"]' "}",
        )
        filter3 = Filter.objects.create(
            user=self.user, name="Filter3", filter_string="{" f'"tags": ["object=2"]' "}",
        )

        self.assertTrue(filter1.tags_fit(self.incident1))
        self.assertTrue(filter2.tags_fit(self.incident1))
        self.assertFalse(filter3.tags_fit(self.incident1))

    def test_filter(self):
        filter1 = Filter.objects.create(
            user=self.user, name="Filter1", filter_string="{" f'"sourceSystemIds": [{self.nav1.pk}]' "}",
        )
        filter2 = Filter.objects.create(
            user=self.user, name="Filter2", filter_string="{" f'"sourceSystemIds": [{self.zabbix1.pk}]' "}",
        )

        self.assertTrue(filter1.incident_fits(self.incident1))
        self.assertFalse(filter1.incident_fits(self.incident2))

        self.assertFalse(filter2.incident_fits(self.incident1))
        self.assertTrue(filter2.incident_fits(self.incident2))

        self.assertEqual(set(filter1.filtered_incidents), {self.incident1})
        self.assertEqual(set(filter2.filtered_incidents), {self.incident2})


class ViewTests(APITestCase, MockIncidentData):
    def setUp(self):
        super().init_mock_data()

        user_token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {user_token.key}")

        incident1_json = IncidentSerializer([self.incident1], many=True).data
        self.incident1_json = JSONRenderer().render(incident1_json)

        timeslot1 = Timeslot.objects.create(user=self.user, name="Never")
        filter1 = Filter.objects.create(
            user=self.user, name="Critical incidents", filter_string="{" f'"sourceSystemIds": [{self.nav1.pk}]' "}",
        )
        self.notification_profile1 = NotificationProfile.objects.create(user=self.user, timeslot=timeslot1)
        self.notification_profile1.filters.add(filter1)

    def test_incidents_filtered_by_notification_profile_view(self):
        response = self.client.get(
            reverse("notification-profile:notification-profile-incidents", args=[self.notification_profile1.pk])
        )
        response.render()
        self.assertEqual(response.content, self.incident1_json)

    # TODO: test more endpoints
