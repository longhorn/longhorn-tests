*** Settings ***
Documentation    Node Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/node_keywords.py

*** Keywords ***
Add ${disk_type} type disk ${disk_path} for all worker nodes
    ${worker_nodes}=    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    ${worker_node}    ${disk_type}    ${disk_path}
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
