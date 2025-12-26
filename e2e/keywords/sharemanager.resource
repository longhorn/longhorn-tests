*** Settings ***
Documentation       ShareManager Keywords

Library             ../libs/keywords/common_keywords.py
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

Delete sharemanager pod of deployment ${deployment_id} and wait for recreation
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    delete_sharemanager_pod_and_wait_for_recreation    ${volume_name}

Wait for sharemanager pod of deployment ${deployment_id} restart
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    wait_for_sharemanager_pod_restart    ${volume_name}

Wait for sharemanager pod of deployment ${deployment_id} running
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    wait_for_share_manager_pod_running    ${volume_name}

Assert encrypted disk size in sharemanager pod for ${workload_kind} ${workload_id} is ${size}
    ${expected_size_byte} =    convert_size_to_bytes    ${size}    to_str=True

    ${workload_name}=    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    ${share_manager_pod}=    Set Variable    share-manager-${volume_name}
    Wait Until Keyword Succeeds    ${RETRY_COUNT}    ${RETRY_INTERVAL}
    ...    Check encrypted disk size in sharemanager pod    ${share_manager_pod}    ${volume_name}    ${expected_size_byte}

Check encrypted disk size in sharemanager pod
    [Arguments]    ${sharemanager_pod}    ${volume_name}    ${expected_size}
    ${cmd}=    Set Variable    fdisk -l | grep /dev/mapper/${volume_name}
    ${longhorn_namespace} =    get_longhorn_namespace
    ${result}=    pod_exec    ${sharemanager_pod}    ${longhorn_namespace}    ${cmd}
    Should Contain    ${result}    ${expected_size}
