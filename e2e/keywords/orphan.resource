*** Settings ***
Documentation       Orphan keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/orphan_keywords.py
Library             ../libs/keywords/instancemanager_keywords.py

*** Keywords ***
Create ${engine_type} orphaned replica for volume ${volume_id} on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${orphaned_replica_name} =    create_orphaned_replica    ${node_name}    ${volume_name}    ${engine_type}
    [Return]    ${orphaned_replica_name}

Wait for orphan count to be ${orphan_count}
    wait_for_orphan_count    ${orphan_count}

Cleanup orphans
    delete_orphans
