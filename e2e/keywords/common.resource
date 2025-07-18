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
Library             ../libs/keywords/orphan_keywords.py
Library             ../libs/keywords/backing_image_keywords.py
Library             ../libs/keywords/engine_image_keywords.py
Library             ../libs/keywords/setting_keywords.py
Library             ../libs/keywords/backupstore_keywords.py
Library             ../libs/keywords/backup_keywords.py
Library             ../libs/keywords/system_backup_keywords.py
Library             ../libs/keywords/sharemanager_keywords.py
Library             ../libs/keywords/k8s_keywords.py
Library             ../libs/keywords/secret_keywords.py
Library             ../libs/keywords/csi_volume_snapshot_keywords.py

*** Keywords ***
Test should pass
    No Operation

Set disk path based on host provider and architecture
    ${HOST_PROVIDER}=    Get Environment Variable    HOST_PROVIDER    vagrant
    ${ARCH}=    Get Environment Variable    ARCH    amd64
    IF    "${HOST_PROVIDER}" == "aws"
        IF    "${ARCH}" == "amd64"
            Set Test Variable    ${DISK_PATH}    /dev/xvdh
        ELSE IF    "${ARCH}" == "arm64"
            Set Test Variable    ${DISK_PATH}    /dev/nvme1n1
        END
    ELSE IF    '${HOST_PROVIDER}' == "harvester"
        Set Test Variable    ${DISK_PATH}    /dev/vdc
    ELSE IF    '${HOST_PROVIDER}' == "vagrant"
        Set Test Variable    ${DISK_PATH}    /dev/vdb
    END

Enable v2 data engine and add block disks
    ${V2_DATA_ENGINE_ENABLED}=    get_setting    v2-data-engine
    # if it's already configured, no need to do it again
    Return From Keyword If    "${V2_DATA_ENGINE_ENABLED}" == "true"
    set_disk_path_based_on_host_provider_and_architecture
    update_setting    v2-data-engine    true
    ${worker_nodes}=    get_worker_nodes
    FOR    ${worker_node}    IN    @{worker_nodes}
        add_disk    block-disk    ${worker_node}    block    ${DISK_PATH}
    END

Set up test environment
    init_k8s_api_client
    setup_control_plane_network_latency
    set_backupstore
    IF     "${DATA_ENGINE}" == "v2"
        Enable v2 data engine and add block disks
    END

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
    set_storageclass_default_state    longhorn    ${True}
    cleanup_secrets
    cleanup_backups
    cleanup_system_backups
    cleanup_system_restores
    delete_orphans
    cleanup_backing_images
    cleanup_node_labels
    cleanup_disks
    cleanup_engine_images
    reset_backupstore
    reset_settings
    reset_node_tags
    reset_node_disks_tags
    cleanup_k8s_node_zone
    cleanup_csi_volume_snapshots
    cleanup_csi_volume_snapshot_classes
