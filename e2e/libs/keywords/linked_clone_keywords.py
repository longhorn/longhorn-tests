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

    # -------------------------------------------------------------------------
    # Backup / restore of a linked-clone volume
    # -------------------------------------------------------------------------

    def wait_for_backup_volume_linked_clone_source(self, volume_name,
                                                   expected_src_volume_name,
                                                   expected_snapshot_name):
        """Assert the BackupVolume CR of volume_name records the given
        linked-clone source volume and snapshot.

        Retried because the backup_volume_controller only picks the values up on
        its next backup volume sync.
        """
        for _ in range(self.retry_count):
            bv = self._get_backup_volume_cr(volume_name)
            if bv is not None:
                status = bv.get("status", {}) or {}
                src_volume = status.get("linkedCloneSourceVolume", "")
                src_snapshot = status.get("linkedCloneSourceSnapshot", "")
                if src_volume != "" and src_snapshot != "":
                    assert src_volume == expected_src_volume_name, (
                        f"BackupVolume of {volume_name} records linked-clone source "
                        f"volume {src_volume!r}, expected {expected_src_volume_name!r}"
                    )
                    assert src_snapshot == expected_snapshot_name, (
                        f"BackupVolume of {volume_name} records linked-clone source "
                        f"snapshot {src_snapshot!r}, expected {expected_snapshot_name!r}"
                    )
                    logging(f"BackupVolume of {volume_name} records linked-clone "
                            f"source {src_volume}/{src_snapshot}")
                    return
            time.sleep(self.retry_interval)

        bv = self._get_backup_volume_cr(volume_name)
        actual = (bv or {}).get("status", {}) if bv else "no BackupVolume CR"
        assert False, (
            f"BackupVolume of {volume_name} never recorded a linked-clone source "
            f"(expected {expected_src_volume_name}/{expected_snapshot_name}), "
            f"last seen status: {actual}"
        )

    def _get_backup_volume_cr(self, volume_name):
        """Return the BackupVolume CR whose spec.volumeName is volume_name.

        The CR name is generated, so the volume has to be matched on the spec
        field rather than looked up by name.
        """
        try:
            bvs = self.obj_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="backupvolumes",
            )
        except Exception as e:
            logging(f"Failed to list backupvolumes: {e}")
            return None

        for bv in bvs.get("items", []):
            if bv.get("spec", {}).get("volumeName", "") == volume_name:
                return bv
        return None

    def verify_volume_is_linked_clone_of(self, volume_name, expected_src_volume_name,
                                         expected_snapshot_name):
        """Assert spec.cloneMode and spec.dataSource identify the volume as a
        linked clone of the given source volume and snapshot.
        """
        volume = self.volume.get(volume_name)
        spec = volume.get("spec", {})

        clone_mode = spec.get("cloneMode", "")
        assert clone_mode == "linked-clone", (
            f"Volume {volume_name} has cloneMode {clone_mode!r}, "
            f"expected 'linked-clone'"
        )

        data_source = spec.get("dataSource", "")
        expected_data_source = \
            f"snap://{expected_src_volume_name}/{expected_snapshot_name}"
        assert data_source == expected_data_source, (
            f"Volume {volume_name} has dataSource {data_source!r}, "
            f"expected {expected_data_source!r}"
        )

        logging(f"Volume {volume_name} is a linked clone of "
                f"{expected_src_volume_name}/{expected_snapshot_name}")

    def verify_all_src_replicas_referenced_by_clone(self, src_volume_name,
                                                    clone_volume_name):
        """Assert every remaining src replica is referenced by at least one
        clone replica's linkedCloneSrcReplicaName field.

        Retries to allow recently deleted replica CRs to disappear.
        """
        for i in range(self.retry_count):
            src_replicas = self.replica.get(src_volume_name, node_name=None)
            clone_replicas = self.replica.get(clone_volume_name, node_name=None)

            referenced_src_names = set()
            for cr in clone_replicas:
                src_name = cr.get("spec", {}).get("linkedCloneSrcReplicaName", "")
                if src_name:
                    referenced_src_names.add(src_name)

            src_names = set(r["metadata"]["name"] for r in src_replicas)
            unreferenced = src_names - referenced_src_names
            if not unreferenced:
                logging(f"All {len(src_names)} replicas of {src_volume_name} "
                        f"are referenced by clone {clone_volume_name}")
                return

            time.sleep(self.retry_interval)

        assert False, \
            f"Src volume {src_volume_name} has unreferenced replicas " \
            f"{unreferenced} (clone {clone_volume_name} references: " \
            f"{referenced_src_names})"
