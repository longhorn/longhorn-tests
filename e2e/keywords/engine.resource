*** Settings ***
Documentation    Longhorn engine related keywords resources

Library    ../libs/steps.py

*** Keywords ***

Engine state should be ${expected_engine_state}
    Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Check engine state should be ${expected_engine_state}

Check engine state should be ${expected_engine_state}
    ${engine_current_state} =   get_engine_state   ${volume_name}   ${volume_attached_node}
    check_workload_state    ${engine_current_state}    ${expected_engine_state}

