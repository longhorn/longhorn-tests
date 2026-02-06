from strategy import LonghornOperationStrategy

from volume.base import Base
from volume.crd import CRD
from volume.rest import Rest


class Volume(Base):

    _strategy = LonghornOperationStrategy.CRD

    def __init__(self):
        if self._strategy == LonghornOperationStrategy.CRD:
            self.volume = CRD()
        else:
            self.volume = Rest()

    def create(self, volume_name, size, numberOfReplicas, frontend, migratable, dataLocality, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted, nodeSelector, diskSelector, backupBlockSize, rebuildConcurrentSyncLimit):
        return self.volume.create(volume_name, size, numberOfReplicas, frontend, migratable, dataLocality, accessMode, dataEngine, backingImage, Standby, fromBackup, encrypted, nodeSelector, diskSelector, backupBlockSize, rebuildConcurrentSyncLimit)

    def delete(self, volume_name, wait):
        return self.volume.delete(volume_name, wait)

    def wait_for_volume_deleted(self, volume_name):
        return self.volume.wait_for_volume_deleted(volume_name)

    def attach(self, volume_name, node_name, disable_frontend, wait, retry):
        return self.volume.attach(volume_name, node_name, disable_frontend, wait, retry)

    def is_attached_to(self, volume_name, node_name):
        return self.volume.is_attached_to(volume_name, node_name)

    def detach(self, volume_name, node_name):
        return self.volume.detach(volume_name, node_name)

    def get(self, volume_name):
        return self.volume.get(volume_name)

    def list(self, label_selector=None, dataEngine=None):
        return self.volume.list(label_selector=label_selector, dataEngine=dataEngine)

    def list_names(self, label_selector=None, dataEngine=None):
        return [item['metadata']['name'] for item in self.list(label_selector, dataEngine)]

    def set_annotation(self, volume_name, annotation_key, annotation_value):
        return self.volume.set_annotation(volume_name, annotation_key, annotation_value)

    def get_annotation_value(self, volume_name, annotation_key):
        return self.volume.get_annotation_value(volume_name, annotation_key)

    def wait_for_volume_state(self, volume_name, desired_state):
        return self.volume.wait_for_volume_state(volume_name, desired_state)

    def wait_for_volume_condition(self, volume_name, condition_name, condition_status, reason):
        return self.volume.wait_for_volume_condition(volume_name, condition_name, condition_status, reason)

    def wait_for_restore_required_status(self, volume_name, restore_required_state):
        return self.volume.wait_for_restore_required_status(volume_name, restore_required_state)

    def wait_for_volume_clone_status(self, volume_name, desired_state):
        return self.volume.wait_for_volume_clone_status(volume_name, desired_state)

    def wait_for_volume_to_be_created(self, volume_name):
        self.volume.wait_for_volume_to_be_created(volume_name)

    def wait_for_volume_attached(self, volume_name):
        self.volume.wait_for_volume_robustness_not(volume_name, "unknown")
        self.volume.wait_for_volume_state(volume_name, "attached")

    def wait_for_volume_detached(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "detached")

    def wait_for_volume_attaching(self, volume_name):
        self.volume.wait_for_volume_attaching(volume_name)

    def wait_for_volume_stuck_attaching(self, volume_name):
        self.volume.wait_for_volume_keep_in_state(volume_name, "attaching")

    def wait_for_volume_faulted(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "detached")
        self.volume.wait_for_volume_robustness(volume_name, "faulted")

    def wait_for_volume_healthy(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "attached")
        self.volume.wait_for_volume_robustness(volume_name, "healthy")

    def wait_for_volume_migration_to_be_ready(self, volume_name):
        self.volume.wait_for_volume_migration_to_be_ready(volume_name)

    def wait_for_volume_migration_complete(self, volume_name, node_name):
        self.volume.wait_for_volume_migration_complete(volume_name, node_name)

    def wait_for_volume_migration_to_rollback(self, volume_name, node_name):
        self.volume.wait_for_volume_migration_to_rollback(volume_name, node_name)

    def wait_for_volume_restoration_to_complete(self, volume_name, backup_name):
        if backup_name:
            self.volume.wait_for_volume_restoration_to_complete(volume_name, backup_name)
        else:
            self.volume.wait_for_restore_required_status(volume_name, False)

    def wait_for_volume_restoration_start(self, volume_name, backup_name):
        self.volume.wait_for_volume_restoration_start(volume_name, backup_name)

    def expand(self, volume_name, size):
        return self.volume.expand(volume_name, size)

    def wait_for_volume_expand_to_size(self, volume_name, size):
        return self.volume.wait_for_volume_expand_to_size(volume_name, size)

    def wait_for_volume_degraded(self, volume_name):
        self.volume.wait_for_volume_state(volume_name, "attached")
        self.volume.wait_for_volume_robustness(volume_name, "degraded")

    def wait_for_volume_unknown(self, volume_name):
        self.volume.wait_for_volume_robustness(volume_name, "unknown")

    def get_endpoint(self, volume_name):
        return self.volume.get_endpoint(volume_name)

    def write_random_data(self, volume_name, size, data_id):
        return self.volume.write_random_data(volume_name, size, data_id)

    def prefill_with_fio(self, volume_name, size):
        return self.volume.prefill_with_fio(volume_name, size)

    def write_scattered_data_with_fio(self, volume_name, size, bs, ratio):
        return self.volume.write_scattered_data_with_fio(volume_name, size, bs, ratio)

    def keep_writing_data(self, volume_name):
        return self.volume.keep_writing_data(volume_name, 256)

    def delete_replica(self, volume_name, node_name):
        return self.volume.delete_replica(volume_name, node_name)

    def delete_replica_by_name(self, volume_name, replica_name):
        return self.volume.delete_replica_by_name(volume_name, replica_name)

    def wait_for_replica_rebuilding_start(self, volume_name, node_name=None):
        return self.volume.wait_for_replica_rebuilding_start(volume_name, node_name)

    def is_replica_rebuilding_in_progress(self, volume_name, node_name=None):
        return self.volume.is_replica_rebuilding_in_progress(volume_name, node_name)

    def crash_replica_processes(self, volume_name):
        return self.volume.crash_replica_processes(volume_name)

    def crash_node_replica_process(self, volume_name, node_name):
        return self.volume.crash_node_replica_process(volume_name, node_name)

    def wait_for_replica_stopped(self, volume_name, node_name):
        return self.volume.is_replica_running(volume_name, node_name, is_running=False)

    def wait_for_replica_running(self, volume_name, node_name):
        return self.volume.is_replica_running(volume_name, node_name, is_running=True)

    def wait_for_replica_to_be_deleted(self, volume_name, node_name):
        return self.volume.wait_for_replica_to_be_deleted(volume_name, node_name)

    def get_replica_name_on_node(self, volume_name, node_name):
        return self.volume.get_replica_name_on_node(volume_name, node_name)

    def wait_for_replica_count(self, volume_name, node_name, replica_count, running):
        return self.volume.wait_for_replica_count(volume_name, node_name, replica_count, running)

    def wait_for_replica_rebuilding_complete(self, volume_name, node_name=None):
        return self.volume.wait_for_replica_rebuilding_complete(volume_name, node_name)

    def check_data_checksum(self, volume_name, data_id):
        return self.volume.check_data_checksum(volume_name, data_id)

    def get_checksum(self, volume_name):
        return self.volume.get_checksum(volume_name)

    def get_sha512sum(self, volume_name):
        return self.volume.get_sha512sum(volume_name)

    def validate_volume_replicas_anti_affinity(self, volume_name):
        return self.volume.validate_volume_replicas_anti_affinity(volume_name)

    def update_volume_spec(self, volume_name, key, value):
        return self.volume.update_volume_spec(volume_name, key, value)

    def activate(self, volume_name):
        return self.volume.activate(volume_name)

    def create_persistentvolume(self, volume_name, retry):
        return self.volume.create_persistentvolume(volume_name, retry)

    def create_persistentvolumeclaim(self, volume_name, retry):
        return self.volume.create_persistentvolumeclaim(volume_name, retry)

    def upgrade_engine_image(self, volume_name, engine_image_name):
        return self.volume.upgrade_engine_image(volume_name, engine_image_name)

    def wait_for_engine_image_upgrade_completed(self, volume_name, engine_image_name):
        return self.volume.wait_for_engine_image_upgrade_completed(volume_name, engine_image_name)

    def validate_volume_setting(self, volume_name, setting_name, value):
        return self.volume.validate_volume_setting(volume_name, setting_name, value)

    def trim_filesystem(self, volume_name, is_expect_fail=False):
        return self.volume.trim_filesystem(volume_name, is_expect_fail=is_expect_fail)

    def update_offline_replica_rebuild(self, volume_name, rebuild_type):
        return self.volume.update_offline_replica_rebuild(volume_name, rebuild_type)

    def update_data_locality(self, volume_name, data_locality):
        return self.volume.update_data_locality(volume_name, data_locality)

    def check_volume_has_recurringjob(self, volume_name, job_name):
        self.volume.check_volume_has_recurringjob(volume_name, job_name)

    def check_volume_has_recurringjob_group(self, volume_name, job_group_name):
        self.volume.check_volume_has_recurringjob_group(volume_name, job_group_name)
