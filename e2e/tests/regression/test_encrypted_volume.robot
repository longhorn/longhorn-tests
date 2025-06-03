*** Settings ***
Documentation    Encrypted Volume Test Cases

Test Tags    encrypted

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Encrypted Volume Basic
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact
