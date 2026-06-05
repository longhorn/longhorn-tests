*** Settings ***
Documentation    Linked-Clone Volume Keywords
...
...    A linked-clone volume is a V2 (SPDK) volume cloned from a snapshot of a
...    source volume.  Unlike a full clone, linked-clone replicas physically
...    co-locate on the same node+disk as source replicas and share the parent
...    snapshot data — no data copy is needed.
...
...    Relevant spec fields:
...      spec.dataSource.type                   = "snapshot"
...      spec.dataSource.parameters.volumeName  = <src-volume-name>
...      spec.dataSource.parameters.snapshotName= <src-snapshot-name>
...      spec.cloneMode                         = "linked-clone"
...      spec.dataEngine                        = "v2"
...
...    After scheduling:
...      spec.linkedCloneSrcReplicaName  (per replica) is set
...      label linked-clone-src-replica  (per replica) is set
...
...    Clone progress: volume.status.cloneStatus.state
...      Initiated -> InProgress -> completed

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/linked_clone_keywords.py


*** Keywords ***
# ---------------------------------------------------------------------------
# Volume lifecycle
# ---------------------------------------------------------------------------

Create linked clone volume ${clone_id} from snapshot ${snap_id} of volume ${src_id}
    [Arguments]    &{config}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    ${snapshot_id} =    Convert To String    ${snap_id}
    create_linked_clone_volume    ${clone_volume_name}    ${src_volume_name}    ${snapshot_id}    &{config}

# ---------------------------------------------------------------------------
# Clone status waits
# ---------------------------------------------------------------------------

Wait for linked clone volume ${clone_id} clone status to be ${state}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    wait_for_linked_clone_volume_clone_status    ${clone_volume_name}    ${state}

Wait for linked clone volume ${clone_id} clone to complete
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    wait_for_linked_clone_volume_clone_status_completed    ${clone_volume_name}

# ---------------------------------------------------------------------------
# CR existence verifications
# ---------------------------------------------------------------------------

Verify engine CR exists for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    verify_engine_cr_exists    ${volume_name}

Verify replica CRs exist for volume ${volume_id}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    verify_replica_crs_exist    ${volume_name}

# ---------------------------------------------------------------------------
# Linked-clone replica field / label / co-location checks
# ---------------------------------------------------------------------------

Wait for linked clone volume ${clone_id} replica fields set
    [Documentation]    Wait until each replica of the clone volume has
    ...    spec.linkedCloneSrcReplicaName set and the linked-clone-src-replica
    ...    label present.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    wait_for_linked_clone_replica_fields_set    ${clone_volume_name}

Verify linked clone volume ${clone_id} replicas co-located with volume ${src_id}
    [Documentation]    Assert every clone replica shares the same nodeID and diskID
    ...    as the source replica referenced by linkedCloneSrcReplicaName.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    verify_linked_clone_replica_colocation    ${clone_volume_name}    ${src_volume_name}

Verify linked clone volume ${clone_id} src replica names unchanged
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    verify_linked_clone_src_replica_names_unchanged    ${clone_volume_name}

# ---------------------------------------------------------------------------
# "Should fail" keywords — webhook-enforced constraints
# ---------------------------------------------------------------------------

Create linked clone volume ${clone_id} with wrong size from snapshot ${snap_id} of volume ${src_id} should fail
    [Documentation]    Attempt to create a linked-clone volume with a spec.size that does
    ...    not match the source snapshot's RestoreSize; expect the webhook to reject it.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    ${snapshot_id} =    Convert To String    ${snap_id}
    create_linked_clone_volume_with_wrong_size_should_fail    ${clone_volume_name}    ${src_volume_name}    ${snapshot_id}

Delete src replica of volume ${volume_id} should fail
    [Documentation]    Attempt to delete a source replica via kubectl; expect the
    ...    admission webhook to deny the request while a linked-clone child exists.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_name} =    get_src_replica_referenced_by_clone    ${volume_name}
    Run command and expect output
    ...    kubectl delete replicas.longhorn.io -n ${LONGHORN_NAMESPACE} ${replica_name}
    ...    admission webhook

Delete entrypoint snapshot of clone volume ${clone_id} should fail
    [Documentation]    Attempt to delete the entrypoint snapshot via kubectl; expect
    ...    the admission webhook to deny the request while a linked-clone volume exists.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${snapshot_name} =    get_entrypoint_snapshot_name_from_clone    ${clone_volume_name}
    ${src_volume_name} =    get_src_volume_name_from_clone    ${clone_volume_name}
    Run command and expect output
    ...    kubectl delete snapshots.longhorn.io -n ${LONGHORN_NAMESPACE} ${snapshot_name}
    ...    admission webhook

Delete volume ${volume_id} as src should fail
    [Documentation]    Attempt to delete the source volume via kubectl; expect the
    ...    admission webhook to deny the request while linked-clone volumes exist.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run command and expect output
    ...    kubectl delete volumes.longhorn.io -n ${LONGHORN_NAMESPACE} ${volume_name}
    ...    admission webhook

Decrease volume ${volume_id} replica count to ${count} should fail
    [Documentation]    Attempt to patch the source volume's numberOfReplicas below
    ...    the number of its linked-clone volumes; expect the webhook to deny it.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    Run command and expect output
    ...    kubectl patch volumes.longhorn.io -n ${LONGHORN_NAMESPACE} ${volume_name} --type=merge -p '{"spec":{"numberOfReplicas": ${count}}}'
    ...    admission webhook

# ---------------------------------------------------------------------------
# "Still exists" assertions (post-clone-deletion checks)
# ---------------------------------------------------------------------------

Verify volume ${volume_id} still exists
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    verify_volume_exists    ${volume_name}

Verify entrypoint snapshot of clone volume ${clone_id} still exists
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${snapshot_name} =    get_entrypoint_snapshot_name_from_clone    ${clone_volume_name}
    ${src_volume_name} =    get_src_volume_name_from_clone    ${clone_volume_name}
    verify_snapshot_exists_by_name    ${src_volume_name}    ${snapshot_name}

# ---------------------------------------------------------------------------
# Data inheritance verification
# ---------------------------------------------------------------------------

Verify linked clone volume ${clone_id} data matches source volume ${src_id}
    [Documentation]    Assert the clone volume contains the same data as the
    ...    source volume (both must be attached).
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    verify_clone_data_matches_source    ${clone_volume_name}    ${src_volume_name}

Verify linked clone volume ${clone_id} expanded data matches volume ${src_id}
    [Documentation]    Assert the clone volume's expanded region (written at an
    ...    offset beyond the original size) matches the source volume's expanded
    ...    data.  Uses the offset/size stored in the source volume's annotations.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    verify_clone_expanded_data_matches_source    ${clone_volume_name}    ${src_volume_name}

# ---------------------------------------------------------------------------
# No-snapshot creation
# ---------------------------------------------------------------------------

Create linked clone volume ${clone_id} from volume ${src_id} without snapshot name
    [Documentation]    Create a linked-clone volume specifying only the source
    ...    volume name.  Longhorn auto-creates the entrypoint snapshot.
    [Arguments]    &{config}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    create_linked_clone_volume_no_snapshot    ${clone_volume_name}    ${src_volume_name}    &{config}

Verify linked clone volume ${clone_id} has entrypoint snapshot label set
    [Documentation]    Assert the linked-clone-source-snapshot label is set on
    ...    the clone volume, confirming Longhorn auto-created the snapshot.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    verify_linked_clone_entrypoint_snapshot_label_set    ${clone_volume_name}

# ---------------------------------------------------------------------------
# Named-snapshot operations (use actual CR names captured before deletion)
# ---------------------------------------------------------------------------

Verify named snapshot ${snap_name} of volume ${volume_id} still exists
    [Documentation]    Assert a snapshot CR (by its actual CR name) still
    ...    exists on the given volume.  Use when the snapshot name was captured
    ...    before the clone volume was deleted and cannot be retrieved from the
    ...    clone volume's dataSource any longer.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    verify_snapshot_exists_by_name    ${volume_name}    ${snap_name}

Delete named snapshot ${snap_name} of volume ${volume_id}
    [Documentation]    Delete a snapshot CR directly by its actual CR name.
    ...    Used to verify that a deletion constraint is lifted after its
    ...    linked-clone volume has been removed.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_named_snapshot_cr    ${volume_name}    ${snap_name}

Wait for named snapshot ${snap_name} of volume ${volume_id} to be deleted
    [Documentation]    Wait until the named snapshot CR is no longer present.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_named_snapshot_cr_deleted    ${volume_name}    ${snap_name}

