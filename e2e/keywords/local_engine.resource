*** Settings ***
Documentation    Local data engine keywords

Library    OperatingSystem
Library    Collections
Library    ../libs/keywords/local_engine_keywords.py
Resource    common.resource
Resource    deployment.resource
Resource    node.resource
Resource    persistentvolumeclaim.resource
Resource    setting.resource
Resource    storageclass.resource
Resource    volume.resource

*** Keywords ***
Set up local engine test
    Skip If    '${DATA_ENGINE}' != 'local'    Local-engine tests require DATA_ENGINE=local
    ${node_name}=    Get Environment Variable    LOCAL_ENGINE_NODE
    ${disk_path}=    Get Environment Variable    LOCAL_ENGINE_DISK_PATH
    ${second_disk_path}=    Get Environment Variable    LOCAL_ENGINE_SECOND_DISK_PATH    ${EMPTY}
    Set Suite Variable    ${LOCAL_ENGINE_NODE}    ${node_name}
    Set Suite Variable    ${LOCAL_ENGINE_DISK_PATH}    ${disk_path}
    Set Suite Variable    ${LOCAL_ENGINE_DISK_NAME}    local-engine-e2e
    Set Suite Variable    ${LOCAL_ENGINE_SECOND_DISK_PATH}    ${second_disk_path}
    Set Suite Variable    ${LOCAL_ENGINE_SECOND_DISK_NAME}    local-engine-e2e-second
    ${auto_delete_setting}=    get_setting    auto-delete-pod-when-volume-detached-unexpectedly
    Set Suite Variable    ${ORIGINAL_AUTO_DELETE_POD_SETTING}    ${auto_delete_setting}
    ${capacity_tracking_setting}=    get_setting    csi-storage-capacity-tracking
    Set Suite Variable    ${ORIGINAL_CAPACITY_TRACKING_SETTING}    ${capacity_tracking_setting}
    ${provisioning_mode}=    get_setting    local-data-engine-provisioning-mode
    Set Suite Variable    ${ORIGINAL_LOCAL_PROVISIONING_MODE}    ${provisioning_mode}
    ${storage_layout}=    get_setting    local-data-engine-storage-layout
    Set Suite Variable    ${ORIGINAL_LOCAL_STORAGE_LAYOUT}    ${storage_layout}
    ${local_data_engine_setting}=    get_setting    local-data-engine
    Set Suite Variable    ${ORIGINAL_LOCAL_DATA_ENGINE_SETTING}    ${local_data_engine_setting}
    Should Not Be Empty    ${node_name}    LOCAL_ENGINE_NODE must name the Kubernetes node used by the test
    Should Not Be Empty    ${disk_path}    LOCAL_ENGINE_DISK_PATH must identify a dedicated, disposable block device
    Clean up local engine test
    ${disk_names}=    Create List    ${LOCAL_ENGINE_DISK_NAME}
    ${disk_paths}=    Create List    ${LOCAL_ENGINE_DISK_PATH}
    IF    $second_disk_path
        Append To List    ${disk_names}    ${LOCAL_ENGINE_SECOND_DISK_NAME}
        Append To List    ${disk_paths}    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    END
    assert_local_engine_disk_paths_available
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${disk_names}
    ...    ${disk_paths}
    update_setting    local-data-engine    true

Clean up local engine suite
    Clean up local engine test
    ${local_data_engine_setting}=    Get Variable Value    \${ORIGINAL_LOCAL_DATA_ENGINE_SETTING}    ${NONE}
    IF    $local_data_engine_setting is not None
        Run Keyword And Ignore Error
        ...    update_setting
        ...    local-data-engine
        ...    ${local_data_engine_setting}
    END

Clean up local engine test
    Run Keyword And Ignore Error    cleanup_deployments
    Run Keyword And Ignore Error    cleanup_persistentvolumeclaims
    Run Keyword And Ignore Error    cleanup_volumes
    Run Keyword And Ignore Error    cleanup_storageclasses
    ${node_name}=    Get Variable Value    \${LOCAL_ENGINE_NODE}    ${NONE}
    IF    $node_name
        Run Keyword And Ignore Error    Remove second local engine test disk
        Run Keyword And Ignore Error    Remove local engine test disk
    END
    ${auto_delete_setting}=    Get Variable Value    \${ORIGINAL_AUTO_DELETE_POD_SETTING}    ${NONE}
    IF    $auto_delete_setting is not None
        Run Keyword And Ignore Error
        ...    update_setting
        ...    auto-delete-pod-when-volume-detached-unexpectedly
        ...    ${auto_delete_setting}
    END
    ${capacity_tracking_setting}=    Get Variable Value    \${ORIGINAL_CAPACITY_TRACKING_SETTING}    ${NONE}
    IF    $capacity_tracking_setting is not None
        Run Keyword And Ignore Error
        ...    update_setting
        ...    csi-storage-capacity-tracking
        ...    ${capacity_tracking_setting}
    END
    ${provisioning_mode}=    Get Variable Value    \${ORIGINAL_LOCAL_PROVISIONING_MODE}    ${NONE}
    IF    $provisioning_mode is not None
        Run Keyword And Ignore Error
        ...    update_setting
        ...    local-data-engine-provisioning-mode
        ...    ${provisioning_mode}
    END
    ${storage_layout}=    Get Variable Value    \${ORIGINAL_LOCAL_STORAGE_LAYOUT}    ${NONE}
    IF    $storage_layout is not None
        Run Keyword And Ignore Error
        ...    update_setting
        ...    local-data-engine-storage-layout
        ...    ${storage_layout}
    END

Use local engine provisioning mode
    [Arguments]    ${mode}
    update_setting    local-data-engine-provisioning-mode    ${mode}

Use local engine storage layout
    [Arguments]    ${layout}
    update_setting    local-data-engine-storage-layout    ${layout}

Add and verify local engine test disk
    add_disk
    ...    ${LOCAL_ENGINE_DISK_NAME}
    ...    ${LOCAL_ENGINE_NODE}
    ...    lvm
    ...    ${LOCAL_ENGINE_DISK_PATH}
    wait_for_local_engine_disk_ready
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    ...    ${LOCAL_ENGINE_DISK_PATH}
    wait_for_local_engine_disk_backend_initialized
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    ...    ${LOCAL_ENGINE_DISK_PATH}

Require second local engine test disk
    Skip If
    ...    not $LOCAL_ENGINE_SECOND_DISK_PATH
    ...    LOCAL_ENGINE_SECOND_DISK_PATH must identify a second dedicated, disposable block device
    Should Not Be Equal    ${LOCAL_ENGINE_DISK_PATH}    ${LOCAL_ENGINE_SECOND_DISK_PATH}

Add and verify independent local engine test disks
    Add and verify local engine test disk
    add_disk
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_NODE}
    ...    lvm
    ...    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    wait_for_local_engine_disk_ready
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    wait_for_local_engine_disk_backend_initialized
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    wait_for_local_engine_independent_disks
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    ...    ${LOCAL_ENGINE_DISK_PATH}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_SECOND_DISK_PATH}

Add and verify pooled local engine member disk
    ${initial_capacity}=    get_local_engine_disk_capacity
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    Should Be True    ${initial_capacity} > 0
    add_disk
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_NODE}
    ...    lvm
    ...    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    wait_for_local_engine_pooled_disks
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    ...    ${LOCAL_ENGINE_DISK_PATH}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    ...    ${initial_capacity}

Verify local engine storage layout change is rejected
    [Arguments]    ${layout}
    verify_local_engine_storage_layout_change_rejected    ${layout}

Verify local engine representative disk removal is rejected
    disable_disk    ${LOCAL_ENGINE_NODE}    ${LOCAL_ENGINE_DISK_NAME}
    verify_local_engine_representative_disk_removal_rejected
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}

Disable first local engine test disk scheduling
    disable_disk    ${LOCAL_ENGINE_NODE}    ${LOCAL_ENGINE_DISK_NAME}

Create local engine CSI workload
    Create storageclass longhorn-local-e2e with
    ...    dataEngine=local
    ...    numberOfReplicas=1
    ...    volumeBindingMode=WaitForFirstConsumer
    Create persistentvolumeclaim 0 without waiting for bound
    ...    sc_name=longhorn-local-e2e
    ...    storage_size=2Gi
    ${node_selector}=    Set Variable    {"kubernetes.io/hostname":"${LOCAL_ENGINE_NODE}"}
    Create deployment 0 with persistentvolumeclaim 0    node_selector=${node_selector}
    Wait for persistentvolumeclaim 0 status to be Bound
    Wait for volume of persistentvolumeclaim 0 healthy

Create local engine CSI workload with provisioning mode
    [Arguments]    ${mode}
    Create storageclass longhorn-local-e2e with
    ...    dataEngine=local
    ...    localProvisioningMode=${mode}
    ...    numberOfReplicas=1
    ...    volumeBindingMode=WaitForFirstConsumer
    Create persistentvolumeclaim 0 without waiting for bound
    ...    sc_name=longhorn-local-e2e
    ...    storage_size=2Gi
    ${node_selector}=    Set Variable    {"kubernetes.io/hostname":"${LOCAL_ENGINE_NODE}"}
    Create deployment 0 with persistentvolumeclaim 0    node_selector=${node_selector}
    Wait for persistentvolumeclaim 0 status to be Bound
    Wait for volume of persistentvolumeclaim 0 healthy

Create capacity-aware local engine CSI workload
    update_setting    csi-storage-capacity-tracking    true
    Wait Until Keyword Succeeds
    ...    2 min
    ...    2 sec
    ...    Check CSI Driver Storage Capacity
    ...    true
    Create storageclass longhorn-local-capacity-e2e with
    ...    dataEngine=local
    ...    numberOfReplicas=1
    ...    volumeBindingMode=WaitForFirstConsumer
    wait_for_local_engine_storage_capacity
    ...    longhorn-local-capacity-e2e
    ...    ${LOCAL_ENGINE_NODE}
    Create persistentvolumeclaim 0 without waiting for bound
    ...    sc_name=longhorn-local-capacity-e2e
    ...    storage_size=2Gi
    Create deployment 0 with persistentvolumeclaim 0
    Wait for persistentvolumeclaim 0 status to be Bound
    Wait for volume of persistentvolumeclaim 0 healthy
    Check deployment 0 pod is running on node ${LOCAL_ENGINE_NODE}

Verify local engine CSI workload backend
    ${claim_name}=    generate_name_with_suffix    claim    0
    ${volume_name}=    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    ${replica_name}=    wait_for_local_engine_volume_ready
    ...    ${volume_name}
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    Set Test Variable    ${LOCAL_ENGINE_VOLUME_NAME}    ${volume_name}
    Set Test Variable    ${LOCAL_ENGINE_REPLICA_NAME}    ${replica_name}
    Set Test Variable    ${LOCAL_ENGINE_VOLUME_DISK_NAME}    ${LOCAL_ENGINE_DISK_NAME}

Verify local engine CSI workload backend on second disk
    ${claim_name}=    generate_name_with_suffix    claim    0
    ${volume_name}=    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    ${replica_name}=    wait_for_local_engine_volume_ready
    ...    ${volume_name}
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    Set Test Variable    ${LOCAL_ENGINE_VOLUME_NAME}    ${volume_name}
    Set Test Variable    ${LOCAL_ENGINE_REPLICA_NAME}    ${replica_name}
    Set Test Variable    ${LOCAL_ENGINE_VOLUME_DISK_NAME}    ${LOCAL_ENGINE_SECOND_DISK_NAME}

Expand local engine CSI workload to 3Gi
    Expand persistentvolumeclaim 0 size to 3Gi
    Wait for deployment 0 volume size expanded
    ${expected_size}=    convert_size_to_bytes    3Gi
    wait_for_local_engine_logical_volume_size
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    ...    ${LOCAL_ENGINE_REPLICA_NAME}
    ...    ${expected_size}
    # Some kubelets complete filesystem expansion only on the next mount.
    Scale down deployment 0 to detach volume
    Scale up deployment 0 to attach volume
    Wait for volume of persistentvolumeclaim 0 healthy
    ${deployment_name}=    generate_name_with_suffix    deployment    0
    wait_for_filesystem_size_in_workload    ${deployment_name}    ${expected_size}

Restart local instance manager during sustained I/O
    update_setting    auto-delete-pod-when-volume-detached-unexpectedly    true
    ${deployment_name}=    generate_name_with_suffix    deployment    0
    verify_local_instance_manager_restart_during_io
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${deployment_name}

Verify local engine capacity and I/O metrics
    ${deployment_name}=    generate_name_with_suffix    deployment    0
    verify_local_engine_capacity_and_io_metrics
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_VOLUME_DISK_NAME}
    ...    ${LOCAL_ENGINE_VOLUME_NAME}
    ...    ${deployment_name}

Verify local engine provisioning backend
    [Arguments]    ${mode}
    verify_local_engine_provisioning_mode
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_VOLUME_DISK_NAME}
    ...    ${LOCAL_ENGINE_VOLUME_NAME}
    ...    ${LOCAL_ENGINE_REPLICA_NAME}
    ...    ${mode}

Verify local engine thin pool is absent
    wait_for_local_engine_thin_pool_absent
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_VOLUME_DISK_NAME}

Delete local engine CSI workload and verify backend cleanup
    Delete deployment 0
    Delete persistentvolumeclaim 0
    wait_for_volume_deleted    ${LOCAL_ENGINE_VOLUME_NAME}
    wait_for_local_engine_logical_volume_deleted
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_VOLUME_DISK_NAME}
    ...    ${LOCAL_ENGINE_REPLICA_NAME}

Delete and verify local engine test disk
    Remove local engine test disk

Remove local engine test disk
    ${exists}=    local_engine_disk_exists
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_DISK_NAME}
    IF    $exists
        disable_disk    ${LOCAL_ENGINE_NODE}    ${LOCAL_ENGINE_DISK_NAME}
        delete_disk    ${LOCAL_ENGINE_DISK_NAME}    ${LOCAL_ENGINE_NODE}
    END
    wait_for_local_engine_disk_removed    ${LOCAL_ENGINE_NODE}    ${LOCAL_ENGINE_DISK_NAME}

Delete and verify independent local engine test disks
    Remove second local engine test disk
    Remove local engine test disk

Remove second local engine test disk
    ${exists}=    local_engine_disk_exists
    ...    ${LOCAL_ENGINE_NODE}
    ...    ${LOCAL_ENGINE_SECOND_DISK_NAME}
    IF    $exists
        disable_disk    ${LOCAL_ENGINE_NODE}    ${LOCAL_ENGINE_SECOND_DISK_NAME}
        delete_disk    ${LOCAL_ENGINE_SECOND_DISK_NAME}    ${LOCAL_ENGINE_NODE}
    END
    wait_for_local_engine_disk_removed    ${LOCAL_ENGINE_NODE}    ${LOCAL_ENGINE_SECOND_DISK_NAME}
