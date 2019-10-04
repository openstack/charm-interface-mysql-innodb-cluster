# Overview

This interface layer handles the intra-cluster relations for
msyql-innodb-cluster.

# Usage

## Peers

The interface layer will set the following state:

  * `{relation_name}.connected`  The cluster relation is established.
  * `{relation_name}.available`  The cluster relation data is complete.
  * `{relation_name}.clustered`  All cluster units are clustered.

Cluster relation information can be set on the relation with the following methods:


Set the cluster relation information to connect to this unit:

```python
    def cluster.set_cluster_connection_info(
        "192.168.1.5", "clusteruser", "passwd")
```

Indicate this unit's readiness for clustering:

```python
    cluster.set_unit_configure_ready():
```

Indicate this unit has been clustered:

```python
    cluster.set_unit_clustered(self):
    cluster.set_unit_configure_ready(self):
```


For example:

```python

@reactive.when('cluster.connected')
@reactive.when_not('cluster.available')
def send_cluster_connection_info(cluster):
    with charm.provide_charm_instance() as instance:
        cluster.set_cluster_connection_info(
            instance.cluster_address,
            instance.cluster_user,
            instance.cluster_password)


@reactive.when('cluster.available')
def create_remote_cluster_user(cluster):
    with charm.provide_charm_instance() as instance:
        for unit in cluster.all_joined_units:
            instance.create_cluster_user(
                unit.received['cluster-address'],
                unit.received['cluster-user'],
                unit.received['cluster-password'])

        cluster.set_unit_configure_ready()

@reactive.when('leadership.set.cluster-created')
@reactive.when('cluster.available')
def signal_clustered(cluster):
    # Optimize clustering by causing a cluster relation changed
    with charm.provide_charm_instance() as instance:
        if reactive.is_flag_set(
                "leadership.set.cluster-instance-clustered-{}"
                .format(instance.cluster_address)):
            cluster.set_unit_clustered()
        instance.assess_status()
```

The interface will automatically determine the network space binding on the
local unit to present to the MySQL InnoDB cluster based on the name of the
relation. This can be overridden using the cluster_host parameter of the
set_cluster_connection_info method.
