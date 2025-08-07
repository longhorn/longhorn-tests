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
Resource    ../keywords/sharemanager.resource

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

Test Encrypted RWX Volume Online Expansion
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-crypto    storage_size=50MiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 10 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Expand deployment 0 volume to 100 MiB
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    # Verify the actual disk size in the sharemanager pod.
    # NOTE: For encrypted volumes, 16MiB is reserved for the encryption header.
    # Therefore, a 100MiB requested volume will result in an 84MiB actual disk size.
    And Assert encrypted disk size in sharemanager pod for deployment 0 is 84MiB

    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact
