*** Settings ***
Documentation    Basic Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/engine.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/backup.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Create volume with invalid name should fail
  [Arguments]    ${invalid_volume_name}
  When Run Keyword And Expect Error    *    Create volume     ${invalid_volume_name}    retry=False
  Then No volume created

*** Test Cases ***
Test Invalid Volume Name
    [Tags]    coretest
    [Documentation]    Test invalid volume name
    [Template]    Create volume with invalid name should fail
        wrong_volume-name-1.0
        wrong_volume-name

Test Volume Basic
    [Tags]    coretest
    [Documentation]    Test basic volume operations
    ...
    ...                1. Create a volume and attach to the current node, then check volume states
    ...                2. Write then read back to check volume data
    Given Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    When Attach volume 0
    And Wait for volume 0 healthy

    When Write data to volume 0
    Then Check volume 0 data is intact

    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0

Test V1 Snapshot
    [Tags]    coretest    snapshot-purge
    [Documentation]    Test snapshot operations
    Given Create volume 0 with    dataEngine=v1
    When Attach volume 0
    And Wait for volume 0 healthy

    And Create snapshot 0 of volume 0

    And Write data 1 to volume 0
    And Create snapshot 1 of volume 0

    And Write data 2 to volume 0
    And Create snapshot 2 of volume 0

    Then Validate snapshot 0 is parent of snapshot 1 in volume 0 snapshot list
    And Validate snapshot 1 is parent of snapshot 2 in volume 0 snapshot list
    And Validate snapshot 2 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 2 of volume 0
    Then Validate snapshot 2 is in volume 0 snapshot list
    And Validate snapshot 2 is marked as removed in volume 0 snapshot list
    And Check volume 0 data is data 2

    When Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 healthy
    And Create snapshot 3 of volume 0
    Then Validate snapshot 3 is parent of volume-head in volume 0 snapshot list

    When Revert volume 0 to snapshot 1
    And Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Check volume 0 data is data 1
    And Validate snapshot 1 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 1 of volume 0
    And Delete snapshot 0 of volume 0

    And Purge volume 0 snapshot
    Then Validate snapshot 0 is not in volume 0 snapshot list
    And Validate snapshot 1 is in volume 0 snapshot list
    And Validate snapshot 1 is marked as removed in volume 0 snapshot list
    And Validate snapshot 2 is not in volume 0 snapshot list

    And Check volume 0 data is data 1

Test Strict Local Volume Disabled Revision Counter By Default
    [Tags]    coretest    single-replica
    [Documentation]
    ...    1. Set the global setting disable-revision-counter to false
    ...    2. Create a volume with 1 replica and strict-local data locality
    ...    3. See that the revisionCounterDisabled: true for volume/engine/replica CRs
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Setting disable-revision-counter is not supported for v2 data engine
    END

    Given Setting disable-revision-counter is set to {"v1":"false"}

    When Create volume 0 with    numberOfReplicas=1    dataLocality=strict-local
    And Wait for volume 0 detached
    Then Volume 0 setting revisionCounterDisabled should be True
    And Volume 0 engine revisionCounterDisabled should be True
    And Volume 0 replica revisionCounterDisabled should be True

Replica Rebuilding
    [Documentation]    -- Manual test plan --
    ...                1. Create and attach a volume.
    ...                2. Write a large amount of data to the volume.
    ...                3. Disable disk scheduling and the node scheduling for one replica.
    ...                4. Crash the replica progress. Verify
    ...                    - the corresponding replica in not running state.
    ...                    - the volume will keep robustness Degraded.
    ...                5. Enable the disk scheduling. Verify nothing changes.
    ...                6. Enable the node scheduling. Verify.
    ...                    - the failed replica is reused by Longhorn.
    ...                    - the data content is correct after rebuilding.
    ...                    - volume r/w works fine.
    ...
    ...                == Not implemented ==
    ...                7. Direct delete one replica via UI. Verify
    ...                - a new replica will be replenished immediately.
    ...                - the rebuilding progress in UI page looks good.
    ...                - the data content is correct after rebuilding.
    ...                - volume r/w works fine.
    Given Create volume 0 with    size=10Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    And Write 1 GB data to volume 0

    And Disable node 1 scheduling
    And Disable node 1 default disk

    When Record volume 0 replica name on node 1
    And Delete ${DATA_ENGINE} instance manager on node 1
    Then Wait volume 0 replica on node 1 stopped
    And Wait for volume 0 degraded

    When Enable node 1 default disk
    Then Check volume 0 replica on node 1 kept in stopped
    And Check volume 0 kept in degraded

    When Enable node 1 scheduling
    # it isn’t guaranteed to catch the moment when the replica is rebuilding.
    # a replica could become healthy directly without showing the rebuilding progress
    Then Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    And Check volume 0 crashed replica reused on node 1

    And Check volume 0 data is intact
    And Check volume 0 works

Test File Ownership And Permission By Executing Git Clone
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1

    When Run commands in deployment 0    commands=git clone https://github.com/longhorn/longhorn.git
    And Run commands in deployment 1    commands=git clone https://github.com/longhorn/longhorn.git
    Then Test should pass

Test Rapid Volume Detachment
    Given Setting orphan-resource-auto-deletion is set to instance
    And Setting orphan-resource-auto-deletion-grace-period is set to 60
    And Create volume 0 with    dataEngine=${DATA_ENGINE}

    FOR    ${i}    IN RANGE    100
        When Attach volume 0 to node 0    wait=False
        And Detach volume 0
        And Wait for volume 0 detached
        Then Wait for engine instances in ${DATA_ENGINE} instance manager CR on node 0 to be cleaned up
    END

Test Deploy V2 Volume With Disabled V1 Data Engine
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test case not support for v1 data engine
    END
    Given Setting v1-data-engine is set to false
    And Create volume 0 with    size=2Gi    numberOfReplicas=3    dataEngine=v2
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    When Write data to volume 0
    Then Check volume 0 data is intact

Test Dynamic PV Has No Node Affinity
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12656
    ...    1. Create a Longhorn storageclass and a PVC to trigger dynamic provisioning.
    ...    2. Wait for the volume to be created and bound.
    ...    3. Ensure the dynamically provisioned PV does not contain spec.nodeAffinity.
    ${claim_name}=    Generate name with suffix    claim    0
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    Then Run command and not expect output
    ...    kubectl get pv $(kubectl get pvc ${claim_name} -ojsonpath='{.spec.volumeName}') -o yaml
    ...    nodeAffinity:

Test Filesystem Trim
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/7534
    ...    1. Create a workload to use a Longhorn volume.
    ...    2. Write data to the volume and then delete the data.
    ...    3. Trigger filesystem trim on the volume.
    ...    4. Check the volume's used storage size is reduced after trim.
    ...    Note: v2 volumes don't support unmapMarkSnapChainRemoved and Remove Snapshots During Filesystem Trim
    ...          so pytest test case test_filesystem_trim doesn't work on v2 volumes.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy

    When Write 256 MB data to file testfile in deployment 0
    And Volume of deployment 0 actual size should be greater than 256Mi
    And Run commands in deployment 0    commands=rm -rf /data/testfile && sync
    And Trim deployment 0 volume should pass
    Then Volume of deployment 0 actual size should be less than 256Mi

Test Auto Salvage After Volume Faulted By Instance Manager Deletion
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/8430
    ...    1. Dynamically provision a v1/v2 volume via storageclass, create a deployment
    ...       workload and write data to it.
    ...    2. Disable auto-salvage setting.
    ...    3. Force delete all instance manager pods for the volume's data engine on all
    ...       nodes so that all replicas fail and the volume becomes faulted.
    ...    4. Confirm the volume remains in faulted state for a sufficient period
    ...    5. Re-enable auto-salvage setting.
    ...    6. Verify the faulted volume automatically recovers to healthy and the
    ...       data written in step 1 is intact.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    When Setting auto-salvage is set to false
    And Delete ${DATA_ENGINE} instance manager on node 0
    And Delete ${DATA_ENGINE} instance manager on node 1
    And Delete ${DATA_ENGINE} instance manager on node 2
    Then Check volume of deployment 0 kept in faulted

    When Setting auto-salvage is set to true
    Then Wait for volume of deployment 0 healthy
    And Wait for deployment 0 pods stable
    And Check deployment 0 data in file data.txt is intact

Test Refuse To Attach Strict-local Volume To A Different Node
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/8546
    ...                Test that a strict-local volume cannot be attached to a different node
    ...                after it has been attached and detached from its original node.
    ...
    ...                1. Create a strict-local volume
    ...                2. Attach it to node 0
    ...                3. Detach it from node 0
    ...                4. Attach it to node 1 should fail
    Given Create volume 0 with    numberOfReplicas=1    dataLocality=strict-local    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    When Detach volume 0
    And Wait for volume 0 detached

    Then Attach volume 0 to node 1 should fail

Test Instance Manager AWS Role Annotation
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/9923
    ...    Verify that the iam.amazonaws.com/role annotation is propagated to
    ...    instance manager pods when AWS_IAM_ROLE_ARN is set in the backup
    ...    credential secret, and removed when the key is deleted.
    ...
    ...    1. Create a volume
    ...    2. Write some data
    ...    3. Create a backup
    ...    4. Check there is no iam.amazonaws.com/role annotation in instance manager pods
    ...    5. Patch the s3 secret: add AWS_IAM_ROLE_ARN
    ...    6. Check there is iam.amazonaws.com/role=test-aws-iam-role-arn in instance manager pods
    ...    7. Create a backup
    ...    8. Delete all instance manager pods
    ...    9. Check there is still iam.amazonaws.com/role=test-aws-iam-role-arn in instance manager pods
    ...    10. Create a backup
    ...    11. Remove AWS_IAM_ROLE_ARN from the s3 secret
    ...    12. Check there is no iam.amazonaws.com/role annotation in instance manager pods
    ${LONGHORN_BACKUPSTORE}=    Get Environment Variable    LONGHORN_BACKUPSTORE    default=${EMPTY}
    IF    not $LONGHORN_BACKUPSTORE.startswith('s3://')
        Skip    Test requires S3 backupstore, got: ${LONGHORN_BACKUPSTORE}
    END

    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Create backup 0 for volume 0
    Then Run command and not expect output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l longhorn.io/component=instance-manager,longhorn.io/data-engine=${DATA_ENGINE} -ojson | jq '.items[0].metadata.annotations'
    ...    iam.amazonaws.com/role

    # AWS_IAM_ROLE_ARN: test-aws-iam-role-arn
    When Run command
    ...    kubectl patch secret minio-secret -n ${LONGHORN_NAMESPACE} -p '{"data": {"AWS_IAM_ROLE_ARN": "dGVzdC1hd3MtaWFtLXJvbGUtYXJu"}}'
    Then Run command and expect output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l longhorn.io/component=instance-manager,longhorn.io/data-engine=${DATA_ENGINE} -ojson | jq '.items[0].metadata.annotations'
    ...    "iam.amazonaws.com/role": "test-aws-iam-role-arn"
    And Create backup 1 for volume 0

    When Delete ${DATA_ENGINE} instance manager on node 0
    And Delete ${DATA_ENGINE} instance manager on node 1
    And Delete ${DATA_ENGINE} instance manager on node 2
    And Check volume 0 kept in healthy
    Then Run command and expect output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l longhorn.io/component=instance-manager,longhorn.io/data-engine=${DATA_ENGINE} -ojson | jq '.items[0].metadata.annotations'
    ...    "iam.amazonaws.com/role": "test-aws-iam-role-arn"
    And Create backup 2 for volume 0

    When Run command
    ...    kubectl patch secret minio-secret -n ${LONGHORN_NAMESPACE} --type=json -p='[{"op": "remove", "path": "/data/AWS_IAM_ROLE_ARN"}]'
    Then Run command and not expect output
    ...    kubectl get pods -n ${LONGHORN_NAMESPACE} -l longhorn.io/component=instance-manager,longhorn.io/data-engine=${DATA_ENGINE} -ojson | jq '.items[0].metadata.annotations'
    ...    iam.amazonaws.com/role
