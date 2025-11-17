*** Settings ***
Documentation       Longhorn Keywords

Library             ../libs/keywords/instancemanager_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/k8s_keywords.py
Library             ../libs/keywords/longhorn_deploy_keywords.py
Library             ../libs/keywords/backup_keywords.py
Library             ../libs/keywords/backing_image_keywords.py
Library             ../libs/keywords/engine_keywords.py

*** Variables ***
@{longhorn_workloads}
...    csi-attacher
...    csi-provisioner
...    csi-resizer
...    csi-snapshotter
...    longhorn-driver-deployer
...    longhorn-csi-plugin
...    longhorn-manager
...    longhorn-ui

*** Keywords ***
Wait for longhorn ready
    wait_for_all_instance_manager_running

Wait for all instance managers removed
    wait_for_all_instance_manager_removed

Wait for Longhorn workloads pods stable
    [Arguments]    @{args}
    @{workload_list} =    Create List
    FOR    ${workload_name}    IN    @{args}
        Append To List    ${workload_list}    ${workload_name}
    END
    wait_for_workloads_pods_stably_running    ${workload_list}    longhorn-system

Check Longhorn workload pods ${condition} annotated with ${key}
    [Arguments]    @{args}
    @{workload_list} =    Create List
    FOR    ${workload_name}    IN    @{args}
        Append To List    ${workload_list}    ${workload_name}
    END

    ${is_annotated} =    is_workloads_pods_has_annotations    ${workload_list}    ${key}

    # Check if workloads annotated with key based on condition.
    # If condition is "not", then check if workloads are not annotated with key.
    # If condition is "is", then check if workloads are annotated with key.
    # Otherwise, fail the test.
    Run Keyword IF    '${condition}' == 'not'    Should Not Be True    ${is_annotated}
    ...    ELSE IF    '${condition}' == 'is'    Should Be True    ${is_annotated}
    ...    ELSE    Fail    Invalid condition ${condition}

Check Longhorn workload pods ${condition} running with CNI interface ${interface}
    [Arguments]    @{args}
    @{workload_list} =    Create List
    FOR    ${workload_name}    IN    @{args}
        Append To List    ${workload_list}    ${workload_name}
    END

    ${has_interface} =    is_workloads_pods_has_cni_interface    ${workload_list}    ${interface}

    # Check if workloads have interface based on condition.
    # If condition is "not", then check if workloads do not have CNI interface.
    # If condition is "is", then check if workloads have CNI interface.
    # Otherwise, fail the test.
    Run Keyword IF    '${condition}' == 'not'    Should Not Be True    ${has_interface}
    ...    ELSE IF    '${condition}' == 'is'    Should Be True    ${has_interface}
    ...    ELSE    Fail    Invalid condition ${condition}

Check ${engine_type} instance manager is not running on drained node
    check_instance_manager_existence_on_node    ${drained_node}    ${engine_type}    ${False}

Check ${engine_type} instance manager is running on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    check_instance_manager_existence_on_node    ${node_name}    ${engine_type}    ${True}

Check ${engine_type} instance manager is not running on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    check_instance_manager_existence_on_node    ${node_name}    ${engine_type}    ${False}

Check v1 instance manager pods did not restart
    check_all_instance_managers_not_restart

Check v1 instance manager pods recreated
    wait_all_instance_managers_recreated

Wait for engine instances in ${engine_type} instance manager CR on node ${node_id} to be cleaned up
    ${node_name} =    get_node_by_index    ${node_id}
    wait_for_instance_manager_cr_engine_instances_to_be_cleaned_up    ${node_name}    ${engine_type}

Uninstall Longhorn
    ${backups_before_uninstall} =     list_all_backups
    uninstall_longhorn_system
    Set Test Variable    ${backups_before_uninstall}

Check all Longhorn CRD removed
    check_longhorn_crd_removed

Install Longhorn
    install_longhorn_system

Delete ${engine_type} instance manager on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    delete_instance_manager_on_node    ${node_name}    ${engine_type}

Delete ${engine_type} instance manager of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${node_name} =    get_volume_node    ${volume_name}
    delete_instance_manager_on_node    ${node_name}    ${engine_type}

Delete ${engine_type} instance manager of deployment ${deployment_id} volume
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    ${node_name} =    get_volume_node    ${volume_name}
    delete_instance_manager_on_node    ${node_name}    ${engine_type}

Wait for Longhorn components all running
    wait_for_namespace_pods_running    longhorn-system

Install Longhorn stable version
    install_longhorn_system    install_stable_version=True

Uninstall Longhorn stable version
    ${backups_before_uninstall} =     list_all_backups
    uninstall_longhorn_system    is_stable_version=True
    Set Test Variable    ${backups_before_uninstall}

Upgrade Longhorn to transient version
    ${upgraded} =    upgrade_longhorn    upgrade_to_transient_version=True
    IF    "${upgraded}" == ${False}
        Log To Console    Upgrade failed
        Fail    Upgrading Longhorn to transient failed
    END

Upgrade Longhorn to custom version
    ${upgraded} =    upgrade_longhorn
    IF    "${upgraded}" == ${False}
        Log To Console    Upgrade failed
        Fail    Upgrading Longhorn failed
    END

Upgrade Longhorn to custom version should fail
    ${upgraded} =     upgrade_longhorn    wait_when_fail=False
    IF    "${upgraded}" == ${True}
        Log To Console    Upgrade succeed
        Fail    Upgrading Longhorn succeed
    END

Enable Storage Network
    enable_storage_network_setting

Check Longhorn node ${type} state on power off node is ${expect_state}
    ${status} =    get_longhorn_node_condition_status    ${last_volume_node}    ${type}
    Should Be Equal    ${status}    ${expect_state}

Check longhorn manager pods not restarted after test start
    check_pod_not_restart_after_specific_time    longhorn-system    app=longhorn-manager    ${test_start_time}

Check longhorn backing image manager image is ${expected_image}
    check_backing_image_manager_images    ${expected_image}

Assert disk size in instance manager pod for ${workload_kind} ${workload_id} is ${size}
    ${expected_size_byte} =    convert_size_to_bytes    ${size}    to_str=True
    ${workload_name}=    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name}=    get_workload_volume_name    ${workload_name}
    ${instance_manager_name} =    get_engine_instance_manager_name    ${volume_name}
    Wait Until Keyword Succeeds    ${RETRY_COUNT}    ${RETRY_INTERVAL}
    ...    Check disk size in instance manager pod    ${instance_manager_name}    ${volume_name}    ${expected_size_byte}

Check disk size in instance manager pod
    [Arguments]    ${instance_manager_name}    ${volume_name}    ${expected_size}
    ${cmd}=    Set Variable    fdisk -l | grep /dev/mapper/${volume_name}
    ${result}=    pod_exec    ${instance_manager_name}    longhorn-system    ${cmd}
    Should Contain    ${result}    ${expected_size}
