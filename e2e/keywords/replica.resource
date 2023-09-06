*** Settings ***
Documentation       Longhorn replica related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/replica_keywords.py
Resource            node.resource


*** Keywords ***
All replicas state should eventually be ${expected_replica_state}
    FOR    ${node_index}    IN    @{cluster_node_index}
        ${target_node_index} =    Evaluate    ${node_index}+1
        Run keyword And Continue On Failure
        ...    Wait Until Keyword Succeeds
        ...    ${retry_timeout_second} seconds
        ...    ${retry_interval} seconds
        ...    Replica on node ${target_node_index} state should be ${expected_replica_state}
    END

Replica state on node ${node_index} should eventually be ${expected_replica_state}
    Run keyword And Continue On Failure
    ...    Wait Until Keyword Succeeds
    ...    ${retry_timeout_second} seconds
    ...    ${retry_interval} seconds
    ...    Replica on node ${node_index} state should be ${expected_replica_state}

Replica on node ${node_index} state should be ${expected_replica_state}
    ${target_node_index} =    Evaluate    ${node_index}-1
    ${replica_current_state} =    get_replica_state
    ...    ${volume_name}
    ...    ${cluster_node_index}[${target_node_index}]
    check_workload_state    ${replica_current_state}    ${expected_replica_state}

Wait for replica on node ${node_index} start rebuilding
    ${target_node_index} =    Evaluate    ${node_index}-1
    wait_for_replica_rebuilding_start    ${volume_name}    ${target_node_index}

Wait for replica on node ${node_index} complete rebuilding
    ${target_node_index} =    Evaluate    ${node_index}-1
    wait_for_replica_rebuilding_complete    ${volume_name}    ${target_node_index}

Delete the replica on node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    delete_replica    ${volume_name}    ${target_node_index}

Wait until all replicas rebuilt
    FOR    ${node_index}    IN    @{cluster_node_index}
        Run keyword And Continue On Failure
        ...    wait_for_replica_rebuilding_complete    ${volume_name}    ${node_index}
    END

Wait for all replicas to be created
    wait_for_replica_created    ${volume_name}    ${number_of_replicas}
