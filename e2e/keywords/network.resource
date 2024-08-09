*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/network_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py

*** Variables ***


*** Keywords ***
Disconnect volume node network of statefulset ${statefulset_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    statefulset    ${statefulset_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    disconnect_node_network    ${node_name}    ${duration}

Disconnect volume nodes network for ${duration} seconds
    [Arguments]    @{args}
    @{node_list} =    Create List
    FOR    ${arg}    IN    @{args}
        @{workload} =    Split String    ${arg}
        ${workload_name} =    generate_name_with_suffix    ${workload}[0]    ${workload}[1]
        ${volume_name} =    get_workload_volume_name    ${workload_name}
        ${node_name} =    get_volume_node    ${volume_name}
        Append To List    ${node_list}    ${node_name}
    END
    disconnect_network_on_nodes    ${duration}    ${node_list}

Disconnect volume node network of statefulset ${statefulset_id} for ${duration} seconds without waiting for completion
    ${workload_name} =   generate_name_with_suffix    statefulset    ${statefulset_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    ${network_block_pod_name} =    disconnect_node_network_without_waiting_completion    ${node_name}    ${duration}
    Set Test Variable    ${network_block_pod_name}

Disconnect volume ${volume_id} node network for ${duration} seconds without waiting for completion
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    ${network_block_pod_name} =    disconnect_node_network_without_waiting_completion    ${node_name}    ${duration}
    Set Test Variable    ${network_block_pod_name}

Wait for disconnected node back
    wait_for_block_network_pod_completed    ${network_block_pod_name}    Succeeded
