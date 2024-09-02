*** Settings ***
Documentation       Longhorn engine related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/engine_keywords.py

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
