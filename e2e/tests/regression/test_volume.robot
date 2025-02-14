*** Settings ***
Documentation    Volume Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/node.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/volume.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Create volume with invalid name should fail
  [Arguments]    ${invalid_volume_name}
  Given Create volume     ${invalid_volume_name}
  Then No volume created

*** Test Cases ***

Test RWX Volume Data Integrity After CSI Plugin Pod Restart
    [Tags]    volume    rwx    storage-network
    [Documentation]    Test RWX volume data directory is accessible after Longhorn CSI plugin pod restart.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8184

    Given Set setting auto-delete-pod-when-volume-detached-unexpectedly to true
    And Create persistentvolumeclaim 0 using RWX volume
    And Create deployment 0 with persistentvolumeclaim 0 with max replicaset
    And Write 10 MB data to file data.txt in deployment 0

    When Delete Longhorn DaemonSet longhorn-csi-plugin pod on node 1
    And Wait for Longhorn workloads pods stable
        ...    longhorn-csi-plugin

    Then Check deployment 0 data in file data.txt is intact

Test Detached Volume Should Not Reattach After Node Eviction
    [Tags]    volume    node-eviction
    [Documentation]    Test detached volume should not reattach after node eviction.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/9781

    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy

    When Detach volume 0
    And Set node 1 with    allowScheduling=false    evictionRequested=true

    Then Wait for volume 0 detached
    And Assert volume 0 remains detached for at least 60 seconds

Test RWX Volume Without Migratable Should Be Incompatible With Strict-Local
    [Tags]    volume    rwx
    [Documentation]    Test RWX volume is incompatible in strict-local mode without migratable
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/6735

    When Create volume 0 with    numberOfReplicas=1    migratable=False    accessMode=RWX    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    Then No volume created

Test Volume Attached at Maximum Snapshot Count
    [Tags]    volume    snapshot-limit
    [Documentation]    Validate that reaching the snapshot limit of 250 does not affect
    ...                volume attach/detach operations.
    ...                Issue: https://github.com/longhorn/longhorn/issues/10308
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}    numberOfReplicas=1
    And Attach volume 0
    And Wait for volume 0 healthy
    When Create 249 snapshot for volume 0
    And Detach volume 0
    Then Attach volume 0
    And Wait for volume 0 healthy
