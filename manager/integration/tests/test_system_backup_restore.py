import pytest
import time

from common import client  # NOQA
from common import volume_name # NOQA

from common import check_volume_data
from common import cleanup_volume
from common import create_and_check_volume
from common import create_backup
from common import get_self_host_id
from common import system_backup_random_name
from common import system_backup_wait_for_state
from common import system_restore_random_name
from common import system_restore_wait_for_state
from common import update_setting
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import wait_for_volume_restoration_completed

from common import SETTING_BACKUPSTORE_POLL_INTERVAL

from backupstore import set_random_backupstore  # NOQA


@pytest.mark.system_backup_restore   # NOQA
def test_system_backup_and_restore(client, set_random_backupstore):  # NOQA
    """
    Scenario: test system backup and restore

    Issue: https://github.com/longhorn/longhorn/issues/1455

    Given setup backup target
    When create system backup
    Then system backup should be in state Ready

    When restore system backup
    Then system restore should be in state Completed

    """
    system_backup_name = system_backup_random_name()
    client.create_system_backup(Name=system_backup_name)

    system_backup_wait_for_state("Ready", system_backup_name, client)

    system_restore_name = system_restore_random_name()
    client.create_system_restore(Name=system_restore_name,
                                 SystemBackup=system_backup_name)

    system_restore_wait_for_state("Completed", system_restore_name, client)


@pytest.mark.system_backup_restore   # NOQA
def test_system_backup_and_restore_volume_with_data(client, volume_name, set_random_backupstore):  # NOQA
    """
    Scenario: test system backup and restore volume with data

    Issue: https://github.com/longhorn/longhorn/issues/1455

    Given volume created
    And data written to volume
    And volume backup created
    And system backup created
    And system backup in state Ready
    And volume deleted

    When restore system backup
    Then system restore should be in state Completed

    When wait for volume restoration to complete
    And volume detached

    Then attach volume
    And volume should be healthy
    And volume data should exist

    """
    host_id = get_self_host_id()

    volume = create_and_check_volume(client, volume_name)
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    _, _, _, data = create_backup(client, volume_name)

    system_backup_name = system_backup_random_name()
    client.create_system_backup(Name=system_backup_name)

    system_backup_wait_for_state("Ready", system_backup_name, client)

    cleanup_volume(client, volume)

    system_restore_name = system_restore_random_name()
    client.create_system_restore(Name=system_restore_name,
                                 SystemBackup=system_backup_name)

    system_restore_wait_for_state("Completed", system_restore_name, client)

    restored_volume = client.by_id_volume(volume_name)
    wait_for_volume_restoration_completed(client, volume_name)
    wait_for_volume_detached(client, volume_name)

    restored_volume.attach(hostId=host_id)
    restored_volume = wait_for_volume_healthy(client, volume_name)

    check_volume_data(restored_volume, data)


@pytest.mark.system_backup_restore   # NOQA
def test_system_backup_delete_when_other_system_backup_using_name_as_prefix(client, set_random_backupstore):  # NOQA
    """
    Scenario: test deleting system backup when there are other system backups
              using the name as prefix

    Issue: https://github.com/longhorn/longhorn/issues/6045

    Given setup backup target.
    And setting (backupstore-poll-interval) is (10 seconds).
    When create 3 system backups (aa, aaa, aaaa)
    Then system backups should be in state Ready

    When delete system backup (aa)
    And wait 60 seconds
    Then system backups should exists (aaa, aaaa)
    """
    update_setting(client, SETTING_BACKUPSTORE_POLL_INTERVAL, "10")

    system_backup_names = ["aa", "aaa", "aaaa"]
    for name in system_backup_names:
        client.create_system_backup(Name=name)

    for name in system_backup_names:
        system_backup_wait_for_state("Ready", name, client)

    aa_system_backup = client.by_id_system_backup("aa")
    client.delete(aa_system_backup)

    time.sleep(60)
    system_backups = client.list_system_backup()
    assert len(system_backups) == 2

    for system_backup in client.list_system_backup():
        assert system_backup["name"] in ["aaa", "aaaa"]
