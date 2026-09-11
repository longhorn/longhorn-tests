from longhorn_deploy import LonghornDeploy
from utility.utility import generate_name_with_suffix
from utility.utility import get_all_crs
from utility.utility import get_longhorn_namespace
from utility.utility import logging

import subprocess
import time


class longhorn_deploy_keywords:

    def __init__(self):
        self.longhorn = LonghornDeploy()

    def uninstall_longhorn_system(self, is_stable_version=False):
        self.longhorn.uninstall(is_stable_version)

    def check_longhorn_crd_removed(self):
        self.longhorn.check_longhorn_crd_removed()

    def install_longhorn_system(self, custom_cmd="", install_stable_version=False, longhorn_namespace="longhorn-system"):
        self.longhorn.install(custom_cmd, install_stable_version, longhorn_namespace)

    def upgrade_longhorn(self, upgrade_to_transient_version=False, timeout=600, wait_when_fail=True, custom_cmd="", wait=True):
        return self.longhorn.upgrade(upgrade_to_transient_version, timeout, wait_when_fail, custom_cmd, wait)

    def wait_for_longhorn_upgrade_process(self, process, timeout=600):
        try:
            process.wait(timeout=timeout)
            return True if process.returncode == 0 else False
        except subprocess.TimeoutExpired:
            logging(f"Upgrade timeout after {timeout}s. Killing process...")
            process.kill()
            process.wait()
            return False

    def enable_storage_network_setting(self):
        self.longhorn.enable_storage_network_setting()

    def wait_for_instance_manager_upgrade_relocation_node_for_volume_on_node(self, volume_id, node_name, timeout=600, poll_interval=5):
        volume_name = generate_name_with_suffix("volume", volume_id)
        return self.wait_for_instance_manager_upgrade_relocation_for_volume_name(
            volume_name, node_name, timeout, poll_interval
        )

    def wait_for_instance_manager_upgrade_relocation_for_volume_name(self, volume_name, node_name, timeout=600, poll_interval=5):
        """Wait for IM upgrade relocation to start for a given volume name (e.g., pvc-xxx)."""
        namespace = get_longhorn_namespace()
        retry_count = (int(timeout) + int(poll_interval) - 1) // int(poll_interval)
        last_state = ""

        for i in range(retry_count):
            try:
                upgrades = get_all_crs("longhorn.io", "v1beta2", namespace, "instancemanagerupgrades")
                matched_upgrades = [
                    item for item in upgrades.get("items", [])
                    if item.get("spec", {}).get("nodeID") == node_name
                ]

                if matched_upgrades:
                    matched_upgrades.sort(key=lambda item: item.get("metadata", {}).get("creationTimestamp", ""))
                    latest_upgrade = matched_upgrades[-1]
                    status = latest_upgrade.get("status", {})
                    last_state = status.get("state", "")
                    engine_status = status.get("engines", {}).get(volume_name, {})
                    relocation_node = engine_status.get("temporaryNodeID", "")
                    if relocation_node:
                        logging(
                            f"Found relocation node {relocation_node} for volume {volume_name} "
                            f"on source node {node_name} from IMU {latest_upgrade.get('metadata', {}).get('name')}"
                        )
                        return relocation_node

                logging(
                    f"Waiting for IMU relocation for volume {volume_name} on node {node_name} "
                    f"(latest state: {last_state}), retry ({i}) ..."
                )
            except Exception as e:
                logging(f"Getting instance manager upgrade relocation state error: {e}")

            time.sleep(int(poll_interval))

        assert False, (
            f"Failed to wait for instance manager upgrade relocation for volume {volume_name} "
            f"on node {node_name}"
        )
