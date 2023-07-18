*** Settings ***
Documentation    Kubernetes cluster nodes related keywords resources

Library    ../libs/steps.py

*** Variables ***
${POD_EVICTION_TIME_OUT}=    300

*** Keywords ***
Get the index of the cluster nodes
    ${cluster_node_index} =    get_cluster_node_index   ${volume_name}   ${request_replica_count}
    Set Test Variable    ${cluster_node_index}

Power off node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    power_off_node   ${cluster_node_index}[${target_node_index}]

Power on node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    power_on_node   ${cluster_node_index}[${target_node_index}]

Get node index without replica
    ${node_index_without_replica} =    get_no_replica_node   ${volume_name}   ${request_replica_count}
    Set Test Variable    ${node_index_without_replica}

Get node index with replica
    ${node_index_with_replica} =    get_with_replica_node   ${volume_name}   ${request_replica_count}
    Set Test Variable    ${node_index_with_replica}

Node ${node_index} state should be ${expected_node_state}
    ${target_node_index} =    Evaluate    ${node_index}-1
    Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Check node ${cluster_node_index}[${target_node_index}] state should be ${expected_node_state}

Check node ${node_index} state should be ${expected_node_state}
    ${node_current_state} =   get_node_state   ${node_index}
    Should Be Equal    ${node_current_state}    ${expected_node_state}

Node ${node_index} should have ${expected_replica_count} volume replica
    ${target_node_index} =    Evaluate    ${node_index}-1
    Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Check node ${cluster_node_index}[${target_node_index}] replica count should be ${expected_replica_count}

Check node ${node_index} replica count should be ${expected_replica_count}
    ${node_replica_count} =   get_node_replica_count   ${node_index}   ${volume_name}
    ${expected_replica_count_number} =   Convert To Integer  ${expected_replica_count}
    Should Be Equal    ${node_replica_count}    ${expected_replica_count_number}

Reboot node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    reboot_node   ${cluster_node_index}[${target_node_index}]

Restart Kubelet node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    restart_kubelet   ${cluster_node_index}[${target_node_index}]    0

Restart Kubelet timeout on node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    restart_kubelet   ${cluster_node_index}[${target_node_index}]   ${POD_EVICTION_TIME_OUT}

During writing data into mount point interrupt node ${node_index} network for ${time_inerval} seconds
    ${target_node_index} =    Evaluate    ${node_index}-1
    during_data_writing_interrupt_network   ${cluster_node_index}[${target_node_index}]   ${time_inerval}   ${volume_name}
