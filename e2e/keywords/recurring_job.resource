*** Settings ***
Documentation    Recurring Job Keywords

Library    Collections
Library    ../libs/keywords/recurring_job_keywords.py

*** Keywords ***
Create snapshot and backup recurring job for volume ${idx}
    create_snapshot_recurring_job_for_volume    ${volume_list}[${idx}]
    create_backup_recurring_job_for_volume    ${volume_list}[${idx}]

Check recurring jobs for volume ${idx} work
    check_recurring_jobs_work    ${volume_list}[${idx}]