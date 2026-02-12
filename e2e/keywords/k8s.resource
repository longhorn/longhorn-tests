*** Settings ***
Documentation       K8s keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/k8s_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/host_keywords.py
Library             ../libs/keywords/node_keywords.py

*** Keywords ***
Stop volume node kubelet of ${workload_kind} ${workload_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    restart_kubelet    ${node_name}    ${duration}

Stop control plane kubelet for ${duration} seconds
    ${control_plane_node_name} =    get_control_plane_node
    restart_kubelet    ${control_plane_node_name}    ${duration}

Delete volume of ${workload_kind} ${workload_id} volume node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${deleted_node} =    delete_volume_node    ${volume_name}
    Set Test Variable    ${deleted_node}

Delete volume of ${workload_kind} ${workload_id} replica node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${deleted_node} =    delete_replica_node    ${volume_name}
    Set Test Variable    ${deleted_node}

Delete node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    delete_node    ${node_name}

Add deleted node back
    reboot_node_by_name    ${deleted_node}
    IF     "${DATA_ENGINE}" == "v2"
        add_disk    block-disk    ${deleted_node}    block    ${DISK_PATH}
    END

Set k8s node ${node_id} zone ${zone_name}
    ${node_name} =    get_node_by_index    ${node_id}
    set_k8s_node_zone    ${node_name}    ${zone_name}

Force drain volume of ${workload_kind} ${workload_id} volume node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${drained_node} =    get_volume_node    ${volume_name}
    ${last_volume_node} =    get_volume_node    ${volume_name}
    force_drain_node    ${drained_node}
    wait_for_all_pods_evicted    ${drained_node}
    Set Test Variable    ${drained_node}
    Set Test Variable    ${last_volume_node}

Force drain volume of ${workload_kind} ${workload_id} replica node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${drained_node} =    get_replica_node    ${volume_name}
    ${last_volume_node} =    get_volume_node    ${volume_name}
    force_drain_node    ${drained_node}
    wait_for_all_pods_evicted    ${drained_node}
    Set Test Variable    ${drained_node}
    Set Test Variable    ${last_volume_node}

Force drain node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    force_drain_node    ${node_name}

Drain volume of ${workload_kind} ${workload_id} volume node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${drained_node} =    get_volume_node    ${volume_name}
    ${last_volume_node} =    get_volume_node    ${volume_name}
    drain_node    ${drained_node}
    wait_for_all_pods_evicted    ${drained_node}
    Set Test Variable    ${drained_node}
    Set Test Variable    ${last_volume_node}

Uncordon the drained node
    uncordon_node    ${drained_node}

Uncordon node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    uncordon_node    ${node_name}

Cordon node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    cordon_node    ${node_name}
    check_node_is_not_schedulable    ${node_name}

Cordon ${workload_kind} ${workload_id} volume node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${volume_node} =    get_volume_node    ${volume_name}
    cordon_node    ${volume_node}
    check_node_is_not_schedulable    ${volume_node}

Cordon all other nodes beside ${workload_kind} ${workload_id} volume node
    ${workload_name}=    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=      get_workload_volume_name    ${workload_name}
    ${volume_node}=      get_volume_node    ${volume_name}
    FOR    ${node_id}    IN RANGE    0    3
        ${node_name}=    get_node_by_index    ${node_id}
        Run Keyword Unless    '${node_name}' == '${volume_node}'    cordon_node    ${node_name}
    END

Uncordon nodes
    uncordon_all_nodes

Force drain all nodes
    FOR    ${node_id}    IN RANGE    0    3
        ${node_name} =    get_node_by_index    ${node_id}
        force_drain_node    ${node_name}
        wait_for_all_pods_evicted    ${node_name}
    END

Check node ${node_id} cordoned
    ${node_name} =    get_node_by_index    ${node_id}
    check_node_cordoned    ${node_name}

Get node ${node_id} status
    ${node_id}=  Convert To String  ${node_id}
    ${node_name}=  get_node_by_index  ${node_id}
    ${is_ready}=  is_node_ready  ${node_name}
    Log    Node ${node_name} ready status is ${is_ready}
    ${node_status}=  Create Dictionary    node_id=${node_id}    node_name=${node_name}    node_ready=${is_ready}
    [Return]  ${node_status}

Get healthy node names
    @{healthy_node_names}=    Create List
    FOR    ${i}    IN RANGE    0    3
        ${node_status}=    Get node ${i} status
        Run Keyword If    ${node_status["node_ready"]} == True
        ...    Append To List    ${healthy_node_names}    ${node_status["node_name"]}
    END
    [Return]    ${healthy_node_names}

Force drain node ${node_id} and expect failure
    ${drained_node} =    get_node_by_index    ${node_id}
    ${instance_manager_name} =     get_instance_manager_on_node    ${drained_node}
    Run Keyword And Expect Error    *    force_drain_node    ${drained_node}
    Set Test Variable    ${instance_manager_name}
    Set Test Variable    ${drained_node}

Force drain node ${node_id} and expect success
    ${drained_node} =    get_node_by_index    ${node_id}
    ${instance_manager_name} =     get_instance_manager_on_node    ${drained_node}
    force_drain_node    ${drained_node}
    Set Test Variable    ${instance_manager_name}
    Set Test Variable    ${drained_node}

The drain process not completed
    check_drain_process_not_completed    ${drain_process}

The drain process completed
    wait_for_all_pods_evicted    ${drained_node}
    check_drain_process_completed    ${drain_process}

Check PDB not exist
    [Arguments]    ${instance_manager}
    check_instance_manager_pdb_not_exist    ${instance_manager}

Install system upgrade controller
    deploy_system_upgrade_controller

Upgrade kubernetes to latest version
    [Arguments]    &{config}
    upgrade_k8s_to_latest_version    &{config}

Is Longhorn components all running
    ${all_running}=    is_namespaced_pods_all_running    ${LONGHORN_NAMESPACE}
    [Return]    ${all_running}
