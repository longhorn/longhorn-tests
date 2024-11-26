from replica import Replica


class replica_keywords:

    def __init__(self):
        self.replica = Replica()

    def validate_replica_setting(self, volume_name, setting_name, value):
        return self.replica.validate_replica_setting(volume_name, setting_name, value)
