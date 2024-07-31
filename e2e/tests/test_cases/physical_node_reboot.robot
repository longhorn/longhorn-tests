*** Settings ***
Documentation    Physical node reboot

Test Tags    manual_test_case

Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/host.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${VOLUME_TYPE}    RWO
${DATA_ENGINE}    v1

*** Test Cases ***
Physical Node Reboot With Attached Deployment
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using ${VOLUME_TYPE} volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 100 MB data to file data in deployment 0

    And Reboot volume node of deployment 0
    And Wait for deployment 0 pods stable
    Then Check deployment 0 data in file data is intact

Physical Node Reboot With Attached Statefulset
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using ${VOLUME_TYPE} volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0

    And Reboot volume node of statefulset 0
    And Wait for statefulset 0 pods stable
    Then Check statefulset 0 data in file data is intact
