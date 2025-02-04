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
