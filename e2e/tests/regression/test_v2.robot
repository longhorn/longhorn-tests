*** Settings ***
Documentation    v2 Data Engine Test Cases

Test Tags    regression    v2

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/node.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up v2 test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks

*** Test Cases ***
Test V2 Volume Basic
    [Tags]  coretest
    [Documentation]    Test basic v2 volume operations
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    When Create volume 0 with    dataEngine=v2
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0

Test V2 Snapshot
    [Tags]    coretest
    [Documentation]    Test snapshot operations
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create volume 0 with    dataEngine=v2
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

    When Delete snapshot 2 CR of volume 0
    Then Validate snapshot 2 is not in volume 0 snapshot list
    And Check volume 0 data is data 2

    When Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0 in maintenance mode
    And Wait for volume 0 healthy

    And Revert volume 0 to snapshot 1
    And Detach volume 0
    And Wait for volume 0 detached
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Check volume 0 data is data 1
    And Validate snapshot 1 is parent of volume-head in volume 0 snapshot list

    When Delete snapshot 1 CR of volume 0
    And Delete snapshot 0 CR of volume 0

    # delete a snapshot won't mark the snapshot as removed
    # but directly remove it from the snapshot list without purge
    Then Validate snapshot 1 is not in volume 0 snapshot list
    And Validate snapshot 0 is not in volume 0 snapshot list

    And Check volume 0 data is data 1

Degraded Volume Replica Rebuilding
    [Tags]    coretest    replica
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Disable node 2 scheduling
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 attached and degraded
    And Write 2048 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on node 0
        And Wait until volume of deployment 0 replica rebuilding completed on node 0
        And Delete replica of deployment 0 volume on node 1
        And Wait until volume of deployment 0 replica rebuilding completed on node 1
        And Wait for volume of deployment 0 attached and degraded
        And Wait for deployment 0 pods stable
        Then Check deployment 0 data in file data.txt is intact
    END

V2 Volume Should Block Trim When Volume Is Degraded
    [Tags]    cluster
    [Documentation]    Issues:
    ...    https://github.com/longhorn/longhorn-tests/pull/2114
    ...    https://github.com/longhorn/longhorn/issues/8430
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Setting auto-salvage is set to true
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0

        When Restart cluster
        And Wait for longhorn ready
        And Wait for volume of deployment 0 attached and degraded
        Then Trim deployment 0 volume should fail

        When Wait for workloads pods stable
        ...    deployment 0
        And Wait for volume of deployment 0 healthy
        And Check deployment 0 works
        Then Trim deployment 0 volume should pass
    END

V2 Volume Should Cleanup Resources When Instance Manager Is Deleted
    [Tags]    coretest
    [Documentation]    Verify that v2 volumes cleanup resources when their instance manager
    ...                is deleted. And ensure this process does not impact v1 volumes.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/9959

    When Create volume 0 with    dataEngine=v2
    And Create volume 1 with    dataEngine=v2
    And Create volume 2 with    dataEngine=v1
    And Attach volume 0 to node 0
    And Attach volume 1 to node 0
    And Attach volume 2 to node 0
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Wait for volume 2 healthy
    And Write data to volume 0
    And Write data to volume 1
    And Write data to volume 2

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Cordon node 0
        And Delete v2 instance manager of volume 0

        Then Assert DM device for volume 0 not exist on node 0
        And Assert DM device for volume 1 not exist on node 0
        And Assert device for volume 0 not exist on node 0
        And Assert device for volume 1 not exist on node 0
        And Assert device for volume 2 does exist on node 0

        When Uncordon node 0
        And Wait for volume 0 healthy
        And Wait for volume 1 healthy
        And Wait for volume 2 healthy

        Then Assert DM device for volume 0 does exist on node 0
        And Assert DM device for volume 1 does exist on node 0
        And Assert device for volume 0 does exist on node 0
        And Assert device for volume 1 does exist on node 0
        And Assert device for volume 2 does exist on node 0
        And Check volume 0 data is intact
        And Check volume 1 data is intact
        And Check volume 2 data is intact
    END

Test V2 Data Engine Selective Activation
    [Tags]    replica
    # create volumes with 2 replicas on node 0 and node 1
    # there is no replica on node 2
    Given Create volume 0 attached to node 0 with 2 replicas excluding node 2    dataEngine=v2
    And Create volume 1 attached to node 0 with 2 replicas excluding node 2    dataEngine=v1

    When Label node 2 with node.longhorn.io/disable-v2-data-engine=true
    Then Check v2 instance manager is not running on node 2
    And Check v1 instance manager is running on node 2

    When Label node 2 with node.longhorn.io/disable-v2-data-engine-
    Then Check v2 instance manager is running on node 2

    When Update volume 0 replica count to 3
    And Wait for volume 0 healthy
    Then Volume 0 should have running replicas on node 2

Test V2 Data Engine Selective Activation During Replica Rebuilding
    [Tags]    replica
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create volume 0 attached to node 0 with 2 replicas excluding node 2    dataEngine=v2
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Label node 2 with node.longhorn.io/disable-v2-data-engine=true
    And Delete volume 0 replica on node 0
    And Wait until volume 0 replicas rebuilding completed
    And Delete volume 0 replica on node 1
    And Wait until volume 0 replicas rebuilding completed
    Then Volume 0 should have 0 replicas on node 2
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test V2 Data Engine Selective Activation With Existing Engine And Replica
    [Tags]    replica
    # create a volume with replicas on node 0 and node 1
    # and attach it to node 2
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    Given Create volume 0 attached to node 2 with 2 replicas excluding node 2    dataEngine=v2

    ${node_0}=    Get Node By Index    0
    When Run command and expect output
    ...    kubectl label node ${node_0} node.longhorn.io/disable-v2-data-engine=true
    ...    cannot disable v2 data engine

    ${node_2}=    Get Node By Index    2
    When Run command and expect output
    ...    kubectl label node ${node_2} node.longhorn.io/disable-v2-data-engine=true
    ...    cannot disable v2 data engine

Check Block Device Is Not In Use Before Creating Disk
    [Documentation]    Issue:
    ...    https://github.com/longhorn/longhorn/issues/12179
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    When Create 1 Gi block type device block-device-check on node 0
    And Run command on node    0
    ...    sudo mkfs.xfs ${mount_path}
    And Add block device block-device-check on node 0 should result in unschedulable state
    And Disable disk block-device-check scheduling without ready check on node 0
    And Delete disk block-device-check on node 0

    When Run command on node    0
    ...    sudo wipefs -a ${mount_path}
    And Add block device block-device-check on node 0 should success
