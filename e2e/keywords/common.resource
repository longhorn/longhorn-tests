*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/recurring_job_keywords.py


*** Variables ***


*** Keywords ***
Set test environment
    init_k8s_api_client
    init_node_exec    ${TEST NAME}
    @{volume_list} =    Create List
    Set Test Variable    ${volume_list}

Cleanup test resources
    cleanup_node_exec
    cleanup_recurring_jobs    ${volume_list}
    cleanup_volumes    ${volume_list}
