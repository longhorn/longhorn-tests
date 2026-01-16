*** Settings ***
Documentation    Node Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/node_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Add ${disk_type} type disk ${disk_path} for all worker nodes
    ${worker_nodes}=    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    ${disk_type}-disk    ${worker_node}    ${disk_type}    ${disk_path}
    END

Set node ${node_id} with
    [Arguments]    &{config}
    ${node_name} =    get_node_by_index    ${node_id}
    set_node   ${node_name}    &{config}

Set node ${node_id} tags
    [Arguments]    @{tags}
    ${node_name} =    get_node_by_index    ${node_id}
    set_node_tags   ${node_name}    @{tags}

Set node ${node_id} disks tags
    [Arguments]    @{tags}
    ${node_name} =    get_node_by_index    ${node_id}
    set_node_disks_tags   ${node_name}    @{tags}

Label node ${node_id} with ${label}
    ${node_name} =    get_node_by_index    ${node_id}
    label_node   ${node_name}    ${label}

Disable node ${node_id} scheduling
    ${node_name} =    get_node_by_index    ${node_id}
    disable_node_scheduling    ${node_name}

Enable node ${node_id} scheduling
    ${node_name} =    get_node_by_index    ${node_id}
    enable_node_scheduling    ${node_name}

Evict node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${evicted_node} =    Set Variable    ${node_name}
    Append to list    ${evicted_nodes}    ${evicted_node}
    evict_node    ${node_name}

Unevict evicted nodes
    FOR    ${evicted_node}    IN    @{evicted_nodes}
        Run keyword And Ignore Error    unevict_node    ${evicted_node}
        Remove Values From List    ${evicted_nodes}    ${evicted_node}
    END

Disable node ${node_id} default disk
    ${node_name} =    get_node_by_index    ${node_id}
    disable_default_disk    ${node_name}

Enable node ${node_id} default disk
    ${node_name} =    get_node_by_index    ${node_id}
    enable_default_disk    ${node_name}

Disable disk ${disk_name} scheduling on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    disable_disk    ${node_name}    ${disk_name}

Enable disk ${disk_name} scheduling on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    enable_disk    ${node_name}    ${disk_name}

Request eviction on default disk of node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    request_eviction_on_default_disk    ${node_name}

Cancel eviction on default disk of node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    cancel_eviction_on_default_disk    ${node_name}

Request eviction on disk ${disk_name} of node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    request_eviction_on_disk    ${node_name}    ${disk_name}

Cancel eviction on disk ${disk_name} of node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    cancel_eviction_on_disk    ${node_name}    ${disk_name}

Check node ${node_id} disk ${disk_name} is in pressure
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_disk_in_pressure    ${node_name}    ${disk_name}

Check node ${node_id} disk ${disk_name} is not in pressure
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_disk_not_in_pressure    ${node_name}    ${disk_name}

Create ${disk_size} Gi ${disk_type} type disk ${disk_name} on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    create_volume   ${disk_name}    size=${disk_size}Gi    numberOfReplicas=1    dataEngine=${DATA_ENGINE}
    attach_volume    ${disk_name}    ${node_name}
    wait_for_volume_healthy    ${disk_name}
    IF    "${disk_type}" == "filesystem"
        ${mount_path} =    mount_disk    ${disk_name}    ${node_name}
    ELSE IF    "${disk_type}" == "block"
        ${mount_path} =    Set Variable    /dev/longhorn/${disk_name}
    END
    add_disk    ${disk_name}    ${node_name}    ${disk_type}    ${mount_path}

Wait for node ${node_id} default disk broken
    ${node_name} =    get_node_by_index    ${node_id}
    wait_default_disk_file_system_changed    ${node_name}
    wait_default_disk_unschedulable    ${node_name}

Delete node ${node_id} default disk
    ${node_name} =    get_node_by_index    ${node_id}
    delete_default_disk    ${node_name}

Record node ${node_id} default disk uuid
    ${node_name} =    get_node_by_index    ${node_id}
    ${recorded_disk_uuid} =    get_default_disk_uuid_on_node    ${node_name}
    Set Test Variable    ${recorded_disk_uuid}

Wait for Longhorn node ${node_id} up
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_longhorn_node_up    ${node_name}
