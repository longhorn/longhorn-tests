*** Settings ***
Documentation    Replica Test Cases

Test Tags    regression    replica

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/snapshot.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Replica Rebuilding Per Volume Limit
    [Tags]    coretest
    [Documentation]    Test the volume always only have one replica scheduled for rebuild
    ...
    ...    1. Set soft anti-affinity to `true`.
    ...    2. Create a volume with 1 replica.
    ...    3. Attach the volume and write a few hundreds MB data to it.
    ...    4. Scale the volume replica to 5.
    ...    5. Monitor the volume replica list to make sure there should be only 1 replica in WO state.
    ...    6. Wait for the volume to complete rebuilding. Then remove 4 of the 5 replicas.
    ...    7. Monitoring the volume replica list again.
    ...    8. Once the rebuild was completed again, verify the data checksum.
    Given Setting replica-soft-anti-affinity is set to true
    And Create volume 0 with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Update volume 0 replica count to 5
    Then Only one replica rebuilding will start at a time for volume 0
    And Monitor only one replica rebuilding will start at a time for volume 0
    And Wait until volume 0 replicas rebuilding completed

    When Delete 4 replicas of volume 0
    Then Only one replica rebuilding will start at a time for volume 0
    And Monitor only one replica rebuilding will start at a time for volume 0
    And Wait until volume 0 replicas rebuilding completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Offline Replica Rebuilding
    [Tags]    coretest    offline-rebuilding
    [Documentation]    Test offline replica rebuilding for a volume.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8443
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write 3 GB data to volume 0
    And Detach volume 0
    And Wait for volume 0 detached

    When Delete volume 0 replica on node 0
    Then Enable volume 0 offline replica rebuilding
    And Wait until volume 0 replica rebuilding started on node 0
    And Wait for volume 0 detached
    And Volume 0 should have 3 replicas when detached
    And Ignore volume 0 offline replica rebuilding

    When Delete volume 0 replica on node 0
    Then Setting offline-replica-rebuilding is set to true
    And Wait until volume 0 replica rebuilding started on node 0
    And Wait for volume 0 detached
    And Volume 0 should have 3 replicas when detached
    And Setting offline-replica-rebuilding is set to false

Test Preempt Offline Replica Rebuilding By A Workload
    [Tags]    coretest    offline-rebuilding
    [Documentation]    Test preempt offline replica rebuilding by a workload.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/8443
    Given Create volume 0 with    size=6Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Detach volume 0
    And Wait for volume 0 detached
    And Create deployment 0 with volume 0
    And Wait for volume 0 healthy
    And Write 5120 MB data to file data.txt in deployment 0
    And Scale down deployment 0 to detach volume
    And Wait for volume 0 detached

    # enable offline replica rebuilding.
    When Delete volume 0 replica on node 0
    And Enable volume 0 offline replica rebuilding
    # wait for offline rebuilding to start.
    Then Wait until volume 0 replica rebuilding started on node 0
    And Volume 0 should have 3 replicas

    # scale up the workload and it will preempt the offline rebuilding.
    When Scale up deployment 0 to attach volume
    # the volume might be detched or not so we only wait for volume becomes healthy.
    # we should try to check if offline rebuilding will be canceled and online rebuilding takes over.
    # then the volume becomes healthy without offline rebuilding.
    And Wait for volume 0 healthy
    # write some data with workload pod to check if the workload works.
    And Write 64 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

Test Evict Replicas Repeatedly
    [Documentation]    https://github.com/longhorn/longhorn/issues/9780
    ...    1. Create a pod that uses a v2 Longhorn volume.
    ...    2. Evict one of the replica nodes.
    ...    3. Repeat step 2.
    Given Create volume 0 attached to node 2 with 2 replicas excluding node 2    dataEngine=${DATA_ENGINE}
    And Wait for volume 0 healthy
    And Write data to volume 0

    FOR   ${i}    IN RANGE    10
        When Evict node ${{ ${i} % 2 }}
        # an extra replica will be created on the other node first
        Then Volume 0 should have 3 replicas
        # then the original replica will be evicted
        And Volume 0 should have 2 replicas
        And Wait for volume 0 healthy
        And Unevict evicted nodes
    END

    And Check volume 0 data is intact
    And Run command and not expect output
    ...    kubectl logs -n longhorn-system -l longhorn.io/component=instance-manager,longhorn.io/node=${NODE_0},longhorn.io/data-engine=${DATA_ENGINE}
    ...    write: broken pipe

Test Delete Instance Manager Of Single Replica Volume
    [Tags]    single-replica
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11525
    ...    Create a v2 volume with 1 replica on node-a
    ...    Attach it to node-b
    ...    Crash all v2 IM pods by delete them (crashing the IM pod which has the only replica of the volume)
    ...    Volume should recover
    Given Create single replica volume 0 with replica on node 1    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Delete ${DATA_ENGINE} instance manager on node 1
    And Wait for volume 0 unknown
    And Wait for volume 0 healthy
    Then Check volume 0 data is intact

    When Delete ${DATA_ENGINE} instance manager on node 0
    And Wait for volume 0 unknown
    And Wait for volume 0 healthy
    Then Check volume 0 data is intact

Test Offline Replica Rebuilding Volume Status Condition
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/11246
    Given Setting offline-replica-rebuilding is set to true
    And Create volume vol with    dataEngine=${DATA_ENGINE}
    And Attach volume vol
    And Wait for volume vol healthy
    And Write data to volume vol
    And Run command and not expect output
    ...    kubectl get volumes vol -n longhorn-system -oyaml
    ...    OfflineRebuildingInProgress
    And Detach volume vol
    And Wait for volume vol detached

    When Delete volume vol replica on replica node
    Then Run command and wait for output
    ...    kubectl get volumes vol -n longhorn-system -oyaml
    ...    OfflineRebuildingInProgress
    And Wait until volume vol replica rebuilding completed on replica node
    And Wait for volume vol detached
    And Run command and not expect output
    ...    kubectl get volumes vol -n longhorn-system -oyaml
    ...    OfflineRebuildingInProgress

Test Replica Rebuild Performance With Concurrent Sync Limit
    [Tags]    performance
    [Documentation]    Test to verify that increasing concurrent sync limit improves rebuild speed.
    ...
    ...                - Issue: https://github.com/longhorn/longhorn/issues/11331
    ...
    ...                - 1. Create a 5Gi volume with 3 replicas and attach it to a node.
    ...                - 2. Prefill volume with 2G sequential data and take snapshot 0.
    ...                - 3. Write 2G scattered data (4k blocks, 20% ratio) and take snapshot 1.
    ...                - 4. Write 2G scattered data (4k blocks, 20% ratio) again and take snapshot 2.
    ...                - 5. Delete one replica and measure the 1st baseline rebuild time.
    ...                - 6. Set replica-rebuild-concurrent-sync-limit to 5.
    ...                - 7. Delete another replica and measure the 2nd rebuild time.
    ...                - 8. Verify the 2nd rebuild time is less than the 1st baseline time.
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test case not support for v2 data engine
    END

    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy

    # Prefill volume with sequential data
    When Prefill volume 0 with fio    size=2G
    And Create snapshot 0 of volume 0
    # Write scattered tiny chunks and take snapshots
    And Write scattered data to volume 0 with fio    size=2G    bs=4k    ratio=0.2
    And Create snapshot 1 of volume 0
    And Write scattered data to volume 0 with fio    size=2G    bs=4k    ratio=0.2
    And Create snapshot 2 of volume 0

    # Measure 1st baseline rebuild time
    And Delete volume 0 replica on node 0
    And Wait until volume 0 replica rebuilding started on node 0
    ${rebuild_time}=    Wait until volume 0 replica rebuilding completed on node 0
    And Wait for volume 0 healthy

    # Set concurrent sync limit and measure 2nd rebuild time
    When Setting replica-rebuild-concurrent-sync-limit is set to 5
    And Delete volume 0 replica on node 1
    And Wait until volume 0 replica rebuilding started on node 1
    ${2nd_rebuild_time}=    Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy

    # Verify improvement
    Then Should Be True    ${2nd_rebuild_time} < ${rebuild_time}
    ...    msg=The 2nd replica rebuilding time (${2nd_rebuild_time}s) should be faster than 1st (${rebuild_time}s)

Test Volume Level Replica Rebuild Concurrent Sync Limit
    [Tags]    performance
    [Documentation]    Test to verify volume-level rebuildConcurrentSyncLimit setting effect.
    ...
    ...                - Issue: https://github.com/longhorn/longhorn/issues/11331
    ...
    ...                - 1. Create a 5Gi volume with rebuildConcurrentSyncLimit=5 and 3 replicas.
    ...                - 2. Prefill volume with 2G sequential data and take snapshot 0.
    ...                - 3. Write 2G scattered data (4k blocks, 20% ratio) and take snapshot 1.
    ...                - 4. Write 2G scattered data (4k blocks, 20% ratio) again and take snapshot 2.
    ...                - 5. Delete one replica and measure the 1st optimized rebuild time (with limit=5).
    ...                - 6. Update volume rebuildConcurrentSyncLimit to 0 (use global default).
    ...                - 7. Delete another replica and measure the 2nd baseline rebuild time (with default limit).
    ...                - 8. Verify the 1st optimized rebuild time is less than the 2nd baseline time.
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    Test case not support for v2 data engine
    END

    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    rebuildConcurrentSyncLimit=5    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy

    # Prefill volume with sequential data
    When Prefill volume 0 with fio    size=2G
    And Create snapshot 0 of volume 0
    # Write scattered tiny chunks and take snapshots
    And Write scattered data to volume 0 with fio    size=2G    bs=4k    ratio=0.2
    And Create snapshot 1 of volume 0
    And Write scattered data to volume 0 with fio    size=2G    bs=4k    ratio=0.2
    And Create snapshot 2 of volume 0
    # Measure 1st optimized rebuild time with volume-level limit=5
    And Delete volume 0 replica on node 0
    And Wait until volume 0 replica rebuilding started on node 0
    ${rebuild_time}=    Wait until volume 0 replica rebuilding completed on node 0
    And Wait for volume 0 healthy

    # Update volume to use global default (0) and measure baseline rebuild time
    When Update volume 0 rebuild concurrent sync limit to 0
    And Delete volume 0 replica on node 1
    And Wait until volume 0 replica rebuilding started on node 1
    ${2nd_rebuild_time}=    Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy

    # Verify improvement
    Then Should Be True    ${rebuild_time} < ${2nd_rebuild_time}
    ...    msg=The 1st replica rebuilding time (${rebuild_time}s) should be faster than 2nd (${2nd_rebuild_time}s)