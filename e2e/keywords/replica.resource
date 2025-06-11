*** Settings ***
Documentation       Longhorn replica related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/replica_keywords.py
Library             ../libs/keywords/node_keywords.py

*** Keywords ***
Volume ${volume_id} replica ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_replica_setting    ${volume_name}    ${setting_name}    ${setting_value}

There should be running replicas on node ${node_id} disk ${disk_name}
    ${node_name} =    get_node_by_index    ${node_id}
    ${disk_uuid} =    get_disk_uuid    ${node_name}    ${disk_name}
    ${replicas} =    get_replicas    volume_name=    node_name=${node_name}    disk_uuid=${disk_uuid}
    Should Be True    len(${replicas}) > 0
