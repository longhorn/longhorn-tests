*** Settings ***
Documentation    Longhorn replica related keywords resources

Library    ../libs/steps.py

*** Keywords ***
All replicas state should be ${expected_replica_state}
    FOR    ${node_index}    IN    @{node_index_with_replica}
        Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Check replica on node ${node_index} state should be ${expected_replica_state}
    END

Replica state on node ${node_index} should be ${expected_replica_state}
    ${target_node_index} =    Evaluate    ${node_index}-1
    Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Check replica on node ${node_index_with_replica}[${target_node_index}] state should be ${expected_replica_state}

Check replica on node ${node_index} state should be ${expected_replica_state}
    ${replica_current_state} =   get_replica_state   ${volume_name}   ${node_index}
    check_workload_state    ${replica_current_state}    ${expected_replica_state}

Delete replica ${replica_0} to trigger replica ${replica_0} rebuilding
    delete_replica    ${volume_name}    ${replica_0}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}

During replica ${replica_0} rebuilding, delete replica ${replica_1}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_1}

Wait until replica ${replica_0} rebuilt, delete replica ${replica_2}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_2}

Wait until all replicas rebuilt
    wait_for_replica_rebuilding_complete    ${volume_name}    0
    wait_for_replica_rebuilding_complete    ${volume_name}    1
    wait_for_replica_rebuilding_complete    ${volume_name}    2