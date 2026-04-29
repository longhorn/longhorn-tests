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

Delete sharemanager pod of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    delete_sharemanager_pod    ${volume_name}

Wait for sharemanager pod of ${workload_kind} ${workload_id} recreation
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_sharemanager_pod_recreation    ${volume_name}

Check no sharemanager pod of ${workload_kind} ${workload_id} recreation
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    check_no_sharemanager_pod_recreation    ${volume_name}

Wait for sharemanager pod of ${workload_kind} ${workload_id} running
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_share_manager_pod_running    ${volume_name}

Wait for sharemanager pod of ${workload_kind} ${workload_id} deleted
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_sharemanager_pod_deleted    ${volume_name}

Assert disk size in sharemanager pod for ${workload_kind} ${workload_id} is ${size}
    ${expected_size_byte} =    convert_size_to_bytes    ${size}    to_str=True

    ${workload_name}=    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    ${share_manager_pod}=    Set Variable    share-manager-${volume_name}
    wait_for_disk_size_in_sharemanager_pod    ${share_manager_pod}    ${volume_name}    ${expected_size_byte}

Assert encrypted disk size in sharemanager pod for ${workload_kind} ${workload_id} is ${size}
    ${expected_size_byte} =    convert_size_to_bytes    ${size}    to_str=True

    ${workload_name}=    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    ${share_manager_pod}=    Set Variable    share-manager-${volume_name}
    wait_for_encrypted_disk_size_in_sharemanager_pod    ${share_manager_pod}    ${volume_name}    ${expected_size_byte}

Get sharemanager spec image of ${workload_kind} ${workload_id}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${spec_image} =    get_sharemanager_spec_image    ${volume_name}
    [Return]    ${spec_image}

Assert sharemanager current image of ${workload_kind} ${workload_id} is ${expected_image}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${current_image} =    get_sharemanager_current_image    ${volume_name}
    Should Be Equal    ${current_image}    ${expected_image}

Check sharemanager current image
    [Arguments]    ${volume_name}    ${expected_image}
    ${current_image} =    get_sharemanager_current_image    ${volume_name}
    Should Be Equal    ${current_image}    ${expected_image}

Assert sharemanager current image of ${workload_kind} ${workload_id} matches spec image
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${spec_image} =    get_sharemanager_spec_image    ${volume_name}
    ${current_image} =    get_sharemanager_current_image    ${volume_name}
    Should Be Equal    ${current_image}    ${spec_image}

Assert sharemanager pod container image of ${workload_kind} ${workload_id} matches spec image
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${spec_image} =    get_sharemanager_spec_image    ${volume_name}
    ${pod_image} =    get_sharemanager_pod_container_image    ${volume_name}
    Should Be Equal    ${pod_image}    ${spec_image}
