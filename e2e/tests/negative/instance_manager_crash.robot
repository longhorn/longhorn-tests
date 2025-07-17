*** Settings ***
Documentation    Negative Test Cases

Test Tags    manual    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Crash Instance Manager While Workload Pod Is Starting
    [Tags]    encrypted
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete instance-manager of deployment 0 volume
        # after deleting instance manager, the workload pod will be recrated as well
        And Wait for deployment 0 pods stable
        And Wait for volume of deployment 0 healthy
        Then Check deployment 0 data in file data.txt is intact

        And Delete pod of deployment 0    wait=False
        And Wait for deployment 0 pods container creating
    END
