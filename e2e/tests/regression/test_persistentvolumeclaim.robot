*** Settings ***
Documentation    PersistentVolumeClaim Test Cases

Test Tags    regression

Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/variables.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1

*** Test Cases ***

Test persistentvolumeclaim expand more than storage maximum size should fail
    [Tags]    volume    expansion
    [Documentation]    Verify that a PersistentVolumeClaim cannot be expanded beyond
    ...                the storage maximum size.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/6633

    Given Set setting storage-over-provisioning-percentage to 100
    And Create persistentvolumeclaim 0 using RWX volume    storage_size=2GiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 10 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Expand deployment 0 volume more than storage maximum size should fail
        Then Assert volume size of deployment 0 remains 2GiB for at least 5 seconds
        And Assert persistentvolumeclaim 0 requested size remains 2GiB for at least 5 seconds
        And Check deployment 0 data in file data.txt is intact

        When Expand deployment 0 volume by 1 GiB
        Then Assert persistentvolumeclaim 0 requested size remains 3GiB for at least 5 seconds
        And Assert volume size of deployment 0 remains 3GiB for at least 5 seconds
        And Check deployment 0 data in file data.txt is intact
    END
