*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${RWX_VOLUME_FAST_FAILOVER}    false
${DATA_ENGINE}    v1

*** Test Cases ***
Force Drain Volume Node While Replica Rebuilding
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 2048 MB data to file data.txt in deployment 0
    And Write 2048 MB data to file data.txt in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on volume node
        And Wait until volume of deployment 0 replica rebuilding started on volume node
        And Force drain volume of deployment 0 volume node

        Then Wait for volume of deployment 0 attached to another node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact

        When Delete replica of deployment 1 volume on volume node
        And Wait until volume of deployment 1 replica rebuilding started on volume node
        And Force drain volume of deployment 1 volume node

        Then Wait for volume of deployment 1 attached to another node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data.txt is intact
    END

Force Drain Replica Node While Replica Rebuilding
    Given Set setting rwx-volume-fast-failover to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create persistentvolumeclaim 1 using RWX volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 2048 MB data to file data.txt in deployment 0
    And Write 2048 MB data to file data.txt in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuilding started on replica node
        And Force drain volume of deployment 0 replica node

        Then Wait for volume of deployment 0 attached to the original node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact

        When Delete replica of deployment 1 volume on replica node
        And Wait until volume of deployment 1 replica rebuilding started on replica node
        And Force drain volume of deployment 1 replica node

        Then Wait for volume of deployment 1 attached to the original node and degraded
        And Uncordon the drained node
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data.txt is intact
    END
