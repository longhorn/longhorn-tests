from csi_volume_snapshot import CSIVolumeSnapshot

class csi_volume_snapshot_keywords:

    def __init__(self):
        self.csi_volume_snapshot = CSIVolumeSnapshot()

    def create_csi_volume_snapshot_class(self, class_name, type=None, deletionPolicy=None):
        self.csi_volume_snapshot.create_csi_volume_snapshot_class(class_name, type, deletionPolicy)

    def create_csi_volume_snapshot(self, snapshot_name, pvc_name):
        self.csi_volume_snapshot.create_csi_volume_snapshot(snapshot_name, pvc_name)

    def wait_for_csi_volume_snapshot_to_be_ready(self, snapshot_name):
        self.csi_volume_snapshot.wait_for_csi_volume_snapshot_to_be_ready(snapshot_name)

    def get_longhorn_snapshot_name_associated_with_csi_volume_snapshot(self, snapshot_name):
        return self.csi_volume_snapshot.get_longhorn_snapshot_name_associated_with_csi_volume_snapshot(snapshot_name)

    def cleanup_csi_volume_snapshot_classes(self):
        self.csi_volume_snapshot.cleanup_csi_volume_snapshot_classes()

    def delete_csi_volume_snapshot(self, snapshot_name):
        self.csi_volume_snapshot.delete_csi_volume_snapshot(snapshot_name)

    def cleanup_csi_volume_snapshots(self):
        self.csi_volume_snapshot.cleanup_csi_volume_snapshots()

    def force_delete_volumesnapshot(self, snapshot_name):
        self.csi_volume_snapshot.force_delete_volumesnapshot(snapshot_name)
