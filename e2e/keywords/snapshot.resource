*** Settings ***
Documentation    Snapshot Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/snapshot_keywords.py

*** Keywords ***
Create snapshot ${snapshot_id} of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_snapshot    ${volume_name}    ${snapshot_id}

Delete snapshot ${snapshot_id} of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_snapshot    ${volume_name}    ${snapshot_id}

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
