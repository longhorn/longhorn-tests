*** Settings ***
Documentation    Volume Keywords

Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create a volume ${size} GB with ${replica_count} replicas
    ${volume_name} =    create_volume   ${size}    ${replica_count}
    attach_volume    ${volume_name}
    Set Test Variable    ${volume_name}

Write data to the volume
    ${volume_data_checksum} =     write_volume_random_data   ${volume_name}    1024
    Set Test Variable    ${volume_data_checksum}

Delete replica ${replica_0} to trigger replica ${replica_0} rebuilding
    delete_replica    ${volume_name}    ${replica_0}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}

During replica ${replica_0} rebuilding, delete replica ${replica_1}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_1}

Wait until replica ${replica_0} rebuilt, delete replica ${replica_2}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_2}

Check data is intact
    check_data    ${volume_name}    ${volume_data_checksum}

Wait until all replicas rebuilt
    wait_for_replica_rebuilding_complete    ${volume_name}    0
    wait_for_replica_rebuilding_complete    ${volume_name}    1
    wait_for_replica_rebuilding_complete    ${volume_name}    2