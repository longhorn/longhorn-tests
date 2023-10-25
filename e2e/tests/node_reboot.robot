*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/workload.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${VOLUME_TYPE}    rwo

*** Test Cases ***
Reboot Node One By One While Workload Heavy Writing
    Given Create deployment 0 with rwo volume
    And Create deployment 1 with rwx volume
    And Create deployment 2 with rwo and strict-local volume
    And Create statefulset 0 with rwo volume
    And Create statefulset 1 with rwx volume
    And Create statefulset 2 with rwo and strict-local volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to deployment 0
        And Keep writing data to deployment 1
        And Keep writing data to deployment 2
        And Keep writing data to statefulset 0
        And Keep writing data to statefulset 1
        And Keep writing data to statefulset 2

        When Reboot node 0
        And Reboot node 1
        And Reboot node 2
        And Wait for longhorn ready

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Power Off Node One By Once For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Create deployment 0 with rwo volume
    And Create deployment 1 with rwx volume
    And Create deployment 2 with rwo and strict-local volume
    And Create statefulset 0 with rwo volume
    And Create statefulset 1 with rwx volume
    And Create statefulset 2 with rwo and strict-local volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to deployment 0
        And Keep writing data to deployment 1
        And Keep writing data to deployment 2
        And Keep writing data to statefulset 0
        And Keep writing data to statefulset 1
        And Keep writing data to statefulset 2

        When Power off node 0 for 6 mins
        And Power off node 1 for 6 mins
        And Power off node 2 for 6 mins
        And Wait for longhorn ready

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Reboot All Worker Nodes While Workload Heavy Writing
    Given Create deployment 0 with rwo volume
    And Create deployment 1 with rwx volume
    And Create deployment 2 with rwo and strict-local volume
    And Create statefulset 0 with rwo volume
    And Create statefulset 1 with rwx volume
    And Create statefulset 2 with rwo and strict-local volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to deployment 0
        And Keep writing data to deployment 1
        And Keep writing data to deployment 2
        And Keep writing data to statefulset 0
        And Keep writing data to statefulset 1
        And Keep writing data to statefulset 2

        When Restart all worker nodes
        And Wait for longhorn ready

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Power Off All Worker Nodes For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Create deployment 0 with rwo volume
    And Create deployment 1 with rwx volume
    And Create deployment 2 with rwo and strict-local volume
    And Create statefulset 0 with rwo volume
    And Create statefulset 1 with rwx volume
    And Create statefulset 2 with rwo and strict-local volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to deployment 0
        And Keep writing data to deployment 1
        And Keep writing data to deployment 2
        And Keep writing data to statefulset 0
        And Keep writing data to statefulset 1
        And Keep writing data to statefulset 2

        When Power off all worker nodes for 6 mins
        And Wait for longhorn ready

        Then Check deployment 0 works
        And Check deployment 1 works
        And Check deployment 2 works
        And Check statefulset 0 works
        And Check statefulset 1 works
        And Check statefulset 2 works
    END

Reboot Volume Node While Workload Heavy Writing
    Given Create statefulset 0 with ${VOLUME_TYPE} volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to statefulset 0

        When Reboot volume node of statefulset 0
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 stable

        Then Check statefulset 0 works
    END

Power Off Volume Node For More Than Pod Eviction Timeout While Workload Heavy Writing
    Given Create statefulset 0 with rwo volume

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        And Keep writing data to statefulset 0

        When Power off volume node of statefulset 0 for 6 mins
        And Wait for volume of statefulset 0 healthy
        And Wait for statefulset 0 stable

        Then Check statefulset 0 works
    END
