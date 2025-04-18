*** Settings ***
Documentation       Orphan keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/orphan_keywords.py

*** Variables ***

*** Keywords ***
Create orphan replica for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    create_orphaned_replica_for_volume    ${volume_name}

Wait for orphan count to be ${orphan_count}
    wait_for_orphan_count    ${orphan_count}

Cleanup orphans
    delete_orphans
