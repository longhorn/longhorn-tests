import pytest

import test_ha

from common import client, clients, random_labels, volume_name, core_api  # NOQA
from common import flexvolume, csi_pv_baseimage, pvc_baseimage, pod  # NOQA
from common import flexvolume_baseimage, csi_pv, pvc, pod_make  # NOQA
from common import BASE_IMAGE_EXT4, BASE_IMAGE_EXT4_SIZE
from test_basic import volume_basic_test, volume_iscsi_basic_test
from test_basic import snapshot_test, backup_test, backup_labels_test
from test_engine_upgrade import engine_offline_upgrade_test
from test_engine_upgrade import engine_live_upgrade_test
from test_engine_upgrade import engine_live_upgrade_rollback_test
from test_migration import migration_confirm_test, migration_rollback_test
from test_flexvolume import flexvolume_mount_test, flexvolume_io_test
from test_csi import csi_mount_test, csi_io_test, csi_backup_test
from test_recurring_job import recurring_job_labels_test


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_volume_basic_with_base_image(clients, volume_name):  # NOQA
    volume_basic_test(clients, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_volume_iscsi_basic_with_base_image(clients, volume_name):  # NOQA
    volume_iscsi_basic_test(clients, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_snapshot_with_base_image(clients, volume_name):  # NOQA
    snapshot_test(clients, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_backup_with_base_image(clients, volume_name):  # NOQA
    backup_test(clients, volume_name, str(BASE_IMAGE_EXT4_SIZE),
                BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_backup_labels_with_base_image(clients, random_labels, volume_name):  # NOQA
    backup_labels_test(clients, random_labels, volume_name,
                       str(BASE_IMAGE_EXT4_SIZE), BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_ha_simple_recovery_with_base_image(client, volume_name):  # NOQA
    test_ha.ha_simple_recovery_test(client, volume_name,
                                    str(BASE_IMAGE_EXT4_SIZE),
                                    BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
def test_ha_salvage_with_base_image(client, core_api, volume_name):  # NOQA
    test_ha.ha_salvage_test(client, core_api, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
def test_ha_backup_deletion_recovery(client, volume_name):  # NOQA
    test_ha.ha_backup_deletion_recovery_test(client, volume_name,
                                             str(BASE_IMAGE_EXT4_SIZE),
                                             BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
def test_engine_offline_upgrade_with_base_image(client, volume_name):  # NOQA
    engine_offline_upgrade_test(client, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
def test_engine_live_upgrade_with_base_image(client, volume_name):  # NOQA
    engine_live_upgrade_test(client, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
def test_engine_live_upgrade_rollback_with_base_image(client, volume_name):  # NOQA
    engine_live_upgrade_rollback_test(client, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
def test_migration_confirm_with_base_image(clients, volume_name):  # NOQA
    migration_confirm_test(clients, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
def test_migration_rollback_with_base_image(clients, volume_name):  # NOQA
    migration_rollback_test(clients, volume_name, BASE_IMAGE_EXT4)


@pytest.mark.baseimage  # NOQA
@pytest.mark.flexvolume  # NOQA
def test_flexvolume_mount_with_base_image(client, core_api, flexvolume_baseimage, pod):  # NOQA
    flexvolume_mount_test(client, core_api, flexvolume_baseimage, pod,
                          BASE_IMAGE_EXT4_SIZE)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
@pytest.mark.flexvolume  # NOQA
def test_flexvolume_io_with_base_image(client, core_api, flexvolume_baseimage, pod):  # NOQA
    flexvolume_io_test(client, core_api, flexvolume_baseimage, pod)


@pytest.mark.baseimage  # NOQA
@pytest.mark.csi  # NOQA
def test_csi_mount_with_base_image(client, core_api, csi_pv_baseimage, pvc_baseimage, pod_make):  # NOQA
    csi_mount_test(client, core_api, csi_pv_baseimage, pvc_baseimage, pod_make,
                   BASE_IMAGE_EXT4_SIZE, BASE_IMAGE_EXT4)


@pytest.mark.coretest   # NOQA
@pytest.mark.baseimage  # NOQA
@pytest.mark.csi  # NOQA
def test_csi_io_with_base_image(client, core_api, csi_pv_baseimage, pvc_baseimage, pod_make):  # NOQA
    csi_io_test(client, core_api, csi_pv_baseimage, pvc_baseimage, pod_make)


@pytest.mark.coretest  # NOQA
@pytest.mark.baseimage  # NOQA
@pytest.mark.csi  # NOQA
def test_csi_backup_with_base_image(client, core_api, csi_pv, pvc, pod_make):  # NOQA
    csi_backup_test(client, core_api, csi_pv, pvc, pod_make, BASE_IMAGE_EXT4)


@pytest.mark.baseimage
@pytest.mark.recurring_job
def test_recurring_job_labels_with_base_image(client, random_labels, volume_name):  # NOQA
    recurring_job_labels_test(client, random_labels, volume_name,
                              str(BASE_IMAGE_EXT4_SIZE), BASE_IMAGE_EXT4)
