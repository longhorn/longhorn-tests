#!/usr/sbin/python
import pytest

import common
from common import client, core_api, csi_pv, pod_make, pvc  # NOQA
from common import Gi, DEFAULT_VOLUME_SIZE, VOLUME_RWTEST_SIZE
from common import create_and_wait_pod, create_pvc_spec, delete_and_wait_pod
from common import generate_random_data, read_volume_data, write_volume_data
from common import generate_volume_name

# Using a StorageClass because GKE is using the default StorageClass if not
# specified. Volumes are still being manually created and not provisioned.
CSI_PV_TEST_STORAGE_NAME = 'longhorn-csi-pv-test'


def create_pv_storage(api, cli, pv, claim, base_image, from_backup):
    """
    Manually create a new PV and PVC for testing.
    """
    cli.create_volume(
        name=pv['metadata']['name'], size=pv['spec']['capacity']['storage'],
        numberOfReplicas=int(pv['spec']['csi']['volumeAttributes']
                             ['numberOfReplicas']),
        baseImage=base_image, fromBackup=from_backup)
    common.wait_for_volume_detached(cli, pv['metadata']['name'])

    api.create_persistent_volume(pv)
    api.create_namespaced_persistent_volume_claim(
        body=claim,
        namespace='default')


def update_storageclass_references(name, pv, claim):
    """
    Rename all references to a StorageClass to a specified name.
    """
    pv['spec']['storageClassName'] = name
    claim['spec']['storageClassName'] = name


def create_and_wait_csi_pod(pod_name, client, core_api, csi_pv, pvc, pod_make, base_image, from_backup):  # NOQA
    pv_name = generate_volume_name()
    create_and_wait_csi_pod_named_pv(pv_name, pod_name, client, core_api,
                                     csi_pv, pvc, pod_make, base_image,
                                     from_backup)


def create_and_wait_csi_pod_named_pv(pv_name, pod_name, client, core_api, csi_pv, pvc, pod_make, base_image, from_backup):  # NOQA
    pod = pod_make(name=pod_name)
    pod['spec']['volumes'] = [
        create_pvc_spec(pv_name)
    ]
    csi_pv['metadata']['name'] = pv_name
    csi_pv['spec']['csi']['volumeHandle'] = pv_name
    csi_pv['spec']['csi']['volumeAttributes']['fromBackup'] = from_backup
    pvc['metadata']['name'] = pv_name
    pvc['spec']['volumeName'] = pv_name
    update_storageclass_references(CSI_PV_TEST_STORAGE_NAME, csi_pv, pvc)

    create_pv_storage(core_api, client, csi_pv, pvc, base_image, from_backup)
    create_and_wait_pod(core_api, pod)


@pytest.mark.coretest   # NOQA
@pytest.mark.csi  # NOQA
def test_csi_mount(client, core_api, csi_pv, pvc, pod_make):  # NOQA
    """
    Test that a statically defined CSI volume can be created, mounted,
    unmounted, and deleted properly on the Kubernetes cluster.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """
    volume_size = DEFAULT_VOLUME_SIZE * Gi
    csi_mount_test(client, core_api,
                   csi_pv, pvc, pod_make, volume_size)


def csi_mount_test(client, core_api, csi_pv, pvc, pod_make,  # NOQA
                   volume_size, base_image=""): # NOQA
    create_and_wait_csi_pod('csi-mount-test', client, core_api, csi_pv, pvc,
                            pod_make, base_image, "")

    volumes = client.list_volume()
    assert len(volumes) == 1
    assert volumes[0]["name"] == csi_pv['metadata']['name']
    assert volumes[0]["size"] == str(volume_size)
    assert volumes[0]["numberOfReplicas"] == \
        int(csi_pv['spec']['csi']['volumeAttributes']["numberOfReplicas"])
    assert volumes[0]["state"] == "attached"
    assert volumes[0]["baseImage"] == base_image


@pytest.mark.csi  # NOQA
def test_csi_io(client, core_api, csi_pv, pvc, pod_make):  # NOQA
    """
    Test that input and output on a statically defined CSI volume works as
    expected.

    Fixtures are torn down here in reverse order that they are specified as a
    parameter. Take caution when reordering test fixtures.
    """
    csi_io_test(client, core_api, csi_pv, pvc, pod_make)


def csi_io_test(client, core_api, csi_pv, pvc, pod_make, base_image=""):  # NOQA
    pv_name = generate_volume_name()
    pod_name = 'csi-io-test'
    create_and_wait_csi_pod_named_pv(pv_name, pod_name, client, core_api,
                                     csi_pv, pvc, pod_make, base_image, "")

    test_data = generate_random_data(VOLUME_RWTEST_SIZE)
    write_volume_data(core_api, pod_name, test_data)
    delete_and_wait_pod(core_api, pod_name)
    common.wait_for_volume_detached(client, csi_pv['metadata']['name'])

    pod_name = 'csi-io-test-2'
    pod = pod_make(name=pod_name)
    pod['spec']['volumes'] = [
        create_pvc_spec(pv_name)
    ]
    csi_pv['metadata']['name'] = pv_name
    csi_pv['spec']['csi']['volumeHandle'] = pv_name
    pvc['metadata']['name'] = pv_name
    pvc['spec']['volumeName'] = pv_name
    update_storageclass_references(CSI_PV_TEST_STORAGE_NAME, csi_pv, pvc)

    create_and_wait_pod(core_api, pod)

    resp = read_volume_data(core_api, pod_name)
    assert resp == test_data


@pytest.mark.csi  # NOQA
def test_csi_backup(client, core_api, csi_pv, pvc, pod_make):
    """
    Test that backup/restore works with volumes created by CSI driver.
    """
    csi_backup_test(client, core_api, csi_pv, pvc, pod_make)


def csi_backup_test(client, core_api, csi_pv, pvc, pod_make, base_image=""):  # NOQA
    pod_name = 'csi-backup-test'
    create_and_wait_csi_pod(pod_name, client, core_api, csi_pv, pvc, pod_make,
                            base_image, "")
    test_data = generate_random_data(VOLUME_RWTEST_SIZE)

    setting = client.by_id_setting(common.SETTING_BACKUP_TARGET)
    # test backupTarget for multiple settings
    backupstores = common.get_backupstore_url()
    i = 1
    for backupstore in backupstores:
        if common.is_backupTarget_s3(backupstore):
            backupsettings = backupstore.split("$")
            setting = client.update(setting, value=backupsettings[0])
            assert setting["value"] == backupsettings[0]

            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value=backupsettings[1])
            assert credential["value"] == backupsettings[1]
        else:
            setting = client.update(setting, value=backupstore)
            assert setting["value"] == backupstore
            credential = client.by_id_setting(
                    common.SETTING_BACKUP_TARGET_CREDENTIAL_SECRET)
            credential = client.update(credential, value="")
            assert credential["value"] == ""

        backupstore_test(client, core_api, csi_pv, pvc, pod_make, pod_name,
                         base_image, test_data, i)
        i += 1


def backupstore_test(client, core_api, csi_pv, pvc, pod_make, pod_name, base_image, test_data, i):  # NOQA
    vol_name = csi_pv['metadata']['name']
    write_volume_data(core_api, pod_name, test_data)

    volume = client.by_id_volume(vol_name)
    snap = volume.snapshotCreate()
    volume.snapshotBackup(name=snap["name"])

    bv, b = common.find_backup(client, vol_name, snap["name"])

    pod2_name = 'csi-backup-test-' + str(i)
    create_and_wait_csi_pod(pod2_name, client, core_api, csi_pv, pvc, pod_make,
                            base_image, b["url"])

    resp = read_volume_data(core_api, pod2_name)
    assert resp == test_data

    bv.backupDelete(name=b["name"])

    backups = bv.backupList()
    found = False
    for b in backups:
        if b["snapshotName"] == snap["name"]:
            found = True
            break
    assert not found
