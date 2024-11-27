*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/setting.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Delete Volume Node While Replica Rebuilding
    Given Set setting node-down-pod-deletion-policy to do-nothing
    And Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Write 2048 MB data to file data in deployment 0
    And Write 2048 MB data to file data in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on volume node
        And Wait until volume of deployment 0 replica rebuilding started on volume node
        And Delete volume of deployment 0 volume node

        Then Wait for volume of deployment 0 attached and unknown
        And Add deleted node back
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data is intact

        When Delete replica of deployment 1 volume on volume node
        And Wait until volume of deployment 1 replica rebuilding started on volume node
        And Delete volume of deployment 1 volume node

        Then Wait for volume of deployment 1 attached and unknown
        And Add deleted node back
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data is intact
    END

Delete Replica Node While Replica Rebuilding
    Given Set setting node-down-pod-deletion-policy to do-nothing
    And Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Write 2048 MB data to file data in deployment 0
    And Write 2048 MB data to file data in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuilding started on replica node
        And Delete volume of deployment 0 replica node

        Then Wait for volume of deployment 0 attached and degraded
        And Add deleted node back
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data is intact

        When Delete replica of deployment 1 volume on replica node
        And Wait until volume of deployment 1 replica rebuilding started on replica node
        And Delete volume of deployment 1 replica node

        Then Wait for volume of deployment 1 attached and degraded
        And Add deleted node back
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data is intact
    END
