import time

from kubernetes import client

from replica import Replica
from volume import Volume

import utility.constant as constant
from utility.utility import logging
from utility.utility import get_retry_count_and_interval


class linked_clone_keywords:

    def __init__(self):
        self.obj_api = client.CustomObjectsApi()
        self.volume = Volume()
        self.replica = Replica()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    # -------------------------------------------------------------------------
    # Linked-clone specific replica field/label checks
    # -------------------------------------------------------------------------

    def wait_for_linked_clone_replica_fields_set(self, clone_volume_name):
        """Wait until every clone replica has:
          - spec.linkedCloneSrcReplicaName set (non-empty)
          - metadata.labels['longhorn.io/linked-clone-src-replica'] present
        """
        logging(f"Waiting for linked-clone replica fields to be set on {clone_volume_name}")
        for i in range(self.retry_count):
            replicas = self.replica.get(clone_volume_name, node_name=None)
            if len(replicas) == 0:
                time.sleep(self.retry_interval)
                continue

            all_fields_set = all(
                r.get("spec", {}).get("linkedCloneSrcReplicaName", "") != ""
                for r in replicas
            )
            all_labeled = all(
                "longhorn.io/linked-clone-src-replica" in r.get("metadata", {}).get("labels", {})
                for r in replicas
            )

            if all_fields_set and all_labeled:
                logging(f"All {len(replicas)} clone replica(s) of {clone_volume_name} "
                        f"have linkedCloneSrcReplicaName set and linked-clone-src-replica label")
                return

            time.sleep(self.retry_interval)

        replicas = self.replica.get(clone_volume_name, node_name=None)
        missing = [
            r["metadata"]["name"] for r in replicas
            if r.get("spec", {}).get("linkedCloneSrcReplicaName", "") == ""
            or "longhorn.io/linked-clone-src-replica" not in r.get("metadata", {}).get("labels", {})
        ]
        assert False, \
            f"Timed out waiting for linkedCloneSrcReplicaName / label on " \
            f"{clone_volume_name} replicas: {missing}"

    def verify_linked_clone_replica_colocation(self, clone_volume_name, src_volume_name):
        """Assert each clone replica co-locates (same nodeID + diskID) with its
        corresponding source replica identified by linkedCloneSrcReplicaName."""
        clone_replicas = self.replica.get(clone_volume_name, node_name=None)
        src_replicas = self.replica.get(src_volume_name, node_name=None)

        assert len(clone_replicas) > 0, \
            f"No clone replicas found for {clone_volume_name}"
        assert len(src_replicas) > 0, \
            f"No source replicas found for {src_volume_name}"

        src_replica_map = {
            r["metadata"]["name"]: {
                "nodeID": r["spec"]["nodeID"],
                "diskID": r["spec"]["diskID"],
            }
            for r in src_replicas
        }

        for cr in clone_replicas:
            cr_name = cr["metadata"]["name"]
            linked_src = cr["spec"].get("linkedCloneSrcReplicaName", "")
            assert linked_src != "", \
                f"Clone replica {cr_name} has no linkedCloneSrcReplicaName"
            assert linked_src in src_replica_map, \
                f"linkedCloneSrcReplicaName '{linked_src}' of {cr_name} " \
                f"not found among {src_volume_name} replicas"

            src_info = src_replica_map[linked_src]
            cr_node = cr["spec"]["nodeID"]
            cr_disk = cr["spec"]["diskID"]
            assert cr_node == src_info["nodeID"], \
                f"Clone replica {cr_name} is on node '{cr_node}' but its source " \
                f"replica '{linked_src}' is on node '{src_info['nodeID']}'"
            assert cr_disk == src_info["diskID"], \
                f"Clone replica {cr_name} is on disk '{cr_disk}' but its source " \
                f"replica '{linked_src}' is on disk '{src_info['diskID']}'"

        logging(f"All clone replicas of {clone_volume_name} are correctly co-located "
                f"with their source replicas from {src_volume_name}")

    # -------------------------------------------------------------------------
    # Helper accessors (used by should-fail keywords)
    # -------------------------------------------------------------------------

    def get_src_replica_referenced_by_clone(self, volume_name):
        """Return the name of a src replica that is referenced by a linked-clone child.

        Looks at all replicas in the system with linkedCloneSrcReplicaName
        pointing to a replica of the given volume.
        """
        for i in range(self.retry_count):
            replicas = self.replica.get(volume_name, node_name=None)
            if not replicas:
                time.sleep(self.retry_interval)
                continue

            src_names = {r["metadata"]["name"] for r in replicas}
            # Find clone replicas that reference any of these src replicas
            all_replicas = self.replica.get(None, None)
            for r in all_replicas:
                src_ref = r.get("spec", {}).get("linkedCloneSrcReplicaName", "")
                if src_ref in src_names:
                    logging(f"Got src replica name for {volume_name}: {src_ref}")
                    return src_ref

            time.sleep(self.retry_interval)
        assert False, f"No src replica of volume {volume_name} is referenced by a linked-clone child"

    def get_entrypoint_snapshot_name_from_clone(self, clone_volume_name):
        """Return the entrypoint snapshot CR name stored in the clone volume's dataSource.

        dataSource string format: "snap://<volumeName>/<snapshotName>"
        """
        volume = self.volume.get(clone_volume_name)
        data_source = volume["spec"]["dataSource"]  # "snap://srcVol/snapName"
        assert data_source.startswith("snap://"), \
            f"Expected snap:// dataSource but got: {data_source}"
        path = data_source[len("snap://"):]
        parts = path.split("/", 1)
        assert len(parts) == 2 and parts[1], \
            f"Cannot parse snapshot name from dataSource: {data_source}"
        snapshot_name = parts[1]
        logging(f"Entrypoint snapshot for clone {clone_volume_name}: {snapshot_name}")
        return snapshot_name

    def get_src_volume_name_from_clone(self, clone_volume_name):
        """Return the source volume name stored in the clone volume's dataSource.

        dataSource string format: "snap://<volumeName>/<snapshotName>" or "vol://<volumeName>"
        """
        volume = self.volume.get(clone_volume_name)
        data_source = volume["spec"]["dataSource"]
        assert "://" in data_source, f"Unexpected dataSource format: {data_source}"
        path = data_source.split("://", 1)[1]
        src_volume_name = path.split("/")[0]
        logging(f"Source volume for clone {clone_volume_name}: {src_volume_name}")
        return src_volume_name

    # -------------------------------------------------------------------------
    # Constraint: immutability check (linkedCloneSrcReplicaName must not change)
    # -------------------------------------------------------------------------

    def verify_linked_clone_src_replica_names_unchanged(self, clone_volume_name):
        """Assert linkedCloneSrcReplicaName on every clone replica is still set
        (non-empty) — verifying the field was not cleared/changed."""
        replicas = self.replica.get(clone_volume_name, node_name=None)
        for r in replicas:
            name = r["metadata"]["name"]
            linked_src = r["spec"].get("linkedCloneSrcReplicaName", "")
            assert linked_src != "", \
                f"linkedCloneSrcReplicaName was unexpectedly cleared on replica {name}"
        logging(f"linkedCloneSrcReplicaName is still set on all replicas of {clone_volume_name}")

    # -------------------------------------------------------------------------
    # Helpers for "volume still exists" / "snapshot still exists" checks
    # -------------------------------------------------------------------------

    def verify_volume_exists(self, volume_name):
        """Assert the volume CR can be fetched (still exists)."""
        volume = self.volume.get(volume_name)
        assert volume is not None and volume.get("metadata", {}).get("name") == volume_name, \
            f"Volume {volume_name} does not exist or returned unexpected object"
        logging(f"Volume {volume_name} still exists")

    def verify_snapshot_exists_by_name(self, src_volume_name, snapshot_name):
        """Assert a snapshot CR (identified by its actual name) still exists.

        Uses the Kubernetes CRD API so the check works for both attached and
        detached volumes (the REST snapshotList() action is only available
        when the volume is attached and raises AttributeError otherwise).
        """
        try:
            snap_cr = self.obj_api.get_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="snapshots",
                name=snapshot_name
            )
            vol_label = snap_cr.get("metadata", {}).get("labels", {}).get("longhornvolume", "")
            assert vol_label == src_volume_name, (
                f"Snapshot {snapshot_name!r} exists but belongs to volume "
                f"{vol_label!r}, not {src_volume_name!r}"
            )
            logging(f"Snapshot {snapshot_name} of volume {src_volume_name} still exists (CRD)")
        except AssertionError:
            raise
        except Exception as e:
            assert False, (
                f"Snapshot {snapshot_name!r} of volume {src_volume_name} does not exist: {e}"
            )

    # -------------------------------------------------------------------------
    # No-snapshot creation (Longhorn auto-creates the entrypoint snapshot)
    # -------------------------------------------------------------------------

    def verify_linked_clone_entrypoint_snapshot_label_set(self, clone_volume_name):
        """Assert that the linked-clone-source-snapshot label is set on the clone
        volume, confirming Longhorn auto-created and recorded the snapshot name."""
        label_key = "longhorn.io/linked-clone-source-snapshot"
        for i in range(self.retry_count):
            volume = self.volume.get(clone_volume_name)
            labels = volume.get("metadata", {}).get("labels", {})
            if labels.get(label_key, "") != "":
                logging(f"linked-clone-source-snapshot label set on "
                        f"{clone_volume_name}: {labels[label_key]}")
                return
            time.sleep(self.retry_interval)
        assert False, \
            f"linked-clone-source-snapshot label not set on {clone_volume_name} " \
            f"after {self.retry_count} retries"
