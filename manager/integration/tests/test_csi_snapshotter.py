import time
from urllib.parse import urlparse

import pytest
from backupstore import backupstore_s3  # NOQA
from backupstore import set_random_backupstore  # NOQA
from common import RETRY_COUNTS
from common import RETRY_INTERVAL
from common import client  # NOQA
from common import core_api  # NOQA
from common import create_and_wait_pod
from common import create_pvc_spec
from common import create_snapshot
from common import csi_pv  # NOQA
from common import find_backup
from common import get_custom_object_api_client
from common import get_pod_data_md5sum
from common import pod_make  # NOQA
from common import prepare_pod_with_data_in_mb
from common import pvc  # NOQA
from common import volume_name  # NOQA
from common import wait_for_backup_completion
from common import wait_for_backup_delete
from common import wait_for_volume_detached
from common import wait_for_volume_restoration_completed
from kubernetes.client.rest import ApiException


@pytest.fixture
def volumesnapshotclass(request):
    class VolumeSnapshotClassFactory():
        manifests = []

        @staticmethod
        def create_volumesnapshotclass(name, deletepolicy, snapshot_type=None):
            manifest = {
                'kind': 'VolumeSnapshotClass',
                'apiVersion': 'snapshot.storage.k8s.io/v1beta1',
                'metadata': {
                  'name': name
                },
                'driver': 'driver.longhorn.io',
                'deletionPolicy': deletepolicy
            }

            if snapshot_type is not None:
                manifest.update({'parameters': {'type': snapshot_type}})

            VolumeSnapshotClassFactory.manifests.append(manifest)

            api = get_custom_object_api_client()

            manifest_api_version = manifest["apiVersion"]

            api_group = urlparse(manifest_api_version).path.split("/")[0]
            api_version = urlparse(manifest_api_version).path.split("/")[1]
            plural = "volumesnapshotclasses"

            try:
                api.create_cluster_custom_object(group=api_group,
                                                 version=api_version,
                                                 plural=plural,
                                                 body=manifest)
            except ApiException as e:
                print("exception creating volumesnapshotclass %s\n" % e)

            return manifest

    yield VolumeSnapshotClassFactory.create_volumesnapshotclass

    api = get_custom_object_api_client()

    for manifest in VolumeSnapshotClassFactory.manifests:
        name = manifest["metadata"]["name"]
        api_group = urlparse(manifest["apiVersion"]).path.split("/")[0]
        api_version = urlparse(manifest["apiVersion"]).path.split("/")[1]
        plural = "volumesnapshotclasses"

        try:
            api.delete_cluster_custom_object(group=api_group,
                                             version=api_version,
                                             plural=plural,
                                             name=name)
        except ApiException as e:
            assert e.status == 404


@pytest.fixture
def volumesnapshot(request):
    class VolumeSnapshotFactory():
        manifests = []

        @staticmethod
        def create_volumesnapshot(name,
                                  namespace,
                                  volumesnapshotclass_name,
                                  source_type,
                                  source_name):
            manifest = {
                'apiVersion': 'snapshot.storage.k8s.io/v1beta1',
                'kind': 'VolumeSnapshot',
                'metadata': {
                  'name': name,
                  'namespace': namespace,
                },
                'spec': {
                  'volumeSnapshotClassName': volumesnapshotclass_name,
                  'source': {
                    source_type: source_name
                  }
                }
            }

            VolumeSnapshotFactory.manifests.append(manifest)

            api = get_custom_object_api_client()

            api_group = urlparse(manifest["apiVersion"]).path.split("/")[0]
            api_version = urlparse(manifest["apiVersion"]).path.split("/")[1]
            name = manifest["metadata"]["name"]
            plural = "volumesnapshots"

            try:
                api.create_namespaced_custom_object(group=api_group,
                                                    version=api_version,
                                                    namespace=namespace,
                                                    plural=plural,
                                                    body=manifest)
            except ApiException as e:
                print("exception create volumesnapshot %s\n" % e)

            for i in range(RETRY_COUNTS):
                status = \
                    api.get_namespaced_custom_object_status(
                            group=api_group,
                            version=api_version,
                            namespace=namespace,
                            plural=plural,
                            name=name)
                if "status" in status:
                    if "boundVolumeSnapshotContentName" in status["status"]:
                        break
                time.sleep(RETRY_INTERVAL)

            return status

    yield VolumeSnapshotFactory.create_volumesnapshot

    api = get_custom_object_api_client()

    for manifest in VolumeSnapshotFactory.manifests:
        api_group = urlparse(manifest["apiVersion"]).path.split("/")[0]
        api_version = urlparse(manifest["apiVersion"]).path.split("/")[1]
        namespace = manifest["metadata"]["namespace"]
        name = manifest["metadata"]["name"]
        plural = "volumesnapshots"

        try:
            api.delete_namespaced_custom_object(group=api_group,
                                                version=api_version,
                                                namespace=namespace,
                                                plural=plural,
                                                name=name)
        except ApiException as e:
            assert e.status == 404


@pytest.fixture
def volumesnapshotcontent(request):
    class VolumeSnapshotContentFactory():
        manifests = []

        @staticmethod
        def create_volumesnapshotcontent(name,
                                         volumesnapshotclass_name,
                                         delete_policy,
                                         snapshot_handle,
                                         volumesnapshot_ref_name,
                                         volumesnapshot_ref_namespace):
            manifest = {
                "apiVersion": "snapshot.storage.k8s.io/v1beta1",
                "kind": "VolumeSnapshotContent",
                "metadata": {
                  "name": name,
                },
                "spec": {
                  "volumeSnapshotClassName": volumesnapshotclass_name,
                  "driver": "driver.longhorn.io",
                  "deletionPolicy": delete_policy,
                  "source": {
                    "snapshotHandle": snapshot_handle
                  },
                  "volumeSnapshotRef": {
                    "name": volumesnapshot_ref_name,
                    "namespace": volumesnapshot_ref_namespace
                  }
                }
              }

            VolumeSnapshotContentFactory.manifests.append(manifest)

            api = get_custom_object_api_client()

            api_group = urlparse(manifest["apiVersion"]).path.split("/")[0]
            api_version = urlparse(manifest["apiVersion"]).path.split("/")[1]
            name = manifest["metadata"]["name"]
            plural = "volumesnapshotcontents"

            try:
                api.create_cluster_custom_object(group=api_group,
                                                 version=api_version,
                                                 plural=plural,
                                                 body=manifest)
            except ApiException as e:
                print("exception create volumesnapshotcontent %s\n" % e)

            for i in range(RETRY_COUNTS):
                status = \
                    api.get_cluster_custom_object_status(group=api_group,
                                                         version=api_version,
                                                         plural=plural,
                                                         name=name)
                if "status" in status:
                    if status["status"]["readyToUse"] is True:
                        break
                time.sleep(RETRY_INTERVAL)

            return status

    yield VolumeSnapshotContentFactory.create_volumesnapshotcontent

    api = get_custom_object_api_client()

    for manifest in VolumeSnapshotContentFactory.manifests:
        api_group = urlparse(manifest["apiVersion"]).path.split("/")[0]
        api_version = urlparse(manifest["apiVersion"]).path.split("/")[1]
        name = manifest["metadata"]["name"]
        plural = "volumesnapshotcontents"

        try:
            api.delete_cluster_custom_object(group=api_group,
                                             version=api_version,
                                             plural=plural,
                                             name=name)
        except ApiException as e:
            assert e.status == 404


def get_volumesnapshotcontent(volumesnapshot_uid):
    api = get_custom_object_api_client()
    api_group = "snapshot.storage.k8s.io"
    api_version = "v1beta1"
    plural = "volumesnapshotcontents"

    volumesnapshotcontents = \
        api.list_cluster_custom_object(group=api_group,
                                       version=api_version,
                                       plural=plural)

    for v in volumesnapshotcontents["items"]:
        if v["spec"]["volumeSnapshotRef"]["uid"] == volumesnapshot_uid:
            break

    return v


def delete_volumesnapshot(name, namespace):
    api = get_custom_object_api_client()
    api_group = "snapshot.storage.k8s.io"
    api_version = "v1beta1"
    plural = "volumesnapshots"

    try:
        api.delete_namespaced_custom_object(group=api_group,
                                            version=api_version,
                                            namespace=namespace,
                                            plural=plural,
                                            name=name)
    except ApiException as e:
        assert e.status == 404


def wait_for_volumesnapshot_ready(volumesnapshot_name, namespace, ready_to_use=True): # NOQA
    api = get_custom_object_api_client()
    api_group = "snapshot.storage.k8s.io"
    api_version = "v1beta1"
    plural = "volumesnapshots"

    for i in range(RETRY_COUNTS):
        v = api.get_namespaced_custom_object_status(group=api_group,
                                                    version=api_version,
                                                    namespace=namespace,
                                                    plural=plural,
                                                    name=volumesnapshot_name)

        if v["status"]["readyToUse"] is True:
            break

        time.sleep(RETRY_INTERVAL)

    assert v["status"]["readyToUse"] is ready_to_use
    return v


def restore_csi_volume_snapshot(core_api, client, csivolsnap, pvc_name, pvc_request_storage_size): # NOQA
    restore_pvc = {
        'apiVersion': 'v1',
        'kind': 'PersistentVolumeClaim',
        'metadata': {
            'name': pvc_name
        },
        'spec': {
            'accessModes': [
                'ReadWriteOnce'
            ],
            'resources': {
                'requests': {
                    'storage': pvc_request_storage_size
                }
            },
            'storageClassName': 'longhorn',
            'dataSource': {
                 'kind': 'VolumeSnapshot',
                 'apiGroup': 'snapshot.storage.k8s.io',
                 'name': csivolsnap["metadata"]["name"]
             }
        }
    }

    core_api.create_namespaced_persistent_volume_claim(body=restore_pvc,
                                                       namespace='default')

    restore_volume_name = None
    restore_pvc_name = restore_pvc["metadata"]["name"]
    for i in range(RETRY_COUNTS):
        restore_pvc = \
            core_api.read_namespaced_persistent_volume_claim(
                name=restore_pvc_name,
                namespace="default")

        if restore_pvc.spec.volume_name is not None:
            restore_volume_name = restore_pvc.spec.volume_name
            break

        time.sleep(RETRY_INTERVAL)

    assert restore_volume_name is not None

    wait_for_volume_restoration_completed(client, restore_volume_name)
    wait_for_volume_detached(client, restore_volume_name)

    return restore_pvc


@pytest.mark.parametrize("volsnapshotclass_delete_policy,backup_is_deleted", [("Delete", True), ("Retain", False)]) # NOQA
def test_csi_volumesnapshot_basic(set_random_backupstore, # NOQA
                                  volumesnapshotclass, # NOQA
                                  volumesnapshot, # NOQA
                                  client, # NOQA
                                  core_api, # NOQA
                                  volume_name, # NOQA
                                  csi_pv, # NOQA
                                  pvc, # NOQA
                                  pod_make, # NOQA
                                  volsnapshotclass_delete_policy, # NOQA
                                  backup_is_deleted,
                                  csi_snapshot_type=None): # NOQA
    """
    Test creation / restoration / deletion of a backup via the csi snapshotter

    Context:

    We want to allow the user to programmatically create/restore/delete
    longhorn backups via the csi snapshot mechanism
    ref: https://kubernetes.io/docs/concepts/storage/volume-snapshots/

    Setup:

    1. Make sure your cluster contains the below crds
    https://github.com/kubernetes-csi/external-snapshotter
    /tree/master/client/config/crd
    2. Make sure your cluster contains the snapshot controller
    https://github.com/kubernetes-csi/external-snapshotter
    /tree/master/deploy/kubernetes/snapshot-controller

    Steps:

    def csi_volumesnapshot_creation_test(snapshotClass=longhorn|custom):
    1. create volume(1)
    2. write data to volume(1)
    3. create a kubernetes `VolumeSnapshot` object
       the `VolumeSnapshot.uuid` will be used to identify a
       **longhorn snapshot** and the associated `VolumeSnapshotContent` object
    4. check creation of a new longhorn snapshot named `snapshot-uuid`
    5. check for `VolumeSnapshotContent` named `snapcontent-uuid`
    6. wait for `VolumeSnapshotContent.readyToUse` flag to be set to **true**
    7. check for backup existance on the backupstore

    # the csi snapshot restore sets the fromBackup field same as
    # the StorageClass based restore approach.
    def csi_volumesnapshot_restore_test():
    8. create a `PersistentVolumeClaim` object where the `dataSource` field
       references the `VolumeSnapshot` object by name
    9. verify creation of a new volume(2) bound to the pvc created in step(8)
    10. verify data of new volume(2) equals data
        from backup (ie old data above)

    # default longhorn snapshot class is set to Delete
    # add a second test with a custom snapshot class with deletionPolicy
    # set to Retain you can reuse these methods for that and other tests
    def csi_volumesnapshot_deletion_test(deletionPolicy='Delete|Retain'):
    11. delete `VolumeSnapshot` object
    12. if deletionPolicy == Delete:
        13. verify deletion of `VolumeSnapshot` and
            `VolumeSnapshotContent` objects
        14. verify deletion of backup from backupstore
    12. if deletionPolicy == Retain:
        13. verify deletion of `VolumeSnapshot`
        14. verify retention of `VolumeSnapshotContent`
            and backup on backupstore

    15. cleanup
    """

    csisnapclass = \
        volumesnapshotclass(name="snapshotclass",
                            deletepolicy=volsnapshotclass_delete_policy,
                            snapshot_type=csi_snapshot_type)

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api,
                                    csi_pv, pvc, pod_make,
                                    volume_name,
                                    data_path="/data/test")

    # Create volumeSnapshot test
    csivolsnap = volumesnapshot(volume_name + "-volumesnapshot",
                                "default",
                                csisnapclass["metadata"]["name"],
                                "persistentVolumeClaimName",
                                pvc_name)

    volume = client.by_id_volume(volume_name)

    for i in range(RETRY_COUNTS):
        snapshots = volume.snapshotList()
        if len(snapshots) == 2:
            break
        time.sleep(RETRY_INTERVAL)

    lh_snapshot = None
    snapshots = volume.snapshotList()
    for snapshot in snapshots:
        if snapshot["name"] == "snapshot-" + csivolsnap["metadata"]["uid"]:
            lh_snapshot = snapshot
    assert lh_snapshot is not None

    wait_for_volumesnapshot_ready(csivolsnap["metadata"]["name"],
                                  csivolsnap["metadata"]["namespace"])

    bv1, b = find_backup(client, volume_name, lh_snapshot["name"])

    assert b["snapshotName"] == lh_snapshot["name"]

    restore_pvc_name = pvc["metadata"]["name"] + "-restore"
    restore_pvc_size = pvc["spec"]["resources"]["requests"]["storage"]

    restore_csi_volume_snapshot(core_api,
                                client,
                                csivolsnap,
                                restore_pvc_name,
                                restore_pvc_size)

    restore_pod = pod_make()
    restore_pod_name = restore_pod["metadata"]["name"]
    restore_pod['spec']['volumes'] = [create_pvc_spec(restore_pvc_name)]

    create_and_wait_pod(core_api, restore_pod)
    restore_md5sum = \
        get_pod_data_md5sum(core_api, restore_pod_name, path="/data/test")
    assert restore_md5sum == md5sum

    # Delete volumeSnapshot test
    delete_volumesnapshot(csivolsnap["metadata"]["name"], "default")

    if backup_is_deleted is False:
        find_backup(client, volume_name, b["snapshotName"])
    else:
        wait_for_backup_delete(client, volume_name, b["name"])


@pytest.mark.parametrize("volsnapshotclass_delete_policy,backup_is_deleted", [("Delete", True), ("Retain", False)]) # NOQA
def test_csi_volumesnapshot_restore_existing_backup(set_random_backupstore, # NOQA
                                                    client, # NOQA
                                                    core_api, # NOQA
                                                    volume_name, # NOQA
                                                    csi_pv, # NOQA
                                                    pvc, # NOQA
                                                    pod_make, # NOQA
                                                    volumesnapshotclass, # NOQA
                                                    volumesnapshotcontent,
                                                    volumesnapshot, # NOQA
                                                    volsnapshotclass_delete_policy, # NOQA
                                                    backup_is_deleted): # NOQA
    """
    Test retention of a backup while deleting the associated `VolumeSnapshot`
    via the csi snapshotter

    Context:

    We want to allow the user to programmatically create/restore/delete
    longhorn backups via the csi snapshot mechanism
    ref: https://kubernetes.io/docs/concepts/storage/volume-snapshots/

    Setup:

    1. Make sure your cluster contains the below crds
    https://github.com/kubernetes-csi/external-snapshotter
    /tree/master/client/config/crd
    2. Make sure your cluster contains the snapshot controller
    https://github.com/kubernetes-csi/external-snapshotter
    /tree/master/deploy/kubernetes/snapshot-controller

    Steps:

    1. create new snapshotClass with deletionPolicy set to Retain
    2. call csi_volumesnapshot_creation_test(snapshotClass=custom)
    3. call csi_volumesnapshot_restore_test()
    4. call csi_volumesnapshot_deletion_test(deletionPolicy='Retain'):
    5. cleanup
    """
    csisnapclass = \
        volumesnapshotclass(name="snapshotclass",
                            deletepolicy=volsnapshotclass_delete_policy)

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api,
                                    csi_pv, pvc, pod_make,
                                    volume_name,
                                    data_path="/data/test")

    volume = client.by_id_volume(volume_name)
    snap = create_snapshot(client, volume_name)
    volume.snapshotBackup(name=snap.name)
    wait_for_backup_completion(client, volume_name, snap.name)
    bv, b = find_backup(client, volume_name, snap.name)

    csivolsnap_name = volume_name + "-volumesnapshot"
    csivolsnap_namespace = "default"

    volsnapcontent = \
        volumesnapshotcontent("volsnapcontent",
                              csisnapclass["metadata"]["name"],
                              "Delete",
                              "bs://" + volume_name + "/" + b.name,
                              csivolsnap_name,
                              csivolsnap_namespace)

    csivolsnap = volumesnapshot(csivolsnap_name,
                                csivolsnap_namespace,
                                csisnapclass["metadata"]["name"],
                                "volumeSnapshotContentName",
                                volsnapcontent["metadata"]["name"])

    restore_pvc_name = pvc["metadata"]["name"] + "-restore"
    restore_pvc_size = pvc["spec"]["resources"]["requests"]["storage"]

    restore_csi_volume_snapshot(core_api,
                                client,
                                csivolsnap,
                                restore_pvc_name,
                                restore_pvc_size)

    restore_pod = pod_make()
    restore_pod_name = restore_pod["metadata"]["name"]
    restore_pod['spec']['volumes'] = [create_pvc_spec(restore_pvc_name)]

    create_and_wait_pod(core_api, restore_pod)
    restore_md5sum = \
        get_pod_data_md5sum(core_api, restore_pod_name, path="/data/test")

    assert restore_md5sum == md5sum

    # Delete volumeSnapshot test
    delete_volumesnapshot(csivolsnap["metadata"]["name"], "default")

    if backup_is_deleted is False:
        find_backup(client, volume_name, b["snapshotName"])
    else:
        wait_for_backup_delete(client, volume_name, b["name"])


@pytest.mark.parametrize("volsnapshotclass_delete_policy,backup_is_deleted", [("Delete", True)]) # NOQA
def test_csi_snapshot_with_bak_param(set_random_backupstore, # NOQA
                                  volumesnapshotclass, # NOQA
                                  volumesnapshot, # NOQA
                                  client, # NOQA
                                  core_api, # NOQA
                                  volume_name, # NOQA
                                  csi_pv, # NOQA
                                  pvc, # NOQA
                                  pod_make, # NOQA
                                  volsnapshotclass_delete_policy, # NOQA
                                  backup_is_deleted): # NOQA
    """
    Context:

    After deploy the CSI snapshot CRDs, Controller at
    https://longhorn.io/docs/1.2.3/snapshots-and-backups/
    csi-snapshot-support/enable-csi-snapshot-support/

    Create VolumeSnapshotClass with type=bak
      - longhorn-backup (type=bak)

    Test the extend CSI snapshot type=bak support to Longhorn snapshot

    Steps:

    0. Create Longhorn volume test-vol
        - Size 5GB
        - Create PV/PVC/Workload for the Longhorn volume
        - Write data into volume
        - Setup backup store
    1. Test create CSI snapshot
        - Create VolumeSnapshot with class longhorn-backup
        - Should have backup generated
    2. Test create new volume from CSI snapshot
        - Create PVC from VolumeSnapshot generated in step 1
        - Attach PVC and verify data
    3. Test delete CSI snapshot
        - Delete VolumeSnapshot
        - The backup should deleted as well
    """
    test_csi_volumesnapshot_basic(set_random_backupstore, # NOQA
                                  volumesnapshotclass, # NOQA
                                  volumesnapshot, # NOQA
                                  client, # NOQA
                                  core_api, # NOQA
                                  volume_name, # NOQA
                                  csi_pv, # NOQA
                                  pvc, # NOQA
                                  pod_make, # NOQA
                                  volsnapshotclass_delete_policy, # NOQA
                                  backup_is_deleted, # NOQA
                                  csi_snapshot_type='bak')


@pytest.mark.skip(reason="TODO") # NOQA
def test_csi_snapshot_with_snap_param(client, volume_name): # NOQA
    """
    Context:

    After deploy the CSI snapshot CRDs, Controller at
    https://longhorn.io/docs/1.2.3/snapshots-and-backups/
    csi-snapshot-support/enable-csi-snapshot-support/

    Create VolumeSnapshotClass with type=snap
      - longhorn-snapshot (type=snap)

    Test the extend CSI snapshot type=snap support to Longhorn snapshot

    Steps:

    0. Create Longhorn volume test-vol
        - Size 5GB
        - Create PV/PVC/Workload for the Longhorn volume
        - Write data into volume
        - Setup backup store
    1. Test create CSI snapshot
        - Volume is in detached state
            - Scale down the workload
            - Create VolumeSnapshot with class longhorn-snap
            - Verify that the volumesnapshot object is not ready
        - Volume is in attached state
            - Scale up the workload
            - Verify the Longhorn snapshot generated
    2. Test create new volume from CSI snapshot
        - Create volume from longhorn-snapshot
            - Source volume is attached && Longhorn snapshot exist
                - Create PVC from snapshot generated from step 1
                - Attach the PVC and verify data
            - Source volume is detached
                - Scale down the workload
                - Create PVC from VolumeSnapshot generated from step 1
                - Verify PVC provision failed
            - Source volume is attached && Longhorn snapshot doesn’t exist
                - Scale up the workload
                - Use VolumeSnapshotContent.snapshotHandle to
                  specify Longhorn snapshot generated in step 1
                - Delete the Longhorn snapshot
                - Create PVC from VolumeSnapshot generated from step 1
                - PVC should be stuck in provisioning state
    3. Test delete CSI snapshot
        - Type is snap
            - volume is attached && snapshot doesn’t exist
                - Delete the VolumeSnapshot
                - VolumeSnapshot is deleted
            - volume is attached && snapshot exist
                - Verify the creation of Longhorn snapshot with the name in
                  the field VolumeSnapshotContent.snapshotHandle
                - Delete the VolumeSnapshot
                - Verify that Longhorn snapshot is removed or marked as removed
                - Verify that the VolumeSnapshot is deleted.
            - volume is detached
                - Delete the VolumeSnapshot
                - Verify that VolumeSnapshot is stuck in deleting
    """


def test_csi_snapshot_with_invalid_param(
                                  volumesnapshotclass, # NOQA
                                  volumesnapshot, # NOQA
                                  client, # NOQA
                                  core_api, # NOQA
                                  volume_name, # NOQA
                                  csi_pv, # NOQA
                                  pvc, # NOQA
                                  pod_make, # NOQA
                                  request): # NOQA
    """
    Context:

    After deploy the CSI snapshot CRDs, Controller at
    https://longhorn.io/docs/1.2.4/snapshots-and-backups/
    csi-snapshot-support/enable-csi-snapshot-support/

    Create VolumeSnapshotClass with type=invalid
      - invalid (type=invalid)

    Test the extend CSI snapshot type=invalid behavior to Longhorn snapshot

    Steps:

    0. Create Longhorn volume test-vol
        - Size 5GB
        - Create PV/PVC for the Longhorn volume
        - Write data into volume
        - Setup backup store
    1. Test create CSI snapshot
        - Create VolumeSnapshot with class invalid
        - Verify that the volumesnapshot object is not ready
    """
    # Step 0
    csi_snapshot_type = "invalid"
    csisnapclass = \
        volumesnapshotclass(name="snapshotclass-invalid",
                            deletepolicy="Delete",
                            snapshot_type=csi_snapshot_type)

    pod_name, pv_name, pvc_name, md5sum = \
        prepare_pod_with_data_in_mb(client, core_api,
                                    csi_pv, pvc, pod_make,
                                    volume_name,
                                    data_path="/data/test")

    # Step 1
    csivolsnap = volumesnapshot(volume_name + "-volumesnapshot",
                                "default",
                                csisnapclass["metadata"]["name"],
                                "persistentVolumeClaimName",
                                pvc_name)

    wait_for_volumesnapshot_ready(
                            volumesnapshot_name=csivolsnap["metadata"]["name"],
                            namespace='default',
                            ready_to_use=False)

    def finalizer():
        delete_volumesnapshot(csivolsnap["metadata"]["name"],
                              'default')

    request.addfinalizer(finalizer)
