from common import client, clients, volume_name  # NOQA
from common import BASE_IMAGE
from test_basic import volume_basic_test, volume_iscsi_basic_test
from test_basic import snapshot_test, backup_test
from test_ha import ha_simple_recovery_test, ha_salvage_test
from test_engine_upgrade import engine_offline_upgrade_test
from test_engine_upgrade import engine_live_upgrade_test
from test_engine_upgrade import engine_live_upgrade_rollback_test
from test_migration import migration_confirm_test, migration_rollback_test


def test_volume_basic_with_base_image(clients, volume_name):  # NOQA
    volume_basic_test(clients, volume_name, BASE_IMAGE)


def test_volume_iscsi_basic_with_base_image(clients, volume_name):  # NOQA
    volume_iscsi_basic_test(clients, volume_name, BASE_IMAGE)


def test_snapshot_with_base_image(clients, volume_name):  # NOQA
    snapshot_test(clients, volume_name, BASE_IMAGE)


def test_backup_with_base_image(clients, volume_name):  # NOQA
    backup_test(clients, volume_name, BASE_IMAGE)


def test_ha_simple_recovery_with_base_image(client, volume_name):  # NOQA
    ha_simple_recovery_test(client, volume_name, BASE_IMAGE)


def test_ha_salvage_with_base_image(client, volume_name):  # NOQA
    ha_salvage_test(client, volume_name, BASE_IMAGE)


def test_engine_offline_upgrade_with_base_image(client, volume_name):  # NOQA
    engine_offline_upgrade_test(client, volume_name, BASE_IMAGE)


def test_engine_live_upgrade_with_base_image(client, volume_name):  # NOQA
    engine_live_upgrade_test(client, volume_name, BASE_IMAGE)


def test_engine_live_upgrade_rollback_with_base_image(client, volume_name):  # NOQA
    engine_live_upgrade_rollback_test(client, volume_name, BASE_IMAGE)


def test_migration_confirm_with_base_image(clients, volume_name):  # NOQA
    migration_confirm_test(clients, volume_name, BASE_IMAGE)


def test_migration_rollback_with_base_image(clients, volume_name):  # NOQA
    migration_rollback_test(clients, volume_name, BASE_IMAGE)
