*** Settings ***
Documentation    Storage Network Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Storage Network Should Not Restart Migratable RWX Volume Workload Pods
    [Tags]    setting    storage-network    volume    migratable-rwx    csi
    [Documentation]    Verifies that when the `storage-network-for-rwx-volume-enabled`
    ...                setting is set to `true`, workload pods using migratable
    ...                RWX volumes do not restart unexpectedly.
    ...
    ...                This test ensures that restarting the `longhorn-csi-plugin`
    ...                pods does not impact workloads attached to migratable RWX
    ...                volumes.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/11158
    ...
    ...                Precondition: Storage network configured.
    Given Setting endpoint-network-for-rwx-volume is set to kube-system/demo-192-168-0-0
    And Wait for Longhorn workloads pods stable
        ...    longhorn-csi-plugin
    And Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Create persistentvolume for volume 0
    And Create persistentvolumeclaim for volume 0
    And Create deployment 0 using volume 0    num_replicaset=1
    And Record deployment 0 pod UIDs

    When Delete Longhorn DaemonSet longhorn-csi-plugin pod on all nodes

    Then Assert pod UIDs of deployment 0 remain unchanged    num_checks=60
