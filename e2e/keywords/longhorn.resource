*** Settings ***
Documentation       Longhorn Keywords

Library             ../libs/keywords/instancemanager_keywords.py
Library             ../libs/keywords/workload_keywords.py
Library             ../libs/keywords/k8s_keywords.py
Library             ../libs/keywords/longhorn_deploy_keywords.py
Library             ../libs/keywords/backup_keywords.py

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

Check instance-manager pod is not running on drained node
    ${pod} =     get_instance_manager_on_node    ${drained_node}
    Should Be Equal    ${pod}    ${None}

Check instance-manager pod is running on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${pod} =     get_instance_manager_on_node    ${node_name}
    Should Not Be Equal    ${pod}    ${None}

Uninstall Longhorn
    ${backups_before_uninstall} =     list_all_backups
    uninstall_longhorn_system
    Set Test Variable    ${backups_before_uninstall}

Check all Longhorn CRD removed
    check_longhorn_crd_removed

Install Longhorn
    install_longhorn_system

Delete instance-manager on node ${node_id}
    ${node_name} =    get_node_by_index    ${node_id}
    ${pods} =    list_pods    longhorn-system    longhorn.io/component=instance-manager,longhorn.io/data-engine=${DATA_ENGINE},longhorn.io/node=${NODE_NAME}
    FOR    ${pod}    IN    @{pods}
        delete_pod    ${pod}    longhorn-system    wait=False
    END

Delete instance-manager of volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${instance_manager} =     get_volume_instance_manager    ${volume_name}
    delete_pod    ${instance_manager}    longhorn-system

Delete instance-manager of deployment ${deployment_id} volume
    ${deployment_name} =   generate_name_with_suffix    deployment    ${deployment_id}
    ${volume_name} =    get_workload_volume_name    ${deployment_name}
    ${instance_manager} =     get_volume_instance_manager    ${volume_name}
    delete_pod    ${instance_manager}    longhorn-system

Wait for Longhorn components all running
    wait_for_namespace_pods_running    longhorn-system

Install Longhorn stable version
    install_longhorn_system    is_stable_version=True

Uninstall Longhorn stable version
    ${backups_before_uninstall} =     list_all_backups
    uninstall_longhorn_system    is_stable_version=True
    Set Test Variable    ${backups_before_uninstall}
