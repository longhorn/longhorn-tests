*** Settings ***
Documentation    Negative Test Cases

Test Tags    manual    negative    instance-manager

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Crash Instance Manager While RWO Encrypted Workload Pod Is Starting
    [Tags]    encrypted    rwo   volume
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete ${DATA_ENGINE} instance manager of deployment 0 volume
        # after deleting instance manager, the workload pod will be recrated as well
        And Wait for deployment 0 pods stable
        And Wait for volume of deployment 0 healthy
        Then Check deployment 0 data in file data.txt is intact

        And Delete pod of deployment 0    wait=False
        And Wait for deployment 0 pods container creating
    END

Crash Instance Manager While RWX Encrypted Workload Pod Is Starting
    [Tags]    encrypted    rwx    volume
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-crypto
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete ${DATA_ENGINE} instance manager of deployment 0 volume
        # after deleting instance manager, the workload pod will be recrated as well
        And Wait for deployment 0 pods stable
        And Wait for volume of deployment 0 healthy
        Then Check deployment 0 data in file data.txt is intact

        And Delete pod of deployment 0    wait=False
        And Wait for deployment 0 pods container creating
    END

Crash Single Instance Manager While RWO Encrypted Volume Backup Is Restoring
    [Tags]    encrypted    rwo    volume    backup-restore
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}    accessMode=RWO    encrypted=true
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0

    When Create volume 1 from backup 0 of volume 0  dataEngine=${DATA_ENGINE}  encrypted=true
    And Wait for volume 1 restoration from backup 0 of volume 0 start
    # crash one engines by killing their instance-manager pods
    And Delete ${DATA_ENGINE} instance manager of volume 1

    Then Wait for volume 1 restoration to complete
    When Attach volume 1 to healthy node
    Then Wait for volume 1 healthy
    And Check volume 1 data is backup 0 of volume 0

Crash Single Instance Manager While RWX Encrypted Volume Backup Is Restoring
    [Tags]    encrypted    rwx    volume    backup-restore
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}    accessMode=RWX    encrypted=true
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0

    When Create volume 1 from backup 0 of volume 0  dataEngine=${DATA_ENGINE}  encrypted=true
    And Wait for volume 1 restoration from backup 0 of volume 0 start
    # crash one engines by killing their instance-manager pods
    And Delete ${DATA_ENGINE} instance manager of volume 1

    Then Wait for volume 1 restoration to complete
    When Attach volume 1 to healthy node
    Then Wait for volume 1 healthy
    And Check volume 1 data is backup 0 of volume 0
