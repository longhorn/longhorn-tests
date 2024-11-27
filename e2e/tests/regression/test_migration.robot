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
    And Write data to volume 0
    And Attach volume 0 to node 1
    Then Wait for volume 0 migration ready
    And Detach volume 0 from node 0
    And Wait for volume 0 migrated to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
