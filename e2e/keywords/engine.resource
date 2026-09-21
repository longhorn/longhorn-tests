*** Settings ***
Documentation       Longhorn engine related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/engine_keywords.py
Library             ../libs/keywords/instancemanager_keywords.py

*** Keywords ***
Engine state should eventually be ${expected_engine_state}
    Run keyword And Continue On Failure
    ...    Wait Until Keyword Succeeds
    ...    ${retry_timeout_second} seconds
    ...    ${retry_interval} seconds
    ...    Engine state should be ${expected_engine_state}

Engine state should be ${expected_engine_state}
    ${engine_current_state} =    get_engine_state    ${volume_name}    ${volume_attached_node}
    check_workload_state    ${engine_current_state}    ${expected_engine_state}

Volume ${volume_id} engine ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_engine_setting    ${volume_name}    ${setting_name}    ${setting_value}

Inject stale stopped v1 engine process for volume ${volume_id} on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${engine_name} =    get_engine_name    ${volume_name}
    create_stale_stopped_engine_process    ${node_name}    ${engine_name}

Volume ${volume_id} engine process should exist on node ${node_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${engine_name} =    get_engine_name    ${volume_name}
    ${present} =    is_engine_process_present    ${node_name}    ${engine_name}
    Should Be True    ${present}    Engine process ${engine_name} should exist on node ${node_name}
