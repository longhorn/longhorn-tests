*** Settings ***
Documentation    Negative Test Cases

Library    ../libs/common.py

*** Test Cases ***
Replica Rebuilding With Replica Deletion
    Create a volume 5 GB with 3 replicas
    Write data to the volume
    FOR    ${i}    IN RANGE    200
        Delete replica 0 to trigger replica rebuilding
        During replica 0 rebuilding, delete replica 1
        Wait until replica 0 rebuilt, delete replica 2
        Check data is intact
    END

*** Keywords ***
Create a volume ${size} GB with ${replica_count} replicas
    ${volume_name} =    create_volume   ${size}    ${replica_count}
    Set Test Variable    ${volume_name}

Write data to the volume
    ${checksum} =     write_volume_random_data   ${volume_name}    2048
    Set Test Variable    ${checksum}

Delete replica ${replica_0} to trigger replica rebuilding
    delete_replica    ${volume_name}    ${replica_0}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}

During replica ${replica_0} rebuilding, delete replica ${replica_1}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_1}

Wait until replica ${replica_0} rebuilt, delete replica ${replica_2}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_2}

Check data is intact
    check_data    ${volume_name}    ${checksum}