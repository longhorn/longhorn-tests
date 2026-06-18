*** Settings ***
Documentation       Longhorn replica related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/replica_keywords.py
Library             ../libs/keywords/node_keywords.py
Library             ../libs/keywords/workload_keywords.py

*** Keywords ***
Volume ${volume_id} replica ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_replica_setting    ${volume_name}    ${setting_name}    ${setting_value}

There should be running replicas on node ${node_id} disk ${disk_name}
    ${node_name} =    get_node_by_index    ${node_id}
    ${disk_uuid} =    get_disk_uuid    ${node_name}    ${disk_name}
    wait_for_disk_replica_count    volume_name=    node_name=${node_name}    disk_uuid=${disk_uuid}

There should be no replica on node ${node_id} disk ${disk_name}
    ${node_name} =    get_node_by_index    ${node_id}
    ${disk_uuid} =    get_disk_uuid    ${node_name}    ${disk_name}
    wait_for_disk_replica_count    volume_name=    node_name=${node_name}    disk_uuid=${disk_uuid}    count=0

There should be ${replica_count} replicas of volume ${volume_id} on node ${node_id} disk ${disk_name}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${disk_uuid} =    get_disk_uuid    ${node_name}    ${disk_name}
    wait_for_disk_replica_count    volume_name=${volume_name}    node_name=${node_name}    disk_uuid=${disk_uuid}    count=${replica_count}

There should be no replica of volume ${volume_id} on node ${node_id} disk ${disk_name}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${disk_uuid} =    get_disk_uuid    ${node_name}    ${disk_name}
    wait_for_disk_replica_count    volume_name=${volume_name}    node_name=${node_name}    disk_uuid=${disk_uuid}    count=0

Delete replica
    [Arguments]    ${replica_name}
    [Documentation]    Delete a replica custom resource by its exact name using kubectl.
    delete_replica_by_name    ${replica_name}

Verify replica lvol is deleted from SPDK lvol list on node ${node_id}
    [Arguments]    ${replica_name}
    ${node_name} =    get_node_by_index    ${node_id}
    verify_replica_lvol_deleted_from_spdk_lvol    ${node_name}    ${replica_name}

Verify replica lvol exists in SPDK lvol list on node ${node_id}
    [Arguments]    ${replica_name}
    ${node_name} =    get_node_by_index    ${node_id}
    verify_replica_lvol_exists_in_spdk_lvol    ${node_name}    ${replica_name}

Assert replica file size of ${resource_kind} ${resource_id} is ${expected_size}
    ${expected_bytes} =    convert_size_to_bytes    ${expected_size}    to_str=True
    ${resource_name}=    generate_name_with_suffix    ${resource_kind}    ${resource_id}
    ${volume_name}=    Run Keyword If    '${resource_kind}' == 'volume'
    ...        Set Variable    ${resource_name}
    ...    ELSE
    ...        get_workload_volume_name    ${resource_name}
    wait_for_replica_file_size    ${volume_name}    ${expected_bytes}
