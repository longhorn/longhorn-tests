*** Settings ***
Documentation    System Backup Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/system_backup_keywords.py

*** Keywords ***
Create system backup ${system_backup_id}
    ${backup_name} =    generate_name_with_suffix    system-backup    ${system_backup_id}
    create_system_backup    ${backup_name}

Restore system backup ${system_backup_id}
    ${backup_name} =    generate_name_with_suffix    system-backup    ${system_backup_id}
    create_system_restore    ${backup_name}

Delete system backup ${system_backup_id}
    ${backup_name} =    generate_name_with_suffix    system-backup    ${system_backup_id}
    delete_system_backup    ${backup_name}

Wait for system backup ${system_backup_name} ready
    wait_for_system_backup_ready    ${system_backup_name}

Set system backup ${backup_name} status
    [Arguments]    &{status}
    set_system_backup_status    ${backup_name}    &{status}

Check system backup ${backup_name} createdAt is empty
    check_system_backup_created_at_empty    ${backup_name}

Wait for system backup ${backup_name} deleted
    wait_for_system_backup_deleted    ${backup_name}
