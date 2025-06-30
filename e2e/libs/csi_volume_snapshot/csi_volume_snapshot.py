import yaml
import time

from kubernetes import client
from kubernetes.client.rest import ApiException

from utility.utility import logging
from utility.utility import get_retry_count_and_interval

class CSIVolumeSnapshot:

    def __init__(self):
        self.api = client.CustomObjectsApi()
        self.group = "snapshot.storage.k8s.io"
        self.version = "v1"
        self.retry_count, self.retry_interval = get_retry_count_and_interval()
        self.volume_snapshot_class_name = None

    def create_csi_volume_snapshot_class(self, class_name, type, deletionPolicy):

        logging(f"Creating csi volume snapshot class {class_name}")

        filepath = "./templates/csi_volume_snapshot/volumesnapshotclass.yaml"
        with open(filepath, 'r') as f:

            manifest_dict = yaml.safe_load(f)

            # correct snapshot class fields
            if class_name:
                manifest_dict['metadata']['name'] = class_name
            if type:
                manifest_dict['parameters']['type'] = type
            if deletionPolicy:
                manifest_dict['deletionPolicy'] = deletionPolicy

            self.api.create_cluster_custom_object(
                group=self.group,
                version=self.version,
                plural="volumesnapshotclasses",
                body=manifest_dict
            )

        self.volume_snapshot_class_name = class_name
        logging(f"Created csi volume snapshot class {class_name}")

    def create_csi_volume_snapshot(self, snapshot_name, pvc_name):

        logging(f"Creating csi volume snapshot {snapshot_name} for pvc {pvc_name}")

        filepath = "./templates/csi_volume_snapshot/volumesnapshot.yaml"
        with open(filepath, 'r') as f:

            manifest_dict = yaml.safe_load(f)

            # correct snapshot fields
            manifest_dict['spec']['volumeSnapshotClassName'] = self.volume_snapshot_class_name
            manifest_dict['metadata']['name'] = snapshot_name
            manifest_dict['spec']['source']['persistentVolumeClaimName'] = pvc_name

            self.api.create_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace="default",
                plural="volumesnapshots",
                body=manifest_dict
            )

        logging(f"Created csi volume snapshot {snapshot_name} for pvc {pvc_name}")

    def wait_for_csi_volume_snapshot_to_be_ready(self, snapshot_name):
        for i in range(self.retry_count):
            logging(f"Waiting for csi volume snapshot {snapshot_name} to be ready ... ({i})")
            try:
                snapshot = self.get_csi_volume_snapshot(snapshot_name)
                if snapshot["status"]["readyToUse"] is True:
                    return
            except Exception as e:
                logging(f"Waiting for csi volume snapshot {snapshot_name} to be ready error: {e}")
            time.sleep(self.retry_interval)
        assert False, f"Failed to wait for csi volume snapshot {snapshot_name} to be ready"

    def list_csi_volume_snapshots(self):

        snapshots = self.api.list_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace="default",
            plural="volumesnapshots"
        )

        snapshot_list = [item["metadata"]["name"] for item in snapshots.get("items", [])]

        logging(f"Got csi volume snapshots {snapshot_list}")

        return snapshot_list

    def get_csi_volume_snapshot(self, snapshot_name):

        snapshot = self.api.get_namespaced_custom_object(
            group=self.group,
            version=self.version,
            namespace="default",
            plural="volumesnapshots",
            name=snapshot_name
        )

        logging(f"Got csi volume snapshot {snapshot}")

        return snapshot

    def get_longhorn_snapshot_name_associated_with_csi_volume_snapshot(self, csi_volume_snapshot_name):
        snapshot = self.get_csi_volume_snapshot(csi_volume_snapshot_name)
        longhorn_snapshot_name = "snapshot-" + snapshot["metadata"]["uid"]
        logging(f"Got longhorn snapshot name {longhorn_snapshot_name} associated with csi volume snapshot {csi_volume_snapshot_name}")
        return longhorn_snapshot_name

    def cleanup_csi_volume_snapshot_classes(self):

        logging(f"Cleaning up csi volume snapshot classes")

        try:
            classes = self.api.list_cluster_custom_object(
                group=self.group,
                version=self.version,
                plural="volumesnapshotclasses"
            )

            for item in classes.get("items", []):
                name = item["metadata"]["name"]
                logging(f"Deleting csi volume snapshot class {name}")
                try:
                    self.api.delete_cluster_custom_object(
                        group=self.group,
                        version=self.version,
                        plural="volumesnapshotclasses",
                        name=name
                    )
                except ApiException as delete_exception:
                    assert delete_exception.status == 404
        except ApiException as list_exception:
            assert list_exception.status == 404

    def delete_csi_volume_snapshot(self, csi_volume_snapshot_name):
        for i in range(self.retry_count):
            logging(f"Deleting csi volume snapshot {csi_volume_snapshot_name} ... ({i})")
            try:
                self.api.delete_namespaced_custom_object(
                    group=self.group,
                    version=self.version,
                    namespace="default",
                    plural="volumesnapshots",
                    name=csi_volume_snapshot_name
                )
            except ApiException as e:
                if e.status == 404:
                    return
            time.sleep(self.retry_interval)
        assert False, f"Failed to delete csi volume snapshot {csi_volume_snapshot_name}"

    def cleanup_csi_volume_snapshots(self):

        logging(f"Cleaning up csi volume snapshots")

        try:
            snapshots = self.api.list_namespaced_custom_object(
                group=self.group,
                version=self.version,
                namespace="default",
                plural="volumesnapshots"
            )

            for item in snapshots.get("items", []):
                name = item["metadata"]["name"]
                logging(f"Deleting csi volume snapshot {name}")
                try:
                    self.api.delete_namespaced_custom_object(
                        group=self.group,
                        version=self.version,
                        namespace="default",
                        plural="volumesnapshots",
                        name=name
                    )
                except ApiException as delete_exception:
                    assert delete_exception.status == 404
        except ApiException as list_exception:
            assert list_exception.status == 404
