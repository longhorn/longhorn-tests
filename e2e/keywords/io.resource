*** Settings ***
Library             ../libs/keywords/io_keywords.py
Library             ../libs/keywords/instancemanager_keywords.py
Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/node_keywords.py
Library             ../libs/keywords/workload_keywords.py

*** Keywords ***
Create dm linear device from block device ${block_disk_path} as ${dm_device_name} on node ${node_id}
    [Documentation]    Create a dm linear device from a raw block device (without formatting/mounting).
    ${node_name} =    get_node_by_index    ${node_id}
    ${result} =    setup_dm_linear_device_from_block_disk    ${block_disk_path}    ${dm_device_name}    ${node_name}
    Set Test Variable    ${dm_sectors}    ${result}[sectors]
    RETURN    ${result}

Create and mount dm disk from block device ${block_disk_path} as ${dm_device_name} on node ${node_id} to ${mount_point}
    [Documentation]    Create a dm linear device from a raw block device, format it as ext4, and mount it.
    ${node_name} =    get_node_by_index    ${node_id}
    ${result} =    setup_dm_linear_device_from_block_disk    ${block_disk_path}    ${dm_device_name}    ${node_name}
    Set Test Variable    ${dm_sectors}    ${result}[sectors]
    format_and_mount_dm_device    ${dm_device_name}    ${mount_point}    ${node_name}
    RETURN    ${result}

Switch dm device to error mode
    [Documentation]    Switch the dm device to the error target to simulate disk I/O errors.
    [Arguments]    ${dm_device_name}    ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    switch_dm_device_to_error    ${dm_device_name}    ${dm_sectors}    ${node_name}

Switch dm device to linear mode
    [Documentation]    Switch the dm device to linear mode
    [Arguments]    ${dm_device_name}    ${node_id}    ${block_device_path}
    ${node_name} =    get_node_by_index    ${node_id}
    switch_dm_device_to_linear    ${dm_device_name}    ${block_device_path}    ${dm_sectors}    ${node_name}

Force unmount dm disk at ${mount_point} on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    force_unmount_dm_device    ${mount_point}    ${node_name}

Cleanup dm disk ${dm_device_name} on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    cleanup_dm_device    ${dm_device_name}    ${node_name}

Wipe block device ${block_device_path} on node ${node_id}
    [Documentation]    Wipe filesystem and partition signatures from a block device.
    ${node_name} =    get_node_by_index    ${node_id}
    wipe_block_device_signatures    ${block_device_path}    ${node_name}

Start fsync writer on ${workload_kind} ${workload_id}
    [Documentation]    Start a background fsync writer that tracks max per-write latency in memory.
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${pod_name} =    get_workload_pod_name    ${workload_name}
    start_fsync_writer    ${pod_name}

Assert no IO stall greater than ${threshold_sec} seconds
    assert_no_io_stall    ${threshold_sec}
