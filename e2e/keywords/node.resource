*** Settings ***
Documentation       Kubernetes nodes related keywords

Library             Collections
Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/pod_keywords.py
Library             ../libs/keywords/node_keywords.py


*** Variables ***
${POD_EVICTION_TIME_OUT}=       300


*** Keywords ***
Get the index of the cluster nodes
    ${cluster_node_index} =    get_cluster_node_indices
    Set Test Variable    ${cluster_node_index}

Power off node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    Run keyword And Continue On Failure
    ...    power_off_node
    ...    ${cluster_node_index}[${target_node_index}]

Power on node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    Run keyword And Continue On Failure
    ...    power_on_node
    ...    ${cluster_node_index}[${target_node_index}]

Node ${node_index} state should eventually be ${expected_node_state}
    ${target_node_index} =    Evaluate    ${node_index}-1
    Run keyword And Continue On Failure
    ...    Wait Until Keyword Succeeds
    ...    ${retry_timeout_second} seconds
    ...    ${retry_interval} seconds
    ...    Node ${cluster_node_index}[${target_node_index}] state should be ${expected_node_state}

Node ${node_index} state should be ${expected_node_state}
    ${node_current_state} =    get_node_state    ${node_index}
    Should Be Equal    ${node_current_state}    ${expected_node_state}

Node ${node_index} should have ${expected_replica_count} volume replica
    ${target_node_index} =    Evaluate    ${node_index}-1
    ${node_replica_count} =    get_node_replica_count    ${cluster_node_index}[${target_node_index}]    ${volume_name}
    ${expected_replica_count_number} =    Convert To Integer    ${expected_replica_count}
    Run keyword And Continue On Failure
    ...    Should Be Equal    ${node_replica_count}    ${expected_replica_count_number}

Waiting for pods on node ${node_index} to be evicted
    ${target_node_index} =    Evaluate    ${node_index}-1
    wait_all_pods_evicted    ${target_node_index}
