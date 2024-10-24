*** Settings ***
Documentation    Volume Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/backup_keywords.py

*** Keywords ***
Create volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}

Create volume ${volume_id} with
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}    &{config}

Create DR volume ${volume_id} from backup ${backup_id}
    [Arguments]    &{config}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url} =    get_backup_url    ${backup_id}
    create_volume   ${volume_name}    frontend=    Standby=True    fromBackup=${backup_url}    &{config}

Create volume ${volume_id} from ${workload_kind} ${workload_id} volume backup ${backup_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name}=    get_workload_volume_name    ${workload_name}
    ${volume_name}=    generate_name_with_suffix    volume    ${volume_id}
    ${backup_url}=    get_backup_url    ${backup_id}    ${workload_volume_name}
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

Attach volume ${volume_id} to node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    attach_volume    ${volume_name}    ${node_name}

Attach volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume    ${volume_name}

Attach volume ${volume_id} to ${workload_kind} ${workload_id} node
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${workload_volume_name} =    get_workload_volume_name    ${workload_name}
    ${node_name} =    get_volume_node    ${workload_volume_name}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume    ${volume_name}    ${node_name}

Attach volume ${volume_id} in maintenance mode
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume_in_maintenance_mode    ${volume_name}

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
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_volume    ${volume_name}

Write data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    write_volume_random_data   ${volume_name}    2048

Write ${size} GB data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    write_volume_random_data   ${volume_name}    ${${size} * 1024}

Write data ${data_id} to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    write_volume_random_data   ${volume_name}    2048    ${data_id}

Write data ${data_id} ${size} MB to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    write_volume_random_data   ${volume_name}    ${size}    ${data_id}

Keep writing data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    keep_writing_data    ${volume_name}

Delete volume ${volume_id} replica on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_replica_on_node    ${volume_name}    ${replica_locality}

Wait for volume ${volume_id} healthy
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_healthy    ${volume_name}

Wait for volume ${volume_id} attached
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_attached    ${volume_name}

Wait for volume ${volume_id} attached and unknown
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_unknown    ${volume_name}

Wait for volume ${volume_id} detached
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_detached    ${volume_name}

Wait for volume ${volume_id} faulted
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_faulted    ${volume_name}

Wait for volume ${volume_id} degraded
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_degraded    ${volume_name}

Check volume ${volume_id} replica on node ${node_id} kept in stopped
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        wait_for_replica_stopped    ${volume_name}    ${node_name}
        Sleep    ${RETRY_INTERVAL}
    END

Check for volume ${volume_id} kept in degraded
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        wait_for_volume_degraded    ${volume_name}
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

Wait for volume ${volume_id} migration ready
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_migration_ready    ${volume_name}

Wait for volume ${volume_id} migrated to node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_volume_migration_completed    ${volume_name}    ${node_name}

Wait for volume ${volume_id} restoration from backup ${backup_id} completed
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${backup_name} =    get_backup_name    ${backup_id}
    wait_for_volume_restoration_completed    ${volume_name}    ${backup_name}

Wait until volume ${volume_id} replica rebuilding started on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_start_on_node    ${volume_name}    ${replica_locality}

Wait until volume ${volume_id} replica rebuilding completed on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_complete_on_node    ${volume_name}    ${replica_locality}

Wait until volume ${volume_id} replicas rebuilding completed
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

Crash volume ${volume_id} replica processes
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    crash_replica_processes    ${volume_name}

Crash volume ${volume_id} replica process on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${crashed_replica_name} =     crash_node_replica_process    ${volume_name}    ${node_name}
    Set Test Variable    ${crashed_replica_name}

Check volume ${volume_id} crashed replica reused on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${current_replica_name} =     get_replica_name_on_node    ${volume_name}    ${node_name}
    Should Be Equal    ${crashed_replica_name}    ${current_replica_name}

Wait volume ${volume_id} replica on node ${node_id} stopped
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_replica_stopped    ${volume_name}    ${node_name}

Check volume ${volume_id} replica on node ${node_id} exist
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${replica_name}    get_replica_name_on_node    ${volume_name}    ${node_name}
    Should Not Be Equal    ${replica_name}    ${None}

Check volume ${volume_id} data is intact
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    check_data_checksum    ${volume_name}

Check volume ${volume_id} data is data ${data_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    check_data_checksum    ${volume_name}    ${data_id}

Check volume ${volume_id} works
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${volume_data_checksum} =     write_volume_random_data   ${volume_name}    1024
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
    Create volume ${volume_id} with    size=${size}Gi    numberOfReplicas=3
    Attach volume ${volume_id} to node 1
    Wait for volume ${volume_id} healthy
    Update volume ${volume_id} replica count to 2
    Delete volume ${volume_id} replica on volume node

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
    wait_for_volume_restoration_completed    ${volume_name}    ${backup_name}

Volume ${volume_id} setting ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_volume_setting    ${volume_name}    ${setting_name}    ${setting_value}
