import time

from kubernetes import client

from engine import Engine
from replica import Replica
from snapshot import Snapshot
from volume import Volume

import utility.constant as constant
from utility.constant import LABEL_TEST
from utility.constant import LABEL_TEST_VALUE
from utility.utility import logging
from utility.utility import get_retry_count_and_interval
from utility.utility import convert_size_to_bytes


class linked_clone_keywords:

    def __init__(self):
        self.obj_api = client.CustomObjectsApi()
        self.volume = Volume()
        self.replica = Replica()
        self.snapshot = Snapshot()
        self.engine = Engine()
        self.retry_count, self.retry_interval = get_retry_count_and_interval()

    # -------------------------------------------------------------------------
    # Volume creation
    # -------------------------------------------------------------------------

    def get_snapshot_name(self, volume_name, snapshot_id):
        """Return the actual Longhorn snapshot CR name for the given snapshot_id."""
        snapshot = self.snapshot.get(volume_name, snapshot_id)
        assert snapshot is not None, \
            f"Snapshot with id={snapshot_id} not found for volume {volume_name}"
        logging(f"Snapshot id={snapshot_id} of volume {volume_name} has name: {snapshot.name}")
        return snapshot.name

    def create_linked_clone_volume(self, clone_volume_name, src_volume_name,
                                   snapshot_id, size=None, numberOfReplicas=3):
        """Create a linked-clone V2 volume from a snapshot of a source volume.

        The volume spec will contain:
          spec.dataSource  = "snap://<srcVolume>/<snapshotName>"  (string)
          spec.cloneMode   = "linked-clone"
          spec.dataEngine  = "v2"

        If size is None (default), use the source volume's current spec.size so
        that expanded source volumes produce same-sized clones.
        """
        snapshot_name = self.get_snapshot_name(src_volume_name, snapshot_id)
        logging(f"Creating linked-clone volume {clone_volume_name} from "
                f"{src_volume_name} snapshot {snapshot_name}")

        if size is None:
            src_vol = self.volume.get(src_volume_name)
            size_bytes = str(src_vol["spec"]["size"])
            logging(f"Using source volume size {size_bytes} for linked-clone volume {clone_volume_name}")
        else:
            size_bytes = str(convert_size_to_bytes(size))
        body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {
                "name": clone_volume_name,
                "labels": {
                    LABEL_TEST: LABEL_TEST_VALUE,
                }
            },
            "spec": {
                "frontend": "blockdev",
                "size": size_bytes,
                "numberOfReplicas": int(numberOfReplicas),
                "dataEngine": "v2",
                "accessMode": "rwo",
                "dataSource": f"snap://{src_volume_name}/{snapshot_name}",
                "cloneMode": "linked-clone",
                "migratable": False,
                "dataLocality": "disabled",
                "replicaAutoBalance": "ignored",
                "revisionCounterDisabled": True,
            }
        }

        created = False
        for i in range(self.retry_count):
            try:
                self.obj_api.create_namespaced_custom_object(
                    group="longhorn.io",
                    version="v1beta2",
                    namespace=constant.LONGHORN_NAMESPACE,
                    plural="volumes",
                    body=body
                )
                created = True
                break
            except Exception as e:
                logging(f"Failed to create linked-clone volume {clone_volume_name} "
                        f"(attempt {i}): {e}")
                time.sleep(self.retry_interval)

        assert created, f"Failed to create linked-clone volume {clone_volume_name}"
        self.volume.wait_for_volume_to_be_created(clone_volume_name)
        logging(f"Linked-clone volume {clone_volume_name} created successfully")

    def create_linked_clone_volume_with_wrong_size_should_fail(self, clone_volume_name, src_volume_name, snapshot_id):
        """Try to create a linked-clone volume with a spec.size that doesn't match
        the source snapshot's RestoreSize; assert the webhook rejects the request."""
        snapshot_name = self.get_snapshot_name(src_volume_name, snapshot_id)
        src_vol = self.volume.get(src_volume_name)
        # Use a size that is clearly wrong: double the source volume's size.
        wrong_size = int(src_vol["spec"]["size"]) * 2
        logging(f"Attempting to create linked-clone {clone_volume_name} with wrong size {wrong_size} "
                f"(expected source snapshot size)")
        body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {"name": clone_volume_name, "labels": {LABEL_TEST: LABEL_TEST_VALUE}},
            "spec": {
                "frontend": "blockdev",
                "size": str(wrong_size),
                "numberOfReplicas": 1,
                "dataEngine": "v2",
                "accessMode": "rwo",
                "dataSource": f"snap://{src_volume_name}/{snapshot_name}",
                "cloneMode": "linked-clone",
            }
        }
        try:
            self.obj_api.create_namespaced_custom_object(
                group="longhorn.io", version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="volumes", body=body)
            assert False, (f"Expected webhook to reject linked-clone {clone_volume_name} "
                           f"with wrong size {wrong_size}, but creation succeeded")
        except Exception as e:
            err_str = str(e)
            assert "spec.size" in err_str or "RestoreSize" in err_str or "422" in err_str, \
                f"Expected size-mismatch rejection, got unexpected error: {e}"
            logging(f"Webhook correctly rejected linked-clone with wrong size: {e}")

    # -------------------------------------------------------------------------
    # CR existence checks
    # -------------------------------------------------------------------------

    def verify_engine_cr_exists(self, volume_name):
        """Assert at least one engine CR exists for the volume."""
        for i in range(self.retry_count):
            engines = self.engine.get_engines(volume_name)
            if len(engines) >= 1:
                logging(f"Volume {volume_name} has {len(engines)} engine CR(s)")
                return
            time.sleep(self.retry_interval)
        assert False, f"No engine CR found for volume {volume_name}"

    def verify_replica_crs_exist(self, volume_name, expected_count=None):
        """Assert the expected number of replica CRs exist for the volume."""
        for i in range(self.retry_count):
            replicas = self.replica.get(volume_name, node_name=None)
            count = len(replicas)
            if expected_count is not None:
                if count == int(expected_count):
                    logging(f"Volume {volume_name} has {count} replica CR(s) (expected {expected_count})")
                    return
            else:
                if count > 0:
                    logging(f"Volume {volume_name} has {count} replica CR(s)")
                    return
            time.sleep(self.retry_interval)
        assert False, \
            f"Replica CR count mismatch for volume {volume_name}: " \
            f"expected {'at least 1' if expected_count is None else expected_count}, " \
            f"got {len(self.replica.get(volume_name, node_name=None))}"

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
    # Clone status
    # -------------------------------------------------------------------------

    def wait_for_linked_clone_volume_clone_status(self, volume_name, desired_state):
        """Wait for volume.status.cloneStatus.state == desired_state."""
        logging(f"Waiting for {volume_name} cloneStatus.state = '{desired_state}'")
        self.volume.wait_for_volume_clone_status(volume_name, desired_state)

    def wait_for_linked_clone_volume_clone_status_completed(self, volume_name):
        """Wait for cloneStatus.state to reach the 'completed' state."""
        self.wait_for_linked_clone_volume_clone_status(volume_name, "completed")

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
            all_replicas = self.obj_api.list_namespaced_custom_object(
                group="longhorn.io",
                version="v1beta2",
                namespace=constant.LONGHORN_NAMESPACE,
                plural="replicas",
            )["items"]
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
    # Data inheritance check
    # -------------------------------------------------------------------------

    def verify_clone_data_matches_source(self, clone_volume_name, src_volume_name):
        """Assert the clone volume contains the same data as the source volume.

        Both volumes must be attached.  Reads the raw block checksum of the
        written region (limited by the source volume's write-size annotation)
        and compares them to confirm the snapshot data was correctly inherited.
        """
        # Use the source volume's stored write size for both checksums so the
        # comparison is limited to the written region and finishes in seconds.
        size_mb = self.volume.get_write_size_mb(src_volume_name)
        src_checksum = self.volume.get_checksum(src_volume_name)
        # Temporarily set write size on clone so get_checksum uses same region.
        if size_mb and not self.volume.get_write_size_mb(clone_volume_name):
            self.volume.set_write_size_mb(clone_volume_name, size_mb)
        clone_checksum = self.volume.get_checksum(clone_volume_name)
        assert src_checksum == clone_checksum, \
            f"Clone volume {clone_volume_name} data does not match source " \
            f"{src_volume_name}: clone_checksum={clone_checksum}, " \
            f"src_checksum={src_checksum}"
        logging(f"Clone volume {clone_volume_name} correctly inherits data from "
                f"source volume {src_volume_name}")

    def verify_clone_expanded_data_matches_source(self, clone_volume_name, src_volume_name):
        """Assert the clone volume contains the same data as the source in the
        expanded region (the region written via write_data_at_offset).

        Uses the offset/size metadata stored on the source volume's annotations
        to read the same region from both volumes and compare checksums.
        """
        offset_mb = self.volume.get_expanded_data_offset_mb(src_volume_name)
        size_mb = self.volume.get_expanded_data_size_mb(src_volume_name)
        src_checksum = self.volume.get_expanded_data_checksum(src_volume_name)
        if not src_checksum:
            logging(f"No expanded data checksum on {src_volume_name}; skipping expanded data check")
            return
        clone_checksum = self.volume.read_data_at_offset(clone_volume_name, offset_mb, size_mb)
        assert src_checksum == clone_checksum, \
            f"Clone volume {clone_volume_name} expanded data at offset {offset_mb}MB does not " \
            f"match source {src_volume_name}: clone={clone_checksum}, src={src_checksum}"
        logging(f"Clone volume {clone_volume_name} correctly inherits expanded data from "
                f"source volume {src_volume_name} at offset {offset_mb}MB")

    # -------------------------------------------------------------------------
    # No-snapshot creation (Longhorn auto-creates the entrypoint snapshot)
    # -------------------------------------------------------------------------

    def create_linked_clone_volume_no_snapshot(self, clone_volume_name,
                                               src_volume_name, size="2Gi",
                                               numberOfReplicas=3):
        """Create a linked-clone V2 volume specifying only the source volume name.

        No snapshotName is provided; dataSource = "vol://<srcVolume>".  Longhorn
        will auto-create a deterministic entrypoint snapshot and record its name
        in the linked-clone-source-snapshot label on the clone volume.
        """
        logging(f"Creating linked-clone volume {clone_volume_name} from "
                f"{src_volume_name} (no snapshot name — Longhorn will auto-create)")

        size_bytes = str(convert_size_to_bytes(size))
        body = {
            "apiVersion": "longhorn.io/v1beta2",
            "kind": "Volume",
            "metadata": {
                "name": clone_volume_name,
                "labels": {
                    LABEL_TEST: LABEL_TEST_VALUE,
                }
            },
            "spec": {
                "frontend": "blockdev",
                "size": size_bytes,
                "numberOfReplicas": int(numberOfReplicas),
                "dataEngine": "v2",
                "accessMode": "rwo",
                "dataSource": f"vol://{src_volume_name}",
                "cloneMode": "linked-clone",
                "migratable": False,
                "dataLocality": "disabled",
                "replicaAutoBalance": "ignored",
                "revisionCounterDisabled": True,
            }
        }

        created = False
        for i in range(self.retry_count):
            try:
                self.obj_api.create_namespaced_custom_object(
                    group="longhorn.io",
                    version="v1beta2",
                    namespace=constant.LONGHORN_NAMESPACE,
                    plural="volumes",
                    body=body
                )
                created = True
                break
            except Exception as e:
                logging(f"Failed to create linked-clone volume {clone_volume_name} "
                        f"(attempt {i}): {e}")
                time.sleep(self.retry_interval)

        assert created, f"Failed to create linked-clone volume {clone_volume_name}"
        self.volume.wait_for_volume_to_be_created(clone_volume_name)
        logging(f"Linked-clone volume {clone_volume_name} (no snapshot) created successfully")

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
    # Named-snapshot operations (work with actual CR names, not integer IDs)
    # -------------------------------------------------------------------------

    def delete_named_snapshot_cr(self, volume_name, snapshot_name):
        """Delete a snapshot CR by its actual CR name (not integer snapshot_id).

        Used to verify that a constraint is lifted after its linked-clone
        volume is deleted (e.g., Constraint 2: entrypoint snapshot can now be
        deleted once no linked-clone volume references it).
        """
        logging(f"Deleting snapshot CR {snapshot_name} of volume {volume_name}")
        self.obj_api.delete_namespaced_custom_object(
            group="longhorn.io",
            version="v1beta2",
            namespace=constant.LONGHORN_NAMESPACE,
            plural="snapshots",
            name=snapshot_name,
        )

    def wait_for_named_snapshot_cr_deleted(self, volume_name, snapshot_name):
        """Wait until the named snapshot CR no longer exists."""
        logging(f"Waiting for snapshot CR {snapshot_name} of volume {volume_name} "
                f"to be deleted")
        for i in range(self.retry_count):
            snap = self.snapshot.get_snapshot_by_name(volume_name, snapshot_name)
            if snap is None:
                logging(f"Snapshot CR {snapshot_name} of volume {volume_name} "
                        f"has been deleted")
                return
            time.sleep(self.retry_interval)
        assert False, \
            f"Timed out waiting for snapshot CR {snapshot_name} of volume " \
            f"{volume_name} to be deleted"

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

