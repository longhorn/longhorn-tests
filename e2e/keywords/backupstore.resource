*** Settings ***
Documentation    Backup Store Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/backupstore_keywords.py

*** Keywords ***
Place file ${file_name} into the backups folder of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_file_in_backups_folder    ${volume_name}    ${file_name}

Delete file ${file_name} in the backups folder of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_file_in_backups_folder    ${volume_name}    ${file_name}

Create dummy backup from ${filename}
    create_dummy_backup_from_file    ${filename}

Set backupstore poll intervel to ${poll_interval} seconds
    set_backupstore_poll_interval    ${poll_interval}
