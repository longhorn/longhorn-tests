*** Settings ***
Documentation    Migration Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/migration.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
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
    [Tags]    coretest    migration    snapshot-purge
    [Documentation]    Test that a snapshot purge request is rejected while migration is in progress.

    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    When Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Get volume 0 engine and replica names
    And Write data to volume 0
    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready
    Then Purge volume 0 snapshot should fail

Test Migration While Replica Rebuilding
    [Tags]    coretest    migration    replica-rebuilding
    [Documentation]    https://github.com/longhorn/longhorn/issues/14153
    ...    Verify migration during replica rebuilding completes without getting stuck
    ...    and preserves data integrity.
    Given Cordon node 1
    And Cordon node 2
    And Create storageclass migration-rebuilding with
    ...    numberOfReplicas=3    migratable=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0
    ...    sc_name=migration-rebuilding    storage_size=4Gi    volume_type=RWX    volumeMode=Block
    And Wait for persistentvolumeclaim 0 status to be Bound
    ${volume_name} =    Get volume name of persistentvolumeclaim 0
    When Attach volume ${volume_name} to node 0
    And Wait for volume ${volume_name} degraded
    And Write data to volume ${volume_name}

    When Uncordon node 1
    And Uncordon node 2
    And Only one replica rebuilding will start at a time for volume ${volume_name}
    And Attach volume ${volume_name} to node 1    wait=False    retry=False
    Then Wait for volume ${volume_name} migration to be ready
    And Detach volume ${volume_name} from node 0
    And Wait for volume ${volume_name} to migrate to node 1
    And Wait for volume ${volume_name} healthy
    And Check volume ${volume_name} data is intact
