*** Settings ***
Documentation    Negative Test Cases

Test Tags    vm-snapshot    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup host provider and test resources

*** Keywords ***
Cleanup host provider and test resources
    Delete vm snapshots
    Cleanup test resources

*** Test Cases ***
Take VM Snapshot On Volume Node While Workload Heavy Writing
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Create statefulset 1 using RWX volume with longhorn-test storageclass
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to pod of statefulset 0
        When Create vm snapshot on volume node of statefulset 0
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 pods stable
        Then Check statefulset 0 works

        And Keep writing data to pod of statefulset 1
        When Create vm snapshot on volume node of statefulset 1
        And Wait for volume of statefulset 1 healthy
        And Wait for statefulset 1 pods stable
        Then Check statefulset 1 works
    END

Take VM Snapshot On Volume Node While Replica Rebuilding
    Given Create volume 0 with    size=5Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete volume 0 replica on volume node
        And Wait until volume 0 replica rebuilding started on volume node
        And Create vm snapshot on node 0

        Then Wait until volume 0 replica rebuilding completed on volume node
        And Wait for volume 0 healthy
        And Check volume 0 data is intact
    END
