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

*** Variables ***
${INSTANCE_MANAGER_CRASH_LOOP_COUNT}    3

*** Keywords ***
Test Instance Manager Crash During Workload Pod Starting
    [Arguments]    ${access_mode}    ${encrypted}

    IF    ${encrypted}
        Create crypto secret
        ${sc_name}=    Set Variable    longhorn-crypto
        Create storageclass ${sc_name} with    encrypted=true    dataEngine=${DATA_ENGINE}
    ELSE
        ${sc_name}=    Set Variable    longhorn-test
        Create storageclass ${sc_name} with    dataEngine=${DATA_ENGINE}
    END

    When Create persistentvolumeclaim 0    volume_type=${access_mode}    sc_name=${sc_name}
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    FOR    ${i}    IN RANGE    ${INSTANCE_MANAGER_CRASH_LOOP_COUNT}
        When Delete ${DATA_ENGINE} instance manager of deployment 0 volume
        # after deleting instance manager, the workload pod will be recrated as well
        And Wait for deployment 0 pods stable
        And Wait for volume of deployment 0 healthy
        Then Check deployment 0 data in file data.txt is intact

        And Delete pod of deployment 0    wait=False
        # the purpose of this test case is to verify the behavior when the instance manager crashes
        # while the workload pod is still being created, before it's fully running
        # but it's hard to catch the timing when the pod is being created
        # so the test is repeated to increase the chance to catch the timing,
        # and relax the waiting condition to "creating or running" instead of just "creating"
        And Wait for deployment 0 pods container creating or running
    END

Test Instance Manager Crash During Backup Restoration
    [Arguments]    ${access_mode}    ${encrypted}

    IF    ${encrypted}
        Create volume 0 with    dataEngine=${DATA_ENGINE}    accessMode=${access_mode}    encrypted=true
    ELSE
        Create volume 0 with    dataEngine=${DATA_ENGINE}    accessMode=${access_mode}
    END

    When Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0

    IF    ${encrypted}
        Create volume 1 from backup 0 of volume 0    dataEngine=${DATA_ENGINE}    encrypted=true
    ELSE
        Create volume 1 from backup 0 of volume 0    dataEngine=${DATA_ENGINE}
    END

    When Wait for volume 1 restoration from backup 0 of volume 0 start
    # crash one engines by killing their instance-manager pods
    And Delete ${DATA_ENGINE} instance manager of volume 1

    Then Wait for volume 1 restoration to complete
    When Attach volume 1 to healthy node
    Then Wait for volume 1 healthy
    And Check volume 1 data is backup 0 of volume 0

*** Test Cases ***
Crash Instance Manager While RWO Workload Pod Is Starting
    [Tags]    rwo    volume
    Test Instance Manager Crash During Workload Pod Starting    access_mode=RWO    encrypted=${False}

Crash Instance Manager While RWO Encrypted Workload Pod Is Starting
    [Tags]    encrypted    rwo    volume
    Test Instance Manager Crash During Workload Pod Starting    access_mode=RWO    encrypted=${True}

Crash Instance Manager While RWX Workload Pod Is Starting
    [Tags]    rwx    volume
    Test Instance Manager Crash During Workload Pod Starting    access_mode=RWX    encrypted=${False}

Crash Instance Manager While RWX Encrypted Workload Pod Is Starting
    [Tags]    encrypted    rwx    volume
    Test Instance Manager Crash During Workload Pod Starting    access_mode=RWX    encrypted=${True}

Crash Single Instance Manager While RWO Volume Backup Is Restoring
    [Tags]    rwo    volume    backup-restore
    Test Instance Manager Crash During Backup Restoration    access_mode=RWO    encrypted=${False}

Crash Single Instance Manager While RWO Encrypted Volume Backup Is Restoring
    [Tags]    encrypted    rwo    volume    backup-restore
    Test Instance Manager Crash During Backup Restoration    access_mode=RWO    encrypted=${True}

Crash Single Instance Manager While RWX Volume Backup Is Restoring
    [Tags]    rwx    volume    backup-restore
    Test Instance Manager Crash During Backup Restoration    access_mode=RWX    encrypted=${False}

Crash Single Instance Manager While RWX Encrypted Volume Backup Is Restoring
    [Tags]    encrypted    rwx    volume    backup-restore
    Test Instance Manager Crash During Backup Restoration    access_mode=RWX    encrypted=${True}
