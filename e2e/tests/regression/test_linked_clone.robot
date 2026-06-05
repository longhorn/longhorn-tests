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

Test Setup    Set up v2 test environment
Test Teardown    Cleanup test resources

*** Variables ***
# Sizes used by the expansion tests.  Data written after an expansion must land
# in the newly added region, i.e. starting at the offset where the previous size
# ended.  The offsets are therefore derived from the sizes instead of hard coded,
# so they stay correct if a size is changed.
${SRC_VOLUME_SIZE_GI}         2
${CLONE_EXPANDED_SIZE_GI}     3
${NESTED_EXPANDED_SIZE_GI}    4
${CLONE_EXPAND_OFFSET_MB}     ${{ ${SRC_VOLUME_SIZE_GI} * 1024 }}
${NESTED_EXPAND_OFFSET_MB}    ${{ ${CLONE_EXPANDED_SIZE_GI} * 1024 }}
# Amount of data written by the data-writing keywords, both at offset 0 and
# into each expanded region.
${WRITE_SIZE_MB}              200

*** Keywords ***
Set up v2 test environment
    Set up test environment
    Enable v2 data engine and add block disks


*** Test Cases ***
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
    And Write ${WRITE_SIZE_MB} MB data to volume src-vol at offset 0
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
    When Detach volume clone-vol
    And Wait for volume clone-vol detached
    And Delete volume clone-vol
    And Wait for volume clone-vol deleted

    # Constraint 2 lifted: can now delete a source replica
    Then Delete volume src-vol replica on node 0
    And Wait until volume src-vol replicas rebuilding completed
    And Wait for volume src-vol healthy

    # Constraint 3 lifted: entrypoint snapshot can now be deleted
    And Delete snapshot 0 CR of volume src-vol
    And Wait for snapshot 0 to not be in volume src-vol snapshot list

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
    And Write ${WRITE_SIZE_MB} MB data to volume src-vol at offset 0

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

    Then Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset 0 matches volume src-vol


Test Linked Clone Volume Lifecycle
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
    ...    Step 5   (Implicit) Ordering guarantee: clone replica instances must not
    ...             start before linkedCloneSrcReplicaName is set.
    ...    Step 6   Attach clone BEFORE clone completes, wait for completion,
    ...             confirm volume is healthy with 3 running replicas.
    ...    Step 7   Verify inherited data matches snapshot; write new data to clone.
    ...    Step 8   Expand the clone volume to 3Gi, then write data to the
    ...             expanded region and verify it is readable.
    ...    Step 9   Detach and reattach clone to the node the source volume is
    ...             attached to.  Verify clone status, data, and entrypoint snapshot
    ...             CR preserved across engine restart.
    ...    Step 10  Post-clone operations for the clone volume:
    ...             a) Snapshot and backup
    ...             b) Scale replica count down to 1, then back up to 3
    ...             c) Delete a replica; verify rebuild with auto-assigned src field
    ...    Step 11  Create a nested linked-clone volume with 1 replica from the clone volume.
    ...             Scheduling on nodes 1 and 2 is temporarily disabled so the single
    ...             replica lands on node 0 (the engine node), ensuring the IM crash
    ...             in step 14 takes down both the engine and the only replica, which
    ...             triggers auto-salvage recovery.
    ...             Verify the nested clone size matches the expanded clone (3Gi).
    ...    Step 12  Attach the nested clone to the same node as the source volume.
    ...             Verify inherited data from both source and clone volumes.
    ...    Step 13  Post-clone operations for the nested clone volume:
    ...             a) Snapshot and backup
    ...             b) Expand to 4Gi and write data to the expanded region.
    ...    Step 14  Crash the instance manager pod on the node all 3 volumes are
    ...             attached to. src-vol and clone-vol degrade and recover normally.
    ...             nested-clone-vol loses both its engine and its only replica,
    ...             entering a faulted state that triggers auto-salvage.
    ...    Step 15  Wait for the instance manager pod to restart, auto-salvage to
    ...             complete for nested-clone-vol, and all 3 volumes to reach healthy.
    ...    Step 16  Verify the data for all 3 volumes (including expanded regions).
    ...    Step 17  Delete nested clone volume; verify the clone volume and its
    ...             entrypoint snapshot CR still exist.
    ...    Step 18  Delete clone volume; verify the source volume and its
    ...             entrypoint snapshot CR still exist.

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Linked-clone volumes require the V2 data engine
    END

    # ------------------------------------------------------------------
    # Step 1: Create source V2 volume, write data (synced), take snapshot
    # ------------------------------------------------------------------
    Given Create volume src-vol with    dataEngine=v2    numberOfReplicas=3    size=${SRC_VOLUME_SIZE_GI}Gi
    And Attach volume src-vol
    And Wait for volume src-vol healthy
    And Write ${WRITE_SIZE_MB} MB data to volume src-vol at offset 0
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
    # Step 6: Attach clone BEFORE clone completes; wait for healthy
    # ------------------------------------------------------------------
    When Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    And Volume clone-vol should have 3 running replicas

    # ------------------------------------------------------------------
    # Step 7: Verify inherited data; write new data to clone
    # ------------------------------------------------------------------
    Then Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset 0 matches volume src-vol
    When Write ${WRITE_SIZE_MB} MB data to volume clone-vol at offset 0
    Then Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset 0 is intact

    # ------------------------------------------------------------------
    # Step 8: Expand clone volume to 3Gi; write to expanded region
    # ------------------------------------------------------------------
    When Expand volume clone-vol to ${CLONE_EXPANDED_SIZE_GI}Gi
    Then Wait for volume clone-vol size to be ${CLONE_EXPANDED_SIZE_GI}Gi
    And Write ${WRITE_SIZE_MB} MB data to volume clone-vol at offset ${CLONE_EXPAND_OFFSET_MB}
    And Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset ${CLONE_EXPAND_OFFSET_MB} is intact

    # ------------------------------------------------------------------
    # Step 9: Detach and reattach clone to the same node as source volume.
    #         Verifies snapshot CR persistence and data integrity across
    #         engine restart.
    # ------------------------------------------------------------------
    When Detach volume clone-vol
    And Wait for volume clone-vol detached
    Then Attach volume clone-vol to same node as volume src-vol
    And Wait for linked clone volume clone-vol clone to complete
    And Wait for volume clone-vol healthy
    And Verify entrypoint snapshot of clone volume clone-vol still exists
    And Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset 0 is intact
    And Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset ${CLONE_EXPAND_OFFSET_MB} is intact
    And Verify linked clone volume clone-vol src replica names unchanged

    # ------------------------------------------------------------------
    # Step 10a: Snapshot and backup operations on clone volume
    # ------------------------------------------------------------------
    When Create snapshot 2 of volume clone-vol
    And Create backup 0 for volume clone-vol

    # ------------------------------------------------------------------
    # Step 10b: Adjust replica count on clone volume
    # ------------------------------------------------------------------
    When Update volume clone-vol replica count to 1
    And Wait for volume clone-vol healthy
    And Update volume clone-vol replica count to 3
    And Wait for volume clone-vol healthy
    And Wait for all volume clone-vol replicas to have HealthyAt set

    # ------------------------------------------------------------------
    # Step 10c: Replica rebuild on clone volume
    # ------------------------------------------------------------------
    When Delete volume clone-vol replica on node 0
    Then Wait until volume clone-vol replicas rebuilding completed
    And Wait for volume clone-vol healthy
    And Wait for all volume clone-vol replicas to have HealthyAt set
    And Validate snapshot 2 is in volume clone-vol snapshot list

    # ------------------------------------------------------------------
    # Step 11: Create nested linked-clone with 1 replica.
    #          Disable scheduling on nodes 1 and 2 so the scheduler is
    #          forced to place the single replica on node 0, which is the
    #          same node as the engine. This ensures the IM crash in
    #          step 14 takes down both engine and replica simultaneously,
    #          triggering auto-salvage.
    # ------------------------------------------------------------------
    When Create snapshot 3 of volume clone-vol
    And Disable node 1 scheduling
    And Disable node 2 scheduling
    And Create linked clone volume nested-clone-vol from snapshot 3 of volume clone-vol    numberOfReplicas=1
    And Wait for linked clone volume nested-clone-vol replica fields set
    And Enable node 1 scheduling
    And Enable node 2 scheduling
    Then Wait for volume nested-clone-vol size to be ${CLONE_EXPANDED_SIZE_GI}Gi
    # Assert placement and healthyAt rather than running state: the volume is
    # only auto-attached by the clone controller while the clone is in progress,
    # and its attachment ticket is removed once the clone completes, so the
    # replica stops running again before Step 11 attaches the volume explicitly.
    # healthyAt confirms the linked clone actually succeeded for that replica.
    And Volume nested-clone-vol should have 1 replicas on node 0
    And Wait for all volume nested-clone-vol replicas to have HealthyAt set
    # Let the clone controller finish removing its attachment ticket, so the
    # explicit attach in Step 11 does not race with an in-flight detach.
    And Wait for volume nested-clone-vol detached

    # ------------------------------------------------------------------
    # Step 12: Attach nested clone to same node as source; verify data
    # ------------------------------------------------------------------
    When Attach volume nested-clone-vol to same node as volume src-vol
    And Wait for linked clone volume nested-clone-vol clone to complete
    And Wait for volume nested-clone-vol healthy
    Then Check ${WRITE_SIZE_MB} MB data of volume nested-clone-vol at offset 0 matches volume clone-vol
    And Check ${WRITE_SIZE_MB} MB data of volume nested-clone-vol at offset ${CLONE_EXPAND_OFFSET_MB} matches volume clone-vol

    # ------------------------------------------------------------------
    # Step 13a: Snapshot and backup for nested clone
    # ------------------------------------------------------------------
    When Create snapshot 0 of volume nested-clone-vol
    And Create backup 0 for volume nested-clone-vol

    # ------------------------------------------------------------------
    # Step 13b: Expand nested clone to 4Gi; write to expanded region
    # ------------------------------------------------------------------
    When Expand volume nested-clone-vol to ${NESTED_EXPANDED_SIZE_GI}Gi
    Then Wait for volume nested-clone-vol size to be ${NESTED_EXPANDED_SIZE_GI}Gi
    And Write ${WRITE_SIZE_MB} MB data to volume nested-clone-vol at offset ${NESTED_EXPAND_OFFSET_MB}
    And Check ${WRITE_SIZE_MB} MB data of volume nested-clone-vol at offset ${NESTED_EXPAND_OFFSET_MB} is intact

    # ------------------------------------------------------------------
    # Step 14: Crash the instance manager pod on the node all 3 volumes
    #          are attached to. src-vol and clone-vol have replicas on
    #          other nodes and degrade then recover normally.
    #          nested-clone-vol has only 1 replica on this node, so both
    #          its engine and replica fail, putting it in a faulted state
    #          and triggering auto-salvage.
    # ------------------------------------------------------------------
    When Delete v2 instance manager of volume src-vol

    # ------------------------------------------------------------------
    # Step 15: Wait for instance manager restart, auto-salvage for
    #          nested-clone-vol, and all volumes back to healthy.
    # ------------------------------------------------------------------
    Then Wait for longhorn ready
    And Wait for volume src-vol healthy
    And Wait for volume clone-vol healthy
    And Wait for volume nested-clone-vol healthy

    # ------------------------------------------------------------------
    # Step 16: Verify data integrity for all 3 volumes
    # ------------------------------------------------------------------
    Then Check ${WRITE_SIZE_MB} MB data of volume src-vol at offset 0 is intact
    And Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset 0 is intact
    And Check ${WRITE_SIZE_MB} MB data of volume clone-vol at offset ${CLONE_EXPAND_OFFSET_MB} is intact
    And Check ${WRITE_SIZE_MB} MB data of volume nested-clone-vol at offset 0 matches volume clone-vol
    And Check ${WRITE_SIZE_MB} MB data of volume nested-clone-vol at offset ${CLONE_EXPAND_OFFSET_MB} matches volume clone-vol
    And Check ${WRITE_SIZE_MB} MB data of volume nested-clone-vol at offset ${NESTED_EXPAND_OFFSET_MB} is intact

    # ------------------------------------------------------------------
    # Step 17: Delete nested clone; verify clone volume and its
    #          entrypoint snapshot CR still exist
    # ------------------------------------------------------------------
    When Detach volume nested-clone-vol
    And Wait for volume nested-clone-vol detached
    And Delete volume nested-clone-vol
    And Wait for volume nested-clone-vol deleted

    Then Verify volume clone-vol still exists
    And Validate snapshot 3 is in volume clone-vol snapshot list

    # ------------------------------------------------------------------
    # Step 18: Delete clone volume; verify source volume and its
    #          entrypoint snapshot CR still exist
    # ------------------------------------------------------------------
    When Detach volume clone-vol
    And Wait for volume clone-vol detached
    And Delete volume clone-vol
    And Wait for volume clone-vol deleted

    Then Verify volume src-vol still exists
    And Validate snapshot 0 is in volume src-vol snapshot list
