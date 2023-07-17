*** Settings ***
Documentation       Longhorn volume related keywords

Library             ../libs/keywords/volume_keywords.py
Resource            ./node.resource


*** Keywords ***
Create Volume With Fields
    [Arguments]    ${list_of_fields}
    ${volume_name}    ${manifest} =    Create Volume Base Manifest

    FOR    ${field}    IN    @{list_of_fields}
        ${manifest} =    Update Manifest With Fields    ${manifest}    ${field}
    END

    Create Volume With Manifest    ${manifest}

Create Volume Base Manifest
    ${volume_name}    ${manifest} =    create_volume_manifest
    Set Test Variable    ${volume_name}
    RETURN    ${volume_name}    ${manifest}

Update Manifest With Fields
    [Arguments]    ${manifest}    ${field}
    update_manifest_field    ${manifest}    ${field}
    RETURN    ${manifest}

Create Volume With Manifest
    [Arguments]    ${manifest}
    create_volume_using_manifest    ${manifest}

Attach volume to node ${node_index}
    Get the index of the cluster nodes
    ${target_node_index} =    Evaluate    ${node_index}-1
    ${volume_attached_node} =    attach_volume    ${volume_name}    ${cluster_node_index}[${target_node_index}]
    ${non_volume_attached_node} =    get_non_volume_attached_node    ${volume_attached_node}
    Set Test Variable    ${volume_attached_node}
    Set Test Variable    ${non_volume_attached_node}

Write data into mount point
    ${volume_data_checksum} =    write_volume_random_data    ${volume_name}    512
    Set Test Variable    ${volume_data_checksum}

Check data is intact
    check_data    ${volume_name}    ${volume_data_checksum}

Volume ${volume_name} data checksum should be ${volume_data_checksum}
    check_data    ${volume_name}    ${volume_data_checksum}

Volume state should eventually be ${expected_volume_state}
    Run keyword And Continue On Failure
    ...    Wait Until Keyword Succeeds
    ...    ${retry_timeout_second} seconds
    ...    ${retry_interval} seconds
    ...    Volume state should be ${expected_volume_state}

Volume state should be ${expected_volume_state}
    ${volume_current_state} =    get_volume_state    ${volume_name}
    Should Be Equal    ${volume_current_state}    ${expected_volume_state}
