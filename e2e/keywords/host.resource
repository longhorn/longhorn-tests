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

Reboot node ${node_id}
    [Documentation]    Reboot a node by its index.
    ...                Node will be rebooted with default 1 minute downtime.
    ...                Example: Reboot node 0
    reboot_node_by_index    ${node_id}

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

Power off node ${node_id} for ${power_off_time_in_min} mins
    [Documentation]    Power off a node for specified duration in minutes.
    ...                Example: Power off node 0 for 6 mins
    reboot_node_by_index    ${node_id}    ${power_off_time_in_min}

Power off all worker nodes for ${power_off_time_in_min} mins
    reboot_all_worker_nodes    ${power_off_time_in_min}

Restart cluster
    reboot_all_nodes

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

Corrupt CSI block volume staging mount point on node ${node_id} for volume ${volume_name}
    [Documentation]    Corrupt the CSI block volume staging mount point with explicit host operations.
    ...    1. Create fake device symlink /dev/longhorn/${volume_name} -> /dev/zero.
    ...    2. Create staging directory under kubelet CSI staging path.
    ...    3. Bind-mount the staging directory to itself to trigger EBUSY-style cleanup behavior.
    ...    4. Create a broken symlink ${volume_name} -> /nonexistent/path/file to trigger ENOENT.
    ${staging_path} =    Set Variable    /var/lib/kubelet/plugins/kubernetes.io/csi/volumeDevices/staging/${volume_name}
    ${target_path} =    Set Variable    ${staging_path}/${volume_name}
    ${fake_device} =    Set Variable    /dev/longhorn/${volume_name}
    Run command on node    ${node_id}    mkdir -p /dev/longhorn
    Run command on node    ${node_id}    ln -sfn /dev/zero ${fake_device}
    Run command on node    ${node_id}    mkdir -p ${staging_path}
    Run command on node    ${node_id}    mountpoint -q ${staging_path} || mount --bind ${staging_path} ${staging_path}
    Run command on node    ${node_id}    rm -f ${target_path} && ln -s /nonexistent/path/file ${target_path}

Verify CSI block volume staging mount point is corrupted on node ${node_id} for volume ${volume_name}
    [Documentation]    Verify that the CSI block volume staging mount point has been corrupted
    ...    with a broken symlink pointing to /nonexistent/path/file.
    ...    This confirms the corruption created by the explicit host commands in this test keyword.
    ${staging_path} =    Set Variable    /var/lib/kubelet/plugins/kubernetes.io/csi/volumeDevices/staging/${volume_name}/${volume_name}
    Run command on node ${node_id} and wait for output
    ...    file ${staging_path}
    ...    /nonexistent/path/file

Verify CSI block volume staging mount point is recovered on node ${node_id} for volume ${volume_name}
    [Documentation]    Verify that the CSI block volume staging mount point has been recovered
    ...    by confirming the broken symlink pointing to /nonexistent/path/file is no longer present.
    ...    This confirms that the CSI node server has successfully resolved the corrupted mount point.
    ${staging_path} =    Set Variable    /var/lib/kubelet/plugins/kubernetes.io/csi/volumeDevices/staging/${volume_name}/${volume_name}
    Run command on node ${node_id} and not expect output
    ...    file ${staging_path}
    ...    /nonexistent/path/file

Get host log list on path ${log_path} on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${host_log_files} =    get_host_log_files    ${node_name}    ${log_path}
    log    ${host_log_files}
    Set Test Variable    ${host_log_files}
