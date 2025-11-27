*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    String
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/host_keywords.py
Library    ../libs/keywords/k8s_keywords.py
Library    ../libs/keywords/replica_keywords.py

*** Keywords ***
Create pod ${pod_id} using volume ${volume_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    ${claim_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_pod    ${pod_name}    ${claim_name}

Create pod ${pod_id} using persistentvolumeclaim ${claim_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_pod    ${pod_name}    ${claim_name}

Wait for pod ${pod_id} running
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    wait_for_workload_pods_running    ${pod_name}

Delete pod of ${workload_kind} ${workload_id}
    [Arguments]    &{config}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod_name} =    get_workload_pod_name    ${workload_name}
    delete_pod    ${pod_name}    &{config}

Delete pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    delete_pod    ${pod_name}

Keep writing data to pod of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    keep_writing_workload_pod_data    ${workload_name}

Write ${size} MB data to file ${file_name} in pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    write_workload_pod_random_data    ${pod_name}    ${size}    ${file_name}

Write ${size} GB large data to file ${file_name} in pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    write_workload_pod_large_data    ${pod_name}    ${size}    ${file_name}

Run commands in ${workload_kind} ${workload_id}
    [Arguments]    &{config}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    run_commands_workload_pod    ${workload_name}    &{config}

Check pod ${pod_id} data in file ${file_name} is intact
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    check_workload_pod_data_checksum    ${pod_name}    ${file_name}

Record file ${file_name} checksum in pod ${pod_id} as checksum ${checksum_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    ${checksum} =    get_workload_pod_data_checksum   ${pod_name}    ${file_name}
    Set To Dictionary    ${volume_checksums}    ${checksum_id}    ${checksum}

Record file ${file_name} checksum in ${workload_kind} ${workload_id} as checksum ${checksum_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${checksum} =    get_workload_pod_data_checksum   ${workload_name}    ${file_name}
    Set To Dictionary    ${volume_checksums}    ${checksum_id}    ${checksum}

Check pod ${pod_id} file ${file_name} checksum matches checksum ${checksum_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    ${expected_checksum} =    Get From Dictionary    ${volume_checksums}    ${checksum_id}
    check_workload_pod_data_checksum    ${pod_name}    ${file_name}    ${expected_checksum}

Check ${workload_kind} ${workload_id} file ${file_name} checksum matches checksum ${checksum_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${expected_checksum} =    Get From Dictionary    ${volume_checksums}    ${checksum_id}
    check_workload_pod_data_checksum    ${workload_name}    ${file_name}    ${expected_checksum}

Check pod ${pod_id} file ${file_name} has checksum ${expected_checksum}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    check_workload_pod_data_checksum    ${pod_name}    ${file_name}    ${expected_checksum}

Check file ${file_name} exists in pod ${pod_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    ${result}=    check_workload_pod_data_exists    ${pod_name}    ${file_name}
    Should Be True    ${result}

Check pod ${pod_id} works
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    write_workload_pod_random_data    ${pod_name}    1024    random-data
    check_workload_pod_data_checksum    ${pod_name}    random-data

Check pod ${pod_id} did not restart
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    check_workload_pod_did_not_restart    ${pod_name}

Check ${workload_kind} ${workload_id} pods did not restart
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    check_workload_pod_did_not_restart    ${workload_name}

Power off volume node of ${workload_kind} ${workload_id} for ${duration} minutes
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    reboot_node_by_name    ${node_name}    ${duration}

Power off volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${powered_off_node} =    get_volume_node    ${volume_name}
    Append to list      ${powered_off_nodes}     ${powered_off_node}
    ${last_volume_node} =    get_volume_node    ${volume_name}
    power_off_volume_node    ${volume_name}
    Set Test Variable    ${last_volume_node}

Power off volume node of ${workload_kind} ${workload_id} without waiting
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${powered_off_node} =    get_volume_node    ${volume_name}
    Append to list      ${powered_off_nodes}     ${powered_off_node}
    ${last_volume_node} =    get_volume_node    ${volume_name}
    power_off_volume_node    ${volume_name}    waiting=False
    Set Test Variable    ${last_volume_node}

Reboot volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    reboot_node_by_name    ${node_name}

Stop volume node kubelet of ${workload_kind} ${workload_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    restart_kubelet    ${node_name}    ${duration}

Stop volume nodes kubelet for ${duration} seconds
    [Arguments]    @{args}
    @{node_list} =    Create List
    FOR    ${arg}    IN    @{args}
        @{workload} =    Split String    ${arg}
        ${workload_name} =    generate_name_with_suffix    ${workload}[0]    ${workload}[1]
        ${volume_name} =    get_workload_volume_name    ${workload_name}
        ${node_name} =    get_volume_node    ${volume_name}
        Append To List    ${node_list}    ${node_name}
    END
    restart_kubelet_on_nodes    ${duration}    ${node_list}

Wait for volume of ${workload_kind} ${workload_id} detached
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_detached    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attached
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_attached    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} healthy
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    wait_for_workload_volume_healthy    ${workload_name}

Wait until volume of ${workload_kind} ${workload_id} replica rebuilding started on ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_replica_rebuilding_to_start_on_node    ${volume_name}    ${replica_locality}

Wait until volume of ${workload_kind} ${workload_id} replica rebuilding completed on ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_replica_rebuilding_to_complete_on_node    ${volume_name}    ${replica_locality}

Wait for volume of ${workload_kind} ${workload_id} attached and unknown
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_unknown    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} faulted
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_faulted    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attaching
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_attaching    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} stuck in state attaching
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_stuck_attaching    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attached and degraded
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_degraded    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attached and healthy
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_healthy    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attached to the original node and degraded
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_degraded    ${volume_name}
    ${volume_node} =    get_volume_node    ${volume_name}
    Should Be Equal    ${last_volume_node}    ${volume_node}

Wait for volume of ${workload_kind} ${workload_id} attached to another node and degraded
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_degraded    ${volume_name}
    ${volume_node} =    get_volume_node    ${volume_name}
    Should Not Be Equal    ${last_volume_node}    ${volume_node}

Wait for volume of ${workload_kind} ${workload_id} attached to another node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_attached    ${volume_name}
    ${volume_node} =    get_volume_node    ${volume_name}
    Should Not Be Equal    ${last_volume_node}    ${volume_node}

Delete replica of ${workload_kind} ${workload_id} volume on ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    delete_replica_on_node    ${volume_name}    ${replica_locality}

Wait for ${workload_kind} ${workload_id} pods container creating
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    wait_for_workload_pods_container_creating    ${workload_name}

Wait for workloads pods stable
    [Arguments]    @{args}
    @{workload_list} =    Create List
    FOR    ${arg}    IN    @{args}
        @{workload} =    Split String    ${arg}
        ${workload_name} =    generate_name_with_suffix    ${workload}[0]    ${workload}[1]
        Append To List    ${workload_list}    ${workload_name}
    END
    wait_for_workloads_pods_stably_running    ${workload_list}

Delete replica of ${workload_kind} ${workload_id} volume on all ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    delete_replica_on_nodes    ${volume_name}    ${replica_locality}

Update volume of ${workload_kind} ${workload_id} replica count to ${replica_count}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    update_volume_spec    ${volume_name}    numberOfReplicas    ${replica_count}

Wait for ${workload_kind} ${workload_id} pod stuck in ${expect_state} on the original node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod} =     wait_for_pod_kept_in_state    ${workload_name}    ${expect_state}
    ${node_name} =    get_pod_node    ${pod}
    Should Be Equal    ${node_name}    ${last_volume_node}

Wait for ${workload_kind} ${workload_id} pod stuck in ${expect_state} on another node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod} =     wait_for_pod_kept_in_state    ${workload_name}    ${expect_state}
    ${node_name} =    get_pod_node    ${pod}
    Should Not Be Equal    ${node_name}    ${last_volume_node}

Check ${workload_kind} ${workload_id} pod is ${expect_state} on the original node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod} =     wait_for_pod_kept_in_state    ${workload_name}    ${expect_state}
    ${node_name} =    get_pod_node    ${pod}
    Should Be Equal    ${node_name}    ${last_volume_node}

Wait for ${workload_kind} ${workload_id} pod is ${expect_state} on another node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod} =     wait_for_pod_kept_in_state    ${workload_name}    ${expect_state}
    ${node_name} =    get_pod_node    ${pod}
    Should Not Be Equal    ${node_name}    ${last_volume_node}

Trim ${workload_kind} ${workload_id} volume should ${condition}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}

    IF    $condition == "fail"
        trim_workload_volume_filesystem    ${workload_name}    is_expect_fail=True
    ELSE IF    $condition == "pass"
        trim_workload_volume_filesystem    ${workload_name}    is_expect_fail=False
    ELSE
        Fail    "Invalid condition value: ${condition}"
    END

Delete Longhorn ${workload_kind} ${workload_name} pod on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}

    IF    '${workload_name}' == 'engine-image'
        ${label_selector} =    Set Variable    longhorn.io/component=engine-image
    ELSE IF    '${workload_name}' == 'instance-manager'
        ${label_selector} =    Set Variable    longhorn.io/component=instance-manager
    ELSE
        ${label_selector} =    Set Variable    ${EMPTY}
    END
    ${longhorn_namespace} =    get_longhorn_namespace
    delete_workload_pod_on_node    ${workload_name}    ${node_name}    ${longhorn_namespace}    ${label_selector}

Delete Longhorn ${workload_kind} ${workload_name} pod on all nodes
    ${node_names} =    list_node_names_by_role    worker

    ${longhorn_namespace} =    get_longhorn_namespace
    FOR    ${node_name}    IN    @{node_names}
        delete_workload_pod_on_node    ${workload_name}    ${node_name}    ${longhorn_namespace}
    END

Delete Longhorn ${workload_kind} ${workload_name} pod on all nodes simultaneously
    ${node_names} =    list_node_names_by_role    worker

    ${longhorn_namespace} =    get_longhorn_namespace
    FOR    ${node_name}    IN    @{node_names}
        delete_workload_pod_on_node    ${workload_name}    ${node_name}    ${longhorn_namespace}    wait=${False}
    END

Delete Longhorn ${workload_kind} ${workload_name} pod
    ${longhorn_namespace} =    get_longhorn_namespace
    ${pod_name} =    get_workload_pod_name    ${workload_name}    ${longhorn_namespace}
    Log    ${pod_name}
    delete_pod    ${pod_name}     ${longhorn_namespace}

Force delete ${workload_kind} ${workload_id} pod on the original node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    delete_workload_pod_on_node    ${workload_name}    ${last_volume_node}    default

Check volume of ${workload_kind} ${workload_id} replica on node ${node_id} disk ${disk_name}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_node_by_index    ${node_id}
    ${disk_uuid} =    get_disk_uuid    ${node_name}    ${disk_name}
    wait_for_disk_replica_count    volume_name=${volume_name}    node_name=${node_name}    disk_uuid=${disk_uuid}

Expand ${workload_kind} ${workload_id} volume to ${size}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${new_size} =    convert_size_to_bytes    ${size}

    expand_workload_claim_size    ${workload_name}    ${new_size}

Expand ${workload_kind} ${workload_id} volume with additional ${size}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${new_size} =    convert_size_to_bytes    ${size}

    expand_workload_claim_size_with_additional_bytes    ${workload_name}    ${new_size}

Expand ${workload_kind} ${workload_id} volume more than storage maximum size should fail
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    ${max_size} =    get_volume_node_disk_storage_maximum    ${volume_name}    ${node_name}
    ${new_size} =    evaluate    ${max_size} + 1

    Run Keyword And Expect Error    Failed to expand*    expand_workload_claim_size    ${workload_name}    ${new_size}    skip_retry=True

Assert volume size of ${workload_kind} ${workload_id} remains ${size} for at least ${period} seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    FOR    ${i}    IN RANGE    ${period}
        ${expected_size_byte} =    convert_size_to_bytes    ${size}    to_str=True
        ${current_size_byte} =    get_volume_size    ${volume_name}
        Should Be Equal    ${current_size_byte}    ${expected_size_byte}
        Sleep    1
    END

Upgrade volume ${workload_kind} ${workload_id} engine to ${custom_engine_image}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    upgrade_engine_image    ${volume_name}    ${custom_engine_image}
    wait_for_engine_image_upgrade_completed    ${volume_name}    ${custom_engine_image}

Record ${workload_kind} ${workload_id} pod UIDs
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod_uids} =    get_workload_pod_uids    ${workload_name}
    # [Return]    ${pod_uids}
    Set Test Variable    ${recorded_pod_uids}    ${pod_uids}

Assert pod UIDs of ${workload_kind} ${workload_id} remain unchanged
    [Arguments]    ${num_checks}

    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    FOR    ${i}    IN RANGE    ${num_checks}
        Log To Console    Checking pod UIDs of ${workload_name} remain unchanged ...(${i + 1}/${num_checks})
        ${pod_uids} =    get_workload_pod_uids    ${workload_name}
        Should Be Equal As Strings    ${pod_uids}    ${recorded_pod_uids}
        Sleep    1
    END
