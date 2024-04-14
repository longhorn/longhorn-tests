*** Settings ***
Documentation    Volume Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}    2    3

Create volume ${volume_id} with frontend ${frontend_name}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}    2    3    ${frontend_name}

No volume created
    ${volumes} =    list_volumes
    Should Be True    len(${volumes}) == 0

Validate volume ${volume_id} replicas anti-affinity
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_volume_replicas_anti_affinity    ${volume_name}

Create volume ${volume_id} with ${size} GB and ${replica_count} replicas
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_volume   ${volume_name}    ${size}    ${replica_count}

Update volume ${volume_name} replica count to ${replica_count}
    update_volume_spec   ${volume_name}    numberOfReplicas    3

Attach volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    attach_volume    ${volume_name}

Detach volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    detach_volume    ${volume_name}

Delete volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_volume    ${volume_name}

Write data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    write_volume_random_data   ${volume_name}    2048

Keep writing data to volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    keep_writing_data    ${volume_name}

Delete volume ${volume_id} replica on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_replica_on_node    ${volume_name}    ${replica_locality}

Wait for volume ${volume_id} healthy
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_volume_healthy    ${volume_name}

Wait until volume ${volume_id} replica rebuilding started on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_start_on_node    ${volume_name}    ${replica_locality}

Wait until volume ${volume_id} replica rebuilding completed on ${replica_locality}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_complete_on_node    ${volume_name}    ${replica_locality}

Wait until volume ${volume_id} replicas rebuilding completed
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_replica_rebuilding_to_complete   ${volume_name}

Check volume ${volume_id} data is intact
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    check_data_checksum    ${volume_name}

Check volume ${volume_id} works
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${volume_data_checksum} =     write_volume_random_data   ${volume_name}    1024
    #TODO
    # write data to a file in the volume instead of writing /dev/longhorn/vol-name
    # so the data won't be overwritten and we can compare the checksum
