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
Library             ../libs/keywords/persistentvolumeclaim_keywords.py
Library             ../libs/keywords/network_keywords.py
Library             ../libs/keywords/storageclass_keywords.py
Library             ../libs/keywords/node_keywords.py
Library             ../libs/keywords/backing_image_keywords.py
Library             ../libs/keywords/setting_keywords.py
Library             ../libs/keywords/backupstore_keywords.py
Library             ../libs/keywords/backup_keywords.py
Library             ../libs/keywords/sharemanager_keywords.py

*** Keywords ***
Set test environment
    init_k8s_api_client
    init_node_exec    ${SUITE NAME.rsplit('.')[1]}

    setup_control_plane_network_latency
    set_backupstore

    update_setting    v2-data-engine    true
    ${worker_nodes}=    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    ${worker_node}    block    /dev/xvdh
    END

Cleanup test resources
    cleanup_control_plane_network_latency
    reset_node_schedule
    cleanup_node_exec
    cleanup_stress_helper
    cleanup_recurringjobs
    cleanup_deployments
    cleanup_statefulsets
    cleanup_pods
    cleanup_persistentvolumeclaims
    cleanup_volumes
    cleanup_storageclasses
    cleanup_backups
    cleanup_disks
    cleanup_backing_images
    reset_backupstore

Cleanup test resources include off nodes
    Power on off node
    Cleanup test resources

Convert GB to MB
    [Arguments]    ${size_in_gb}
    ${size_in_mb}=    Evaluate    ${size_in_gb} * 1024
    [Return]    ${size_in_mb}
