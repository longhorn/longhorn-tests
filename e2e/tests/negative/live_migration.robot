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

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # power off migration node
    When Power off node 1
    # migration confirmation by detaching from the original node
    And Detach volume 0 from node 0

    # volume stuck in attaching status and waiting for migration node to come back
    Then Check volume 0 kept in attaching

    # power on migration node
    When Power on off nodes

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Rollback After Migration Node Down
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # power off migration node
    When Power off node 1
    # migration rollback by detaching from the migration node
    And Detach volume 0 from node 1

    # migration rollback succeed
    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 degraded
    And Check volume 0 data is intact

Migration Confirmation After Original Node Down
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # power off original node
    When Power off node 0
    # migration confirmation by detaching from the original node
    And Detach volume 0 from node 0

    # migration is stuck until the Kubernetes pod eviction controller decides to
    # terminate the instance-manager pod that was running on the original node.
    # then Longhorn detaches the volume and cleanly reattaches it to the migration node.
    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 degraded
    And Check volume 0 data is intact

Migration Rollback After Original Node Down
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # power off original node
    When Power off node 0
    # migration rollback by detaching from the migration node
    And Detach volume 0 from node 1

    # migration is stuck until the Kubernetes pod eviction controller decides to
    # terminate the instance-manager pod that was running on the original node.
    # then Longhorn detaches the volume and attempts to cleanly reattach it to the original node,
    # but it is stuck in attaching until the node comes back.
    Then Check volume 0 kept in attaching

    # power on original node
    When Power on off nodes

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
