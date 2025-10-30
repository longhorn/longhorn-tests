*** Settings ***
Documentation    Negative Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/host.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Get current minute plus two
    ${minute}=    Get Current Date    result_format=%M
    ${minute}=    Convert To Integer    ${minute}
    ${minute}=    Evaluate    (${minute} + 2) % 60
    Set Test Variable    ${minute}

*** Test Cases ***
Recurring backup job interruptions when Allow Recurring Job While Volume Is Detached is disabled
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.1.0/recurring-backup-job-interruptions/
    ...                Scenario 1- Allow Recurring Job While Volume Is Detached disabled, attached pod scaled down while the recurring backup was in progress.
    Given Setting allow-recurring-job-while-volume-detached is set to false
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass and size 5 Gi
    And Write 4096 MB data to file data in statefulset 0

    When Create backup recurringjob 0
    ...    groups=["default"]
    ...    cron=*/2 * * * *
    ...    concurrency=1
    ...    labels={"test":"recurringjob"}

    Then Wait for backup recurringjob 0 started
    And Scale statefulset 0 to 0
    And Verify backup list contains backup no error for statefulset 0 volume
    And Wait for statefulset 0 volume detached

    When Sleep    180
    And Verify no new backup created

Recurring backup job interruptions when Allow Recurring Job While Volume Is Detached is enabled
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.1.0/recurring-backup-job-interruptions/
    ...                Scenario 2- Allow Recurring Job While Volume Is Detached enabled, attached pod scaled down while the recurring backup was in progress.
    Given Setting allow-recurring-job-while-volume-detached is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass and size 5 Gi
    And Write 4096 MB data to file data in statefulset 0

    When Create backup recurringjob 0
    ...    groups=["default"]
    ...    cron=*/2 * * * *
    ...    concurrency=1
    ...    labels={"test":"recurringjob"}

    Then Wait for backup recurringjob 0 started
    And Scale statefulset 0 to 0
    And Verify backup list contains backup no error for statefulset 0 volume
    And Wait for statefulset 0 volume detached
    
    When Wait for backup recurringjob 0 started
    And Verify backup list contains backup no error for statefulset 0 volume
    And Wait for statefulset 0 volume detached

Recurring backup interruption by node down when cron job and volume on same node
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.1.0/recurring-backup-job-interruptions/
    ...                Scenario 3- Cron job and volume attached to the same node, Node is powered down and volume detached.
    Given Setting allow-recurring-job-while-volume-detached is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass and size 5 Gi
    And Write 4096 MB data to file data in statefulset 0
    # Ensure the cron job pod and volume run on the same node
    And Cordon all other nodes beside statefulset 0 volume node
    And Scale down statefulset 0 to detach volume

    When Get current minute plus two
    And Create backup recurringjob 0
    ...    groups=["default"]
    ...    cron=${minute} * * * *
    ...    concurrency=1
    ...    labels={"test":"recurringjob"}
    
    Then Wait for backup recurringjob 0 started
    And Wait for statefulset 0 volume attached
    And Power off volume node of statefulset 0
    And Wait for statefulset 0 volume detached
    And Uncordon nodes

    When Wait until new pod for backup recurringjob 0 is created
    And Wait for backup recurringjob 0 complete
    And Wait for statefulset 0 volume detached

Recurring backup interruption by node restart when cron job and volume on same node
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.1.0/recurring-backup-job-interruptions/
    ...                Scenario 4- Cron job and volume attached to the same node, Node is restarted.
    Given Setting allow-recurring-job-while-volume-detached is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass and size 5 Gi
    And Write 4096 MB data to file data in statefulset 0
    # Ensure the cron job pod and volume run on the same node
    And Cordon all other nodes beside statefulset 0 volume node
    And Scale down statefulset 0 to detach volume

    When Get current minute plus two
    And Create backup recurringjob 0
    ...    groups=["default"]
    ...    cron=${minute} * * * *
    ...    concurrency=1
    ...    labels={"test":"recurringjob"}

    Then Wait for backup recurringjob 0 started
    And Wait for statefulset 0 volume attached
    And Power off volume node of statefulset 0
    And Wait for statefulset 0 volume detached

    When Power on off nodes
    And Wait for backup recurringjob 0 complete
    And Wait for statefulset 0 volume detached

Recurring backup job interruptions when node is powered down and Pod Deletion Policy is delete-both-statefulset-and-deployment-pod
    [Documentation]    https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.1.0/recurring-backup-job-interruptions/
    ...                Scenario 5- Cron job and volume attached to the same/different node, Node is powered down
    ...                            and Pod Deletion Policy When Node is Down is set as delete-both-statefulset-and-deployment-pod
    Given Setting node-down-pod-deletion-policy is set to delete-both-statefulset-and-deployment-pod
    Given Setting allow-recurring-job-while-volume-detached is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass and size 5 Gi
    And Write 4096 MB data to file data in statefulset 0

    When Get current minute plus two
    And Create backup recurringjob 0
    ...    groups=["default"]
    ...    cron=${minute} * * * *
    ...    concurrency=1
    ...    labels={"test":"recurringjob"}

    Then Wait for backup recurringjob 0 started
    And Power off volume node of statefulset 0
    And Sleep    180

    When Wait until new pod for backup recurringjob 0 is created
    And Wait for volume of statefulset 0 attached to another node
    And Wait for backup recurringjob 0 complete
