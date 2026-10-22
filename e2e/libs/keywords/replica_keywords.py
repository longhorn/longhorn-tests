from replica import Replica


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

    def get_volume_replica_ip(self, volume_name, node_name):
        return self._get_running_replica(volume_name, node_name)["status"]["ip"]

    def get_volume_replica_port(self, volume_name, node_name):
        return int(self._get_running_replica(volume_name, node_name)["status"]["port"])

    def _get_running_replica(self, volume_name, node_name):
        replicas = [
            replica for replica in self.replica.get(volume_name, node_name)
            if replica.get("status", {}).get("currentState") == "running"
        ]
        assert len(replicas) == 1, (
            f"Expected one running replica for volume {volume_name} on "
            f"node {node_name}, got {len(replicas)}"
        )
        return replicas[0]
