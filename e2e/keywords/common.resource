*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/node_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/recurring_job_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/network_keywords.py


*** Variables ***


*** Keywords ***
Set test environment
    init_k8s_api_client
    init_node_exec    ${SUITE NAME.rsplit('.')[1]}
    init_storageclasses
    @{volume_list} =    Create List
    Set Test Variable    ${volume_list}
    @{deployment_list} =    Create List
    Set Test Variable    ${deployment_list}
    @{statefulset_list} =    Create List
    Set Test Variable    ${statefulset_list}
    setup_control_plane_network_latency

Cleanup test resources
    cleanup_control_plane_network_latency
    cleanup_node_exec
    cleanup_stress_helper
    cleanup_recurring_jobs    ${volume_list}
    cleanup_volumes    ${volume_list}
    cleanup_deployments    ${deployment_list}
    cleanup_statefulsets    ${statefulset_list}
    cleanup_storageclasses
