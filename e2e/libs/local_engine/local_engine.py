import ast
import json
import time

from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.utils.quantity import parse_quantity

from node import Node
from node_exec import NodeExec
from utility.constant import LONGHORN_NAMESPACE
from utility.utility import get_retry_count_and_interval
from utility.utility import logging
from utility.utility import pod_exec
from metrics.metrics import get_longhorn_metrics
from workload.pod import list_pods


class LocalEngine:

    THIN_POOL_NAME = "longhorn-thin-pool"
    VG_TAG = "longhorn-local-data-engine"

    IO_DATA_PATH = "/data/local-engine-im-restart-data"
    IO_READBACK_PATH = "/data/local-engine-im-restart-readback"
    IO_ERROR_PATH = "/tmp/local-engine-im-restart-error"
    IO_LOG_PATH = "/tmp/local-engine-im-restart.log"
    IO_PID_PATH = "/tmp/local-engine-im-restart.pid"
    IO_PROGRESS_PATH = "/tmp/local-engine-im-restart-progress"
    IO_STALL_TIMEOUT = 10

    def __init__(self):
        self.core_api = client.CoreV1Api()
        self.storage_api = client.StorageV1Api()
        self.custom_objects_api = client.CustomObjectsApi()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    def wait_for_storage_capacity(
            self, storage_class_name, node_name):
        last_capacities = []
        for i in range(self.retry_count):
            capacities = self.storage_api.list_csi_storage_capacity_for_all_namespaces().items
            last_capacities = [
                capacity for capacity in capacities
                if capacity.storage_class_name == storage_class_name
            ]
            for capacity in last_capacities:
                selector = capacity.node_topology
                labels = selector.match_labels if selector else {}
                expressions = selector.match_expressions if selector else []
                matches_node = (
                    (labels or {}).get("kubernetes.io/hostname") == node_name
                    or any(
                        expression.key == "kubernetes.io/hostname"
                        and node_name in (expression.values or [])
                        for expression in (expressions or [])
                    )
                )
                raw_capacity = str(capacity.capacity or "0")
                capacity_bytes = int(parse_quantity(raw_capacity))
                if matches_node and capacity_bytes > 0:
                    logging(
                        f"StorageClass {storage_class_name} advertises "
                        f"{raw_capacity} bytes on {node_name}"
                    )
                    return capacity_bytes
            logging(
                f"Waiting for positive CSI storage capacity for "
                f"{storage_class_name} on {node_name} ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"StorageClass {storage_class_name} did not advertise capacity "
            f"on {node_name}: {last_capacities}"
        )

    @staticmethod
    def _metric_sample(metrics, metric_name, label_name, label_value):
        for family in metrics:
            for sample in family.samples:
                if (
                    sample.name == metric_name
                    and sample.labels.get(label_name) == label_value
                ):
                    return sample
        return None

    def verify_capacity_and_io_metrics(
            self, node_name, disk_name, volume_name, workload_name):
        node = self._get_node(node_name)
        disk_status = node.get("status", {}).get("diskStatus", {}).get(
            disk_name, {})
        maximum = int(disk_status.get("storageMaximum", 0))
        available = int(disk_status.get("storageAvailable", 0))
        if maximum <= 0 or available <= 0 or available > maximum:
            raise AssertionError(
                f"Invalid LVM capacity for {disk_name}: {disk_status}"
            )
        conditions = {
            condition["type"]: condition.get("status")
            for condition in disk_status.get("conditions", [])
        }
        if conditions.get("Ready") != "True" or \
                conditions.get("Schedulable") != "True":
            raise AssertionError(
                f"LVM disk {disk_name} is not healthy and schedulable: "
                f"{disk_status}"
            )

        workload_pod = self._get_workload_pod(workload_name)
        sequence = self._start_sustained_io(workload_pod.metadata.name)
        required_positive = {
            "longhorn_volume_write_throughput": ("volume", volume_name),
            "longhorn_volume_write_iops": ("volume", volume_name),
            "longhorn_volume_write_latency": ("volume", volume_name),
            "longhorn_disk_write_throughput": ("disk", disk_name),
            "longhorn_disk_write_iops": ("disk", disk_name),
            "longhorn_disk_write_latency": ("disk", disk_name),
        }
        required_present = {
            "longhorn_disk_capacity_bytes": ("disk", disk_name),
            "longhorn_disk_usage_bytes": ("disk", disk_name),
            "longhorn_disk_reservation_bytes": ("disk", disk_name),
            "longhorn_volume_read_throughput": ("volume", volume_name),
            "longhorn_volume_read_iops": ("volume", volume_name),
            "longhorn_volume_read_latency": ("volume", volume_name),
        }
        last_values = {}
        try:
            # The first scrape establishes the IM's cumulative-counter baseline.
            get_longhorn_metrics(node_name)
            for i in range(self.retry_count):
                sequence = self._wait_for_io_progress(
                    workload_pod.metadata.name, sequence)
                metrics = get_longhorn_metrics(node_name)
                last_values = {}
                all_positive = True
                for name, (label_name, label_value) in required_positive.items():
                    sample = self._metric_sample(
                        metrics, name, label_name, label_value)
                    last_values[name] = None if sample is None else sample.value
                    if sample is None or float(sample.value) <= 0:
                        all_positive = False
                all_present = all(
                    self._metric_sample(metrics, name, label_name, label_value)
                    is not None
                    for name, (label_name, label_value) in required_present.items()
                )
                if all_positive and all_present:
                    # Compare a single scrape with fresh controller state. The
                    # Node status may lag the LV operation that changed usage.
                    node = self._get_node(node_name)
                    disk_spec = node.get("spec", {}).get(
                        "disks", {}).get(disk_name, {})
                    disk_status = node.get("status", {}).get(
                        "diskStatus", {}).get(disk_name, {})
                    maximum = int(disk_status.get("storageMaximum", 0))
                    available = int(disk_status.get("storageAvailable", 0))
                    capacity = self._metric_sample(
                        metrics, "longhorn_disk_capacity_bytes",
                        "disk", disk_name)
                    usage = self._metric_sample(
                        metrics, "longhorn_disk_usage_bytes",
                        "disk", disk_name)
                    reservation = self._metric_sample(
                        metrics, "longhorn_disk_reservation_bytes",
                        "disk", disk_name)
                    capacity_matches = int(capacity.value) == maximum
                    usage_matches = int(usage.value) == maximum - available
                    reservation_matches = int(reservation.value) == int(
                        disk_spec.get("storageReserved", 0))
                    if not (
                        capacity_matches
                        and usage_matches
                        and reservation_matches
                    ):
                        last_values.update({
                            "nodeCapacity": maximum,
                            "nodeUsage": maximum - available,
                            "metricCapacity": capacity.value,
                            "metricUsage": usage.value,
                            "metricReservation": reservation.value,
                        })
                        logging(
                            "Waiting for local capacity status and metrics "
                            f"to converge ... ({i}): {last_values}"
                        )
                        time.sleep(self.retry_interval)
                        continue
                    logging(
                        f"Verified local volume and VG capacity/I/O metrics: "
                        f"{last_values}"
                    )
                    return
                logging(
                    f"Waiting for positive local volume and VG I/O metrics "
                    f"... ({i}): {last_values}"
                )
                time.sleep(self.retry_interval)
        finally:
            self._stop_sustained_io(workload_pod.metadata.name)
        raise AssertionError(
            f"Local volume and VG I/O metrics did not become positive: "
            f"{last_values}"
        )

    def _get_node(self, node_name):
        return self.custom_objects_api.get_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=LONGHORN_NAMESPACE,
            plural="nodes",
            name=node_name,
        )

    def _list_local_instance_manager_pods(self, node_name):
        label_selector = (
            "longhorn.io/component=instance-manager,"
            "longhorn.io/data-engine=local,"
            f"longhorn.io/node={node_name}"
        )
        return self.core_api.list_namespaced_pod(
            namespace=LONGHORN_NAMESPACE,
            label_selector=label_selector,
        ).items

    @staticmethod
    def _pod_is_ready(pod):
        statuses = pod.status.container_statuses or []
        return (
            pod.status.phase == "Running"
            and statuses
            and all(status.ready for status in statuses)
        )

    def _get_local_instance_manager_pod(self, node_name):
        for pod in self._list_local_instance_manager_pods(node_name):
            statuses = pod.status.container_statuses or []
            all_ready = statuses and all(status.ready for status in statuses)
            if pod.status.phase == "Running" and all_ready:
                return pod.metadata.name
        return None

    def _get_ready_local_instance_manager_pod(self, node_name):
        for pod in self._list_local_instance_manager_pods(node_name):
            if self._pod_is_ready(pod):
                return pod
        return None

    def _get_workload_pod(self, workload_name):
        pods = self.core_api.list_namespaced_pod(
            namespace="default",
            label_selector=f"app={workload_name}",
        ).items
        if len(pods) != 1:
            raise AssertionError(
                f"Expected one pod for workload {workload_name}, got "
                f"{[pod.metadata.name for pod in pods]}"
            )
        return pods[0]

    @staticmethod
    def _pod_restart_count(pod):
        return sum(
            status.restart_count
            for status in (pod.status.container_statuses or [])
        )

    def _assert_workload_pod_unchanged(
            self, workload_name, expected_uid, expected_restart_count):
        pod = self._get_workload_pod(workload_name)
        restart_count = self._pod_restart_count(pod)
        if pod.metadata.uid != expected_uid:
            raise AssertionError(
                f"Workload pod was recreated during the local instance "
                f"manager restart: expected UID {expected_uid}, got "
                f"{pod.metadata.uid}"
            )
        if restart_count != expected_restart_count:
            raise AssertionError(
                f"Workload pod {pod.metadata.name} restarted during the "
                f"local instance manager restart: expected restart count "
                f"{expected_restart_count}, got {restart_count}"
            )
        if not self._pod_is_ready(pod):
            raise AssertionError(
                f"Workload pod {pod.metadata.name} stopped being ready "
                "during the local instance manager restart"
            )
        return pod

    def _start_sustained_io(self, pod_name):
        command = (
            f"rm -f {self.IO_ERROR_PATH} {self.IO_LOG_PATH} "
            f"{self.IO_PID_PATH} {self.IO_PROGRESS_PATH}; "
            "("
            "sequence=0; "
            "fail_io() { printf '%s\\n' \"$1\" > "
            f"{self.IO_ERROR_PATH}; exit 1; }}; "
            "while true; do "
            "sequence=$((sequence + 1)); "
            f"dd if=/dev/urandom of={self.IO_DATA_PATH} "
            "bs=1M count=1 status=none || fail_io write-failed; "
            "sync || fail_io sync-failed; "
            f"cp {self.IO_DATA_PATH} {self.IO_READBACK_PATH} "
            "|| fail_io read-failed; "
            f"expected=$(md5sum {self.IO_DATA_PATH} | awk '{{print $1}}'); "
            f"actual=$(md5sum {self.IO_READBACK_PATH} | awk '{{print $1}}'); "
            "[ -n \"$expected\" ] || fail_io checksum-failed; "
            "[ \"$expected\" = \"$actual\" ] "
            "|| fail_io checksum-mismatch; "
            f"printf '%s %s\\n' \"$sequence\" \"$actual\" > "
            f"{self.IO_PROGRESS_PATH}.next; "
            f"mv {self.IO_PROGRESS_PATH}.next {self.IO_PROGRESS_PATH}; "
            "done"
            f") > {self.IO_LOG_PATH} 2>&1 < /dev/null & "
            f"echo $! > {self.IO_PID_PATH}"
        )
        pod_exec(pod_name, "default", command)
        return self._wait_for_io_progress(pod_name, 0)

    def _read_io_progress(self, pod_name):
        command = (
            f"if [ -s {self.IO_ERROR_PATH} ]; then "
            f"printf 'ERROR '; cat {self.IO_ERROR_PATH}; "
            f"elif [ -s {self.IO_PROGRESS_PATH} ]; then "
            f"cat {self.IO_PROGRESS_PATH}; else echo 0; fi"
        )
        output = pod_exec(pod_name, "default", command).strip()
        if output.startswith("ERROR"):
            raise AssertionError(
                f"Sustained I/O failed in workload pod {pod_name}: {output}"
            )
        try:
            return int(output.split()[0])
        except (IndexError, ValueError) as error:
            raise AssertionError(
                f"Invalid sustained-I/O progress from pod {pod_name}: "
                f"{output}"
            ) from error

    def _wait_for_io_progress(self, pod_name, previous_sequence):
        for i in range(self.retry_count):
            sequence = self._read_io_progress(pod_name)
            if sequence > previous_sequence:
                return sequence
            logging(
                f"Waiting for sustained I/O in pod {pod_name} to advance "
                f"past sequence {previous_sequence} ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Sustained I/O in pod {pod_name} did not advance past "
            f"sequence {previous_sequence}"
        )

    def _stop_sustained_io(self, pod_name):
        command = (
            f"if [ -s {self.IO_PID_PATH} ]; then "
            f"kill $(cat {self.IO_PID_PATH}) 2>/dev/null || true; fi"
        )
        try:
            pod_exec(pod_name, "default", command)
            self._read_io_progress(pod_name)
        except ApiException as error:
            logging(
                f"Failed to stop sustained I/O in pod {pod_name}: {error}"
            )

    def verify_instance_manager_restart_during_io(
            self, node_name, workload_name):
        workload_pod = self._get_workload_pod(workload_name)
        workload_uid = workload_pod.metadata.uid
        restart_count = self._pod_restart_count(workload_pod)
        instance_manager = self._get_ready_local_instance_manager_pod(
            node_name)
        if instance_manager is None:
            raise AssertionError(
                f"No ready local instance manager found on {node_name}"
            )

        pod_name = workload_pod.metadata.name
        initial_sequence = self._start_sustained_io(pod_name)
        old_instance_manager_uid = instance_manager.metadata.uid
        logging(
            "Restarting local instance manager "
            f"{instance_manager.metadata.name} "
            f"with sustained I/O at sequence {initial_sequence}"
        )

        try:
            self.core_api.delete_namespaced_pod(
                name=instance_manager.metadata.name,
                namespace=LONGHORN_NAMESPACE,
                grace_period_seconds=0,
            )

            replacement = None
            last_sequence = initial_sequence
            last_progress_at = time.monotonic()
            restart_started_at = last_progress_at
            for i in range(self.retry_count):
                self._assert_workload_pod_unchanged(
                    workload_name, workload_uid, restart_count)
                sequence = self._read_io_progress(pod_name)
                if sequence > last_sequence:
                    last_sequence = sequence
                    last_progress_at = time.monotonic()
                elif time.monotonic() - last_progress_at > \
                        self.IO_STALL_TIMEOUT:
                    raise AssertionError(
                        f"Sustained I/O stopped advancing for more than "
                        f"{self.IO_STALL_TIMEOUT} seconds during the local "
                        "instance manager restart"
                    )

                for candidate in self._list_local_instance_manager_pods(
                        node_name):
                    if (
                        candidate.metadata.uid != old_instance_manager_uid
                        and self._pod_is_ready(candidate)
                    ):
                        replacement = candidate
                        break

                if (
                    replacement is not None
                    and time.monotonic() - restart_started_at >= 3
                    and last_sequence > initial_sequence
                ):
                    break
                logging(
                    f"Waiting for replacement local instance manager while "
                    f"I/O is at sequence {last_sequence} ... ({i})"
                )
                time.sleep(self.retry_interval)

            if replacement is None:
                raise AssertionError(
                    f"Local instance manager on {node_name} was not replaced"
                )

            final_sequence = self._wait_for_io_progress(
                pod_name, last_sequence)
            self._assert_workload_pod_unchanged(
                workload_name, workload_uid, restart_count)
            logging(
                f"Local instance manager changed from UID "
                f"{old_instance_manager_uid} to {replacement.metadata.uid}; "
                f"workload pod UID {workload_uid} remained unchanged and "
                f"verified I/O advanced from sequence {initial_sequence} "
                f"to {final_sequence}"
            )
        finally:
            self._stop_sustained_io(pod_name)

    def assert_disk_path_available(self, node_name, disk_name, disk_path):
        node = self._get_node(node_name)
        disks = node.get("spec", {}).get("disks", {})
        for existing_name, disk in disks.items():
            if disk.get("diskType") == "lvm" and existing_name != disk_name:
                raise AssertionError(
                    f"Node {node_name} already has LVM disk {existing_name}; "
                    "the local-engine test requires a node without another "
                    "LVM disk"
                )
            if disk.get("path") == disk_path and existing_name != disk_name:
                raise AssertionError(
                    f"Dedicated local-engine test path {disk_path} is already "
                    "used by "
                    f"disk {existing_name} on node {node_name}"
                )

    def assert_disk_paths_available(self, node_name, disk_names, disk_paths):
        if len(disk_names) != len(disk_paths):
            raise AssertionError("Local-engine disk names and paths differ")
        node = self._get_node(node_name)
        disks = node.get("spec", {}).get("disks", {})
        allowed_names = set(disk_names)
        allowed_paths = set(disk_paths)
        for existing_name, disk in disks.items():
            if (
                disk.get("diskType") == "lvm"
                and existing_name not in allowed_names
            ):
                raise AssertionError(
                    f"Node {node_name} already has unrelated LVM disk "
                    f"{existing_name}; the test requires dedicated LVM disks"
                )
            if (
                disk.get("path") in allowed_paths
                and existing_name not in allowed_names
            ):
                raise AssertionError(
                    f"Dedicated local-engine path {disk.get('path')} is "
                    f"already used by disk {existing_name}"
                )

    def lvm_disk_exists(self, node_name, disk_name):
        return disk_name in self._get_node(node_name).get(
            "spec", {}).get("disks", {})

    def _disk_status(self, node_name, disk_name):
        return self._get_node(node_name).get("status", {}).get(
            "diskStatus", {}).get(disk_name, {})

    def _disk_uuid(self, node_name, disk_name):
        return self._disk_status(node_name, disk_name).get("diskUUID", "")

    def wait_for_lvm_disk_ready(self, node_name, disk_name, disk_path):
        disk_status = None
        for i in range(self.retry_count):
            node = self._get_node(node_name)
            disk_spec = node.get("spec", {}).get("disks", {}).get(
                disk_name, {})
            disk_status = node.get("status", {}).get("diskStatus", {}).get(
                disk_name, {})
            conditions = {
                condition["type"]: condition
                for condition in disk_status.get("conditions", [])
            }
            ready = conditions.get("Ready", {}).get("status") == "True"
            schedulable = (
                conditions.get("Schedulable", {}).get("status") == "True"
            )
            if (
                disk_spec.get("diskType") == "lvm"
                and disk_spec.get("path") == disk_path
                and disk_status.get("diskUUID")
                and int(disk_status.get("storageMaximum", 0)) > 0
                and ready
                and schedulable
            ):
                logging(
                    f"LVM disk {disk_name} on {node_name} is ready with UUID "
                    f"{disk_status['diskUUID']}"
                )
                return disk_status["diskUUID"]
            logging(
                f"Waiting for LVM disk {disk_name} on {node_name} "
                f"to be ready ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"LVM disk {disk_name} on {node_name} did not become ready: "
            f"{disk_status}"
        )

    def wait_for_local_volume_ready(self, volume_name, node_name, disk_name):
        expected_disk_uuid = self.wait_for_lvm_disk_ready(
            node_name,
            disk_name,
            self._get_node(node_name)["spec"]["disks"][disk_name]["path"],
        )
        volume = None
        replicas = []
        for i in range(self.retry_count):
            volume = self.custom_objects_api.get_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=LONGHORN_NAMESPACE,
                plural="volumes",
                name=volume_name,
            )
            replicas = self.custom_objects_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=LONGHORN_NAMESPACE,
                plural="replicas",
                label_selector=f"longhornvolume={volume_name}",
            )["items"]
            spec = volume.get("spec", {})
            status = volume.get("status", {})
            replica_ready = (
                len(replicas) == 1
                and replicas[0].get("spec", {}).get("dataEngine") == "local"
                and replicas[0].get("spec", {}).get("nodeID") == node_name
                and replicas[0].get("spec", {}).get("diskID")
                == expected_disk_uuid
                and replicas[0].get("status", {}).get("currentState")
                == "running"
            )
            if (
                spec.get("dataEngine") == "local"
                and int(spec.get("numberOfReplicas", 0)) == 1
                and status.get("state") == "attached"
                and status.get("robustness") == "healthy"
                and status.get("currentNodeID") == node_name
                and replica_ready
            ):
                replica_name = replicas[0]["metadata"]["name"]
                self.wait_for_logical_volume(
                    node_name, disk_name, replica_name, present=True)
                return replica_name
            logging(
                f"Waiting for local volume {volume_name} placement "
                f"to be ready ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Local volume {volume_name} did not become ready on disk "
            f"{disk_name}: "
            f"volume={volume}, replicas={replicas}"
        )

    def wait_for_logical_volume(
            self, node_name, disk_name, replica_name, present=True):
        last_output = ""
        last_vg = ""
        vg_lookup = self._vg_lookup_command(
            self._disk_uuid(node_name, disk_name))
        for i in range(self.retry_count):
            pod_name = self._get_local_instance_manager_pod(node_name)
            if pod_name:
                command = (
                    vg_lookup +
                    "lvs --devicesfile longhorn.devices --noheadings "
                    "--separator ';' "
                    "-o vg_name,lv_name,lv_active,lv_path "
                    f"\"$vg/{replica_name}\" 2>/dev/null"
                )
                last_output = pod_exec(
                    pod_name, LONGHORN_NAMESPACE, command).strip()
                if present and last_output:
                    fields = [
                        field.strip() for field in last_output.split(";")
                    ]
                    if (
                        len(fields) == 4
                        and fields[0]
                        and fields[1] == replica_name
                        and fields[2] == "active"
                        and fields[3]
                    ):
                        last_vg = fields[0]
                        logging(
                            f"Logical volume {last_vg}/{replica_name} is "
                            "active"
                        )
                        return
                if not present and not last_output:
                    logging(
                        f"Logical volume for {disk_name}/{replica_name} was deleted"
                    )
                    return
            logging(
                f"Waiting for logical volume on {disk_name}/{replica_name} "
                f"to be {'present' if present else 'absent'} ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Logical volume on {disk_name}/{replica_name} did not become "
            f"{'present' if present else 'absent'}: {last_output}"
        )

    def wait_for_logical_volume_size(
            self, node_name, disk_name, replica_name, expected_size):
        expected_size = int(expected_size)
        last_output = ""
        vg_lookup = self._vg_lookup_command(
            self._disk_uuid(node_name, disk_name))
        for i in range(self.retry_count):
            pod_name = self._get_local_instance_manager_pod(node_name)
            if pod_name:
                command = (
                    vg_lookup +
                    "lvs --devicesfile longhorn.devices --noheadings "
                    "--units b --nosuffix -o lv_size "
                    f"\"$vg/{replica_name}\" 2>/dev/null"
                )
                last_output = pod_exec(
                    pod_name, LONGHORN_NAMESPACE, command).strip()
                try:
                    if int(last_output) >= expected_size:
                        logging(
                            f"Logical volume on {disk_name}/{replica_name} "
                            f"expanded to {last_output} bytes"
                        )
                        return
                except ValueError:
                    pass
            logging(
                "Waiting for logical volume on "
                f"{disk_name}/{replica_name} to "
                f"reach {expected_size} bytes ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Logical volume on {disk_name}/{replica_name} did not reach "
            f"{expected_size} bytes: {last_output}"
        )

    def verify_provisioning_mode(
            self, node_name, disk_name, volume_name, replica_name, mode):
        replica_name = replica_name.strip()
        expected_thin = mode == "thin"
        last_state = None
        for i in range(self.retry_count):
            volume = self.custom_objects_api.get_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=LONGHORN_NAMESPACE,
                plural="volumes",
                name=volume_name,
            )
            replicas = self.custom_objects_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=LONGHORN_NAMESPACE,
                plural="replicas",
                label_selector=f"longhornvolume={volume_name}",
            )["items"]
            disk_status = self._disk_status(node_name, disk_name)
            pod_name = self._get_local_instance_manager_pod(node_name)
            if pod_name and len(replicas) == 1:
                command = (
                    self._vg_lookup_command(disk_status.get("diskUUID", "")) +
                    "lvs --devicesfile longhorn.devices --reportformat json "
                    "--units b --nosuffix "
                    "-o vg_name,lv_name,lv_size,lv_attr,pool_lv,data_percent "
                    "\"$vg\" 2>/dev/null || true"
                )
                output = pod_exec(
                    pod_name, LONGHORN_NAMESPACE, command).strip()
                try:
                    json_start = output.find("{")
                    entries = json.loads(output[json_start:])["report"][0]["lv"]
                except (KeyError, IndexError, TypeError, ValueError):
                    try:
                        entries = ast.literal_eval(output)["report"][0]["lv"]
                    except (KeyError, IndexError, SyntaxError, TypeError,
                            ValueError):
                        entries = []
                by_name = {
                    entry.get("lv_name", "").strip(): entry
                    for entry in entries
                }
                replica = replicas[0]
                actual_replica_name = replica["metadata"]["name"].strip()
                lv = by_name.get(actual_replica_name)
                pool = by_name.get(self.THIN_POOL_NAME)
                volume_actual = int(
                    volume.get("status", {}).get("actualSize", 0))
                spec_mode = volume.get("spec", {}).get(
                    "provisioningMode")
                virtual_size = 0 if lv is None else int(lv["lv_size"])
                thin_backend = (
                    lv is not None
                    and lv.get("pool_lv", "").strip()
                    == self.THIN_POOL_NAME
                    and pool is not None
                    and pool.get("lv_attr", "").strip().startswith("t")
                )
                pool_attr = "" if pool is None else \
                    pool.get("lv_attr", "").strip()
                pool_zeroed = len(pool_attr) > 7 and pool_attr[7] == "z"
                if expected_thin:
                    # Thin actual-size accounting is deferred until it can
                    # account for chunks shared with local-engine snapshots.
                    actual_valid = volume_actual == 0
                else:
                    actual_valid = volume_actual == virtual_size
                capacity_valid = (
                    int(disk_status.get("storageMaximum", 0)) > 0
                    and int(disk_status.get("storageAvailable", 0)) >= 0
                )
                if mode == "thin":
                    mode_backend_valid = thin_backend and pool_zeroed
                else:
                    mode_backend_valid = (
                        lv is not None
                        and not lv.get("pool_lv", "").strip()
                        and pool is None
                    )
                last_state = {
                    "replicaName": actual_replica_name,
                    "requestedReplicaName": replica_name,
                    "lvmNames": list(by_name),
                    "specMode": spec_mode,
                    "volumeActualSize": volume_actual,
                    "lv": lv,
                    "pool": pool,
                    "diskStatus": disk_status,
                }
                if (
                    spec_mode == mode
                    and mode_backend_valid
                    and actual_valid
                    and capacity_valid
                ):
                    logging(
                        f"Verified {mode} provisioning for {volume_name}: "
                        f"actual={volume_actual}, virtual={virtual_size}"
                    )
                    return
            logging(
                f"Waiting for {mode} backend state for {volume_name} "
                f"... ({i}): {last_state}"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Local volume {volume_name} did not reach the expected {mode} "
            f"backend state: {last_state}"
        )

    def wait_for_thin_pool_absent(self, node_name, disk_name):
        last_output = ""
        vg_lookup = self._vg_lookup_command(
            self._disk_uuid(node_name, disk_name))
        for i in range(self.retry_count):
            pod_name = self._get_local_instance_manager_pod(node_name)
            if pod_name:
                command = (
                    vg_lookup +
                    "lvs --devicesfile longhorn.devices --noheadings "
                    f"\"$vg/{self.THIN_POOL_NAME}\" 2>/dev/null || true"
                )
                last_output = pod_exec(
                    pod_name, LONGHORN_NAMESPACE, command).strip()
                if not last_output:
                    logging(f"Thin pool for {disk_name} is absent")
                    return
            logging(
                f"Waiting for thin pool for {disk_name} to be absent ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Thin pool for {disk_name}/{self.THIN_POOL_NAME} still exists: "
            f"{last_output}"
        )

    def wait_for_instance_managers_to_follow_lvm_disks(self):
        """Wait until every worker node runs a local instance manager pod
        exactly when its spec has an lvm disk."""
        worker_nodes = Node().list_node_names_by_role("worker")
        mismatches = []
        for i in range(self.retry_count):
            mismatches = []
            for node_name in worker_nodes:
                disks = self._get_node(node_name).get(
                    "spec", {}).get("disks", {})
                has_lvm_disk = any(
                    disk.get("diskType") == "lvm" for disk in disks.values()
                )
                label_selector = (
                    "longhorn.io/component=instance-manager,"
                    "longhorn.io/data-engine=local,"
                    f"longhorn.io/node={node_name}"
                )
                pods = list_pods(LONGHORN_NAMESPACE, label_selector)
                if has_lvm_disk != (len(pods) > 0):
                    mismatches.append(
                        f"{node_name}: lvm disk={has_lvm_disk}, "
                        f"local instance manager pods={len(pods)}"
                    )
            if not mismatches:
                logging(
                    "Local instance managers follow the LVM disks "
                    "on all worker nodes"
                )
                return
            logging(
                "Waiting for local instance managers to follow the LVM "
                f"disks ... ({i}): {mismatches}"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            "Local instance managers do not follow the LVM disks: "
            + "; ".join(mismatches)
        )

    def get_stable_device_alias(self, node_name, device_path):
        """Return a udev-managed alias of device_path on the node: a
        /dev/disk/by-id link when the device has one, else a
        /dev/disk/by-path link, else "". Partition links and the links
        LVM's own udev rules add for a PV are not aliases of the disk."""
        command = (
            f'target=$(readlink -f {device_path}); '
            'for dir in /dev/disk/by-id /dev/disk/by-path; do '
            'for link in "$dir"/*; do '
            '[ -L "$link" ] || continue; '
            'case "${link##*/}" in '
            'lvm-pv-uuid-*|dm-*|*-part[0-9]*) continue;; esac; '
            '[ "$(readlink -f "$link")" = "$target" ] && echo "$link"; '
            'done; done; true'
        )
        output = NodeExec(node_name).issue_cmd(command)
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("/dev/disk/"):
                logging(
                    f"Device {device_path} on {node_name} has the stable "
                    f"alias {line}"
                )
                return line
        logging(
            f"Device {device_path} on {node_name} has no stable udev alias: "
            f"{output}"
        )
        return ""

    def verify_lvm_device_clean(self, node_name, disk_path):
        """Fail when a device of a removed disk still carries an LVM
        signature or is still a physical volume the local instance manager
        sees. A disk removed through an alias used to keep its VG and PV."""
        devices = self._disk_devices(disk_path)
        last_signatures = ""
        last_pvs = ""
        for i in range(self.retry_count):
            last_signatures = NodeExec(node_name).issue_cmd(
                "for device in " + " ".join(devices) + "; do "
                'wipefs --noheadings --parsable "$device" 2>&1 '
                '| sed "s|^|$device:|"; '
                'echo "device=$device=$(readlink -f $device)"; done'
            )
            resolved = {}
            signatures = []
            for line in last_signatures.splitlines():
                line = line.strip()
                if line.startswith("device="):
                    _, device, target = line.split("=", 2)
                    resolved[device] = target or device
                elif line:
                    signatures.append(line)

            pod_name = self._get_local_instance_manager_pod(node_name)
            last_pvs = ""
            if pod_name:
                last_pvs = pod_exec(
                    pod_name, LONGHORN_NAMESPACE,
                    "pvs --devicesfile longhorn.devices --noheadings "
                    "-o pv_name 2>/dev/null; true"
                )
            pv_names = {
                line.strip() for line in last_pvs.splitlines()
                if line.strip()
            }
            still_pv = [
                device for device in devices
                if device in pv_names or resolved.get(device) in pv_names
            ]
            if not signatures and not still_pv:
                logging(
                    f"Devices {devices} on {node_name} carry no LVM "
                    "signature and are no physical volumes"
                )
                return
            logging(
                f"Waiting for {devices} on {node_name} to be clean: "
                f"signatures={signatures} pvs={still_pv} ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"Devices {devices} on {node_name} were not left clean after the "
            f"disk was removed: wipefs={last_signatures!r} pvs={last_pvs!r}"
        )

    def wait_for_lvm_disk_removed(self, node_name, disk_name):
        for i in range(self.retry_count):
            node = self._get_node(node_name)
            disk_spec = node.get("spec", {}).get("disks", {})
            disk_status = node.get("status", {}).get("diskStatus", {})
            if disk_name not in disk_spec and disk_name not in disk_status:
                logging(
                    f"LVM disk {disk_name} was removed from node {node_name}"
                )
                return
            logging(
                f"Waiting for LVM disk {disk_name} to be removed ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"LVM disk {disk_name} was not removed from node {node_name}"
        )

    @staticmethod
    def _disk_devices(disk_path):
        """The block devices of a disk path: `dev[;dev...]`. A volume group
        name has no devices."""
        return [
            device.strip() for device in disk_path.split(";")
            if device.strip()
        ]

    @staticmethod
    def _vg_lookup_command(disk_uuid):
        """Shell prefix that sets $vg to the volume group whose UUID is the
        disk UUID the node status reports. The UUID never changes for the
        life of the disk, so callers look it up once before polling."""
        return (
            "vg=$(vgs --devicesfile longhorn.devices --noheadings "
            f"--select 'vg_uuid={disk_uuid}' -o vg_name 2>/dev/null "
            "| xargs); "
        )

    def wait_for_lvm_backend_initialized(
            self, node_name, disk_name, disk_path):
        """Wait until every block device of the disk path is a physical
        volume of one volume group that carries the Longhorn tag, whose
        UUID is the disk UUID and which has no other physical volume. One
        pvs report over the devices (aliases included, LVM resolves them)
        gives the volume group fields of each."""
        devices = self._disk_devices(disk_path)
        disk_uuid = self._disk_uuid(node_name, disk_name)
        command = (
            "pvs --devicesfile longhorn.devices --noheadings "
            "--separator ';' -o vg_name,vg_uuid,vg_tags,pv_count "
            + " ".join(devices) + " 2>/dev/null"
        )
        last_output = ""
        for i in range(self.retry_count):
            pod_name = self._get_local_instance_manager_pod(node_name)
            if pod_name and disk_uuid:
                last_output = pod_exec(pod_name, LONGHORN_NAMESPACE, command)
                rows = {
                    tuple(field.strip() for field in line.split(";"))
                    for line in last_output.splitlines() if ";" in line
                }
                if len(rows) == 1 and last_output.count(";") == 3 * len(devices):
                    vg_name, vg_uuid, vg_tags, pv_count = rows.pop()
                    if (
                        vg_uuid == disk_uuid
                        and self.VG_TAG in vg_tags.split(",")
                        and pv_count == str(len(devices))
                    ):
                        logging(
                            f"LVM backend for disk {disk_name} is initialized "
                            f"as volume group {vg_name} ({disk_uuid}) over "
                            f"{devices}"
                        )
                        return
            logging(
                f"Waiting for LVM backend for {disk_name} on {node_name} "
                f"... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"LVM backend for {disk_name} on {node_name} was not initialized: "
            f"{last_output}"
        )

    def verify_lvm_disk_spans_devices(self, node_name, disk_name, disk_path):
        """The capacity of a multi-device disk is the volume group's, which
        spans all its devices: at least 90% of their summed sizes."""
        devices = self._disk_devices(disk_path)
        pod = self._get_ready_local_instance_manager_pod(node_name)
        if pod is None:
            raise AssertionError(
                f"No ready local instance manager pod on {node_name}"
            )
        output = pod_exec(
            pod.metadata.name, LONGHORN_NAMESPACE,
            "for device in " + " ".join(devices) + "; do "
            'blockdev --getsize64 "$device"; done'
        )
        device_sizes = [
            int(line.strip()) for line in output.splitlines()
            if line.strip().isdigit()
        ]
        if len(device_sizes) != len(devices):
            raise AssertionError(
                f"Could not size the devices {devices} on {node_name}: "
                f"{output!r}"
            )
        capacity = int(self._disk_status(node_name, disk_name).get(
            "storageMaximum", 0))
        if capacity < 0.9 * sum(device_sizes) or capacity <= max(device_sizes):
            raise AssertionError(
                f"Disk {disk_name} reports {capacity} bytes, which does not "
                f"span its devices {dict(zip(devices, device_sizes))}"
            )
        logging(
            f"Disk {disk_name} spans {devices}: {capacity} bytes of "
            f"{sum(device_sizes)}"
        )

    def _patch_node_disks_expect_rejection(self, node_name, disks, what):
        """Patch a node's disks and require the admission webhook to reject
        it, returning the rejection message."""
        for i in range(self.retry_count):
            try:
                self.custom_objects_api.patch_namespaced_custom_object(
                    group="longhorn.io",
                    version="v1beta2",
                    namespace=LONGHORN_NAMESPACE,
                    plural="nodes",
                    name=node_name,
                    body={"spec": {"disks": disks}},
                )
            except ApiException as error:
                if error.status in (400, 422):
                    logging(f"Verified that {what} is rejected: {error.reason}")
                    return error.body or error.reason
                if error.status in (429, 500, 503, 504):
                    logging(
                        f"Retrying {what} after transient API error "
                        f"{error.status} ... ({i})"
                    )
                    time.sleep(self.retry_interval)
                    continue
                raise
            raise AssertionError(f"{what} unexpectedly succeeded")
        raise AssertionError(
            f"{what} could not be validated because the Kubernetes API "
            "remained unavailable"
        )

    def verify_lvm_disk_path_change_rejected(
            self, node_name, disk_name, new_path):
        disks = self._get_node(node_name)["spec"]["disks"]
        if disk_name not in disks:
            raise AssertionError(f"LVM disk {disk_name} is missing")
        disk = dict(disks[disk_name], path=new_path)
        message = self._patch_node_disks_expect_rejection(
            node_name, {disk_name: disk},
            f"changing the path of LVM disk {disk_name} to {new_path}")
        if "cannot change" not in str(message):
            raise AssertionError(
                f"The path change was rejected for another reason: {message}"
            )

    def verify_duplicate_lvm_disk_device_rejected(
            self, node_name, disk_name, device_path, free_device):
        """A device listed by an existing LVM disk cannot be registered by
        another disk, and one disk cannot list a device twice: free_device
        belongs to no disk, so listing it twice is the only fault."""
        disks = self._get_node(node_name)["spec"]["disks"]
        if not any(
            disk.get("diskType") == "lvm"
            and device_path in self._disk_devices(disk.get("path", ""))
            for disk in disks.values()
        ):
            raise AssertionError(
                f"Device {device_path} is not registered by an LVM disk on "
                f"{node_name}"
            )
        for path in (device_path, f"{free_device};{free_device}"):
            self._patch_node_disks_expect_rejection(
                node_name,
                {disk_name: {
                    "diskType": "lvm",
                    "path": path,
                    "allowScheduling": True,
                }},
                f"adding LVM disk {disk_name} with path {path}")

    def wait_for_lvm_disk_not_ready(self, node_name, disk_name, reason):
        """Wait until the disk is reported as not ready with the reason
        in its Ready condition, e.g. a device that is not empty."""
        disk_status = None
        for i in range(self.retry_count):
            disk_status = self._disk_status(node_name, disk_name)
            conditions = {
                condition["type"]: condition
                for condition in disk_status.get("conditions", [])
            }
            ready = conditions.get("Ready", {})
            if (
                ready.get("status") == "False"
                and reason in ready.get("message", "")
                and not disk_status.get("diskUUID")
            ):
                logging(
                    f"LVM disk {disk_name} on {node_name} is not ready as "
                    f"expected: {ready.get('message')}"
                )
                return
            logging(
                f"Waiting for LVM disk {disk_name} on {node_name} to be "
                f"reported not ready because of {reason!r} ... ({i})"
            )
            time.sleep(self.retry_interval)
        raise AssertionError(
            f"LVM disk {disk_name} on {node_name} was not reported not ready "
            f"because of {reason!r}: {disk_status}"
        )

    def format_device(self, node_name, device_path):
        """Put an ext4 filesystem on a disposable device, so it is no longer
        empty."""
        NodeExec(node_name).issue_cmd(f"mkfs.ext4 -F -q {device_path}")
        logging(f"Formatted {device_path} on {node_name} with ext4")

    def wipe_device(self, node_name, device_path):
        NodeExec(node_name).issue_cmd(f"wipefs -a {device_path}")
        logging(f"Wiped the signatures of {device_path} on {node_name}")
