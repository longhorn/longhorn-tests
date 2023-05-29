import pytest

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
from common import wait_for_backup_count
from common import wait_for_volume_detached
from common import wait_for_volume_healthy
from common import wait_for_volume_restoration_completed

from backupstore import set_random_backupstore  # NOQA


ALWAYS = "always"
IF_NOT_PRESENT = "if-not-present"


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
def test_system_backup_with_volume_backup_policy_if_not_present(client, volume_name, set_random_backupstore):  # NOQA
    """
    Scenario: system backup with volume backup policy (if-not-present) should
              only create volume backup when there is no existing backup in
              the volume.

    Issue: https://github.com/longhorn/longhorn/issues/5011

    Given a volume is created.

    When system backup (system-backup-1) has no volume backup policy.
    And system backup (system-backup-1) created.
    Then system backup has volume backup policy (if-not-present).
    And system backup is in state (Ready).
    And volume has backup count (1).

    When system backup (system-backup-2) has volume backup policy
         (if-not-present).
    And system backup (system-backup-2) created.
    Then system backup is in state (Ready).
    And volume has backup count (1).
    """
    host_id = get_self_host_id()

    volume = create_and_check_volume(client, volume_name)
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    system_backup_name_1 = system_backup_random_name()
    client.create_system_backup(Name=system_backup_name_1)

    system_backup = client.by_id_system_backup(system_backup_name_1)
    assert system_backup.volumeBackupPolicy == IF_NOT_PRESENT

    system_backup_wait_for_state("Ready", system_backup_name_1, client)

    backup_volume = client.by_id_backupVolume(volume_name)
    wait_for_backup_count(backup_volume, 1)

    system_backup_name_2 = system_backup_random_name()
    client.create_system_backup(Name=system_backup_name_2,
                                VolumeBackupPolicy=IF_NOT_PRESENT)

    system_backup_wait_for_state("Ready", system_backup_name_2, client)

    backup_volume = client.by_id_backupVolume(volume_name)
    wait_for_backup_count(backup_volume, 1)


@pytest.mark.system_backup_restore   # NOQA
def test_system_backup_with_volume_backup_policy_always(client, volume_name, set_random_backupstore):  # NOQA
    """
    Scenario: system backup with volume backup policy (always) should always
              create volume backup, regardless of their existing backups.

    Issue: https://github.com/longhorn/longhorn/issues/5011

    Given a volume is created.
    And volume has backup count (1).

    When system backup (system-backup) has volume backup policy (always).
    And system backup (system-backup) created.
    Then system backup is in state (Ready).
    And volume has backup count (2).
    """
    host_id = get_self_host_id()

    volume = create_and_check_volume(client, volume_name)
    volume.attach(hostId=host_id)
    volume = wait_for_volume_healthy(client, volume_name)

    create_backup(client, volume_name)

    system_backup_name = system_backup_random_name()
    client.create_system_backup(Name=system_backup_name,
                                VolumeBackupPolicy=ALWAYS)

    system_backup_wait_for_state("Ready", system_backup_name, client)

    backup_volume = client.by_id_backupVolume(volume_name)
    wait_for_backup_count(backup_volume, 2)
