# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import charms_openstack.test_utils as test_utils
import mock
import peers


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = []
        hook_set = {
            "when": {
                "joined": (
                    "endpoint.{endpoint_name}.joined",),

                "changed": (
                    "endpoint.{endpoint_name}.changed",),
                "departed": ("endpoint.{endpoint_name}.broken",
                             "endpoint.{endpoint_name}.departed",),
            },
        }
        # test that the hooks were registered
        self.registered_hooks_test_helper(peers, hook_set, defaults)


class TestMySQLInnoDBClusterPeer(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self._patches = {}
        self._patches_start = {}
        self.patch_object(peers.reactive, "clear_flag")
        self.patch_object(peers.reactive, "set_flag")

        _data = {
            "cluster-address": None,
            "cluster-user": None,
            "cluster-password": None,
            "unit-clustered": None}
        self.fake_unit_0 = mock.MagicMock()
        self.fake_unit_0.unit_name = "unit/0"
        self.fake_unit_0.received = _data

        self.fake_unit_1 = mock.MagicMock()
        self.fake_unit_1.unit_name = "unit/1"
        self.fake_unit_1.received = _data

        self.fake_unit_2 = mock.MagicMock()
        self.fake_unit_2.unit_name = "unit/2"
        self.fake_unit_2.received = _data

        self.fake_relation_id = "cluster:19"
        self.fake_relation = mock.MagicMock()
        self.fake_relation.relation_id = self.fake_relation_id
        self.fake_relation.units = [
            self.fake_unit_0,
            self.fake_unit_1,
            self.fake_unit_2]
        self.fake_unit_0.relation = self.fake_relation
        self.fake_unit_1.relation = self.fake_relation
        self.fake_unit_2.relation = self.fake_relation

        self.ep_name = "ep"
        self.ep = peers.MySQLInnoDBClusterPeer(
            self.ep_name, [self.fake_relation])
        self.ep.ingress_address = "10.10.10.10"
        self.ep.relations[0] = self.fake_relation

    def tearDown(self):
        self.ep = None
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def test_joined(self):
        self.ep.set_ingress_address = mock.MagicMock()
        self.ep.joined()
        self.set_flag.assert_called_once_with(
            "{}.connected".format(self.ep_name))
        self.ep.set_ingress_address.assert_called_once()

    def test_changed_not_available(self):
        self.ep.available = mock.MagicMock(return_value=False)
        self.ep.clustered = mock.MagicMock(return_value=False)
        self.ep.changed()

        _calls = [
            mock.call("endpoint.{}.changed.cluster-address"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.cluster-user"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.cluster-password"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.unit-configure-ready"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.unit-clustered"
                      .format(self.ep_name)),
            mock.call("{}.available".format(self.ep_name)),
            mock.call("{}.clustered".format(self.ep_name))]
        self.clear_flag.assert_has_calls(_calls, any_order=True)
        self.set_flag.assert_not_called()

    def test_changed_available(self):
        self.ep.available = mock.MagicMock(return_value=True)
        self.ep.clustered = mock.MagicMock(return_value=True)
        self.ep.changed()

        _ccalls = [
            mock.call("endpoint.{}.changed.cluster-address"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.cluster-user"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.cluster-password"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.unit-configure-ready"
                      .format(self.ep_name)),
            mock.call("endpoint.{}.changed.unit-clustered"
                      .format(self.ep_name))]
        self.clear_flag.assert_has_calls(_ccalls, any_order=True)
        _scalls = [
            mock.call("{}.available".format(self.ep_name)),
            mock.call("{}.clustered".format(self.ep_name))]
        self.set_flag.assert_has_calls(_scalls, any_order=True)

    def test_departed(self):
        self.ep.departed()
        _calls = [
            mock.call("{}.available".format(self.ep_name)),
            mock.call("{}.connected".format(self.ep_name))]
        self.clear_flag.assert_has_calls(_calls, any_order=True)

    def test_relation_ids(self):
        self.assertEqual([self.fake_relation_id], self.ep.relation_ids())

    def test_set_ingress_address(self):
        _calls = [
            mock.call("ingress-address", self.ep.ingress_address),
            mock.call("private-address", self.ep.ingress_address)]
        self.ep.set_ingress_address()
        self.fake_relation.to_publish_raw.__setitem__.assert_has_calls(_calls)

    def test_available_not_available(self):
        self.assertFalse(self.ep.available())

    def test_available_one_unit_not_available(self):
        _data = {
            "cluster-address": "10.5.0.21",
            "cluster-user": "user",
            "cluster-password": "pw"}
        for unit in self.fake_relation.units:
            unit.received = _data
        self.fake_unit_2.received = {
            "cluster-address": "10.5.0.26",
            "cluster-user": None,
            "cluster-password": "pass"}
        self.assertFalse(self.ep.available())

    def test_available_available(self):
        _data = {
            "cluster-address": "10.5.0.21",
            "cluster-user": "user",
            "cluster-password": "pw"}
        for unit in self.fake_relation.units:
            unit.received = _data
        self.assertTrue(self.ep.available())

    def test_clustered_not_clustered(self):
        self.assertFalse(self.ep.clustered())

    def test_clustered_one_unit_not_clustered(self):
        _data = {"unit-clustered": True}
        for unit in self.fake_relation.units:
            unit.received = _data
        self.fake_unit_2.received = {"unit-clustered": None}
        self.assertFalse(self.ep.clustered())

    def test_clustered_clustered(self):
        _data = {"unit-clustered": True}
        for unit in self.fake_relation.units:
            unit.received = _data
        self.assertTrue(self.ep.clustered())

    def test_set_cluster_connection_info(self):
        _pw = "fakepassword"
        _user = "fakeuser"
        self.ep.set_cluster_connection_info(
            self.ep.ingress_address,
            _user,
            _pw)
        _calls = [
            mock.call("cluster-address", self.ep.ingress_address),
            mock.call("cluster-user", _user),
            mock.call("cluster-password", _pw)]
        self.fake_relation.to_publish.__setitem__.assert_has_calls(_calls)
