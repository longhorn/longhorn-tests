*** Settings ***
Documentation    Migration Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/migration.resource
Resource    ../keywords/snapshot.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Migration Confirm
    [Tags]    coretest    migration
    [Documentation]    Test that a migratable RWX volume can be live migrated from one node to another.

    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    When Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Get volume 0 engine and replica names
    And Write data to volume 0
    And Attach volume 0 to node 1
    Then Wait for volume 0 migration to be ready
    And Detach volume 0 from node 0
    And Wait for volume 0 to migrate to node 1    
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Migration Rollback
    [Tags]    coretest    migration
    [Documentation]    Test that a migratable RWX volume can be rolled back to initial node.

    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    When Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Get volume 0 engine and replica names
    And Write data to volume 0
    And Attach volume 0 to node 1
    Then Wait for volume 0 migration to be ready
    And Detach volume 0 from node 1
    And Wait for volume 0 to stay on node 0
    And Volume 0 migration should fail or rollback
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Test Snapshot Purge Rejection While Migration
    [Tags]    coretest    migration
    [Documentation]    Test that a snapshot purge request is rejected while migration is in progress.

    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    When Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Get volume 0 engine and replica names
    And Write data to volume 0
    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready
    Then Purge volume 0 snapshot should fail
