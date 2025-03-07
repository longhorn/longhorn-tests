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

Disable node ${node_id} scheduling
    ${node_name} =    get_node_by_index    ${node_id}
    disable_node_scheduling    ${node_name}

Enable node ${node_id} scheduling
    ${node_name} =    get_node_by_index    ${node_id}
    enable_node_scheduling    ${node_name}

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
