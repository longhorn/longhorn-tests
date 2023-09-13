*** Settings ***
Documentation    Volume Keywords

Library    Collections
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/common_keywords.py

*** Keywords ***
Create a volume with ${size} GB and ${replica_count} replicas
    ${volume_name} =    create_volume   ${size}    ${replica_count}
    attach_volume    ${volume_name}
    Set Test Variable    ${volume_name}
    Append To List    ${volume_list}    ${volume_name}

Create volume ${idx} with ${size} GB and ${replica_count} replicas
    ${volume_name} =    create_volume   ${size}    ${replica_count}
    attach_volume    ${volume_name}
    Insert Into List    ${volume_list}    ${idx}    ${volume_name}

Write data to the volume
    ${volume_data_checksum} =     write_volume_random_data   ${volume_name}    2048
    Set Test Variable    ${volume_data_checksum}

Keep writing data to volume ${idx}
    keep_writing_data    ${volume_list}[${idx}]

Delete replica on replica node to trigger replica rebuilding
    ${replica_node} =    get_replica_node    ${volume_name}
    delete_replica    ${volume_name}    ${replica_node}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_node}

Delete replica on volume node to trigger replica rebuilding
    ${volume_node} =    get_volume_node    ${volume_name}
    delete_replica    ${volume_name}    ${volume_node}
    wait_for_replica_rebuilding_start    ${volume_name}    ${volume_node}

Delete replica ${replica_0} to trigger replica ${replica_0} rebuilding
    delete_replica    ${volume_name}    ${replica_0}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}

During replica ${replica_0} rebuilding, delete replica ${replica_1}
    wait_for_replica_rebuilding_start    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_1}

Wait until replica ${replica_0} rebuilt, delete replica ${replica_2}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_2}

Wait until replica ${replica_0} rebuilt, delete replica ${replica_2}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${replica_0}
    delete_replica    ${volume_name}    ${replica_2}

Check data is intact
    check_data    ${volume_name}    ${volume_data_checksum}

Check volume ${idx} works
    ${volume_data_checksum} =     write_volume_random_data   ${volume_list}[${idx}]    1024
    #TODO
    # write data to a file in the volume instead of writing /dev/longhorn/vol-name
    # so the data won't be overwritten and we can compare the checksum

Wait until all replicas rebuilt
    wait_for_replica_rebuilding_complete    ${volume_name}    0
    wait_for_replica_rebuilding_complete    ${volume_name}    1
    wait_for_replica_rebuilding_complete    ${volume_name}    2

Wait until replica on volume node rebuilt
    ${node_name} =    get_volume_node    ${volume_name}
    wait_for_replica_rebuilding_start    ${volume_name}    ${node_name}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${node_name}

Wait until replica on replica node rebuilt
    ${node_name} =    get_replica_node    ${volume_name}
    wait_for_replica_rebuilding_start    ${volume_name}    ${node_name}
    wait_for_replica_rebuilding_complete    ${volume_name}    ${node_name}
