from utility.utility import logging, get_retry_count_and_interval
from node_exec import NodeExec

import subprocess
import threading
import time

class io_keywords:

    def __init__(self):
        self._fsync_writer_process = None
        self._fsync_writer_thread = None
        self._max_elapsed = 0.0
        self._max_elapsed_lock = threading.Lock()

    def start_fsync_writer(self, pod_name, namespace="default"):
        logging(f"Starting fsync writer on pod {pod_name}")

        cmd = [
            "kubectl", "exec", pod_name, "-n", namespace, "--",
            "sh", "-c",
            "mkdir -p /data && while true; do"
            " dd if=/dev/zero of=/data/io_scratch bs=64k count=1 conv=fsync 2>&1"
            r" | awk -F'copied, ' '/copied/ {print $2+0}';"
            " done",
        ]

        self._max_elapsed = 0.0
        self._fsync_writer_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

        def _reader():
            for line in self._fsync_writer_process.stdout:
                try:
                    elapsed = float(line.strip().split()[0])
                    logging(f"fsync latency: {elapsed}s")
                    with self._max_elapsed_lock:
                        if elapsed > self._max_elapsed:
                            self._max_elapsed = elapsed
                except (ValueError, IndexError):
                    pass

        self._fsync_writer_thread = threading.Thread(target=_reader, daemon=True)
        self._fsync_writer_thread.start()
        time.sleep(1)

    def get_max_fsync_latency(self):
        if self._fsync_writer_process is not None:
            self._fsync_writer_process.terminate()
            try:
                self._fsync_writer_process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                self._fsync_writer_process.kill()
                self._fsync_writer_process.wait()
            self._fsync_writer_thread.join(timeout=5.0)
            self._fsync_writer_process = None
        with self._max_elapsed_lock:
            return self._max_elapsed

    def assert_no_io_stall(self, threshold_sec=3.0):
        max_latency = self.get_max_fsync_latency()
        logging(f"Maximum fsync latency: {max_latency}s (threshold: {threshold_sec}s)")
        if max_latency >= float(threshold_sec):
            retry_count, retry_interval = get_retry_count_and_interval()
            for i in range(retry_count):
                logging(f"IO stall detected, keeping env for debugging ({i+1}/{retry_count}) ...")
                time.sleep(int(retry_interval))
            assert False, f"IO stall detected: max latency {max_latency}s >= {threshold_sec}s threshold"

    def setup_dm_linear_device_from_block_disk(self, block_disk_path, dm_device_name, node_name):
        """
        Setup a device mapper linear device from a raw block device.
        """
        logging(f"Setting up dm-linear device {dm_device_name} from block disk {block_disk_path} on node {node_name}")

        cmd = f"test -b {block_disk_path}"
        result = NodeExec(node_name).issue_cmd(cmd)
        if result and ("No such" in result or "not a block" in result):
            raise Exception(f"Block device {block_disk_path} does not exist or is not a block device")

        cmd = f"blockdev --getsz {block_disk_path}"
        sectors = NodeExec(node_name).issue_cmd(cmd).strip()
        if not sectors or not sectors.isdigit():
            raise Exception(f"Failed to get device size in sectors. Result: {sectors}")

        cmd = f'echo "0 {sectors} linear {block_disk_path} 0" | dmsetup create --noudevsync {dm_device_name}'
        create_result = NodeExec(node_name).issue_cmd(cmd)
        if create_result and ("failed" in create_result.lower() or "error" in create_result.lower()):
            raise Exception(f"Failed to create dm device. Result: {create_result}")

        cmd = f"dmsetup table --noudevsync {dm_device_name}"
        table = NodeExec(node_name).issue_cmd(cmd)
        if "failed" in table.lower() or "No such device" in table:
            raise Exception(f"Device verification failed. Table result: {table}")

        result = {
            "real_dev": block_disk_path,
            "sectors": sectors,
            "dm_device": f"/dev/mapper/{dm_device_name}"
        }
        logging(f"Successfully created dm device {dm_device_name}: {result}")
        return result

    def format_and_mount_dm_device(self, dm_device_name, mount_point, node_name):
        """Format dm device as ext4 and mount it."""
        logging(f"Formatting and mounting dm device {dm_device_name} to {mount_point} on node {node_name}")

        dm_path = f"/dev/mapper/{dm_device_name}"

        # Format device as ext4
        cmd = f"mkfs.ext4 -F {dm_path}"
        NodeExec(node_name).issue_cmd(cmd)

        # Create mount point
        cmd = f"mkdir -p {mount_point}"
        NodeExec(node_name).issue_cmd(cmd)

        # Mount device with errors=continue option
        cmd = f"mount -t ext4 -o errors=continue {dm_path} {mount_point}"
        NodeExec(node_name).issue_cmd(cmd)

        logging(f"Successfully formatted and mounted {dm_device_name} to {mount_point}")

    def force_unmount_dm_device(self, mount_point, node_name):
        """Force unmount a dm device mount point by killing processes and using lazy unmount."""
        logging(f"Force unmounting {mount_point} on node {node_name}")

        # Kill all processes using the mount point
        cmd = f"fuser -km {mount_point} || true"
        NodeExec(node_name).issue_cmd(cmd)

        # Wait for processes to terminate
        timeout = 10
        start_time = time.time()
        while time.time() - start_time < timeout:
            cmd = f"fuser {mount_point} 2>/dev/null"
            result = NodeExec(node_name).issue_cmd(cmd)
            if not result or not result.strip():
                logging(f"All processes using {mount_point} have terminated")
                break
            time.sleep(0.5)
        else:
            logging(f"Warning: Timeout waiting for processes to terminate on {mount_point}")

        # Try normal unmount first, fallback to lazy unmount
        cmd = f"umount {mount_point} || umount -l {mount_point}"
        NodeExec(node_name).issue_cmd(cmd)

        logging(f"Successfully force unmounted {mount_point}")

    def switch_dm_device_to_error(self, dm_device_name, sectors, node_name):
        """Switch device mapper device from linear to error target. This will make all I/O operations fail."""
        logging(f"Switching dm device {dm_device_name} to error mode on node {node_name}")

        # Load the error table (inactive)
        cmd = f'echo "0 {sectors} error" | dmsetup load --noudevsync {dm_device_name}'
        NodeExec(node_name).issue_cmd(cmd)

        # Suspend the device without locking filesystem
        cmd = f"dmsetup suspend --noudevsync --nolockfs {dm_device_name}"
        NodeExec(node_name).issue_cmd(cmd)

        # Resume device to activate the loaded table
        cmd = f"dmsetup resume --noudevsync {dm_device_name}"
        NodeExec(node_name).issue_cmd(cmd)

        logging(f"Successfully switched {dm_device_name} to error mode")

    def switch_dm_device_to_linear(self, dm_device_name, block_device_path, sectors, node_name):
        logging(f"Switching dm device {dm_device_name} to linear mode on node {node_name}")

        # Suspend the device
        cmd = f"dmsetup suspend --noudevsync {dm_device_name}"
        NodeExec(node_name).issue_cmd(cmd)

        # Reload with linear mapping
        cmd = f'echo "0 {sectors} linear {block_device_path} 0" | dmsetup reload {dm_device_name}'
        NodeExec(node_name).issue_cmd(cmd)

        # Resume without flushing
        cmd = f"dmsetup resume --noudevsync --noflush {dm_device_name}"
        NodeExec(node_name).issue_cmd(cmd)

        cmd = f"dmsetup status {dm_device_name}"
        status = NodeExec(node_name).issue_cmd(cmd)
        logging(f"dm device status after switching to linear mode: {status}")

    def cleanup_dm_device(self, dm_device_name, node_name):
        logging(f"Cleaning up dm device {dm_device_name} on node {node_name}")
        cmd = f"dmsetup remove --noudevsync --deferred {dm_device_name}"
        NodeExec(node_name).issue_cmd(cmd)

        logging(f"Successfully cleaned up dm device {dm_device_name}")

    def wipe_block_device_signatures(self, block_device_path, node_name):
        logging(f"Wiping filesystem signatures from {block_device_path} on node {node_name}")

        cmd = f"wipefs -a {block_device_path}"
        NodeExec(node_name).issue_cmd(cmd)
        logging(f"Successfully wiped signatures from {block_device_path}")
