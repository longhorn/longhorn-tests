*** Settings ***
Documentation       Physical Node Keywords

Library             Collections
Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/host_keywords.py
Library             ../libs/keywords/network_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/workload_keywords.py

*** Keywords ***
Reboot volume ${volume_id} volume node
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    reboot_node_by_name    ${node_name}

Reboot volume ${volume_id} replica node
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_replica_node    ${volume_name}
    reboot_node_by_name    ${node_name}

Reboot node ${idx}
    reboot_node_by_index    ${idx}

Restart all worker nodes
    reboot_all_worker_nodes

Power off node ${idx} for ${power_off_time_in_min} mins
    reboot_node_by_index    ${idx}    ${power_off_time_in_min}

Power off all worker nodes for ${power_off_time_in_min} mins
    reboot_all_worker_nodes    ${power_off_time_in_min}

Restart cluster
    reboot_all_nodes
    setup_control_plane_network_latency

Power on off nodes
    FOR    ${powered_off_node}    IN    @{powered_off_nodes}
        Run keyword And Ignore Error    power_on_node_by_name    ${powered_off_node}
        Remove Values From List    ${powered_off_nodes}    ${powered_off_node}
    END

Power off node ${node_id}
    ${powered_off_node} =     get_node_by_index    ${node_id}
    Append to list      ${powered_off_nodes}     ${powered_off_node}
    power_off_node_by_name    ${powered_off_node}
