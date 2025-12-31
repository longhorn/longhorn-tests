*** Settings ***
Documentation    Snapshot Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/snapshot_keywords.py
Library    ../libs/keywords/csi_volume_snapshot_keywords.py

*** Keywords ***
Create snapshot ${snapshot_id} of volume ${volume_id}
    ${snapshot_id}=  Convert To String  ${snapshot_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_snapshot    ${volume_name}    ${snapshot_id}

Create snapshot ${snapshot_id} for ${workload_kind} ${workload_id} volume
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    create_snapshot    ${volume_name}    ${snapshot_id}

Delete snapshot ${snapshot_id} of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_snapshot    ${volume_name}    ${snapshot_id}

Delete snapshot ${snapshot_id} CR of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_snapshot_cr    ${volume_name}    ${snapshot_id}

Delete snapshot ${snapshot_id} of volume ${volume_id} will fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run Keyword And Expect Error    *    delete_snapshot    ${volume_name}    ${snapshot_id}

Delete snapshot ${snapshot_id} of ${workload_kind} ${workload_id} volume
    ${snapshot_id}=  Convert To String  ${snapshot_id}
    ${workload_name}=   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    delete_snapshot    ${volume_name}    ${snapshot_id}

Revert volume ${volume_id} to snapshot ${snapshot_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    revert_snapshot    ${volume_name}    ${snapshot_id}

Purge volume ${volume_id} snapshot
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    purge_snapshot    ${volume_name}

Purge volume ${volume_id} snapshot should fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run Keyword And Expect Error    *    purge_snapshot    ${volume_name}

Validate snapshot ${parent_id} is parent of snapshot ${child_id} in volume ${volume_id} snapshot list
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    is_parent_of   ${volume_name}    ${parent_id}    ${child_id}

Validate snapshot ${parent_id} is parent of volume-head in volume ${volume_id} snapshot list
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    is_parent_of_volume_head   ${volume_name}    ${parent_id}

Validate snapshot ${snapshot_id} is marked as removed in volume ${volume_id} snapshot list
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    is_marked_as_removed    ${volume_name}    ${snapshot_id}

Validate snapshot ${snapshot_id} is not in volume ${volume_id} snapshot list
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    is_not_existing    ${volume_name}    ${snapshot_id}

Validate snapshot ${snapshot_id} is in volume ${volume_id} snapshot list
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    is_existing    ${volume_name}    ${snapshot_id}

Create snapshot ${snapshot_id} of volume ${volume_id} will fail
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run Keyword And Expect Error    *    create_snapshot    ${volume_name}    ${snapshot_id}    waiting=False

Create ${snapshot_count} snapshot for volume ${volume_id}
    FOR    ${i}    IN RANGE    ${snapshot_count}
        Create snapshot ${i} of volume ${volume_id}
    END

Validate snapshot ${snapshot_id} checksum of volume ${volume_id} is skipped for ${timeout} seconds
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    FOR    ${i}    IN RANGE    ${timeout}
        ${checksum} =    get_checksum    ${volume_name}    ${snapshot_id}
        Run Keyword If    '${checksum}' != ''    Fail    Snapshot ${snapshot_id} checksum should be skipped but was calculated at ${i} seconds.
        Sleep    1
    END

Wait for volume ${volume_id} snapshot ${snapshot_id} checksum to be calculated
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_snapshot_checksum_to_be_created    ${volume_name}    ${snapshot_id}

Longhorn snapshot associated with csi volume snapshot ${csi_volume_snapshot_id} of ${workload_kind} ${workload_id} should be created
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${csi_volume_snapshot_id}
    ${longhorn_snapshot_name} =    get_longhorn_snapshot_name_associated_with_csi_volume_snapshot    ${csi_volume_snapshot_name}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_snapshot_to_be_created    ${volume_name}    ${longhorn_snapshot_name}

Longhorn snapshot associated with csi volume snapshot ${csi_volume_snapshot_id} of ${workload_kind} ${workload_id} should be deleted
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${csi_volume_snapshot_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_snapshot_to_be_deleted    ${volume_name}    ${longhorn_snapshot_name}

Longhorn snapshot associated with csi volume snapshot ${csi_volume_snapshot_id} of ${workload_kind} ${workload_id} should still exist
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${csi_volume_snapshot_id}
    ${workload_name} =   generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    wait_for_snapshot_to_be_created    ${volume_name}    ${longhorn_snapshot_name}
