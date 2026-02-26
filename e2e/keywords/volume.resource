*** Settings ***
Documentation    Volume Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/backup_keywords.py

*** Keywords ***
Create volume ${volume_id}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}    &{config}

Create volume ${volume_id} with
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}    &{config}

Create DR volume ${volume_id} from backup ${backup_id} of volume ${source_volume_id}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${source_volume_name} =    generate_name_with_suffix    volume    ${source_volume_id}
    ${backup_url} =    get_backup_url    ${backup_id}    ${source_volume_name}
    create_volume   ${volume_name}    frontend=    Standby=True    fromBackup=${backup_url}    &{config}

Create DR volume ${volume_id} from backup ${backup_name}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url} =    get_backup_url    ${backup_name}
    create_volume   ${volume_name}    frontend=    Standby=True    fromBackup=${backup_url}    &{config}

Create DR volume ${target_volume_id} from backup ${backup_id} of ${workload_kind} ${workload_id} volume
    [Arguments]    &{config}
    ${target_volume_name} =    generate_name_with_suffix    volume    ${target_volume_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${backup_url} =    get_backup_url    ${backup_id}    ${volume_name}
    create_volume   ${target_volume_name}    frontend=    Standby=True    fromBackup=${backup_url}    &{config}

Create volume ${target_volume_id} from backup ${backup_id} of volume ${source_volume_id}
    [Arguments]    &{config}
    ${target_volume_name} =    generate_name_with_suffix    volume    ${target_volume_id}
    ${source_volume_name} =    generate_name_with_suffix    volume    ${source_volume_id}
    ${backup_url} =    get_backup_url    ${backup_id}    ${source_volume_name}
    create_volume   ${target_volume_name}    numberOfReplicas=3    fromBackup=${backup_url}    &{config}

Create volume ${volume_id} from ${workload_kind} ${workload_id} volume backup ${backup_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name}=    get_workload_volume_name    ${workload_name}
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url}=    get_backup_url    ${backup_id}    ${workload_volume_name}
    create_volume   ${volume_name}    size=3Gi    numberOfReplicas=3    fromBackup=${backup_url}

Create volume ${volume_id} from ${workload_kind} ${workload_id} volume latest backup
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name}=    get_workload_volume_name    ${workload_name}
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url}=    get_latest_backup_url    ${workload_volume_name}
    create_volume   ${volume_name}    size=3Gi    numberOfReplicas=3    fromBackup=${backup_url}

No volume created
    ${volumes} =    list_volumes
    Should Be True    len(${volumes}) == 0

Validate volume ${volume_id} replicas anti-affinity
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_volume_replicas_anti_affinity    ${volume_name}

Update volume ${volume_id} replica count to ${replica_count}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    update_volume_spec   ${volume_name}    numberOfReplicas    ${replica_count}

Update volume ${volume_id} rebuild concurrent sync limit to ${limit}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    update_volume_spec   ${volume_name}    rebuildConcurrentSyncLimit    ${limit}

Attach volume ${volume_id} to node ${node_id}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    attach_volume    ${volume_name}    ${node_name}    &{config}

Volume ${volume_id} should be attached to node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${res} =    is_attached_to    ${volume_name}    ${node_name}
    Should Be True    ${res}

Attach volume ${volume_id}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume    ${volume_name}    &{config}

Attach volume ${volume_id} to ${workload_kind} ${workload_id} node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${workload_volume_name}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume    ${volume_name}    ${node_name}

Attach volume ${volume_id} to node ${node_id} should fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    Run Keyword And Expect Error    *    attach_volume    ${volume_name}    ${node_name}    wait=False    retry=False

Attach volume ${volume_id} in maintenance mode
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume_in_maintenance_mode    ${volume_name}

Attach volume ${volume_id} to healthy node
    ${volume_name}=  generate_name_with_suffix  volume  ${volume_id}
    ${healthy_node_names}=  Get healthy node names

    Run Keyword If    ${healthy_node_names} == []
    ...    Fail    No healthy nodes available to attach volume!

    ${healthy_node_name}=  Get From List  ${healthy_node_names}  0
    Log    Attaching volume ${volume_id} to node ${healthy_node_name}
    attach_volume  ${volume_name}  ${healthy_node_name}

Detach volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    detach_volume    ${volume_name}

Detach volume ${volume_id} from node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    detach_volume    ${volume_name}    ${node_name}

Detach volume ${volume_id} from attached node
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    detach_volume    ${volume_name}    ${node_name}

Delete volume ${volume_id}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_volume    ${volume_name}    &{config}

Write data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${checksum} =    write_volume_random_data   ${volume_name}    2048
    Set To Dictionary    ${volume_checksums}    ${volume_id}    ${checksum}

Write ${size} GB data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${checksum} =    write_volume_random_data   ${volume_name}    ${${size} * 1024}
    Set To Dictionary    ${volume_checksums}    ${volume_id}    ${checksum}

Write ${size} Mi data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${checksum} =    write_volume_random_data   ${volume_name}    ${size}
    Set To Dictionary    ${volume_checksums}    ${volume_id}    ${checksum}

Write data ${data_id} to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${checksum} =    write_volume_random_data   ${volume_name}    2048    ${data_id}
    Set To Dictionary    ${volume_checksums}    ${volume_id}    ${checksum}

Write data ${data_id} ${size} MB to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${checksum} =    write_volume_random_data   ${volume_name}    ${size}    ${data_id}
    Set To Dictionary    ${volume_checksums}    ${volume_id}    ${checksum}

Keep writing data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    keep_writing_data    ${volume_name}

Write scattered data to volume ${volume_id} with fio
    [Arguments]    ${size}=2G    ${bs}=4k    ${ratio}=0.2
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    write_volume_scattered_data_with_fio    ${volume_name}    ${size}    ${bs}    ${ratio}

Prefill volume ${volume_id} with fio
    [Arguments]    ${size}=2G
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    prefill_volume_with_fio    ${volume_name}    ${size}

Delete volume ${volume_id} replica on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_replica_on_node    ${volume_name}    ${replica_locality}

Delete volume ${volume_id} replica on all ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_replica_on_nodes    ${volume_name}    ${replica_locality}

Delete ${count} replicas of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_replicas    ${volume_name}    ${count}

Wait for volume ${volume_id} to be created
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_to_be_created    ${volume_name}

Wait for volume ${volume_id} healthy
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_healthy    ${volume_name}

Wait for volume ${volume_id} attached
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_attached    ${volume_name}

Wait for volume ${volume_id} unknown
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_unknown    ${volume_name}

Wait for volume ${volume_id} attached and unknown
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_attached    ${volume_name}
    wait_for_volume_unknown    ${volume_name}

Wait for volume ${volume_id} detached
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_detached    ${volume_name}

Wait for volume ${volume_id} deleted
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_deleted    ${volume_name}

Assert volume ${volume_id} remains detached for at least ${period} seconds
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${period}
        wait_for_volume_detached    ${volume_name}
        Sleep    1
    END

Assert volume ${volume_id} remains attached for at least ${period} seconds
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${period}
        wait_for_volume_attached    ${volume_name}
        Sleep    1
    END

Wait for volume ${volume_id} faulted
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_faulted    ${volume_name}

Wait for volume ${volume_id} degraded
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_degraded    ${volume_name}

Wait for volume ${volume_id} condition ${condition_name} to be ${condition_status}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_condition    ${volume_name}    ${condition_name}    ${condition_status}    &{config}

Wait for volume ${volume_id} cloning to complete
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_clone_status_completed    ${volume_name}

Check volume ${volume_id} replica on node ${node_id} kept in stopped
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    FOR    ${i}    IN RANGE    ${VOLUME_STATE_CHECK_TIMEOUT}
        wait_for_replica_stopped    ${volume_name}    ${node_name}
        Sleep    ${RETRY_INTERVAL}
    END

Check volume ${volume_id} kept in degraded
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${VOLUME_STATE_CHECK_TIMEOUT}
        wait_for_volume_degraded    ${volume_name}
        Sleep    ${RETRY_INTERVAL}
    END

Check volume ${volume_id} kept in attaching
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${VOLUME_STATE_CHECK_TIMEOUT}
        wait_for_volume_attaching    ${volume_name}
        Sleep    ${RETRY_INTERVAL}
    END

Check volume ${volume_id} kept in detached
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        wait_for_volume_detached    ${volume_name}
        Sleep    ${RETRY_INTERVAL}
    END

Check all replicas of volume ${volume_id} kept in error
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        wait_for_volume_faulted    ${volume_name}
        Sleep    ${RETRY_INTERVAL}
    END

Wait for volume ${volume_id} migration to be ready
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_migration_to_be_ready    ${volume_name}

Wait for volume ${volume_id} to migrate to node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_volume_migration_complete    ${volume_name}    ${node_name}

Wait for volume ${volume_id} to stay on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_volume_migration_to_rollback    ${volume_name}    ${node_name}

Wait for volume ${volume_id} restoration to complete
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_restoration_to_complete    ${volume_name}

Wait for volume ${target_volume_id} restoration from backup ${backup_id} of ${workload_kind} ${workload_id} volume completed
    ${target_volume_name} =    generate_name_with_suffix    volume    ${target_volume_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${source_volume_name} =    get_workload_volume_name    ${workload_name}
    ${backup_name} =    get_backup_name    ${backup_id}    ${source_volume_name}
    wait_for_volume_restoration_to_complete    ${target_volume_name}    ${backup_name}

Wait for volume ${volume_id} restoration from backup ${backup_id} of volume ${source_volume_id} completed
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${source_volume_name} =    generate_name_with_suffix    volume    ${source_volume_id}
    ${backup_name} =    get_backup_name    ${backup_id}    ${source_volume_name}
    wait_for_volume_restoration_to_complete    ${volume_name}    ${backup_name}

Wait for volume ${volume_id} restoration from backup ${backup_name} to complete
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_restoration_to_complete    ${volume_name}    ${backup_name}

Wait for volume ${volume_id} restoration from backup ${backup_id} of volume ${source_volume_id} start
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${source_volume_name} =    generate_name_with_suffix    volume    ${source_volume_id}
    ${backup_name} =    get_backup_name    ${backup_id}    ${source_volume_name}
    wait_for_volume_restoration_start    ${volume_name}    ${backup_name}

Wait until volume ${volume_id} replica rebuilding started on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_start_on_node    ${volume_name}    ${replica_locality}

Wait until volume ${volume_id} replica rebuilding completed on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${rebuilding_time} =    wait_for_replica_rebuilding_to_complete_on_node    ${volume_name}    ${replica_locality}
    [Return]    ${rebuilding_time}

Wait until volume ${volume_id} replicas rebuilding completed
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_complete   ${volume_name}

Monitor only one replica rebuilding will start at a time for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_complete   ${volume_name}

Wait until volume ${volume_id} replica rebuilding stopped on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_stop_on_node    ${volume_name}    ${replica_locality}

Only one replica rebuilding on ${replica_locality} will start at a time, either for volume ${volume_id_0} or volume ${volume_id_1}
    ${volume_name_0} =    generate_name_with_suffix    volume    ${volume_id_0}
    ${volume_name_1} =    generate_name_with_suffix    volume    ${volume_id_1}
    only_one_replica_rebuilding_will_start_at_a_time_on_node    ${volume_name_0}    ${volume_name_1}    ${replica_locality}

Both volume ${volume_id_0} and volume ${volume_id_1} replica rebuilding on ${replica_locality} will start at the same time
    ${volume_name_0} =    generate_name_with_suffix    volume    ${volume_id_0}
    ${volume_name_1} =    generate_name_with_suffix    volume    ${volume_id_1}
    both_replica_rebuildings_will_start_at_the_same_time_on_node    ${volume_name_0}    ${volume_name_1}    ${replica_locality}

Only one replica rebuilding will start at a time for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    only_one_replica_rebuilding_will_start_at_a_time    ${volume_name}

Crash volume ${volume_id} replica processes
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    crash_replica_processes    ${volume_name}

Crash volume ${volume_id} replica process on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${original_replica_name} =     crash_node_replica_process    ${volume_name}    ${node_name}
    Set Test Variable    ${original_replica_name}

Record volume ${volume_id} replica name on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${original_replica_name} =     get_replica_name_on_node    ${volume_name}    ${node_name}
    Set Test Variable    ${original_replica_name}

Check volume ${volume_id} crashed replica reused on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${current_replica_name} =     get_replica_name_on_node    ${volume_name}    ${node_name}
    Should Be Equal    ${original_replica_name}    ${current_replica_name}

Wait volume ${volume_id} replica on node ${node_id} stopped
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_replica_stopped    ${volume_name}    ${node_name}

Check volume ${volume_id} replica on node ${node_id} exist
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${replica_name}    get_replica_name_on_node    ${volume_name}    ${node_name}
    Should Not Be Equal    ${replica_name}    ${None}

Wait for volume ${volume_id} replica on node ${node_id} to be deleted
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_replica_to_be_deleted    ${volume_name}    ${node_name}

Volume ${volume_id} should have ${expected_replica_count} running replicas
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    node_name=    replica_count=${expected_replica_count}

Volume ${volume_id} should have ${expected_replica_count} stopped replicas
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    replica_count=${expected_replica_count}    running=${False}

Volume ${volume_id} should have stopped replicas
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    running=${False}

Volume ${volume_id} should have ${expected_replica_count} replicas
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    node_name=    replica_count=${expected_replica_count}    running=${None}

Volume ${volume_id} should have ${expected_replica_count} replicas when detached
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    node_name=    replica_count=${expected_replica_count}    running=${False}

Volume ${volume_id} should have ${expected_replica_count} running replicas on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    node_name=${node_name}    replica_count=${expected_replica_count}
    Set Test Variable    ${volume_name}
    Set Test Variable    ${node_name}
    Set Test Variable    ${replica_count}

Volume ${volume_id} should have ${expected_replica_count} replicas on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    node_name=${node_name}    replica_count=${expected_replica_count}    running=${None}

Number of volume ${volume_id} replicas on node ${node_id_0} should be less than on node ${node_id_1}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name_0} =    get_node_by_index    ${node_id_0}
    ${node_name_1} =    get_node_by_index    ${node_id_1}
    ${replica_count_0} =    wait_for_replica_count    ${volume_name}    node_name=${node_name_0}
    ${replica_count_1} =    wait_for_replica_count    ${volume_name}    node_name=${node_name_1}
    IF    ${replica_count_0} >= ${replica_count_1}
        Log to console    Node ${node_id_0} has more replicas than node ${node_id_1}, ${replica_count_0} >= ${replica_count_1}
        Sleep    ${retry_count}
        Fail    Node ${node_id_0} has more replicas than node ${node_id_1}, ${replica_count_0} >= ${replica_count_1}
    END

Volume ${volume_id} should have running replicas on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${replica_count} =    wait_for_replica_count    ${volume_name}    node_name=${node_name}
    Set Test Variable    ${volume_name}
    Set Test Variable    ${node_name}
    Set Test Variable    ${replica_count}

Volume ${volume_id} should have ${expected_replica_count} running replicas on node ${node_id} and no additional scheduling occurs
    Volume ${volume_id} should have ${expected_replica_count} running replicas on node ${node_id}
    FOR    ${i}    IN RANGE    3
        Log to console    Ensuring there's no additional scheduling for node ${node_name} ... (${i})
        ${new_replica_count} =    wait_for_replica_count    ${volume_name}    node_name=${node_name}    replica_count=${expected_replica_count}
        IF    int(${replica_count}) != int(${new_replica_count})
            Log to console    Additional scheduling occurs: ${replica_count} != ${new_replica_count}
            Sleep    ${retry_count}
            Fail    Additional scheduling occurs: ${replica_count} != ${new_replica_count}
        END
        Sleep    5
    END

Volume ${volume_id} should have running replicas on node ${node_id} and no additional scheduling occurs
    Volume ${volume_id} should have running replicas on node ${node_id}
    FOR    ${i}    IN RANGE    3
        Log to console    Ensuring there's no additional scheduling for node ${node_name} ... (${i})
        ${new_replica_count} =    wait_for_replica_count    ${volume_name}    node_name=${node_name}
        IF     int(${replica_count}) != int(${new_replica_count})
            Log to console    Additional scheduling occurs: ${replica_count} != ${new_replica_count}
            Sleep    ${retry_count}
            Fail    Additional scheduling occurs: ${replica_count} != ${new_replica_count}
        END
        Sleep    5
    END

Check volume ${volume_id} data is intact
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${actual_checksum} =    get_volume_checksum    ${volume_name}
    ${expected_checksum} =    Get From Dictionary    ${volume_checksums}    ${volume_id}
    Should Be Equal    ${actual_checksum}    ${expected_checksum}

Check volume ${volume_id} data is data ${data_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    check_data_checksum    ${volume_name}    ${data_id}

Check volume ${volume_id} works
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${checksum} =     write_volume_random_data   ${volume_name}    1024
    Set To Dictionary    ${volume_checksums}    ${volume_id}    ${checksum}
    #TODO
    # write data to a file in the volume instead of writing /dev/longhorn/vol-name
    # so the data won't be overwritten and we can compare the checksum

Activate DR volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    activate_dr_volume    ${volume_name}

Create persistentvolume for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_persistentvolume_for_volume    ${volume_name}

Create persistentvolumeclaim for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_persistentvolumeclaim_for_volume    ${volume_name}

Create persistentvolume for volume ${volume_id} will fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run Keyword And Expect Error    *    create_persistentvolume_for_volume    ${volume_name}    retry=False

Create persistentvolumeclaim for volume ${volume_id} will fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run Keyword And Expect Error    *    create_persistentvolumeclaim_for_volume    ${volume_name}    retry=False

Create volume ${volume_id} with ${size} GB and no replicas on the attached node
    [Arguments]    &{config}
    Create volume ${volume_id} with    size=${size}Gi    numberOfReplicas=3    &{config}
    Attach volume ${volume_id} to node 1
    Wait for volume ${volume_id} healthy
    Update volume ${volume_id} replica count to 2
    Delete volume ${volume_id} replica on volume node

Create single replica volume ${volume_id} with replica on node ${node_id}
    [Arguments]    &{config}
    Create volume ${volume_id}    numberOfReplicas=3    &{config}
    Attach volume ${volume_id} to node ${node_id}
    Wait for volume ${volume_id} healthy
    Update volume ${volume_id} replica count to 1
    Delete volume ${volume_id} replica on all replica node
    Detach volume ${volume_id} from node ${node_id}
    Wait for volume ${volume_id} detached

Create volume ${volume_id} attached to node ${attach_node_id} with 2 replicas excluding node ${replica_excluding_node_id}
    [Arguments]    &{config}
    Create volume ${volume_id} with    &{config}
    Attach volume ${volume_id} to node ${attach_node_id}
    Wait for volume ${volume_id} healthy
    Update volume ${volume_id} replica count to 2
    Delete volume ${volume_id} replica on node ${replica_excluding_node_id}

Record volume ${volume_id} replica names
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    record_volume_replica_names    ${volume_name}

Check volume ${volume_id} replica names are as recorded
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    check_volume_replica_names_recorded    ${volume_name}

Upgrade volume ${volume_id} engine to compatible engine image
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    upgrade_engine_image    ${volume_name}    ${compatible_engine_image_name}
    wait_for_engine_image_upgrade_completed    ${volume_name}    ${compatible_engine_image_name}

Upgrade volume ${volume_id} engine to ${custom_engine_image}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    upgrade_engine_image    ${volume_name}    ${custom_engine_image}
    wait_for_engine_image_upgrade_completed    ${volume_name}    ${custom_engine_image}

Wait for volume ${volume_id} engine to be upgraded to ${custom_engine_image}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_engine_image_upgrade_completed    ${volume_name}    ${custom_engine_image}

Verify volume ${volume_id} is using engine image ${custom_engine_image}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_engine_image_upgrade_completed    ${volume_name}    ${custom_engine_image}

Upgrade v1 volumes engine to ${custom_engine_image}
    ${volume_names} =    list_volumes    dataEngine=v1
    FOR    ${volume_name}    IN    @{volume_names}
        upgrade_engine_image    ${volume_name}    ${custom_engine_image}
        wait_for_engine_image_upgrade_completed    ${volume_name}    ${custom_engine_image}
    END

Check volume ${volume_id} data is backup ${backup_id} created in another cluster
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${current_checksum} =    get_volume_checksum    ${volume_name}
    ${backup_data} =    get_backup_data_from_backup_list    ${backups_before_uninstall}    ${backup_id}
    Should Be Equal    ${current_checksum}    ${backup_data}

Create volume ${volume_id} from backup ${backup_id} in another cluster
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url} =    get_backup_url_from_backup_list    ${backups_before_uninstall}    ${backup_id}
    create_volume   ${volume_name}    fromBackup=${backup_url}

Create DR volume ${volume_id} from backup ${backup_id} in another cluster
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url} =    get_backup_url_from_backup_list    ${backups_before_uninstall}    ${backup_id}
    create_volume   ${volume_name}    frontend=    Standby=True    fromBackup=${backup_url}

Wait for volume ${volume_id} restoration from backup ${backup_id} in another cluster completed
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_name} =    get_backup_name_from_backup_list    ${backups_before_uninstall}    ${backup_id}
    wait_for_volume_restoration_to_complete    ${volume_name}    ${backup_name}

Volume ${volume_id} setting ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_volume_setting    ${volume_name}    ${setting_name}    ${setting_value}

DR volume ${volume_id} setting ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_volume_setting    ${volume_name}    ${setting_name}    ${setting_value}

Assert DM device for volume ${volume_id} ${condition} exist on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${dm_devices} =   list_dm_devices_on_node    ${node_name}
    IF   '${condition}' == 'does'
        Should Contain    ${dm_devices}    ${volume_name}
    ELSE IF   '${condition}' == 'not'
        Should Not Contain    ${dm_devices}    ${volume_name}
    ELSE
        Fail    Invalid condition: ${condition}
    END

Assert device for volume ${volume_id} ${condition} exist on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${devices} =   list_volume_devices_on_node    ${node_name}
    IF   '${condition}' == 'does'
        Should Contain    ${devices}    ${volume_name}
    ELSE IF   '${condition}' == 'not'
        Should Not Contain    ${devices}    ${volume_name}
    ELSE
        Fail    Invalid condition: ${condition}
    END

Enable volume ${volume_id} offline replica rebuilding
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    update_offline_replica_rebuild    ${volume_name}    enabled

Ignore volume ${volume_id} offline replica rebuilding
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    update_offline_replica_rebuild    ${volume_name}    ignored

Update volume ${volume_id} data locality to ${data_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    update_data_locality    ${volume_name}    ${data_locality}

Wait for volume ${volume_id} size to be ${size}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_expand_to_size    ${volume_name}    ${size}

Expand volume ${volume_id} to ${size}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    expand_volume    ${volume_name}    ${size}

Expand volume ${volume_id} to ${size} should fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run Keyword And Expect Error    *    expand_volume    ${volume_name}    ${size}
