import pytest

from common import client  # NOQA

from common import system_backup_random_name
from common import system_backup_wait_for_state
from common import system_restore_random_name
from common import system_restore_wait_for_state

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
