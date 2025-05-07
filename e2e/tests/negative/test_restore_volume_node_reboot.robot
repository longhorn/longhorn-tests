*** Settings ***
Documentation    The node the restore volume attached to is down
...              - Issue: https://github.com/longhorn/longhorn/issues/1355
...              - Issue: https://github.com/longhorn/longhorn/issues/9865
...              - Test the restoration process of a Longhorn volume when the attached node goes down.
...              - Includes verification for both encrypted and non-encrypted volumes.

Test Tags    manual    negative    longhorn-9865

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/k8s.resource


Test Setup    Set test environment
Test Teardown    Cleanup test resources
Test Template    Restore volume attached node is down

*** Keywords ***
Restore volume attached node is down
    [Arguments]    ${description}    ${encrypted}
    [Documentation]    Test the behavior of restoring a Longhorn volume when the attached node goes down.
    ...                Arguments:
    ...                - ${description}: Description of the test case.
    ...                - ${encrypted}: Boolean to specify if the volume is encrypted (true/false).
    ...                - Manual Test Plan
    ...                - Given Create a volume 0 with 3 replicas.
    ...                - And Attach the volume 0 to a node.
    ...                - And Write data 0 to the volume 0.
    ...                - Then Create a backup of the volume 0.
    ...                - When Restore the backup to volume 1.
    ...                - And During the restoration, power off the node where the volume 1 is attached.
    ...                - And Wait for the restoration to complete.
    ...                - Then Attach the restored volume 1 to a healthy node.
    ...                - Then Verify the restored data matches the backup.
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}    encrypted=${encrypted}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data 0 to volume 0
    And Create backup 0 for volume 0
    And Verify backup list contains backup 0 of volume 0

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Create volume 1 from backup 0 of volume 0  dataEngine=${DATA_ENGINE}  encrypted=${encrypted}
        And Wait for volume 1 restoration from backup 0 of volume 0 start
        And Power off volume 1 volume node without waiting
        Then Wait for volume 1 restoration to complete

        When Attach volume 1 to healthy node
        Then Wait for volume 1 degraded
        And Check volume 1 data is backup 0 of volume 0
        And Detach volume 1 from attached node
        And Delete volume 1
        And Power on off nodes
    END

    And Detach volume 0 from attached node
    And Delete volume 0

*** Test Cases ***    DESCRIPTION    ENCRYPTED
Test Volume Attached Node Is Down During Volume Restoration
    Test Restore Non-encrypted Volume Node Down    false

Test Volume Attached Node Is Down During Encrypted Volume Restoration
    Test Restore Encrypted Volume Node Down    true
