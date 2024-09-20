*** Settings ***
Documentation       K8s keywords

Library             ../libs/keywords/k8s_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/host_keywords.py
Library             ../libs/keywords/node_keywords.py

*** Variables ***
${DRAIN_TIMEOUT}    90

*** Keywords ***
Stop volume node kubelet of ${workload_kind} ${workload_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    restart_kubelet    ${node_name}    ${duration}

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

Add deleted node back
    reboot_node_by_name    ${deleted_node}

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

Cordon ${workload_kind} ${workload_id} volume node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${volume_node} =    get_volume_node    ${volume_name}
    cordon_node    ${volume_node}
    check_node_is_not_schedulable    ${volume_node}

Force drain all nodes
    FOR    ${node_id}    IN RANGE    0    3
        ${node_name} =    get_node_by_index    ${node_id}
        force_drain_node    ${node_name}
        wait_for_all_pods_evicted    ${node_name}
    END

Check node ${node_id} cordoned
    ${node_name} =    get_node_by_index    ${node_id}
    check_node_cordoned    ${node_name}

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
    [Arguments]    ${instance_manger}
    check_instance_manager_pdb_not_exist    ${instance_manger}

