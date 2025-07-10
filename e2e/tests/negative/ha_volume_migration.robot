*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/migration.resource

Test Setup    Set up test environment
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

Migration Confirmation After Migration Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash the engine on the migration node by killing its instance-manager pod
    When Delete ${DATA_ENGINE} instance manager on node 1
    And Sleep    0.5
    # migration confirmation by detaching from the original node
    And Detach volume 0 from node 0

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Confirmation Before Migration Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # migration confirmation by detaching from the original node
    When Detach volume 0 from node 0
    And Log To Console    "Sleep 0.5s after migration confirmation but before the migration engine crash"
    And Sleep    0.5
    # crash the engine on the migration node by killing its instance-manager pod
    And Delete ${DATA_ENGINE} instance manager on node 1

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Rollback After Migration Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash the engine on the migration node by killing its instance-manager pod
    When Delete ${DATA_ENGINE} instance manager on node 1
    And Sleep    0.5
    # migration rollback by detaching from the migration node
    And Detach volume 0 from node 1

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Rollback Before Migration Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # migration rollback by detaching from the migration node
    When Detach volume 0 from node 1
    And Log To Console    "Sleep 0.5s after migration rollback but before the migration engine crash"
    And Sleep    0.5
    # crash the engine on the migration node by killing its instance-manager pod
    And Delete ${DATA_ENGINE} instance manager on node 1

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Confirmation After Original Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash the engine on the original node by killing its instance-manager pod
    When Delete ${DATA_ENGINE} instance manager on node 0
    And Sleep    0.5
    # migration confirmation by detaching from the original node
    And Detach volume 0 from node 0

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Confirmation Before Original Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # migration confirmation by detaching from the original node
    When Detach volume 0 from node 0
    And Log To Console    "Sleep 0.5s after migration confirmation but before the original engine crash"
    And Sleep    0.5
    # crash the engine on the original node by killing its instance-manager pod
    And Delete ${DATA_ENGINE} instance manager on node 0

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Rollback After Original Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash the engine on the original node by killing its instance-manager pod
    When Delete ${DATA_ENGINE} instance manager on node 0
    And Sleep    0.5
    # migration rollback by detaching from the migration node
    And Detach volume 0 from node 1

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Rollback Before Original Engine Crash
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # migration rollback by detaching from the migration node
    When Detach volume 0 from node 1
    And Log To Console    "Sleep 0.5s after migration rollback but before the original engine crash"
    And Sleep    0.5
    # crash the engine on the original node by killing its instance-manager pod
    And Delete ${DATA_ENGINE} instance manager on node 0

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Original Engine Crash During Migration
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash the engine on the original node by killing its instance-manager pod
    When Delete ${DATA_ENGINE} instance manager on node 0
    # longhorn keeps the volume in detached state waiting for user to delete one of the 2 attachments
    Then Wait for volume 0 detached

    # detach the volume from one of nodes should make it fully attach to the other nod
    When Detach volume 0 from node 0
    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Migration Engine Crash During Migration
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash the engine on the migration node by killing its instance-manager pod
    When Delete ${DATA_ENGINE} instance manager on node 1
    # longhorn retries migration and the volume is attached to both nodes eventually
    Then Wait for volume 0 migration to be ready

All Engines Crash During Migration
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # crash all engines by killing their instance-manager pods
    When Delete ${DATA_ENGINE} instance manager on node 0
    And Delete ${DATA_ENGINE} instance manager on node 1
    And Delete ${DATA_ENGINE} instance manager on node 2
    # longhorn keeps the volume in detached state waiting for user to delete one of the 2 attachments
    Then Wait for volume 0 detached

    # detach the volume from one of nodes should make it fully attach to the other nod
    When Detach volume 0 from node 1
    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

Volume Degraded Before Migration And Confirmation
    Given Cordon node 2
    And Delete ${DATA_ENGINE} instance manager on node 2
    And Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 degraded
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # migration confirmation by detaching from the original node
    When Detach volume 0 from node 0

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 degraded
    And Check volume 0 data is intact

Volume Degraded Before Migration And Rollback
    Given Cordon node 2
    And Delete ${DATA_ENGINE} instance manager on node 2
    And Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 degraded
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    # migration rollback by detaching from the migration node
    When Detach volume 0 from node 1

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 degraded
    And Check volume 0 data is intact

Volume Degraded Between Migration And Confirmation
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    When Cordon node 2
    And Delete ${DATA_ENGINE} instance manager on node 2
    # migration confirmation by detaching from the original node
    And Detach volume 0 from node 0

    Then Wait for volume 0 to migrate to node 1
    And Wait for volume 0 degraded
    And Check volume 0 data is intact

Volume Degraded Between Migration And Rollback
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    When Cordon node 2
    And Delete ${DATA_ENGINE} instance manager on node 2
    # migration rollback by detaching from the migration node
    And Detach volume 0 from node 1

    Then Wait for volume 0 to stay on node 0
    And Wait for volume 0 degraded
    And Check volume 0 data is intact

Attempt To Attach To Three Nodes
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    When Attach volume 0 to node 0
    And Volume 0 should be attached to node 0
    When Attach volume 0 to node 1
    And Volume 0 should be attached to node 1
    When Attach volume 0 to node 2
    And Volume 0 should not be attached to node 2

Heavy Writing Between Migration And Confirmation
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Keep writing data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    When Detach volume 0 from node 0
    Then Wait for volume 0 to migrate to node 1
    And Check volume 0 works

Heavy Writing Between Migration And Rollback
    Given Create volume 0 with    migratable=True    accessMode=RWX    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Keep writing data to volume 0

    And Attach volume 0 to node 1
    And Wait for volume 0 migration to be ready

    When Detach volume 0 from node 1
    Then Wait for volume 0 to stay on node 0
    And Check volume 0 works
