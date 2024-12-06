from replica import Replica


class replica_keywords:

    def __init__(self):
        self.replica = Replica()

    def validate_replica_setting(self, volume_name, setting_name, value):
        return self.replica.validate_replica_setting(volume_name, setting_name, value)

    def get_replicas(self, volume_name=None, node_name=None, disk_uuid=None):
        return self.replica.get(volume_name, node_name, disk_uuid)
