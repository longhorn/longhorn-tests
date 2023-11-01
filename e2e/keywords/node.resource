*** Settings ***
Documentation       Physical Node Keywords

Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/node_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/network_keywords.py

*** Keywords ***
During replica rebuilding, reboot volume node
    reboot_volume_node    ${volume_name}

During replica rebuilding, reboot replica node
    reboot_replica_node    ${volume_name}

Reboot volume ${idx} volume node
    reboot_volume_node    ${volume_list}[${idx}]
    FOR    ${item}    IN    @{volume_list}
        wait for volume_attached    ${item}
    END

Reboot volume ${idx} replica node
    reboot_replica_node    ${volume_list}[${idx}]
    FOR    ${item}    IN    @{volume_list}
        wait for volume_attached    ${item}
    END

Reboot node ${idx}
    reboot_node_by_index    ${idx}

Restart all worker nodes
    reboot_all_worker_nodes

Reboot volume node of statefulset ${idx}
    ${volume_name} =    get_workload_volume_name    ${statefulset_list}[${idx}]
    ${node_name} =    get_volume_node    ${volume_name}
    reboot_node_by_name    ${node_name}

Power off node ${idx} for ${power_off_time_in_min} mins
    reboot_node_by_index    ${idx}    ${power_off_time_in_min}

Power off all worker nodes for ${power_off_time_in_min} mins
    reboot_all_worker_nodes    ${power_off_time_in_min}

Power off volume node of statefulset ${idx} for ${power_off_time_in_min} mins
    ${volume_name} =    get_workload_volume_name    ${statefulset_list}[${idx}]
    ${node_name} =    get_volume_node    ${volume_name}
    reboot_node_by_name    ${node_name}    ${power_off_time_in_min}

Wait for longhorn ready
    wait_for_all_instance_manager_running
    FOR    ${deployment}    IN    @{deployment_list}
        wait_for_workload_pod_stable   ${deployment}
    END
    FOR    ${statefulset}    IN    @{statefulset_list}
        wait_for_workload_pod_stable   ${statefulset}
    END

Restart cluster
    reboot_all_nodes
    setup_control_plane_network_latency
    wait_for_all_instance_manager_running
    FOR    ${deployment}    IN    @{deployment_list}
        wait_for_workload_pod_stable   ${deployment}
    END
    FOR    ${statefulset}    IN    @{statefulset_list}
        wait_for_workload_pod_stable   ${statefulset}
    END

Stress the CPU of all ${role} nodes
    stress_node_cpu_by_role    ${role}

Stress the CPU of all volume nodes
    stress_node_cpu_by_volumes    ${volume_list}

Stress the memory of all volume nodes
    stress_node_memory_by_volumes    ${volume_list}
