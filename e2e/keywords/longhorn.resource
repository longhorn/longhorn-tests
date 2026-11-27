*** Settings ***
Documentation       Longhorn Keywords

Library             ../libs/keywords/common_keywords.py
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
...    longhorn-global-manager
...    longhorn-manager
...    longhorn-ui

${LONGHORN_REPO_DIR}    /tmp/longhorn/longhorn

*** Keywords ***
Wait for longhorn ready
    wait_for_all_instance_manager_running

Wait for all instance managers running with default image
    wait_for_all_instance_manager_running_with_default_image

Wait for all v2 instance managers running with default image
    wait_for_all_instance_manager_running_with_default_image

Wait for all instance manager upgrades completed
    instancemanager_keywords.wait_for_all_instance_manager_upgrades_completed

Wait for all v2 instance manager upgrades completed
    instancemanager_keywords.wait_for_all_instance_manager_upgrades_completed

Wait for all instance managers removed
    wait_for_all_instance_manager_removed

Wait for Longhorn node named ${node_name} down
    wait_for_longhorn_node_down    ${node_name}

Wait for Longhorn workloads pods stable
    [Arguments]    @{args}
    @{workload_list} =    Create List
    FOR    ${workload_name}    IN    @{args}
        Append To List    ${workload_list}    ${workload_name}
    END
    ${longhorn_namespace} =    get_longhorn_namespace
    wait_for_workloads_pods_stably_running    ${workload_list}    ${longhorn_namespace}

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

Check instance manager pods of data engine ${data_engine} did not restart
    check_all_instance_managers_not_restart    data_engine=${data_engine}

Check ${data_engine} instance manager pods recreated
    wait_all_instance_managers_recreated    ${data_engine}

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
    [Arguments]    &{config}
    install_longhorn_system    &{config}

Install Longhorn via helm with resource configuration
    [Arguments]    ${cpu_request}    ${memory_request}    ${cpu_limit}    ${memory_limit}    &{config}
    ${patch}=    Set Variable    .longhornManager.resources = {"requests":{"cpu":"${cpu_request}","memory":"${memory_request}"},"limits":{"cpu":"${cpu_limit}","memory":"${memory_limit}"}}
    ${helm_cmd}=    Set Variable    yq eval \'${patch}\' ${LONGHORN_REPO_DIR}/chart/values.yaml > values.yaml
    install_longhorn_system    custom_cmd=${helm_cmd}    &{config}

Delete ${engine_type} instance manager on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    delete_instance_manager_on_node    ${node_name}    ${engine_type}

Get ${engine_type} instance manager pod on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${instance_manager_pod} =    get_instance_manager_pod_on_node    ${node_name}    ${engine_type}
    RETURN    ${instance_manager_pod}

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
    ${longhorn_namespace} =    get_longhorn_namespace
    wait_for_namespace_pods_running    ${longhorn_namespace}

Get Longhorn global manager lease holder
    ${holder} =    get_global_manager_lease_holder
    RETURN    ${holder}

Wait for Longhorn global manager lease holder changed from ${old_holder}
    ${holder} =    wait_for_global_manager_lease_holder_changed    ${old_holder}
    RETURN    ${holder}

Install Longhorn stable version
    [Arguments]    &{config}
    install_longhorn_system    install_stable_version=True    &{config}

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
    [Arguments]    &{config}
    ${upgraded} =    upgrade_longhorn    &{config}
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
    ${longhorn_namespace} =    get_longhorn_namespace
    check_pod_not_restart_after_specific_time    ${longhorn_namespace}    app=longhorn-manager    ${test_start_time}

Check longhorn backing image manager image is ${expected_image}
    check_backing_image_manager_images    ${expected_image}

Wait for disk size for volume ${volume_id} in ${data_engine} instance manager pod to be ${size}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${size_byte} =    convert_size_to_bytes    ${size}    to_str=True
    ${instance_manager_name} =    get_engine_instance_manager_name    ${volume_name}
    # v1 checks /dev/mapper/<volume>, v2 checks the encrypted device /dev/mapper/<volume>-encrypted
    ${device_name} =    Set Variable If    "${data_engine}" == "v2"    ${volume_name}-encrypted    ${volume_name}
    wait_for_disk_size_in_instance_manager_pod    ${instance_manager_name}    ${device_name}    ${size_byte}

Wait for disk size for volume of ${workload_kind} ${workload_id} in ${data_engine} instance manager pod to be ${size}
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${size_byte} =    convert_size_to_bytes    ${size}    to_str=True
    ${instance_manager_name} =    get_engine_instance_manager_name    ${volume_name}
    # v1 checks /dev/mapper/<volume>, v2 checks the encrypted device /dev/mapper/<volume>-encrypted
    ${device_name} =    Set Variable If    "${data_engine}" == "v2"    ${volume_name}-encrypted    ${volume_name}
    wait_for_disk_size_in_instance_manager_pod    ${instance_manager_name}    ${device_name}    ${size_byte}

Wait for raw disk size for volume ${volume_id} in v2 instance manager pod to be ${size}
    [Documentation]    The v2 counterpart of "Assert replica file size". Check the raw device
    ...                size of a v2 volume, which is the volume size + 16Mi header size.
    ...                The expected raw size must be given explicitly.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${size_byte} =    convert_size_to_bytes    ${size}    to_str=True
    ${instance_manager_name} =    get_engine_instance_manager_name    ${volume_name}
    wait_for_disk_size_in_instance_manager_pod    ${instance_manager_name}    ${volume_name}    ${size_byte}

Wait for raw disk size for volume of ${workload_kind} ${workload_id} in v2 instance manager pod to be ${size}
    [Documentation]    The v2 counterpart of "Assert replica file size". Check the raw device
    ...                size of a v2 volume, which is the volume size + 16Mi header size.
    ...                The expected raw size must be given explicitly.
    ${workload_name} =    generate_name_with_suffix    ${workload_kind}    ${workload_id}
    ${volume_name} =    get_workload_volume_name    ${workload_name}
    ${size_byte} =    convert_size_to_bytes    ${size}    to_str=True
    ${instance_manager_name} =    get_engine_instance_manager_name    ${volume_name}
    wait_for_disk_size_in_instance_manager_pod    ${instance_manager_name}    ${volume_name}    ${size_byte}

Patch Longhorn Manager Resources With
    [Arguments]    ${cpu_request}    ${memory_request}    ${cpu_limit}    ${memory_limit}
    patch_longhorn_component_resources_limit    longhorn-manager    daemonset    ${cpu_request}    ${memory_request}    ${cpu_limit}    ${memory_limit}

Check Longhorn Manager Resources Are
    [Arguments]    ${cpu_request}    ${memory_request}    ${cpu_limit}    ${memory_limit}
    ${resources}=    get_longhorn_component_resources_limit    longhorn-manager    daemonset
    Should Be Equal    ${resources['requests']['cpu']}    ${cpu_request}
    Should Be Equal    ${resources['requests']['memory']}    ${memory_request}
    Should Be Equal    ${resources['limits']['cpu']}    ${cpu_limit}
    Should Be Equal    ${resources['limits']['memory']}    ${memory_limit}

Remove Longhorn Manager Resource Limit
    remove_longhorn_component_resources_limit    longhorn-manager    daemonset

Any ${label_selector} Pods Log Should Have ${expect_log} After Test Start
    [Documentation]    Verify that at least one pod matching the given label selector contains
    ...                the expected log substring after test_start_time.
    ...
    ...                Available label selectors for Longhorn components in longhorn-system:
    ...
    ...                  app=longhorn-manager
    ...                  app=longhorn-driver-deployer
    ...                  app=longhorn-csi-plugin
    ...                  app=longhorn-ui
    ...                  app=csi-attacher
    ...                  app=csi-provisioner
    ...                  app=csi-resizer
    ...                  app=csi-snapshotter
    ...                  longhorn.io/component=instance-manager
    ...                  longhorn.io/component=engine-image
    verify_pods_log_after_time_contains    ${label_selector}    ${expect_log}    ${test_start_time}

Any ${label_selector} Pods Log Should Have ${expect_log} In Container ${container} After Test Start
    verify_pods_log_after_time_contains    ${label_selector}    ${expect_log}    ${test_start_time}    container=${container}

Any ${label_selector} Pods Log Should Not Have ${expect_log} After Test Start
    verify_pods_log_after_time_not_contains    ${label_selector}    ${expect_log}    ${test_start_time}

Delete Longhorn node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    delete_longhorn_node    ${node_name}

Delete Longhorn node ${node_id} should fail
    ${node_name} =    get_node_by_index    ${node_id}
    Run Keyword And Expect Error    *    delete_longhorn_node    ${node_name}

Verify ${engine_type} instance manager log on node ${node_id} contain ${expect_log} after test start
    ${node_name} =    get_node_by_index    ${node_id}
    ${pod_name} =    get_instance_manager_pod_on_node    ${node_name}    ${engine_type}
    Log    ${pod_name}
    verify_pod_log_after_time_contains    ${pod_name}    ${expect_log}    ${test_start_time}

Verify ${engine_type} instance manager log on node ${node_id} not contain ${expect_log} after test start
    ${node_name} =    get_node_by_index    ${node_id}
    ${pod_name} =    get_instance_manager_pod_on_node    ${node_name}    ${engine_type}
    Log    ${pod_name}
    verify_pod_log_after_time_not_contains    ${pod_name}    ${expect_log}    ${test_start_time}

Disable Longhorn Webhook Validator
    execute_command    kubectl delete validatingwebhookconfiguration longhorn-webhook-validator --ignore-not-found

Restore Longhorn Webhook Validator
    execute_command    kubectl rollout restart daemonset/longhorn-manager -n longhorn-system
    execute_command    kubectl rollout status daemonset/longhorn-manager -n longhorn-system --timeout=300s

Get ${engine_type} instance manager pod name on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${pod_name} =    get_instance_manager_pod_on_node    ${node_name}    ${engine_type}
    RETURN    ${pod_name}

Wait for v2 instance manager pods restarted
    wait_all_instance_managers_recreated    data_engine=v2
