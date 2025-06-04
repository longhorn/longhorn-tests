*** Settings ***
Documentation    RecurringJob Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/recurringjob_keywords.py

*** Keywords ***
Create snapshot and backup recurringjob for volume ${volume_id}
    Create recurringjob for volume ${volume_id} with    task=snapshot
    Create recurringjob for volume ${volume_id} with    task=backup

Create recurringjob for volume ${volume_id} with
    [Arguments]    &{config}
    ${volume_name} =   generate_name_with_suffix    volume    ${volume_id}
    create_recurringjob_for_volume    ${volume_name}    &{config}

Check recurringjobs for volume ${volume_id} work
    ${volume_name} =   generate_name_with_suffix    volume    ${volume_id}
    check_recurringjobs_work    ${volume_name}
