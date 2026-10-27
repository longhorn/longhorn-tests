*** Settings ***
Documentation    Vault key provider keywords: the in-cluster Vault fixture and the
...              per-volume key entries Longhorn stores in it.

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/vault_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/persistentvolumeclaim_keywords.py
Library    ../libs/keywords/backup_keywords.py
Library    ../libs/keywords/snapshot_keywords.py

*** Keywords ***
Deploy vault fixture
    vault_keywords.deploy_vault_fixture

Make vault unavailable
    set_vault_available    ${False}

Make vault available
    set_vault_available    ${True}

Restore vault availability
    vault_keywords.restore_vault_availability

Cleanup vault keys
    vault_keywords.cleanup_vault_keys

Collect vault diagnostics
    vault_keywords.collect_vault_diagnostics

Assert vault holds key of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    assert_vault_has_key_of_volume    ${volume_name}

Assert vault holds no key of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    assert_vault_has_no_key_of_volume    ${volume_name}

Assert vault keys of ${workload_kind} ${workload_id} and ${other_workload_kind} ${other_workload_id} volumes are equal
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${other_workload_name} =    generate_name_with_suffix    ${other_workload_kind}    ${other_workload_id}
    ${other_volume_name} =    get_workload_volume_name    ${other_workload_name}
    assert_vault_keys_of_volumes_are_equal    ${volume_name}    ${other_volume_name}

Assert vault keys of ${workload_kind} ${workload_id} and ${other_workload_kind} ${other_workload_id} volumes are different
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${other_workload_name} =    generate_name_with_suffix    ${other_workload_kind}    ${other_workload_id}
    ${other_volume_name} =    get_workload_volume_name    ${other_workload_name}
    assert_vault_keys_of_volumes_are_different    ${volume_name}    ${other_volume_name}

Assert vault key of volume ${volume_id} equals key of ${workload_kind} ${workload_id} volume
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name} =    get_workload_volume_name    ${workload_name}
    assert_vault_keys_of_volumes_are_equal    ${volume_name}    ${workload_volume_name}

Record vault key of ${workload_kind} ${workload_id} volume as key ${key_id}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    record_vault_key_of_volume    ${volume_name}    ${key_id}

Restore vault key of ${workload_kind} ${workload_id} volume from key ${key_id}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    restore_vault_key_of_volume    ${volume_name}    ${key_id}

Delete vault key of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    delete_vault_key_of_volume    ${volume_name}

Corrupt vault key of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    corrupt_vault_key_of_volume    ${volume_name}

Assert ${workload_kind} ${workload_id} volume encryption
    [Arguments]    &{expected}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    assert_volume_encryption    ${volume_name}    &{expected}

Assert volume ${volume_id} encryption
    [Arguments]    &{expected}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    assert_volume_encryption    ${volume_name}    &{expected}

Wait for ${workload_kind} ${workload_id} volume encryption key stored
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${version} =    wait_for_volume_encryption_key_stored    ${volume_name}
    RETURN    ${version}

Assert ${workload_kind} ${workload_id} volume encryption condition is ${status}
    [Arguments]    ${reason}=${None}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    assert_volume_encryption_condition    ${volume_name}    ${status}    ${reason}

Wait for vault key of volume ${volume_name} destroyed
    wait_for_vault_key_of_volume_gone    ${volume_name}

Get encryption secret name
    # Library-qualified: Robot matches names ignoring case, spaces and
    # underscores, so the bare call would resolve back to this keyword.
    ${name} =    vault_keywords.get_encryption_secret_name
    RETURN    ${name}

Wait for persistentvolumeclaim ${claim_id} event containing ${message}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    wait_for_pvc_event_message    ${claim_name}    ${message}

Assert vault holds key of backup ${backup_id} of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${backup_name} =    get_backup_name    ${backup_id}    ${volume_name}
    assert_vault_has_key_of_backup    ${backup_name}

Assert vault holds no key of backup ${backup_id} of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${backup_name} =    get_backup_name    ${backup_id}    ${volume_name}
    assert_vault_has_no_key_of_backup    ${backup_name}

Assert vault key of backup ${backup_id} equals key of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${backup_name} =    get_backup_name    ${backup_id}    ${volume_name}
    assert_vault_key_of_backup_equals_volume    ${backup_name}    ${volume_name}

Assert snapshot ${snapshot_id} of ${workload_kind} ${workload_id} volume records encryption key version ${expected}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${snapshot_name} =    get_snapshot_name    ${volume_name}    ${snapshot_id}
    wait_for_volume_snapshot_encryption_key_version    ${snapshot_name}    ${expected}

Create volume ${volume_id} from backup ${backup_id} of deleted volume ${source_volume_name}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url} =    get_backup_url    ${backup_id}    ${source_volume_name}
    create_volume    ${volume_name}    fromBackup=${backup_url}    &{config}

Get backup name of backup ${backup_id} of ${workload_kind} ${workload_id} volume
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${backup_name} =    get_backup_name    ${backup_id}    ${volume_name}
    RETURN    ${backup_name}

Assert vault holds key of backup named ${backup_name}
    assert_vault_has_key_of_backup    ${backup_name}
