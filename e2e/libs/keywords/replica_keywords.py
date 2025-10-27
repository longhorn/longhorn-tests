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
