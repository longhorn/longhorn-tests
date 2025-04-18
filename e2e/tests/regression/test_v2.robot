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
Resource    ../keywords/node.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/k8s.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test V2 Volume Basic
    [Tags]  coretest
    [Documentation]    Test basic v2 volume operations
    When Create volume 0 with    dataEngine=v2
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Check volume 0 data is intact
    And Detach volume 0
    And Wait for volume 0 detached
    And Delete volume 0

Degraded Volume Replica Rebuilding
    [Tags]    coretest
    Given Disable node 2 scheduling
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
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
    Given Set setting auto-salvage to true
    And Create storageclass longhorn-test with    dataEngine=v2
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of deployment 0

        When Restart cluster
        And Wait for longhorn ready
        And Wait for volume of deployment 0 attached and degraded
        Then Trim deployment 0 volume should fail

        When Wait for workloads pods stable
        ...    deployment 0
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
        And Delete instance-manager of volume 0

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

Test Creating V2 Volume With Backing Image After Replica Rebuilding
    Given Create volume 0 with    dataEngine=v2
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0

    And Create backing image bi-v2 with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=v2

    When Delete volume 0 replica on node 1
    And Wait until volume 0 replica rebuilding started on node 1
    And Wait until volume 0 replica rebuilding completed on node 1
    And Wait for volume 0 healthy
    Then Check volume 0 data is data 0

    When Create volume 1 with    size=3Gi    backingImage=bi-v2    dataEngine=v2
    And Create persistentvolume for volume 1
    And Create persistentvolumeclaim for volume 1
    And Create pod 1 using volume 1
    And Wait for pod 1 running
    And Write 1024 MB data to file data.txt in pod 1
