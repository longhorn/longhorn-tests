*** Settings ***
Documentation       Migration Keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/engine_keywords.py
Library             ../libs/keywords/replica_keywords.py

*** Keywords ***
Get volume ${volume_id} engine name
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${engine_name} =    get_engine_name    ${volume_name}
    Set Test Variable    ${engine_name}

Volume ${volume_id} engine should be the same
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${new_engine_name} =    get_engine_name    ${volume_name}
    Should Be Equal    ${engine_name}    ${new_engine_name}

Volume ${volume_id} engine should be different
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${new_engine_name} =    get_engine_name    ${volume_name}
    Should Not Be Equal    ${engine_name}    ${new_engine_name}

Get volume ${volume_id} replica names
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_names} =    get_replica_names    ${volume_name}
    Set Test Variable    ${replica_names}

Volume ${volume_id} replicas should be the same
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${new_replica_names} =    get_replica_names    ${volume_name}
    Should Be Equal As Strings    ${replica_names}    ${new_replica_names}

Volume ${volume_id} replicas should be different
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${new_replica_names} =    get_replica_names    ${volume_name}
    Should Not Be Equal As Strings    ${replica_names}    ${new_replica_names}

Get volume ${volume_id} engine and replica names
    Get volume ${volume_id} engine name
    Get volume ${volume_id} replica names

Volume ${volume_id} migration should fail or rollback
    Volume ${volume_id} engine should be the same
    Volume ${volume_id} replicas should be the same

Volume ${volume_id} migration should succeed
    Volume ${volume_id} engine should be different
    Volume ${volume_id} replicas should be different
