*** Settings ***
Documentation    RecurringJob Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/recurringjob_keywords.py

*** Keywords ***
Create ${job_task} recurringjob ${job_id}
    [Arguments]    &{args}

    ${job_name} =   generate_name_with_suffix    ${job_task}    ${job_id}
    create_recurringjob    ${job_name}    ${job_task}    &{args}

Create snapshot and backup recurringjob for volume ${volume_id}
    ${volume_name} =   generate_name_with_suffix    volume    ${volume_id}
    create_snapshot_recurringjob_for_volume    ${volume_name}
    create_backup_recurringjob_for_volume    ${volume_name}

Check recurringjobs for volume ${volume_id} work
    ${volume_name} =   generate_name_with_suffix    volume    ${volume_id}
    check_recurringjobs_work    ${volume_name}

Create system-backup recurringjob ${job_id}
    [Arguments]    &{config}

    ${job_name} =   generate_name_with_suffix    system-backup    ${job_id}
    create_system_backup_recurringjob    ${job_name}    &{config}

Wait for recurringjob ${job_id} created systembackup to reach ${expected_state} state
    ${job_name} =   generate_name_with_suffix    system-backup    ${job_id}
    wait_for_recurringjob_created_systembackup_state    ${job_name}    ${expected_state}

Assert recurringjob ${job_id} ${created_condition} backup for volume ${volume_id}
    [Arguments]    &{args}

    ${job_name} =   generate_name_with_suffix    system-backup    ${job_id}
    ${volume_name} =   generate_name_with_suffix    volume    ${volume_id}
    IF    "${created_condition}" == "created"
        assert_recurringjob_created_backup_for_volume    ${volume_name}    ${job_name}
    ELSE IF    "${created_condition}" == "not created"
        Run Keyword And Expect Error    *    assert_recurringjob_created_backup_for_volume    ${volume_name}    ${job_name}    retry_count=60
    ELSE
        Fail    Invalid created_condition: ${created_condition}
    END

Wait for ${job_task} recurringjob ${job_id} to complete without error
    ${job_name} =   generate_name_with_suffix    ${job_task}    ${job_id}
    wait_for_recurringjob_pod_completion_without_error    ${job_name}
