from replica import Replica
from datetime import datetime, timezone

from kubernetes import client
from engine import Engine
from utility.constant import LONGHORN_NAMESPACE
from utility.utility import logging


class replica_keywords:

    def __init__(self):
        self.replica = Replica()

    def validate_replica_setting(self, volume_name, setting_name, value):
        return self.replica.validate_replica_setting(volume_name, setting_name, value)

    def get_replicas(self, volume_name=None, node_name=None, disk_uuid=None):
        return self.replica.get(volume_name, node_name, disk_uuid)

    def wait_for_disk_replica_count(self, volume_name=None, node_name=None, disk_uuid=None, count=None):
        return self.replica.wait_for_disk_replica_count(volume_name, node_name, disk_uuid, count)

    def get_replica_names(self, volume_name, numberOfReplicas=3):
        return self.replica.get_replica_names(volume_name, numberOfReplicas)

    def wait_for_replica_file_size(self, volume_name, expected_size):
        return self.replica.wait_for_replica_file_size(volume_name, expected_size)

    def wait_for_replica_failed(self, volume_name, node_name):
        return self.replica.wait_for_replica_failed(volume_name, node_name)

    def mark_replica_failed(self, replica_name):
        """Keep the failed replica CR and data available for reuse by the scheduler."""
        failed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        client.CustomObjectsApi().patch_namespaced_custom_object(
            "longhorn.io", "v1beta2", LONGHORN_NAMESPACE, "replicas", replica_name,
            {"spec": {"failedAt": failed_at}})

    def check_volume_rw_replicas(self, volume_name, *replica_names):
        """Assert the exact RW sources, without allowing an in-progress rebuild."""
        engine = Engine().get_engine(volume_name)
        # The manager translates backend addresses into Replica CR names.
        modes = engine["status"].get("replicaModeMap") or {}
        logging(f"{volume_name}: expected RW={replica_names}, replica modes={modes}")
        assert {name for name, mode in modes.items() if mode == "RW"} == set(replica_names), modes
        assert "WO" not in modes.values(), f"Unexpected replica rebuilding: {modes}"
