*** Settings ***
Documentation    Test DR volume node reboot
...              https://github.com/longhorn/longhorn/issues/8425

Test Tags    manual longhorn-8425

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource


Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${RETRY_COUNT}    400
${LOOP_COUNT}    5
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Test Cases ***
DR Volume Node Reboot During Initial Restoration
    [Tags]  manual  longhorn-8425
    [Documentation]    Test DR volume node reboot
    ...                during initial restoration
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    Then Volume 0 backup 0 should be able to create
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Then Create DR volume 1 from backup 0    dataEngine=${DATA_ENGINE}
        And Wait for volume 1 restoration from backup 0 start
        Then Reboot volume 1 volume node
        And Wait for volume 1 restoration from backup 0 completed
        When Activate DR volume 1
        And Attach volume 1
        And Wait for volume 1 healthy
        Then Check volume 1 data is backup 0
        Then Detach volume 1
        And Delete volume 1
    END

DR Volume Node Reboot During Incremental Restoration
    [Tags]  manual  longhorn-8425
    [Documentation]    Test DR volume node reboot
    ...                During Incremental Restoration
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    Then Volume 0 backup 0 should be able to create
    Then Create DR volume 1 from backup 0    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 restoration from backup 0 completed
    Then Write data 1 to volume 0
    And Volume 0 backup 1 should be able to create
    And Wait for volume 1 restoration from backup 1 start
    Then Reboot volume 1 volume node
    Then Wait for volume 1 restoration from backup 1 completed
    And Activate DR volume 1
    And Attach volume 1
    And Wait for volume 1 healthy
    And Check volume 1 data is backup 1