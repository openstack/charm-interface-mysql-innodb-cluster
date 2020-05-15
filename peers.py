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

from charms import reactive
import charmhelpers.contrib.network.ip as ch_net_ip
import charmhelpers.core as ch_core


class MySQLInnoDBClusterPeer(reactive.Endpoint):

    # MySQL InnoDB Cluster must have at least 3 units for viability
    minimum_cluster_size = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ingress_address = ch_net_ip.get_relation_ip(self.endpoint_name)

    def relation_ids(self):
        return [x.relation_id for x in self.relations]

    def set_ingress_address(self):
        for relation in self.relations:
            relation.to_publish_raw["ingress-address"] = self.ingress_address
            relation.to_publish_raw["private-address"] = self.ingress_address

    @property
    def peer_relation(self):
        # Get the first relation object as we only have one relation to peers
        for relation in self.relations:
            return relation

    def available(self):
        if len(self.all_joined_units) < (self.minimum_cluster_size - 1):
            return False
        for unit in self.all_joined_units:
            if not unit.received['cluster-address']:
                return False
            if not unit.received['cluster-user']:
                return False
            if not unit.received['cluster-password']:
                return False
        return True

    def set_or_clear_available(self):
        if self.available():
            reactive.set_flag(self.expand_name('{endpoint_name}.available'))
        else:
            reactive.clear_flag(self.expand_name('{endpoint_name}.available'))

    def clustered(self):
        if len(self.all_joined_units) < (self.minimum_cluster_size - 1):
            return False
        for unit in self.all_joined_units:
            if not unit.received['unit-clustered']:
                return False
        return True

    @reactive.when('endpoint.{endpoint_name}.joined')
    def joined(self):
        self.set_ingress_address()
        reactive.set_flag(self.expand_name('{endpoint_name}.connected'))
        self.set_or_clear_available()

    @reactive.when('endpoint.{endpoint_name}.changed')
    def changed(self):
        flags = (
            self.expand_name(
                'endpoint.{endpoint_name}.changed.cluster-address'),
            self.expand_name(
                'endpoint.{endpoint_name}.changed.cluster-user'),
            self.expand_name(
                'endpoint.{endpoint_name}.changed.cluster-password'),
            # Optimizers
            self.expand_name(
                'endpoint.{endpoint_name}.changed.unit-configure-ready'),
            self.expand_name(
                'endpoint.{endpoint_name}.changed.unit-clustered'),
        )
        if reactive.all_flags_set(*flags):
            for flag in flags:
                reactive.clear_flag(flag)

        self.set_or_clear_available()

        if self.clustered():
            reactive.set_flag(self.expand_name('{endpoint_name}.clustered'))
        else:
            reactive.clear_flag(self.expand_name('{endpoint_name}.clustered'))

    def remove(self):
        flags = (
            self.expand_name('{endpoint_name}.connected'),
            self.expand_name('{endpoint_name}.available'),
        )
        for flag in flags:
            reactive.clear_flag(flag)

    @reactive.when('endpoint.{endpoint_name}.departed')
    def departed(self):
        self.remove()

    @reactive.when('endpoint.{endpoint_name}.broken')
    def broken(self):
        self.remove()

    def set_cluster_connection_info(
            self, cluster_address, cluster_user, cluster_password):
        """Send cluster connection information to peers.

        :param cluster_address: Cluster IP or hostname
        :type cluster_address: str
        :param cluster_user: User for cluster user
        :type cluster_user: str
        :param cluster_password: Password for cluster user
        :type cluster_password: str
        :side effect: Data is set on the relation
        :returns: None, this function is called for its side effect
        :rtype: None
        """
        if not self.peer_relation:
            ch_core.hookenv.log(
                "No mysql-inndb-cluster peer relation: possibly departing.",
                "WARNING")
            return
        self.peer_relation.to_publish['cluster-address'] = cluster_address
        self.peer_relation.to_publish['cluster-user'] = cluster_user
        self.peer_relation.to_publish['cluster-password'] = cluster_password

    def set_unit_configure_ready(self):
        """Indicate to the cluster peers this unit is ready for configuration.

        :side effect: Data is set on the relation
        :returns: None, this function is called for its side effect
        :rtype: None
        """
        if not self.peer_relation:
            ch_core.hookenv.log(
                "No mysql-inndb-cluster peer relation: possibly departing.",
                "WARNING")
            return
        self.peer_relation.to_publish['unit-configure-ready'] = True

    def set_unit_clustered(self):
        """Indicate to the cluster peers this unit is clustered.

        :side effect: Data is set on the relation
        :returns: None, this function is called for its side effect
        :rtype: None
        """
        if not self.peer_relation:
            ch_core.hookenv.log(
                "No mysql-inndb-cluster peer relation: possibly departing.",
                "WARNING")
            return
        self.peer_relation.to_publish['unit-clustered'] = True
