*** Settings ***
Documentation       ShareManager Keywords

Library             ../libs/keywords/sharemanager_keywords.py

*** Variables ***


*** Keywords ***
Check sharemanager ${condition} using headless service
    ${is_using_headless_service} =    is_sharemanagers_using_headless_service

    # Check if workloads using headless service based on condition.
    # If condition is "not", then check if workloads are not using headless service.
    # If condition is "is", then check if workloads are using headless service.
    # Otherwise, fail the test.
    Run Keyword IF    '${condition}' == 'not'    Should Not Be True    ${is_using_headless_service}
    ...    ELSE IF    '${condition}' == 'is'    Should Be True    ${is_using_headless_service}
    ...    ELSE    Fail    Invalid condition ${condition}

Wait for all sharemanager to be deleted
    wait_for_sharemanagers_deleted

Delete sharemanager of deployment ${deployment_id} and wait for recreation
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    delete_sharemanager_and_wait_for_recreation    ${volume_name}

Wait for sharemanager of deployment ${deployment_id} running
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    wait_for_share_manager_running    ${volume_name}
