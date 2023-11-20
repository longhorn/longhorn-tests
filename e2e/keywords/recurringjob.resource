*** Settings ***
Documentation    Recurring Job Keywords

Library    Collections
Library    ../libs/keywords/recurringjob_keywords.py

*** Keywords ***
Create snapshot and backup recurringjob for volume ${idx}
    create_snapshot_recurringjob_for_volume    ${volume_list}[${idx}]
    create_backup_recurringjob_for_volume    ${volume_list}[${idx}]

Check recurringjobs for volume ${idx} work
    check_recurringjobs_work    ${volume_list}[${idx}]
