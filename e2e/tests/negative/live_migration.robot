*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/host.resource
Resource    ../keywords/migration.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources


*** Test Cases ***
Migration Confirmation After Migration Node Down
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    And Get volume 0 engine and replica names

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # power off migration node
    When Power off node 1
    # migration confirmation by detaching from the original node
    And Detach volume 0 from node 0

    # volume stuck in attaching status and waiting for migration node to come back
    Then Check volume 0 kept in attaching
    And Volume 0 migration should fail or rollback

    # power on migration node
    When Power on off nodes

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
