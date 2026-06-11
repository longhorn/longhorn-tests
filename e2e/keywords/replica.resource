*** Settings ***
Documentation       Longhorn replica related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/replica_keywords.py
Library             ../libs/keywords/instancemanager_keywords.py
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

Delete replica ${replica_name}
    delete_replica_by_name    ${replica_name}

Wait for ${engine_type} replica ${replica_name} deleted from instance manager on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_replica_deleted    ${node_name}    ${replica_name}    ${engine_type}

Wait for ${engine_type} replica ${replica_name} present in instance manager on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_replica_present    ${node_name}    ${replica_name}    ${engine_type}

Assert replica file size of ${resource_kind} ${resource_id} is ${expected_size}
    ${expected_bytes} =    convert_size_to_bytes    ${expected_size}    to_str=True
    ${resource_name}=    generate_name_with_suffix    ${resource_kind}    ${resource_id}
    ${volume_name}=    Run Keyword If    '${resource_kind}' == 'volume'
    ...        Set Variable    ${resource_name}
    ...    ELSE
    ...        get_workload_volume_name    ${resource_name}
    wait_for_replica_file_size    ${volume_name}    ${expected_bytes}
