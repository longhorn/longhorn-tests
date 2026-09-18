from backupstore import Nfs, S3, Cifs

import json
import os
import posixpath
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from kubernetes import client as k8s_client

from utility import constant
from utility.utility import get_backupstore, pod_exec


class backupstore_keywords:

    DELETION_LOCK_NAME = "lock-e2e-deletion"

    def __init__(self):
        backupstore = get_backupstore()
        if backupstore.startswith("s3"):
            self.backupstore = S3()
        elif backupstore.startswith("nfs"):
            self.backupstore = Nfs()
        elif backupstore.startswith("cifs"):
            self.backupstore = Cifs()

    def create_dummy_in_progress_backup(self, volume_name):

        dummy_backup_cfg_data = {"Name": "dummy_backup",
                                 "VolumeName": volume_name,
                                 "CreatedTime": ""}

        self.backupstore.write_backup_cfg_file(volume_name,
                                               "backup-dummy",
                                               dummy_backup_cfg_data)

    def delete_dummy_in_progress_backup(self, volume_name):
        self.backupstore.delete_backup_cfg_file(volume_name,
                                                "backup-dummy")

    def corrupt_backup_cfg_file(self, volume_name, backup_name):

        corrupt_backup_cfg_data = "{corrupt: definitely"

        self.backupstore.write_backup_cfg_file(volume_name,
                                               backup_name,
                                               corrupt_backup_cfg_data)

    def delete_random_backup_block(self, volume_name):
        self.backupstore.delete_random_backup_block(volume_name)

    def create_file_in_backups_folder(self, volume_name, file_name):
        prefix = self.backupstore.get_backup_volume_prefix(volume_name)
        file_path = os.path.join(prefix, "backups" ,file_name)
        self.backupstore.create_file_in_backupstore(file_path)

    def _deletion_lock_path(self, volume_name):
        prefix = self.backupstore.get_backup_volume_prefix(volume_name)
        return os.path.join(prefix, "locks", self.DELETION_LOCK_NAME + ".lck")

    def create_backupstore_deletion_lock(self, volume_name):
        # Type 2 is the backupstore deletion lock, which blocks the type 1 lock a restore acquires.
        lock_data = json.dumps({"Name": self.DELETION_LOCK_NAME, "Type": 2, "Acquired": True})
        self.backupstore.create_file_in_backupstore(self._deletion_lock_path(volume_name), lock_data)

    def delete_backupstore_deletion_lock(self, volume_name):
        self.backupstore.delete_file_in_backupstore(self._deletion_lock_path(volume_name))

    def delete_file_in_backups_folder(self, volume_name, file_name):
        prefix = self.backupstore.get_backup_volume_prefix(volume_name)
        file_path = os.path.join(prefix, "backups" ,file_name)
        self.backupstore.delete_file_in_backupstore(file_path)

    def create_dummy_backup_from_file(self, file_name):
        self.backupstore.create_dummy_backup(file_name)

    def set_backupstore(self):
        self.backupstore.set_backupstore()

    def reset_backupstore(self):
        self.backupstore.reset_backupstore()

    def set_backupstore_poll_interval(self, poll_interval):
        self.backupstore.set_backupstore_poll_interval(poll_interval)

    def set_backupstore_url(self, url):
        self.backupstore.set_backupstore_url(url)

    def set_backupstore_secret(self, secret):
        self.backupstore.set_backupstore_secret(secret)

    def wait_for_backupstore_available(self):
        self.backupstore.wait_for_backupstore_available()

    def get_nfs_backup_target_mount_configuration(self, mount_options=None):
        url = urlparse(get_backupstore().split('$')[0])
        assert url.scheme == "nfs" and url.netloc and url.path, \
            f"Invalid NFS backup target: {url.geturl()}"
        target = url.geturl()
        if mount_options is not None:
            options = [(key, value) for key, value in parse_qsl(url.query, keep_blank_values=True)
                       if key != "nfsOptions"]
            options.append(("nfsOptions", mount_options))
            target = urlunparse(url._replace(query=urlencode(options, safe=',=')))
        # Match backupstore/nfs's mount directory; query options do not change it.
        mount_path = posixpath.normpath(posixpath.join(
            "/var/lib/longhorn-backupstore-mounts",
            url.netloc.replace('.', '_').rstrip(':'), url.path.lstrip('/')))
        return target, mount_path

    def run_nfs_test_command_in_pod(self, pod_name, command,
                                    namespace=constant.LONGHORN_NAMESPACE):
        pod = k8s_client.CoreV1Api().read_namespaced_pod(pod_name, namespace)
        containers = [container.name for container in pod.spec.containers]
        if (pod.metadata.labels or {}).get("app") == "longhorn-manager":
            container = "longhorn-manager"
            assert container in containers, f"Missing longhorn-manager container in {pod_name}"
        else:
            assert len(containers) == 1, \
                f"Expected one instance-manager container in {pod_name}: {containers}"
            container = containers[0]
        return pod_exec(pod_name, namespace, command, container=container)

    def get_nfs_backup_target_mount_entries_in_pod(self, pod_name, mount_path,
                                                   namespace=constant.LONGHORN_NAMESPACE):
        # Exec reads the selected container's mount namespace, where backupstore mounts live.
        command = (
            "while IFS= read -r line; do printf '%s\\n' \"$line\"; "
            "done < /proc/self/mountinfo && echo NFS_MOUNTINFO_READ_OK"
        )
        result = self.run_nfs_test_command_in_pod(pod_name, command, namespace)
        lines = result.splitlines()
        assert lines and lines[-1] == "NFS_MOUNTINFO_READ_OK", \
            f"Failed to read mountinfo in {pod_name}: {result!r}"
        assert len(lines) > 1, f"Empty mountinfo in {pod_name}"
        mounts = []
        for line in lines[:-1]:
            fields = line.split()
            assert len(fields) >= 10 and fields[0].isdigit() and "-" in fields, \
                f"Invalid mountinfo in {pod_name}: {line!r}"
            separator = fields.index("-")
            assert separator >= 6 and len(fields) - separator == 4, \
                f"Invalid mountinfo in {pod_name}: {line!r}"
            target = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])
            if target == mount_path:
                mounts.append({
                    "mount_path": target,
                    "filesystem": fields[separator + 1],
                    "source": fields[separator + 2],
                    "options": (fields[5] + "," + fields[separator + 3]).split(","),
                })
        return mounts

    def assert_nfs_backup_target_mount_options(self, pod_names, mount_path, mount_option,
                                               namespace=constant.LONGHORN_NAMESPACE):
        mount_count = 0
        for pod_name in pod_names:
            mounts = self.get_nfs_backup_target_mount_entries_in_pod(
                pod_name, mount_path, namespace)
            for mount in mounts:
                assert mount["filesystem"] in ("nfs", "nfs4"), \
                    f"Backup target mount in {pod_name} is not NFS"
                options = mount["options"]
                assert "soft" in options, \
                    f"NFS backup target mount in {pod_name} must enforce soft"
                assert "hard" not in options, \
                    f"NFS backup target mount in {pod_name} must override hard"
                assert mount_option in options, \
                    f"NFS backup target mount in {pod_name} must preserve {mount_option}"
                mount_count += 1
        assert mount_count > 0, "No Longhorn-managed NFS backup target mounts found"

    def resolve_nfs_backup_target_server_ip(self):
        url = self.backupstore.get_backupstore_url()
        assert url.startswith("nfs://"), f"Backup target is not NFS: {url}"
        host = urlparse(url).hostname
        assert host, f"Failed to parse NFS host from backup target URL: {url}"
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            return host
        parts = host.split('.')
        assert len(parts) >= 2, f"Cannot parse K8s service name from NFS host '{host}'"
        svc_name, namespace = parts[0], parts[1]
        core_api = k8s_client.CoreV1Api()
        ep = core_api.read_namespaced_endpoints(svc_name, namespace)
        assert ep.subsets and ep.subsets[0].addresses, \
            f"No ready endpoints for service {svc_name}.{namespace}"
        ip = ep.subsets[0].addresses[0].ip
        assert ip, f"Empty endpoint IP for service {svc_name}.{namespace}"
        return ip
