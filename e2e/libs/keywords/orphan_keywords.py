from orphan import Orphan


class orphan_keywords:

    def __init__(self):
        self.orphan = Orphan()

    def create_orphaned_replica_for_volume(self, volume_name):
        self.orphan.create_orphaned_replica_for_volume(volume_name)

    def wait_for_orphan_count(self, count):
        self.orphan.wait_for_orphan_count(count)

    def delete_orphans(self):
        self.orphan.delete_orphans()
