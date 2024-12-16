*** Settings ***
Documentation       Common keywords

Library             Collections
Library             OperatingSystem
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
Set up v2 environment
    update_setting    v2-data-engine    true
    ${worker_nodes}=    get_worker_nodes
    ${host_provider}=    Get Environment Variable    HOST_PROVIDER
    ${disk_path}=    Set Variable If    "${host_provider}" == "harvester"    /dev/vdc    /dev/xvdh
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    block-disk    ${worker_node}    block    ${disk_path}
    END

Set test environment
    init_k8s_api_client
    setup_control_plane_network_latency
    set_backupstore
    set_up_v2_environment

Cleanup test resources
    FOR    ${powered_off_node}    IN    @{powered_off_nodes}
        Run keyword And Ignore Error    power_on_node_by_name    ${powered_off_node}
        Remove Values From List    ${powered_off_nodes}    ${powered_off_node}
    END
    uncordon_all_nodes
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
    cleanup_engine_images
    reset_backupstore
    reset_settings
