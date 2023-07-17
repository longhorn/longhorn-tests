*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/node_keywords.py
Library             ../libs/keywords/volume_keywords.py
Resource            ../keywords/volume.resource


*** Variables ***
${retry_timeout_second}=    600
${retry_interval}=          5


*** Keywords ***
Data should be intact
    Run keyword And Continue On Failure    Volume ${volume_name} data checksum should be ${volume_data_checksum}

Teardown
    Cleanup resource and resume state
    Run Keyword If Test Failed    generate_support_bundle    ${TEST NAME}

Cleanup resource and resume state
    Clean up resources executed on the node
    Restore all nodes state
    Clean up all Longhorn resources

Clean up resources executed on the node
    Run keyword And Continue On Failure    cleanup_resources_on_node

Restore all nodes state
    Run keyword And Continue On Failure    restore_node_state

Clean up all Longhorn resources
    Run keyword And Continue On Failure    cleanup_resources
