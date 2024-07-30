*** Settings ***
Documentation    Node disconnection test
...              https://github.com/longhorn/longhorn/issues/1545

Test Tags    manual_test_case

Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/network.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/workload.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    3
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Test Cases ***
Node Disconnect And Keep Data Writing And No Replica On The Disconnected Node
    [Documentation]    -- Manual test plan --
    ...                Disable auto-salvage.
    ...                Create a volume with 2 replicas on the 1st and the 2nd node.
    ...                Attach the volume to the 3rd node.
    ...                Keep writing data directly to the volume. (sudo dd if=/dev/urandom of=/dev/longhorn/test-1 bs=2M count=2048)
    ...                Disconnect the network of the node that the volume attached to for 100 seconds during the data writing. (sudo nohup ./network_down.sh 100)
    ...                Wait for the node back.
    ...                The volume should remain detached, and all replicas remain in ERROR state.
    Given Set setting auto-salvage to false

    When Create volume 0 with 10 GB and no replicas on the attached node
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
    Given Set setting auto-salvage to false

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
    Given Set setting auto-salvage to false

    When Create volume 0 with 10 GB and no replicas on the attached node
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
    Given Set setting auto-salvage to false

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
    Then Wait for volume 0 detached
