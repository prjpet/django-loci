from channels.test import ChannelTestCase, WSClient
from django.contrib.auth import get_user_model

from . import TestAdminMixin, TestLociMixin
from ..channels.consumers import _get_object_or_none
from ..models import Location, ObjectLocation
from .testdeviceapp.models import Device


class TestChannels(TestAdminMixin, TestLociMixin, ChannelTestCase):
    """
    tests for django_loci.models
    """
    object_model = Device
    location_model = Location
    # floorplan_model = FloorPlan
    object_location_model = ObjectLocation
    user_model = get_user_model()

    def setUp(self):
        client = WSClient()
        self.client = client

    def test_object_or_none(self):
        result = _get_object_or_none(self.location_model, pk=1)
        self.assertEqual(result, None)
        plausible_pk = self.location_model().pk
        result = _get_object_or_none(self.location_model, pk=plausible_pk)
        self.assertEqual(result, None)

    def _test_ws_add(self, pk=None, user=None):
        if not pk:
            ol = self._create_object_location(type='mobile')
            pk = ol.location.pk
        path = '/geo/mobile-location/{0}/'.format(pk)
        if user:
            self.client.force_login(user)
        self.client.send_and_consume('websocket.connect', path=path)
        return path

    def test_ws_add_unauthenticated(self):
        try:
            self._test_ws_add()
        except AssertionError as e:
            self.assertIn('Connection rejected', str(e))
        else:
            self.fail('AssertionError not raised')

    def test_connect_and_disconnect(self):
        path = self._test_ws_add(user=self._create_admin())
        self.assertEqual(self.client.receive(), None)
        self.client.send_and_consume('websocket.disconnect', path=path)

    def test_ws_add_not_staff(self):
        user = self.user_model.objects.create_user(username='user',
                                                   password='password',
                                                   email='test@test.org')
        try:
            self._test_ws_add(user=user)
        except AssertionError as e:
            self.assertIn('Connection rejected', str(e))
        else:
            self.fail('AssertionError not raised')

    def test_ws_add_404(self):
        pk = self.location_model().pk
        admin = self._create_admin()
        try:
            self._test_ws_add(pk=pk, user=admin)
        except AssertionError as e:
            self.assertIn('Connection rejected', str(e))
        else:
            self.fail('AssertionError not raised')
