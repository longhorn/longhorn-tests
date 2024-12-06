*** Settings ***
Documentation    Backup Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/backup_keywords.py

*** Keywords ***
Create backup ${backup_id} for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_backup    ${volume_name}    ${backup_id}

Create backup ${backup_id} for ${workload_kind} ${workload_id} volume
    ${backup_id}=  Convert To String  ${backup_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    create_backup  ${volume_name}  ${backup_id}

Verify backup list contains no error for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    verify_no_error    ${volume_name}

Verify backup list contains backup no error for ${workload_kind} ${workload_id} volume 
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    verify_no_error    ${volume_name}

Verify backup list contains backup ${backup_id} of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup} =    get_backup_name    ${backup_id}    ${volume_name}
    Should Not Be Equal    ${backup}    ${None}

Verify backup list contains backup ${backup_id} of ${workload_kind} ${workload_id} volume
    ${backup_id}=  Convert To String  ${backup_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    ${backup}=    get_backup_name    ${backup_id}    ${volume_name}
    Should Not Be Equal    ${backup}    ${None}

Delete backup volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_backup_volume    ${volume_name}

Check volume ${volume_id} data is backup ${backup_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_name} =    get_backup_name    ${backup_id}
    check_restored_volume_checksum    ${volume_name}    ${backup_name}

Check backup synced from backupstore
    assert_all_backups_before_uninstall_exist    ${backups_before_uninstall}

Volume ${volume_id} backup ${backup_id} should be able to create
    Create backup ${backup_id} for volume ${volume_id}
    Verify backup list contains no error for volume ${volume_id}
    Verify backup list contains backup ${backup_id} of volume ${volume_id}
