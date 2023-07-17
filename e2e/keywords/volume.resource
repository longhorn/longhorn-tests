*** Settings ***
Documentation    Longhorn volume related keywords resources

Library    ../libs/steps.py

Resource    ./node.resource

*** Keywords ***
A ${size} GB ${volume_type} volume with ${request_replica_count} replicas
    ${volume_name} =    create_volume   ${size}   ${request_replica_count}   ${volume_type}
    Set Test Variable    ${volume_name}
    Set Test Variable    ${request_replica_count}
    Get the index of the cluster nodes
    Get node index with replica
    Get node index without replica

Create a volume ${size} GB with ${replica_count} replicas
    ${volume_name} =    create_volume   ${size}    ${replica_count}
    attach_volume    ${volume_name}
    Set Test Variable    ${volume_name}

Attach volume to node ${node_index}
    ${target_node_index} =    Evaluate    ${node_index}-1
    ${volume_attached_node} =    attach_volume   ${volume_name}   ${cluster_node_index}[${target_node_index}]
    ${non_volume_attached_node} =    get_non_volume_attached_node   ${volume_attached_node}
    Set Test Variable    ${volume_attached_node}
    Set Test Variable    ${non_volume_attached_node}

Write data into mount point
    ${volume_data_checksum} =    write_volume_random_data   ${volume_name}    512
    Set Test Variable    ${volume_data_checksum}

Write data to the volume
    ${volume_data_checksum} =     write_volume_random_data   ${volume_name}    1024
    Set Test Variable    ${volume_data_checksum}

Check data is intact
    check_data    ${volume_name}    ${volume_data_checksum}

Volume ${volume_name} data checksum should be ${volume_data_checksum}
    check_data    ${volume_name}    ${volume_data_checksum}

Volume state should be ${expected_volume_state}
    Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Check volume state should be ${expected_volume_state}

Check volume state should be ${expected_volume_state}
    ${volume_current_state} =   get_volume_state   ${volume_name}
    Should Be Equal    ${volume_current_state}    ${expected_volume_state}
