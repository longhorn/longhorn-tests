*** Settings ***
Documentation    Workload Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/workload_keywords.py

*** Keywords ***
Keep writing data to pod of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    keep_writing_workload_pod_data    ${workload_name}

#TODO
# move node related keywords out of workload.resource
Power off volume node of ${workload_kind} ${workload_id} for ${duration} minutes
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    reboot_workload_volume_node    ${workload_name}    ${duration}

Reboot volume node of ${workload_kind} ${workload_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    reboot_workload_volume_node    ${workload_name}

Wait for volume of ${workload_kind} ${workload_id} healthy
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    wait_for_workload_volume_healthy    ${workload_name}

Wait until volume of ${workload_kind} ${workload_id} replica rebuidling started on ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_replica_rebuilding_to_complete_on_node    ${volume_name}    ${replica_locality}

Wait for volume of ${workload_kind} ${workload_id} attached and unknown
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_unknown    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attached and degraded
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_degraded    ${volume_name}

Wait for volume of ${workload_kind} ${workload_id} attached and healthy
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_volume_healthy    ${volume_name}

Delete replica of ${workload_kind} ${workload_id} volume on ${replica_locality}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    delete_replica_on_node    ${volume_name}    ${replica_locality}