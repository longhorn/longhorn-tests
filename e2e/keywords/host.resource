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

Power off volume ${volume_id} volume node
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    ${powered_off_node} =    Set Variable    ${node_name}
    Append to list    ${powered_off_nodes}    ${powered_off_node}
    power_off_node_by_name    ${node_name}

Power off volume ${volume_id} replica node
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_replica_node    ${volume_name}
    ${powered_off_node} =    Set Variable    ${node_name}
    Append to list    ${powered_off_nodes}    ${powered_off_node}
    power_off_node_by_name    ${node_name}

Power off volume ${volume_id} volume node without waiting
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    ${powered_off_node} =    Set Variable    ${node_name}
    Append to list    ${powered_off_nodes}    ${powered_off_node}
    power_off_node_by_name    ${node_name}    waiting=False

Power off volume ${volume_id} replica node without waiting
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_replica_node    ${volume_name}
    ${powered_off_node} =    Set Variable    ${node_name}
    Append to list    ${powered_off_nodes}    ${powered_off_node}
    power_off_node_by_name    ${node_name}    waiting=False

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

Create vm snapshot on node ${node_id}
    ${node_name} =     get_node_by_index    ${node_id}
    create_vm_snapshot    ${node_name}

Create vm snapshot on volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${volume_name}
    create_vm_snapshot    ${node_name}

Delete vm snapshots
    cleanup_vm_snapshots

Run command on node
    [Arguments]    ${node_id}    ${command}
    ${node_name} =    get_node_by_index    ${node_id}
    execute_command_on_node    ${command}    ${node_name}

Run command on node ${node_id} and not expect output
    [Arguments]    ${command}    ${unexpected_output}
    ${node_name} =    get_node_by_index    ${node_id}
    execute_command_on_node_and_not_expect_output    ${command}    ${node_name}    ${unexpected_output}

Run command on node ${node_id} and wait for output
    [Arguments]    ${command}    ${expected_output}
    ${node_name} =    get_node_by_index    ${node_id}
    execute_command_on_node_and_wait_for_output    ${command}    ${node_name}    ${expected_output}

Run command on node ${node_id} and get output
    [Arguments]    ${command}    ${expected_output}
    ${node_name} =    get_node_by_index    ${node_id}
    ${result} =    execute_command_on_node_and_get_output    ${command}    ${node_name}    ${expected_output}
    RETURN    ${result}

Run command on node ${node_id} and get output string
    [Arguments]    ${command}
    ${node_name} =    get_node_by_index    ${node_id}
    ${result} =    execute_command_on_node_and_get_output_string    ${command}    ${node_name}
    RETURN    ${result}

Get host log list on path ${log_path} on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${host_log_files} =    get_host_log_files    ${node_name}    ${log_path}
    log    ${host_log_files}
    Set Test Variable    ${host_log_files}
