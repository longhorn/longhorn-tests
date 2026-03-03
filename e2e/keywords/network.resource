*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/network_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/engine_keywords.py

*** Variables ***


*** Keywords ***
Disconnect volume node network of ${workload_kind} ${workload_id} for ${duration} seconds
    [Documentation]    Disconnect network on the node where workload volume is attached.
    ...                Example: Disconnect volume node network of deployment 0 for 100 seconds
    ...                Example: Disconnect volume node network of statefulset 0 for 100 seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
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

Disconnect volume node network of ${workload_kind} ${workload_id} for ${duration} seconds without waiting for completion
    [Documentation]    Disconnect network on the node where workload volume is attached without waiting for completion.
    ...                Example: Disconnect volume node network of statefulset 0 for 100 seconds without waiting for completion
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    ${network_block_pod_name} =    disconnect_node_network_without_waiting_completion    ${node_name}    ${duration}
    Set Test Variable    ${network_block_pod_name}

Drop instance-manager egress traffic of statefulset ${statefulset_id} for ${duration} seconds without waiting for completion
    ${workload_name} =   generate_name_with_suffix    statefulset    ${statefulset_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${instance_manager_name} =    get_engine_instance_manager_name    ${volume_name}
    drop_pod_egress_traffic    ${instance_manager_name}   ${duration}

Disconnect volume ${volume_id} node network for ${duration} seconds without waiting for completion
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    ${network_block_pod_name} =    disconnect_node_network_without_waiting_completion    ${node_name}    ${duration}
    Set Test Variable    ${network_block_pod_name}

Wait for disconnected node back
    wait_for_block_network_pod_completed    ${network_block_pod_name}    Succeeded

Setup control plane network latency to ${latency_ms} ms
    [Documentation]    Set network latency on control plane nodes
    ...    ${latency_ms}: Latency in milliseconds (e.g., 1500 for 1.5 seconds)
    setup_control_plane_network_latency    ${latency_ms}
Disconnect network on node ${node_id} for ${duration} seconds
    [Documentation]    Disconnect network on node for specified duration.
    ...                Network will automatically reconnect after timeout.
    ...                Example: Disconnect network on node 0 for 100 seconds
    ${node_name} =    get_node_by_index    ${node_id}
    disconnect_node_network    ${node_name}    ${duration}
