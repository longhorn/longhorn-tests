*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/workload_keywords.py

*** Keywords ***
Keep writing data to pod of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    keep_writing_workload_pod_data    ${workload_name}

Power off volume node of ${workload_kind} ${workload_id} for ${duration} minutes
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    reboot_workload_volume_node    ${workload_name}    ${duration}

Reboot volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    reboot_workload_volume_node    ${workload_name}

When Stop volume node kubelet of ${workload_kind} ${workload_id} for ${duration} seconds
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    restart_workload_kubelet    ${workload_name}    ${duration}

Wait for volume of ${workload_kind} ${workload_id} healthy
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    wait_for_workload_volume_healthy    ${workload_name}
