*** Settings ***
Documentation    Negative Test Cases
Resource    ../keywords/workload.resource
Resource    ../keywords/node.resource
Resource    ../keywords/common.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1

*** Test Cases ***
Reboot Node One By One While Workload Heavy Writing
    Create deployment 0 with rwo volume
    Create deployment 1 with rwx volume
    Create deployment 2 with rwo and strict-local volume
    Create statefulset 0 with rwo volume
    Create statefulset 1 with rwx volume
    Create statefulset 2 with rwo and strict-local volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Keep writing data to deployment 0
        Keep writing data to deployment 1
        Keep writing data to deployment 2
        Keep writing data to statefulset 0
        Keep writing data to statefulset 1
        Keep writing data to statefulset 2
        Reboot node 0
        Reboot node 1
        Reboot node 2
        Wait for longhorn ready
        Check deployment 0 works
        Check deployment 1 works
        Check deployment 2 works
        Check statefulset 0 works
        Check statefulset 1 works
        Check statefulset 2 works
    END

Power Off Node One By Once For More Than Pod Eviction Timeout While Workload Heavy Writing
    Create deployment 0 with rwo volume
    Create deployment 1 with rwx volume
    Create deployment 2 with rwo and strict-local volume
    Create statefulset 0 with rwo volume
    Create statefulset 1 with rwx volume
    Create statefulset 2 with rwo and strict-local volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Keep writing data to deployment 0
        Keep writing data to deployment 1
        Keep writing data to deployment 2
        Keep writing data to statefulset 0
        Keep writing data to statefulset 1
        Keep writing data to statefulset 2
        Power off node 0 for 6 mins
        Power off node 1 for 6 mins
        Power off node 2 for 6 mins
        Wait for longhorn ready
        Check deployment 0 works
        Check deployment 1 works
        Check deployment 2 works
        Check statefulset 0 works
        Check statefulset 1 works
        Check statefulset 2 works
    END

Reboot All Worker Nodes While Workload Heavy Writing
    Create deployment 0 with rwo volume
    Create deployment 1 with rwx volume
    Create deployment 2 with rwo and strict-local volume
    Create statefulset 0 with rwo volume
    Create statefulset 1 with rwx volume
    Create statefulset 2 with rwo and strict-local volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Keep writing data to deployment 0
        Keep writing data to deployment 1
        Keep writing data to deployment 2
        Keep writing data to statefulset 0
        Keep writing data to statefulset 1
        Keep writing data to statefulset 2
        Reboot all worker nodes
        Wait for longhorn ready
        Check deployment 0 works
        Check deployment 1 works
        Check deployment 2 works
        Check statefulset 0 works
        Check statefulset 1 works
        Check statefulset 2 works
    END

Power Off All Worker Nodes For More Than Pod Eviction Timeout While Workload Heavy Writing
    Create deployment 0 with rwo volume
    Create deployment 1 with rwx volume
    Create deployment 2 with rwo and strict-local volume
    Create statefulset 0 with rwo volume
    Create statefulset 1 with rwx volume
    Create statefulset 2 with rwo and strict-local volume
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Keep writing data to deployment 0
        Keep writing data to deployment 1
        Keep writing data to deployment 2
        Keep writing data to statefulset 0
        Keep writing data to statefulset 1
        Keep writing data to statefulset 2
        Power off all worker nodes for 6 mins
        Wait for longhorn ready
        Check deployment 0 works
        Check deployment 1 works
        Check deployment 2 works
        Check statefulset 0 works
        Check statefulset 1 works
        Check statefulset 2 works
    END