from local_engine.local_engine import LocalEngine

from utility.utility import logging


class local_engine_keywords:

    def __init__(self):
        self.local_engine = LocalEngine()

    def assert_local_engine_disk_path_available(
            self, node_name, disk_name, disk_path):
        logging(
            f"Checking dedicated local-engine disk path {disk_path} "
            f"on node {node_name}"
        )
        self.local_engine.assert_disk_path_available(
            node_name, disk_name, disk_path)

    def assert_local_engine_disk_paths_available(
            self, node_name, disk_names, disk_paths):
        self.local_engine.assert_disk_paths_available(
            node_name, disk_names, disk_paths)

    def local_engine_disk_exists(self, node_name, disk_name):
        return self.local_engine.lvm_disk_exists(node_name, disk_name)

    def wait_for_local_engine_disk_ready(
            self, node_name, disk_name, disk_path):
        return self.local_engine.wait_for_lvm_disk_ready(
            node_name, disk_name, disk_path)

    def wait_for_local_engine_disk_backend_initialized(
            self, node_name, disk_name, disk_path):
        self.local_engine.wait_for_lvm_backend_initialized(
            node_name, disk_name, disk_path)

    def wait_for_local_engine_volume_ready(
            self, volume_name, node_name, disk_name):
        return self.local_engine.wait_for_local_volume_ready(
            volume_name, node_name, disk_name)

    def wait_for_local_engine_logical_volume_deleted(
            self, node_name, disk_name, replica_name):
        self.local_engine.wait_for_logical_volume(
            node_name,
            disk_name,
            replica_name,
            present=False,
        )

    def wait_for_local_engine_logical_volume_size(
            self, node_name, disk_name, replica_name, expected_size):
        self.local_engine.wait_for_logical_volume_size(
            node_name, disk_name, replica_name, expected_size)

    def wait_for_local_instance_managers_to_follow_lvm_disks(self):
        self.local_engine.wait_for_instance_managers_to_follow_lvm_disks()

    def get_local_engine_disk_stable_alias(self, node_name, disk_path):
        return self.local_engine.get_stable_device_alias(node_name, disk_path)

    def verify_local_engine_disk_device_clean(self, node_name, disk_path):
        self.local_engine.verify_lvm_device_clean(node_name, disk_path)

    def wait_for_local_engine_disk_removed(self, node_name, disk_name):
        self.local_engine.wait_for_lvm_disk_removed(node_name, disk_name)

    def wait_for_local_engine_storage_capacity(
            self, storage_class_name, node_name):
        return self.local_engine.wait_for_storage_capacity(
            storage_class_name, node_name)

    def verify_local_engine_capacity_and_io_metrics(
            self, node_name, disk_name, volume_name, workload_name):
        self.local_engine.verify_capacity_and_io_metrics(
            node_name, disk_name, volume_name, workload_name)

    def verify_local_instance_manager_restart_during_io(
            self, node_name, workload_name):
        self.local_engine.verify_instance_manager_restart_during_io(
            node_name, workload_name)

    def verify_local_engine_provisioning_mode(
            self, node_name, disk_name, volume_name, replica_name, mode):
        self.local_engine.verify_provisioning_mode(
            node_name, disk_name, volume_name, replica_name, mode)

    def wait_for_local_engine_thin_pool_absent(self, node_name, disk_name):
        self.local_engine.wait_for_thin_pool_absent(node_name, disk_name)

    def verify_local_engine_disk_spans_devices(
            self, node_name, disk_name, disk_path):
        self.local_engine.verify_lvm_disk_spans_devices(
            node_name, disk_name, disk_path)

    def verify_local_engine_disk_path_change_rejected(
            self, node_name, disk_name, new_path):
        self.local_engine.verify_lvm_disk_path_change_rejected(
            node_name, disk_name, new_path)

    def verify_local_engine_duplicate_disk_device_rejected(
            self, node_name, disk_name, device_path, free_device):
        self.local_engine.verify_duplicate_lvm_disk_device_rejected(
            node_name, disk_name, device_path, free_device)

    def wait_for_local_engine_disk_not_ready(
            self, node_name, disk_name, reason):
        self.local_engine.wait_for_lvm_disk_not_ready(
            node_name, disk_name, reason)

    def format_local_engine_device(self, node_name, device_path):
        self.local_engine.format_device(node_name, device_path)

    def wipe_local_engine_device(self, node_name, device_path):
        self.local_engine.wipe_device(node_name, device_path)
