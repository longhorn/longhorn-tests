*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    String
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/host_keywords.py
Library    ../libs/keywords/k8s_keywords.py

*** Keywords ***
Create pod ${pod_id} using volume ${volume_id}
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    ${claim_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_pod    ${pod_name}    ${claim_name}

Wait for pod ${pod_id} running
    ${pod_name} =    generate_name_with_suffix    pod    ${pod_id}
    wait_for_workload_pods_running    ${pod_name}

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

Power off volume node of ${workload_kind} ${workload_id} for ${duration} minutes
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    reboot_node_by_name    ${node_name}    ${duration}

Power off volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${powered_off_node} =    get_volume_node    ${volume_name}
    ${last_volume_node} =    get_volume_node    ${volume_name}
    power_off_volume_node    ${volume_name}
    Set Test Variable    ${powered_off_node}
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

Delete replica of ${workload_kind} ${workload_id} volume on ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    delete_replica_on_node    ${volume_name}    ${replica_locality}

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

Check ${workload_kind} ${workload_id} pod is ${expect_state} on another node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod} =     wait_for_pod_kept_in_state    ${workload_name}    ${expect_state}
    ${node_name} =    get_pod_node    ${pod}
    Should Not Be Equal    ${node_name}    ${last_volume_node}

Delete Longhorn ${workload_kind} ${workload_name} pod on node ${node_id}
    
    ${node_name} =    get_node_by_index    ${node_id}
    
    IF    '${workload_name}' == 'engine-image'
        ${label_selector} =    Set Variable    longhorn.io/component=engine-image       
    ELSE IF    '${workload_name}' == 'instance-manager'
        ${label_selector} =    Set Variable    longhorn.io/component=instance-manager
    ELSE
        ${label_selector} =    Set Variable    ${EMPTY}
    END
    delete_workload_pod_on_node    ${workload_name}    ${node_name}    longhorn-system    ${label_selector}

Delete Longhorn ${workload_kind} ${workload_name} pod
    ${pod_name} =    get_workload_pod_name    ${workload_name}    longhorn-system
    Log    ${pod_name}
    delete_pod    ${pod_name}     longhorn-system
