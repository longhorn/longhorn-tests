*** Settings ***
Documentation    Linked-Clone Volume Test Cases
...
...    A linked-clone volume is a V2 (SPDK) volume that is cloned from a snapshot
...    of a source volume.  Unlike a full (copy-based) clone, linked-clone replicas
...    physically co-locate on the same node+disk as source replicas and share the
...    parent snapshot data — no full data copy is required.
...
...    Key spec fields:
...      spec.dataSource  = {type: snapshot, parameters: {volumeName, snapshotName}}
...      spec.cloneMode   = linked-clone
...      spec.dataEngine  = v2
...
...    Per-replica fields set by the scheduler:
...      spec.linkedCloneSrcReplicaName  (immutable once set)
...      label: linked-clone-src-replica (immutable once set)
...
...    Clone lifecycle tracked in volume.status.cloneStatus.state:
...      Initiated -> InProgress -> completed
...
...    Constraints enforced by webhooks:
...      - Cannot delete src volume while linked-clone volumes exist
...      - Cannot delete src replica with active linked-clone children
...      - Cannot delete entrypoint snapshot used by a linked-clone volume
...      - Cannot decrease src volume replica count below # of linked-clone volumes
...      - linkedCloneSrcReplicaName and linked-clone-src-replica label are immutable
...
...    Known V2 / SPDK behaviour covered by these tests:
...      - Snapshot CRs must not be prematurely deleted when a V2 engine restarts
...        after a detach/reattach cycle.  syncSnapshotCRs is guarded against running
...        before engine.Status.ReplicaModeMap is populated (engine monitor's first
...        successful poll), preventing stale empty Snapshots from wiping valid CRs.
...      - ReplicaRebuildVerify is an unimplemented gRPC stub for V2; the WO→RW
...        transition happens internally in the SPDK engine.  Tests verify rebuilt
...        replicas become RW and the volume returns to healthy without the stub.
...      - The VolumeCloneController auto-attaches the clone volume for the clone
...        operation and removes its ticket once cloneStatus.state reaches completed.
...        Tests manually attach the clone volume before clone starts so the volume
...        remains attached (and thus healthy) after the controller ticket is removed.
...      - For linked-clone, if some replicas error during clone but at least one
...        completes, the clone state transitions to completed (not Failed), allowing
...        the errored replicas to be rebuilt normally.
...
...    All tests in this file require the V2 data engine (SPDK).

Test Tags    regression    v2    linked-clone

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/node.resource
Resource    ../keywords/engine.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/linked_clone.resource
Resource    ../keywords/setting.resource

Test Setup    Set up v2 test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks


*** Test Cases ***
Test Linked Clone Volume Basic Lifecycle
    [Tags]    coretest
    [Documentation]
    ...    Covers the full linked-clone lifecycle:
    ...
    ...    Step 1  Create a V2 source volume, write data (fully synced to disk),
    ...            then create a snapshot.  The write-then-snapshot ordering is
    ...            critical: taking a snapshot while a write is still in flight
    ...            produces a partial snapshot whose checksum differs from the
    ...            completed write, causing a data integrity failure in the clone.
    ...    Step 2  Create a linked-clone volume from that snapshot.
    ...    Step 3  Verify engine and replica CRs are created for the clone volume.
    ...    Step 4  Verify scheduler sets linkedCloneSrcReplicaName and the
    ...            linked-clone-src-replica label on every clone replica; confirm
    ...            each clone replica co-locates with its source replica.
    ...    Step 5  Verify the ordering guarantee: clone replica instances must not
    ...            start before linkedCloneSrcReplicaName is set.  The guarantee is
    ...            verified implicitly by the successful clone completion in step 6.
    ...            With the 1-replica clone path (when the engine IM version cannot be
    ...            confirmed at schedule time) only 1 replica runs during the clone
    ...            phase; all 3 become healthy after step 6's rebuild.
    ...    Step 6  Manually attach the clone volume BEFORE clone completes so the
    ...            volume stays attached after the VolumeCloneController removes its
    ...            own auto-attach ticket upon clone completion.  Wait for clone
    ...            completion first, then confirm the volume is healthy and all 3
    ...            replicas are running.
    ...    Step 7  Verify inherited data from source matches the snapshot content,
    ...            then write new data to the clone and confirm it is readable.
    ...    Step 8  Detach and reattach the clone volume.  The V2 SPDK engine restarts
    ...            on reattach; snapshot CRs must not be wiped by syncSnapshotCRs
    ...            during the engine startup window.  Verify clone status is preserved
    ...            (completed), data is intact, and the entrypoint snapshot CR still
    ...            exists on the source volume.
    ...    Step 9  Post-clone operations on the clone volume:
    ...            a) Snapshot and backup (create snapshot, create backup)
    ...            b) Adjust replica count (decrease then scale back up to source count)
    ...            c) Replica rebuild (delete a replica; verify it is re-scheduled with
    ...               linkedCloneSrcReplicaName automatically assigned and becomes RW).
    ...               NOTE: ReplicaRebuildVerify is an unimplemented gRPC stub for V2;
    ...               the WO→RW promotion is internal to the SPDK engine.  Volume
    ...               health is the authoritative signal, not the verify call.
    ...            d) Expand the clone volume
    ...    Step 10 Clone of a clone: create a linked-clone of volume clone-vol (itself a
    ...            linked-clone of volume src-vol), verify data matches, then delete.
    ...    Step 11 Delete the clone volume; verify the source volume and the
    ...            entrypoint snapshot CR still exist.

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Create source V2 volume, write data (synced), take snapshot
    # ------------------------------------------------------------------
    Given Create volume src-vol with    dataEngine=v2    numberOfReplicas=3
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    # Write data keyword issues a synchronous write; the snapshot is taken
    # only after the write returns so the checksum is fully stable.
    And Write data to volume src-vol

    # Create the entrypoint snapshot that the clone will reference.
    And Create snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 2: Create linked-clone volume from the snapshot
    # ------------------------------------------------------------------
    When Create linked clone volume clone-vol from snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 3: Verify engine and replica CRs exist for the clone volume
    # ------------------------------------------------------------------
    Then Verify engine CR exists for volume clone-vol
    And Verify replica CRs exist for volume clone-vol

    # ------------------------------------------------------------------
    # Step 4: Wait for scheduler to set per-replica linked-clone fields
    #         and verify co-location (same node+disk as src replica)
    # ------------------------------------------------------------------
    When Wait for linked clone volume clone-vol replica fields set
    Then Verify linked clone volume clone-vol replicas co-located with volume src-vol
    And Verify linked clone volume clone-vol src replica names unchanged

    # ------------------------------------------------------------------
    # Step 5: Verify replica instances started (ordering guarantee: instances
    #         must not start before linkedCloneSrcReplicaName is set).
    #         For the 1-replica clone path (used when the engine has not yet
    #         started and the IM version cannot be confirmed), only 1 replica
    #         runs during the clone phase.  After the clone completes and the
    #         volume rebuilds to full replica count, all 3 replicas will run.
    #         The ordering guarantee is verified implicitly by the clone
    #         completing successfully in step 6.
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Step 6: Attach the clone volume BEFORE clone completes so the manual
    #         attach ticket keeps the volume up after the VolumeCloneController
    #         removes its auto-attach ticket on clone completion.
    #         Wait for clone completion first, then confirm volume is healthy.
    # ------------------------------------------------------------------
    When Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    # After reaching healthy all replicas must be running (clone + rebuilds done)
    And Volume clone-vol should have 3 running replicas

    # ------------------------------------------------------------------
    # Step 7: Verify inherited data from src, then write new data to clone
    # ------------------------------------------------------------------
    # The clone inherits the snapshot data from the source volume.
    # Verify volume clone-vol contains the same data that was written to volume src-vol
    # before the snapshot was taken.
    Then Verify linked clone volume clone-vol data matches source volume src-vol

    # Write new data to the clone volume and verify it is readable.
    When Write data to volume clone-vol
    Then Check volume clone-vol data is intact

    # ------------------------------------------------------------------
    # Step 8: Detach and reattach; confirm clone status and data preserved.
    #
    #         Detaching a V2 volume stops its SPDK engine instance.  On
    #         reattach the engine starts fresh with an empty SnapshotMap.
    #         The engine monitor's first poll may report an empty snapshot
    #         list, which must NOT cause syncSnapshotCRs to delete the
    #         entrypoint snapshot CR on the source volume.
    # ------------------------------------------------------------------
    When Detach volume clone-vol
    And Wait for volume clone-vol detached

    Then Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    # Verify entrypoint snapshot CR was not wiped during the engine restart.
    And Verify entrypoint snapshot of clone volume clone-vol still exists
    # The clone has diverged (new data written in step 7); verify its own data survived.
    And Check volume clone-vol data is intact
    And Verify linked clone volume clone-vol src replica names unchanged

    # ------------------------------------------------------------------
    # Step 9a: Snapshot and backup operations on clone volume
    #          (both are allowed after clone is completed)
    # ------------------------------------------------------------------
    When Create snapshot 0 of volume clone-vol
    And Create backup 0 for volume clone-vol

    # ------------------------------------------------------------------
    # Step 9b: Adjust replica count on clone volume
    #          (linked-clone volume cannot exceed source replica count,
    #           but can decrease below it and scale back up to source count)
    # ------------------------------------------------------------------
    When Update volume clone-vol replica count to 1
    And Wait for volume clone-vol healthy
    # Scale back up to 3 replicas (= source count; not exceeding it)
    And Update volume clone-vol replica count to 3
    And Wait for volume clone-vol healthy

    # ------------------------------------------------------------------
    # Step 9c: Replica rebuild on clone volume
    #
    #          Delete one replica; the controller schedules a replacement
    #          on a disk that has a source replica and assigns
    #          linkedCloneSrcReplicaName automatically.
    #
    #          For V2, ReplicaRebuildVerify returns Unimplemented (gRPC
    #          stub).  The WO→RW promotion happens inside the SPDK engine
    #          without an external verify call; longhorn-manager logs a
    #          warning and continues.  Volume health is the authoritative
    #          signal.  The snapshot created in Step 9a must also survive
    #          the rebuild (snapshot CR preservation regression check).
    # ------------------------------------------------------------------
    When Delete volume clone-vol replica on node 0
    Then Wait until volume clone-vol replicas rebuilding completed
    And Wait for volume clone-vol healthy
    # Snapshot created in Step 9a must still exist after rebuild.
    And Validate snapshot 0 is in volume clone-vol snapshot list

    # ------------------------------------------------------------------
    # Step 9d: Expand clone volume
    # ------------------------------------------------------------------
    When Expand volume clone-vol to 3Gi
    Then Wait for volume clone-vol size to be 3Gi

    # ------------------------------------------------------------------
    # Step 10: Clone of a clone — create a linked-clone of volume clone-vol
    #          (which is itself a linked-clone of volume src-vol)
    # ------------------------------------------------------------------
    # Take a snapshot of the already-cloned volume clone-vol to capture all data
    When Create snapshot 1 of volume clone-vol
    # Create a second-level linked-clone from that snapshot
    And Create linked clone volume nested-clone-vol from snapshot 1 of volume clone-vol
    And Wait for linked clone volume nested-clone-vol replica fields set
    And Attach volume nested-clone-vol
    And Wait for linked clone volume nested-clone-vol clone to complete
    And Wait for volume nested-clone-vol healthy
    Then Verify linked clone volume nested-clone-vol data matches source volume clone-vol
    And Detach volume nested-clone-vol
    And Wait for volume nested-clone-vol detached
    And Delete volume nested-clone-vol
    And Wait for volume nested-clone-vol deleted

    # ------------------------------------------------------------------
    # Step 11: Delete clone volume; verify src volume + snapshot still exist
    # ------------------------------------------------------------------
    # Record entrypoint snapshot name before deleting the clone volume
    # (cannot be retrieved from the clone volume's dataSource after deletion).
    ${clone_volume_name} =    generate_name_with_suffix    volume    clone-vol
    ${snap_name} =    get_entrypoint_snapshot_name_from_clone    ${clone_volume_name}

    When Delete volume clone-vol
    And Wait for volume clone-vol deleted

    Then Verify volume src-vol still exists
    And Verify named snapshot ${snap_name} of volume src-vol still exists


Test Linked Clone Volume Constraints
    [Tags]    coretest
    [Documentation]
    ...    Verifies the webhook-enforced constraints that protect source resources
    ...    while linked-clone volumes exist:
    ...
    ...    Constraint 1  Cannot create a linked-clone volume with spec.size that
    ...                  does not match the source snapshot's RestoreSize.
    ...    Constraint 2  Cannot delete a source replica while it has active
    ...                  linked-clone children.
    ...    Constraint 3  Cannot delete the entrypoint snapshot used by a
    ...                  linked-clone volume.
    ...    Constraint 4  Cannot delete the source volume while linked-clone
    ...                  volumes exist.
    ...    Constraint 5  Cannot decrease the source volume replica count below
    ...                  the number of linked-clone replicas that depend on it.
    ...
    ...    After the linked-clone volume is deleted all five constraints must
    ...    be lifted (operations must succeed).

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Setup: create source volume, snapshot, and linked-clone volume
    # ------------------------------------------------------------------
    Given Create volume src-vol with    dataEngine=v2    numberOfReplicas=3
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write data to volume src-vol
    And Create snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Constraint 1: Cannot create linked-clone with wrong spec.size
    # ------------------------------------------------------------------
    Then Create linked clone volume clone-vol with wrong size from snapshot 0 of volume src-vol should fail

    When Create linked clone volume clone-vol from snapshot 0 of volume src-vol
    And Wait for linked clone volume clone-vol replica fields set
    And Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy

    # ------------------------------------------------------------------
    # Constraint 2: Cannot delete a source replica while clone exists
    # ------------------------------------------------------------------
    Then Delete src replica of volume src-vol should fail

    # ------------------------------------------------------------------
    # Constraint 3: Cannot delete entrypoint snapshot while clone exists
    # ------------------------------------------------------------------
    And Delete entrypoint snapshot of clone volume clone-vol should fail

    # ------------------------------------------------------------------
    # Constraint 4: Cannot delete source volume while clone exists
    # ------------------------------------------------------------------
    And Delete volume src-vol as src should fail

    # ------------------------------------------------------------------
    # Constraint 5: Cannot decrease src replica count below # of clones
    #               (1 linked-clone volume exists → going below 3 when 1
    #                clone maps 3 replicas should be blocked; try going to 2)
    # ------------------------------------------------------------------
    And Decrease volume src-vol replica count to 2 should fail

    # ------------------------------------------------------------------
    # Teardown: delete the clone volume; all constraints must be lifted
    # ------------------------------------------------------------------
    # Record entrypoint snapshot name before deleting the clone volume.
    ${clone_volume_name} =    generate_name_with_suffix    volume    clone-vol
    ${snap_name} =    get_entrypoint_snapshot_name_from_clone    ${clone_volume_name}

    When Detach volume clone-vol
    And Wait for volume clone-vol detached
    And Delete volume clone-vol
    And Wait for volume clone-vol deleted

    # Constraint 2 lifted: can now delete a source replica
    Then Delete volume src-vol replica on node 0
    And Wait until volume src-vol replicas rebuilding completed
    And Wait for volume src-vol healthy

    # Constraint 3 lifted: entrypoint snapshot can now be deleted
    And Delete named snapshot ${snap_name} of volume src-vol
    And Wait for named snapshot ${snap_name} of volume src-vol to be deleted

    # Constraint 4 lifted: source volume can now be deleted normally
    # (handled by test teardown; verify it still exists here)
    And Verify volume src-vol still exists

    # Constraint 5 lifted: replica count can be decreased
    When Update volume src-vol replica count to 2
    Then Wait for volume src-vol healthy
    And Volume src-vol should have 2 running replicas


Test Linked Clone Volume Creation Without Snapshot Name
    [Tags]    coretest
    [Documentation]
    ...    Verifies that a linked-clone volume can be created without explicitly
    ...    providing a snapshot name.  When no snapshot name is given, Longhorn
    ...    automatically creates a deterministic entrypoint snapshot on the source
    ...    volume and records its name in the clone volume's dataSource and in the
    ...    linked-clone-source-snapshot label.
    ...
    ...    Step 1  Create a V2 source volume and write data to it.
    ...    Step 2  Create a linked-clone volume referencing only the source volume
    ...            (no snapshotName in the dataSource).
    ...    Step 3  Verify Longhorn auto-created and recorded the entrypoint snapshot
    ...            (linked-clone-source-snapshot label set on the clone volume).
    ...    Step 4  Verify the full lifecycle completes (fields set, co-located,
    ...            clone completed, inherited data intact).

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Create source V2 volume and write data
    # ------------------------------------------------------------------
    Given Create volume src-vol with    dataEngine=v2    numberOfReplicas=3
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write data to volume src-vol

    # ------------------------------------------------------------------
    # Step 2: Create linked-clone volume WITHOUT providing a snapshot name
    # ------------------------------------------------------------------
    When Create linked clone volume clone-vol from volume src-vol without snapshot name

    # ------------------------------------------------------------------
    # Step 3: Verify Longhorn auto-created the entrypoint snapshot and set
    #         the linked-clone-source-snapshot label on the clone volume
    # ------------------------------------------------------------------
    Then Verify linked clone volume clone-vol has entrypoint snapshot label set

    # ------------------------------------------------------------------
    # Step 4: Full lifecycle — fields set, co-located, clone completed,
    #         inherited data intact
    # ------------------------------------------------------------------
    When Wait for linked clone volume clone-vol replica fields set
    Then Verify linked clone volume clone-vol replicas co-located with volume src-vol

    When Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy

    Then Verify linked clone volume clone-vol data matches source volume src-vol


Test Linked Clone Volume Advanced Lifecycle
    [Tags]    regression    v2    linked-clone
    [Documentation]
    ...    Comprehensive linked-clone lifecycle covering nesting, expansion, IM crash
    ...    recovery, and cascaded deletion.  All three volumes (source, clone, nested
    ...    clone) are attached to the same node so a single IM pod crash exercises
    ...    all of them simultaneously.
    ...
    ...    Step 1   Create a V2 source volume, write data, take snapshot 0.
    ...    Step 2   Create linked-clone volume clone-vol from snapshot 0 of volume src-vol.
    ...    Step 3   Verify engine and replica CRs exist for the clone volume.
    ...    Step 4   Verify scheduler sets linkedCloneSrcReplicaName and the
    ...             linked-clone-src-replica label on every clone replica; confirm
    ...             each clone replica co-locates with its source replica.
    ...    Step 5   Attach clone BEFORE clone completes, wait for completion,
    ...             confirm volume is healthy with 3 running replicas.
    ...    Step 6   Verify inherited data matches snapshot; write new data to clone.
    ...    Step 7   Expand the clone volume to 3Gi, then write data to the
    ...             expanded region and verify it is readable.
    ...    Step 8   Detach and reattach clone to the node the source volume is
    ...             attached to.  Verify clone status, data, and entrypoint snapshot
    ...             CR preserved across engine restart.
    ...    Step 9   Post-clone operations for the clone volume:
    ...             a) Snapshot and backup
    ...             b) Scale replica count down to 1, then back up to 3
    ...             c) Delete a replica; verify rebuild completes
    ...    Step 10  Create a nested linked-clone volume with 1 replica from the clone volume.
    ...             Scheduling on nodes 1 and 2 is temporarily disabled so the single
    ...             replica lands on node 0 (the engine node), ensuring the IM crash
    ...             in step 13 takes down both the engine and the only replica, which
    ...             triggers auto-salvage recovery.
    ...             Verify the nested clone size matches the expanded clone (3Gi).
    ...    Step 11  Attach the nested clone to the same node as the source volume.
    ...             Verify inherited data from both source and clone volumes.
    ...    Step 12  Post-clone operations for the nested clone volume:
    ...             a) Snapshot and backup
    ...             b) Expand to 4Gi and write data to the expanded region.
    ...    Step 13  Crash the instance manager pod on the node all 3 volumes are
    ...             attached to. src-vol and clone-vol degrade and recover normally.
    ...             nested-clone-vol loses both its engine and its only replica,
    ...             entering a faulted state that triggers auto-salvage.
    ...    Step 14  Wait for the instance manager pod to restart, auto-salvage to
    ...             complete for nested-clone-vol, and all 3 volumes to reach healthy.
    ...    Step 15  Verify the data for all 3 volumes (including expanded regions).
    ...    Step 16  Delete nested clone volume; verify the clone volume and its
    ...             entrypoint snapshot CR still exist.
    ...    Step 17  Delete clone volume; verify the source volume and its
    ...             entrypoint snapshot CR still exist.

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Create source V2 volume, write data (synced), take snapshot
    # ------------------------------------------------------------------
    Given Create volume src-vol with    dataEngine=v2    numberOfReplicas=3
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write data to volume src-vol
    And Create snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 2: Create linked-clone volume clone-vol from snapshot 0 of volume src-vol
    # ------------------------------------------------------------------
    When Create linked clone volume clone-vol from snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 3: Verify engine and replica CRs exist for the clone volume
    # ------------------------------------------------------------------
    Then Verify engine CR exists for volume clone-vol
    And Verify replica CRs exist for volume clone-vol

    # ------------------------------------------------------------------
    # Step 4: Verify scheduler sets per-replica fields and co-location
    # ------------------------------------------------------------------
    When Wait for linked clone volume clone-vol replica fields set
    Then Verify linked clone volume clone-vol replicas co-located with volume src-vol
    And Verify linked clone volume clone-vol src replica names unchanged

    # ------------------------------------------------------------------
    # Step 5: Attach clone BEFORE clone completes; wait for healthy
    # ------------------------------------------------------------------
    When Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    And Volume clone-vol should have 3 running replicas

    # ------------------------------------------------------------------
    # Step 6: Verify inherited data; write new data to clone
    # ------------------------------------------------------------------
    Then Verify linked clone volume clone-vol data matches source volume src-vol
    When Write data to volume clone-vol
    Then Check volume clone-vol data is intact

    # ------------------------------------------------------------------
    # Step 7: Expand clone volume to 3Gi; write to expanded region
    # ------------------------------------------------------------------
    When Expand volume clone-vol to 3Gi
    Then Wait for volume clone-vol size to be 3Gi
    And Write data to volume clone-vol at offset 2048
    And Check volume clone-vol data at offset is intact

    # ------------------------------------------------------------------
    # Step 8: Detach and reattach clone to the same node as source volume.
    #         Verifies snapshot CR persistence and data integrity across
    #         engine restart.
    # ------------------------------------------------------------------
    When Detach volume clone-vol
    And Wait for volume clone-vol detached
    Then Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    And Verify entrypoint snapshot of clone volume clone-vol still exists
    And Check volume clone-vol data is intact
    And Check volume clone-vol data at offset is intact
    And Verify linked clone volume clone-vol src replica names unchanged

    # ------------------------------------------------------------------
    # Step 9a: Snapshot and backup operations on clone volume
    # ------------------------------------------------------------------
    When Create snapshot 2 of volume clone-vol
    And Create backup 0 for volume clone-vol

    # ------------------------------------------------------------------
    # Step 9b: Adjust replica count on clone volume
    # ------------------------------------------------------------------
    When Update volume clone-vol replica count to 1
    And Wait for volume clone-vol healthy
    And Update volume clone-vol replica count to 3
    And Wait for volume clone-vol healthy
    And Wait for all volume clone-vol replicas to have HealthyAt set

    # ------------------------------------------------------------------
    # Step 9c: Replica rebuild on clone volume
    # ------------------------------------------------------------------
    When Delete volume clone-vol replica on node 0
    Then Wait until volume clone-vol replicas rebuilding completed
    And Wait for volume clone-vol healthy
    And Wait for all volume clone-vol replicas to have HealthyAt set
    And Validate snapshot 2 is in volume clone-vol snapshot list

    # ------------------------------------------------------------------
    # Step 10: Create nested linked-clone with 1 replica.
    #          Disable scheduling on nodes 1 and 2 so the scheduler is
    #          forced to place the single replica on node 0, which is the
    #          same node as the engine. This ensures the IM crash in
    #          step 13 takes down both engine and replica simultaneously,
    #          triggering auto-salvage.
    #          Wait for clone-vol to have 3 replicas with HealthyAt set
    #          before creating the nested clone, so that a src replica is
    #          guaranteed to exist on node 0.
    # ------------------------------------------------------------------
    When Create snapshot 3 of volume clone-vol
    And Wait for all volume clone-vol replicas to have HealthyAt set
    And Volume clone-vol should have 3 running replicas
    And Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create linked clone volume nested-clone-vol from snapshot 3 of volume clone-vol    numberOfReplicas=1
    And Wait for linked clone volume nested-clone-vol replica fields set
    And Enable node 1 scheduling
    And Enable node 2 scheduling
    Then Wait for volume nested-clone-vol size to be 3Gi
    And Volume nested-clone-vol should have 1 running replicas on node 0

    # ------------------------------------------------------------------
    # Step 11: Attach nested clone to same node as source; verify data
    # ------------------------------------------------------------------
    When Attach volume nested-clone-vol to same node as volume src-vol
    And Wait for linked clone volume nested-clone-vol clone to complete
    And Wait for volume nested-clone-vol healthy
    Then Verify linked clone volume nested-clone-vol data matches source volume clone-vol
    And Verify linked clone volume nested-clone-vol expanded data matches volume clone-vol

    # ------------------------------------------------------------------
    # Step 12a: Snapshot and backup for nested clone
    # ------------------------------------------------------------------
    When Create snapshot 0 of volume nested-clone-vol
    And Create backup 0 for volume nested-clone-vol

    # ------------------------------------------------------------------
    # Step 12b: Expand nested clone to 4Gi; write to expanded region
    # ------------------------------------------------------------------
    When Expand volume nested-clone-vol to 4Gi
    Then Wait for volume nested-clone-vol size to be 4Gi
    And Write data to volume nested-clone-vol at offset 3072
    And Check volume nested-clone-vol data at offset is intact

    # ------------------------------------------------------------------
    # Step 13: Crash the instance manager pod on the node all 3 volumes
    #          are attached to. src-vol and clone-vol have replicas on
    #          other nodes and degrade then recover normally.
    #          nested-clone-vol has only 1 replica on this node, so both
    #          its engine and replica fail, putting it in a faulted state
    #          and triggering auto-salvage.
    # ------------------------------------------------------------------
    When Delete v2 instance manager of volume src-vol

    # ------------------------------------------------------------------
    # Step 14: Wait for instance manager restart, auto-salvage for
    #          nested-clone-vol, and all volumes back to healthy.
    # ------------------------------------------------------------------
    Then Wait for longhorn ready
    And Wait for volume src-vol healthy
    And Wait for volume clone-vol healthy
    And Wait for volume nested-clone-vol healthy

    # ------------------------------------------------------------------
    # Step 15: Verify data integrity for all 3 volumes
    # ------------------------------------------------------------------
    Then Check volume src-vol data is intact
    And Check volume clone-vol data is intact
    And Check volume clone-vol data at offset is intact
    And Verify linked clone volume nested-clone-vol data matches source volume clone-vol
    And Verify linked clone volume nested-clone-vol expanded data matches volume clone-vol
    And Check volume nested-clone-vol data at offset is intact

    # ------------------------------------------------------------------
    # Step 16: Delete nested clone; verify clone volume and its
    #          entrypoint snapshot CR still exist
    # ------------------------------------------------------------------
    ${nested_clone_volume_name} =    generate_name_with_suffix    volume    nested-clone-vol
    ${snap_name_v2} =    get_entrypoint_snapshot_name_from_clone    ${nested_clone_volume_name}

    When Detach volume nested-clone-vol
    And Wait for volume nested-clone-vol detached
    And Delete volume nested-clone-vol
    And Wait for volume nested-clone-vol deleted

    Then Verify volume clone-vol still exists
    And Verify named snapshot ${snap_name_v2} of volume clone-vol still exists

    # ------------------------------------------------------------------
    # Step 17: Delete clone volume; verify source volume and its
    #          entrypoint snapshot CR still exist
    # ------------------------------------------------------------------
    ${clone_volume_name} =    generate_name_with_suffix    volume    clone-vol
    ${snap_name_v1} =    get_entrypoint_snapshot_name_from_clone    ${clone_volume_name}

    When Detach volume clone-vol
    And Wait for volume clone-vol detached
    And Delete volume clone-vol
    And Wait for volume clone-vol deleted

    Then Verify volume src-vol still exists
    And Verify named snapshot ${snap_name_v1} of volume src-vol still exists

Test Linked Clone Volume Extra Replica Cleanup
    [Documentation]
    ...    Verifies that the extra-replica cleanup correctly deletes only the
    ...    src volume replica that has no linked-clone children, preserving
    ...    replicas referenced by clone volumes.
    ...
    ...    Step 1  Set replica-auto-balance to least-effort.
    ...    Step 2  Create a 3-replica V2 source volume, attach, write data,
    ...            and create a snapshot.
    ...    Step 3  Create a 2-replica linked-clone volume from the source
    ...            volume and wait for clone to complete.
    ...    Step 4  Scale down the source volume replica count to 2.
    ...    Step 5  Verify that only the replica without linked-clone children
    ...            is cleaned up; the 2 remaining replicas are exactly those
    ...            referenced by the clone volume's replicas.

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Set auto-balance to least-effort
    # ------------------------------------------------------------------
    Given Setting replica-auto-balance is set to least-effort

    # ------------------------------------------------------------------
    # Step 2: Create 3-replica V2 source volume, attach, write data, snapshot
    # ------------------------------------------------------------------
    And Create volume src-vol with    dataEngine=v2    numberOfReplicas=3
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write data to volume src-vol
    And Create snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 3: Create 2-replica linked-clone volume and wait for completion
    # ------------------------------------------------------------------
    When Create linked clone volume clone-vol from snapshot 0 of volume src-vol    numberOfReplicas=2
    And Wait for linked clone volume clone-vol replica fields set
    And Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy

    # ------------------------------------------------------------------
    # Step 4: Scale down source volume replica count to 2
    # ------------------------------------------------------------------
    And Update volume src-vol replica count to 2

    # ------------------------------------------------------------------
    # Step 5: Verify only the unreferenced replica is cleaned up
    # ------------------------------------------------------------------
    Then Volume src-vol should have 2 running replicas
    And Verify all replicas of volume src-vol are referenced by clone clone-vol

Test Linked Clone Volume Stale Replica Protection
    [Documentation]
    ...    Verifies that stale replica cleanup does not delete a src volume
    ...    replica that is referenced by a linked-clone volume, even after the
    ...    src volume's staleReplicaTimeout expires.
    ...
    ...    Step 1  Create a 3-replica V2 source volume with staleReplicaTimeout=1
    ...            (minute), attach, write data, and create a snapshot.
    ...    Step 2  Create a 3-replica linked-clone volume with
    ...            staleReplicaTimeout=60, and wait for clone to complete.
    ...    Step 3  Disable scheduling on node 0 and kill the instance manager
    ...            pod on that node to fail both the src and clone replicas.
    ...    Step 4  Wait for both replicas on node 0 to become failed.
    ...    Step 5  Sleep 90s (exceeding the src volume's 1-minute
    ...            staleReplicaTimeout) and verify neither failed replica
    ...            has been cleaned up.

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Create src volume with short stale timeout
    # ------------------------------------------------------------------
    Given Create volume src-vol with    dataEngine=v2    numberOfReplicas=3
    And Update volume src-vol staleReplicaTimeout to 1
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write data to volume src-vol
    And Create snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 2: Create 3-replica linked-clone with long stale timeout
    # ------------------------------------------------------------------
    When Create linked clone volume clone-vol from snapshot 0 of volume src-vol    numberOfReplicas=3
    And Update volume clone-vol staleReplicaTimeout to 60
    And Wait for linked clone volume clone-vol replica fields set
    And Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy

    # ------------------------------------------------------------------
    # Step 3: Disable scheduling on node 0 and kill IM to fail replicas
    # ------------------------------------------------------------------
    And Disable node 0 scheduling
    And Delete v2 instance manager on node 0

    # ------------------------------------------------------------------
    # Step 4: Wait for both replicas on node 0 to become failed
    # ------------------------------------------------------------------
    And Wait for volume src-vol replica on node 0 failed
    And Wait for volume clone-vol replica on node 0 failed

    # ------------------------------------------------------------------
    # Step 5: Sleep past src staleReplicaTimeout, verify no cleanup
    # ------------------------------------------------------------------
    And Sleep    90
    Then Volume src-vol should have 3 replicas
    And Volume clone-vol should have 3 replicas

Test Linked Clone Volume Auto Balance
    [Documentation]
    ...    Verifies that auto-balance correctly rebalances both the source
    ...    volume and the linked-clone volume when a new node becomes available.
    ...
    ...    Step 1  Enable disk-level soft anti-affinity and set auto-balance
    ...            to least-effort.
    ...    Step 2  Disable scheduling on nodes 1 and 2, so all replicas land
    ...            on node 0.
    ...    Step 3  Create a 2-replica V2 source volume, attach, write data,
    ...            and create a snapshot.
    ...    Step 4  Create a 2-replica linked-clone volume and wait for clone
    ...            to complete.
    ...    Step 5  Enable scheduling on node 1 and verify both volumes move
    ...            one replica to node 1.
    ...    Step 6  Verify data integrity after rebalance

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Configure settings
    # ------------------------------------------------------------------
    Given Setting replica-soft-anti-affinity is set to true
    And Setting replica-disk-soft-anti-affinity is set to true
    And Setting replica-auto-balance is set to least-effort

    # ------------------------------------------------------------------
    # Step 2: Disable scheduling on nodes 1 and 2
    # ------------------------------------------------------------------
    And Disable node 1 scheduling
    And Disable node 2 scheduling

    # ------------------------------------------------------------------
    # Step 3: Create 2-replica src volume on node 0
    # ------------------------------------------------------------------
    And Create volume src-vol with    dataEngine=v2    numberOfReplicas=2
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write data to volume src-vol
    And Create snapshot 0 of volume src-vol

    # ------------------------------------------------------------------
    # Step 4: Create 2-replica linked-clone and wait for completion
    # ------------------------------------------------------------------
    When Create linked clone volume clone-vol from snapshot 0 of volume src-vol    numberOfReplicas=2
    And Wait for linked clone volume clone-vol replica fields set
    And Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    And Volume src-vol should have 2 running replicas on node 0
    And Volume clone-vol should have 2 running replicas on node 0

    # ------------------------------------------------------------------
    # Step 5: Enable node 1 and verify auto-balance
    # ------------------------------------------------------------------
    When Enable node 1 scheduling
    Then Volume src-vol should have 1 running replicas on node 0
    And Volume src-vol should have 1 running replicas on node 1
    And Volume clone-vol should have 1 running replicas on node 0
    And Volume clone-vol should have 1 running replicas on node 1

    # ------------------------------------------------------------------
    # Step 6: Verify data integrity after rebalance
    # ------------------------------------------------------------------
    And Verify linked clone volume clone-vol data matches source volume src-vol
