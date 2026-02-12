*** Settings ***
Documentation    Negative Test Cases

Test Tags    network-disconnect    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/common.resource
Resource    ../keywords/network.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Disconnect Volume Node Network While Workload Heavy Writing
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        When Disconnect volume nodes network for 20 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1
        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        And Keep writing data to pod of statefulset 1
        When Disconnect volume nodes network for 360 seconds    statefulset 0    statefulset 1
        And Wait for volume of statefulset 0 healthy
        And Wait for volume of statefulset 1 healthy
        And Wait for workloads pods stable    statefulset 0    statefulset 1
        Then Check statefulset 0 works
        And Check statefulset 1 works
    END

Test Volume Expansion During Network Disconnect With Volume Type
    [Arguments]    ${VOLUME_TYPE}
    [Documentation]    Test volume expansion behavior when attached node network is disconnected during expansion.
    ...                Supports both RWO and RWX volume types.
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/1674
    ...                https://github.com/longhorn/longhorn/issues/5171
    ...
    ...                Test Steps:
    ...                - Create a volume with initial size 5Gi and attach it to a node.
    ...                - Create a workload using the volume and wait for it to be running.
    ...                - Write test data to the volume for data integrity verification.
    ...                - Trigger volume expansion to 10Gi by updating PVC size.
    ...                - Disconnect network on the node where volume is attached for 100 seconds.
    ...                - Reconnect network automatically after timeout.
    ...                - Wait for node to recover and become ready.
    ...                - Verify volume expansion completes successfully within timeout.
    ...                - Verify workload does not stuck in Creating state for more than 5 minutes.
    ...                - Verify volume size is updated to 10Gi.
    ...                - Verify workload recovers to Running state.
    ...                - Verify test data integrity is maintained.
    ...                - Verify filesystem size is expanded to 10Gi.
    ...
    ...                Expected Results:
    ...                - Volume expansion should complete successfully after network recovery.
    ...                - Workload should recover without getting stuck in Creating state.
    ...                - No data loss or corruption should occur.
    ...                - Filesystem should be properly expanded.

    Given Create storageclass longhorn-test with    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=${VOLUME_TYPE}    sc_name=longhorn-test    storage_size=5Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 512 MB data to file data.txt in deployment 0

    When Expand deployment 0 volume to 10Gi
    And Disconnect volume node network of deployment 0 for 100 seconds
    And Wait for volume of deployment 0 attached
    And Wait for volume of deployment 0 healthy

    Then Wait for deployment 0 volume size expanded
    And Wait for workloads pods stable    deployment 0
    And Check deployment 0 data in file data.txt is intact
    And Assert filesystem size in deployment 0 is 10Gi

*** Test Cases ***
Disconnect Volume Node Network While Workload Heavy Writing With RWX Fast Failover Enabled
    Disconnect Volume Node Network While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=true

Disconnect Volume Node Network While Workload Heavy Writing With RWX Fast Failover Disabled
    Disconnect Volume Node Network While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=false

Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing With RWX Fast Failover Enabled
    Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=true

Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing With RWX Fast Failover Disabled
    Disconnect Volume Node Network For More Than Pod Eviction Timeout While Workload Heavy Writing    RWX_VOLUME_FAST_FAILOVER=false

Node Disconnect And Keep Data Writing And No Replica On The Disconnected Node
    [Documentation]    -- Manual test plan --
    ...                Disable auto-salvage.
    ...                Create a volume with 2 replicas on the 1st and the 2nd node.
    ...                Attach the volume to the 3rd node.
    ...                Keep writing data directly to the volume. (sudo dd if=/dev/urandom of=/dev/longhorn/test-1 bs=2M count=2048)
    ...                Disconnect the network of the node that the volume attached to for 100 seconds during the data writing. (sudo nohup ./network_down.sh 100)
    ...                Wait for the node back.
    ...                The volume should remain detached, and all replicas remain in ERROR state.
    Given Setting auto-salvage is set to false

    When Create volume 0 with 10 GB and no replicas on the attached node    dataEngine=${DATA_ENGINE}
    And Keep writing data to volume 0
    And Disconnect volume 0 node network for 100 seconds without waiting for completion

    Then Wait for disconnected node back
    And Check volume 0 kept in detached
    And Check all replicas of volume 0 kept in error

Node Disconnect And Keep Data Writing And Have Replica On The Disconnected Node
    [Documentation]    -- Manual test plan --
    ...                Disable auto-salvage.
    ...                Create a volume with 3 replicas.
    ...                Attach the volume to a node.
    ...                Keep writing data directly to the volume. (sudo dd if=/dev/urandom of=/dev/longhorn/test-1 bs=2M count=2048)
    ...                Disconnect the network of the node that the volume attached to for 100 seconds during the data writing. (sudo nohup ./network_down.sh 100)
    ...                Wait for the node back.
    ...                The volume will be in degraded state and then started the replica rebuilding process.
    ...                The volume become healthy.
    Given Setting auto-salvage is set to false

    When Create volume 0 with    size=10Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy

    When Keep writing data to volume 0
    And Disconnect volume 0 node network for 100 seconds without waiting for completion

    Then Wait for disconnected node back
    And Wait for volume 0 degraded
    And Wait for volume 0 healthy

Node Disconnect And No Replica On Disconnected Node
    [Documentation]    -- Manual test plan --
    ...                Disable auto-salvage.
    ...                Create a volume with 2 replicas on the 1st and the 2nd node.
    ...                Attach the volume to the 3rd node.
    ...                No need to write data to the volume. Directly disconnect the network of the node that the volume attached to for 100 seconds. (sudo nohup ./network_down.sh 100)
    ...                Wait for the node back.
    ...                The volume will be in an attached state with its robustness unknown at first, then the volume become healthy.
    Given Setting auto-salvage is set to false

    When Create volume 0 with 10 GB and no replicas on the attached node    dataEngine=${DATA_ENGINE}
    And Disconnect volume 0 node network for 100 seconds without waiting for completion

    Then Wait for disconnected node back
    And Wait for volume 0 attached
    And Wait for volume 0 healthy

Node Disconnect And Have Replica On Disconnected Node
    [Documentation]    -- Manual test plan --
    ...                Disable auto-salvage.
    ...                Create a volume with 3 replicas.
    ...                Attach the volume to a node.
    ...                No need to write data to the volume. Directly disconnect the network of the node that the volume attached to for 100 seconds. (sudo nohup ./network_down.sh 100)
    ...                Wait for the node back.
    ...                The volume will be in an attached state with its robustness unknown at first, then the volume become healthy.
    Given Setting auto-salvage is set to false

    When Create volume 0 with    size=10Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 1
    And Wait for volume 0 healthy
    And Disconnect volume 0 node network for 100 seconds without waiting for completion

    Then Wait for disconnected node back
    And Wait for volume 0 attached
    And Wait for volume 0 healthy

Node Disconnect With Statefulset
    [Documentation]    -- Manual test plan --
    ...                Launch Longhorn.
    ...                Use statefulset launch a pod with the volume and write some data.
    ...                Run command 'sync' in pod, make sure data fulshed.
    ...                Disconnect the node that the volume attached to for 100 seconds.
    ...                Wait for the node back and the volume reattachment.
    ...                The volume will be in an attached state with its robustness unknown at first, then the volume become healthy
    ...                Verify the data and the pod still works fine.
    ...                Repeat step 2~6 for 3 times.
    ...                Create, Attach, and detach other volumes to the recovered node. All volumes should work fine.
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Write 100 MB data to file data in statefulset 0

        When Disconnect volume node network of statefulset 0 for 100 seconds without waiting for completion
        And Wait for volume of statefulset 0 attached
        And Wait for disconnected node back
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 pods stable

        Then Check statefulset 0 data in file data is intact
    END

    When Create volume 0 with    size=1Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to statefulset 0 node
    And Wait for volume 0 healthy

    And Detach volume 0 from attached node
    And Wait for volume 0 detached
    Then Wait for volume 0 detached

Test Volume Expansion During Network Disconnect With RWO Volume
    [Tags]    expansion    rwo
    [Documentation]    Test RWO volume expansion behavior when attached node network is disconnected during expansion.
    Test Volume Expansion During Network Disconnect With Volume Type    RWO

Test Volume Expansion During Network Disconnect With RWX Volume
    [Tags]    expansion    rwx
    [Documentation]    Test RWX volume expansion behavior when share-manager node network is disconnected during expansion.
    Test Volume Expansion During Network Disconnect With Volume Type    RWX
