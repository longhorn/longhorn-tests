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
    ...
    ...                1. Create a new RWX migratable volume.
    ...                2. Attach to test node to write some test data on it.
    ...                3. Detach from test node.
    ...                4. Get set of nodes excluding the test node
    ...                5. Attach volume to node 1 (initial node)
    ...                6. Attach volume to node 2 (migration target)
    ...                7. Wait for migration ready (engine running on node 2)
    ...                8. Detach volume from node 1
    ...                9. Observe volume migrated to node 2 (single active engine)
    ...                10. Validate initially written test data
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
    ...
    ...                1. Create a new RWX migratable volume.
    ...                2. Attach to test node to write some test data on it.
    ...                3. Detach from test node.
    ...                4. Get set of nodes excluding the test node
    ...                5. Attach volume to node 1 (initial node)
    ...                6. Attach volume to node 2 (migration target)
    ...                7. Wait for migration ready (engine running on node 2)
    ...                8. Detach volume from node 2
    ...                9. Observe volume stayed on node 1 (single active engine)
    ...                10. Validate initially written test data
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
