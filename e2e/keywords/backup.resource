*** Settings ***
Documentation    Backup Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/backup_keywords.py

*** Keywords ***
Create backup ${backup_id} for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_backup    ${volume_name}    ${backup_id}

Verify backup list contains no error for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    verify_no_error    ${volume_name}

Verify backup list contains backup ${backup_id} of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup} =    get_backup    ${volume_name}    ${backup_id}
    Should Not Be Equal    ${backup}    ${None}

Delete backup volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_backup_volume    ${volume_name}
