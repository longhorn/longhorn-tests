from common import clients, volume_name  # NOQA
from common import BASE_IMAGE
from test_basic import volume_basic_test, volume_iscsi_basic_test
from test_basic import snapshot_test, backup_test


def test_volume_basic_with_base_image(clients, volume_name):  # NOQA
    volume_basic_test(clients, volume_name, BASE_IMAGE)


def test_volume_iscsi_basic_with_base_image(clients, volume_name):  # NOQA
    volume_iscsi_basic_test(clients, volume_name, BASE_IMAGE)


def test_snapshot_with_base_image(clients, volume_name):  # NOQA
    snapshot_test(clients, volume_name, BASE_IMAGE)


def test_backup_with_base_image(clients, volume_name):  # NOQA
    backup_test(clients, volume_name, BASE_IMAGE)
