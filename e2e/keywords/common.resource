*** Settings ***
Documentation       Common keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/deployment_keywords.py
Library             ../libs/keywords/network_keywords.py
Library             ../libs/keywords/recurringjob_keywords.py
Library             ../libs/keywords/statefulset_keywords.py
Library             ../libs/keywords/stress_keywords.py
Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/workload_keywords.py

*** Keywords ***
Set test environment
    init_k8s_api_client
    init_node_exec    ${SUITE NAME.rsplit('.')[1]}
    init_storageclasses

    setup_control_plane_network_latency

Cleanup test resources
    cleanup_control_plane_network_latency
    cleanup_node_exec
    cleanup_stress_helper
    cleanup_recurringjobs
    cleanup_deployments
    cleanup_statefulsets
    cleanup_persistentvolumeclaims
    cleanup_volumes
    cleanup_storageclasses

Set ${setting_name} to ${setting_value}
    change_setting    ${setting_name}    ${setting_value}
