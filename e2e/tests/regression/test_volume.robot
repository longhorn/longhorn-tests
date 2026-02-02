*** Settings ***
Documentation    Volume Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/node.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/sharemanager.resource

Test Setup    Set up test environment
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

    Given Setting auto-delete-pod-when-volume-detached-unexpectedly is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
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

Test RWX Volume Automatic Online Expansion
    [Tags]    rwx    volume-expansion
    [Documentation]    Test automatic online filesystem resize for RWX volumes
    ...                Ref: https://github.com/longhorn/longhorn/issues/8119
    ...                Related issues:
    ...                - https://github.com/longhorn/longhorn/issues/8118
    ...                - https://github.com/longhorn/longhorn/issues/9736
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test    storage_size=50MiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 10 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Expand deployment 0 volume to 100MiB
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    And Assert disk size in sharemanager pod for deployment 0 is 100MiB
    And Check deployment 0 data in file data.txt is intact
    # Wait for filesystem to be expanded in the workload pod before writing new data
    And Wait for deployment 0 filesystem size 100MiB
    # Write data that covers the newly expanded blocks to verify filesystem expansion
    And Write 60 MB data to file data2.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 0 data in file data2.txt is intact

Test RWOP Volume
    [Tags]    coretest
    [Documentation]    Test ReadWriteOncePod (RWOP) access mode
    ...
    ...                - 1. Create a PVC with ReadWriteOncePod access mode
    ...                - 2. Verify the volume, PV, and PVC have correct access mode
    ...                - 3. Create a deployment with the RWOP PVC and verify it runs
    ...                - 4. Write and read data to verify the volume works
    ...                - 5. Scale the deployment to 2 replicas
    ...                - 6. Verify the second pod is stuck at pending due to RWOP restriction
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9727
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWOP    sc_name=longhorn-test    storage_size=2Gi
    And Wait for volume of persistentvolumeclaim 0 to be created
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 100 MB data to file 0 in deployment 0

    When Scale deployment 0 to 2
    And Sleep    60

    Then Run command and wait for output
    ...    kubectl get pods -l app=e2e-test-deployment-0 --field-selector=status.phase=Running --no-headers | wc -l
    ...    1
    And Run command and wait for output
    ...    kubectl get pods -l app=e2e-test-deployment-0 --field-selector=status.phase=Pending --no-headers | wc -l
    ...    1
