*** Settings ***
Documentation    Common keywords resources

Library    ../libs/steps.py

Resource    ../keywords/volume.resource

*** Variable ***
${retry_timeout_second}=    600
${retry_interval}=    5

*** Keywords ***
Data should be intact
    Run keyword And Continue On Failure    Wait Until Keyword Succeeds    ${retry_timeout_second} seconds    ${retry_interval} seconds    Volume ${volume_name} data checksum should be ${volume_data_checksum}

Wait ${time_interval} seconds
    wait_with_time_interval    ${time_interval}

Teardown
    Run Keyword If Test Failed    generate_support_bundle    ${TEST NAME}
    cleanup_resources
