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
Library             ../libs/keywords/engine_image_keywords.py
Library             ../libs/keywords/setting_keywords.py
Library             ../libs/keywords/backupstore_keywords.py
Library             ../libs/keywords/backup_keywords.py
Library             ../libs/keywords/sharemanager_keywords.py
Library             ../libs/keywords/k8s_keywords.py

*** Keywords ***
Set test environment
    init_k8s_api_client

    setup_control_plane_network_latency
    set_backupstore

    update_setting    v2-data-engine    true
    ${worker_nodes}=    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    ${worker_node}    block    /dev/xvdh
    END

Cleanup test resources
    Run keyword And Ignore Error    power_on_node_by_name    ${powered_off_node}
    uncordon_all_nodes
    cleanup_control_plane_network_latency
    reset_node_schedule
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
    cleanup_engine_images
    reset_backupstore
