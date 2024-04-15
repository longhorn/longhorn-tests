*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/workload_keywords.py
Library    ../libs/keywords/host_keywords.py
Library    ../libs/keywords/kubelet_keywords.py

*** Keywords ***
Keep writing data to pod of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    keep_writing_workload_pod_data    ${workload_name}

Power off volume node of ${workload_kind} ${workload_id} for ${duration} minutes
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    reboot_volume_node    ${volume_name}    ${duration}

Reboot volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    reboot_volume_node    ${volume_name}

When Stop volume node kubelet of ${workload_kind} ${workload_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    restart_kubelet    ${node_name}    ${duration}

Wait for volume of ${workload_kind} ${workload_id} healthy
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    wait_for_workload_volume_healthy    ${workload_name}
