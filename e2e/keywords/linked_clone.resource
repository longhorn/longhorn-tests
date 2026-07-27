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

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/volume_keywords.py
Library    ../libs/keywords/snapshot_keywords.py
Library    ../libs/keywords/engine_keywords.py
Library    ../libs/keywords/replica_keywords.py
Library    ../libs/keywords/linked_clone_keywords.py


*** Keywords ***
# ---------------------------------------------------------------------------
# Volume lifecycle
# ---------------------------------------------------------------------------

Create linked clone volume ${clone_id} from snapshot ${snap_id} of volume ${src_id}
    [Arguments]    &{config}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    ${snapshot_name} =    get_snapshot_name    ${src_volume_name}    ${snap_id}
    ${src_size} =    get_volume_size    ${src_volume_name}
    ${data_source} =    Set Variable    snap://${src_volume_name}/${snapshot_name}
    create_volume    ${clone_volume_name}    size=${src_size}    dataEngine=v2
    ...    cloneMode=linked-clone    dataSource=${data_source}    &{config}

# ---------------------------------------------------------------------------
# Clone status waits
# ---------------------------------------------------------------------------

Wait for linked clone volume ${clone_id} clone status to be ${state}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    wait_for_volume_clone_status    ${clone_volume_name}    ${state}

Wait for linked clone volume ${clone_id} clone to complete
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    wait_for_volume_clone_status    ${clone_volume_name}    completed

# ---------------------------------------------------------------------------
# CR existence verifications
# ---------------------------------------------------------------------------

Verify engine CR exists for volume ${volume_id}
    [Documentation]    get_engine_name retries until the volume has exactly one
    ...    engine CR and fails if none is ever created.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${engine_name} =    get_engine_name    ${volume_name}
    Should Not Be Empty    ${engine_name}

Verify replica CRs exist for volume ${volume_id}
    [Documentation]    Passing no count makes wait_for_disk_replica_count wait
    ...    for at least one replica CR and fail if none appears.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    wait_for_disk_replica_count    volume_name=${volume_name}

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
    ${snapshot_name} =    get_snapshot_name    ${src_volume_name}    ${snap_id}
    ${src_size} =    get_volume_size    ${src_volume_name}
    ${wrong_size} =    Evaluate    str(int(${src_size}) * 2)
    ${data_source} =    Set Variable    snap://${src_volume_name}/${snapshot_name}
    ${err} =    Run Keyword And Expect Error    *
    ...    create_volume    ${clone_volume_name}    size=${wrong_size}    numberOfReplicas=1
    ...    dataEngine=v2    cloneMode=linked-clone    dataSource=${data_source}    retry=${False}
    Should Contain Any    ${err}    spec.size    RestoreSize    422

Delete src replica of volume ${volume_id} should fail
    [Documentation]    Attempt to delete a source replica via kubectl; expect the
    ...    admission webhook to deny the request while a linked-clone child exists.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replica_name} =    get_src_replica_referenced_by_clone    ${volume_name}
    ${err} =    Run Keyword And Expect Error    *
    ...    Run command    kubectl delete replicas.longhorn.io -n ${LONGHORN_NAMESPACE} ${replica_name}
    Should Contain    ${err}    admission webhook

Delete entrypoint snapshot of clone volume ${clone_id} should fail
    [Documentation]    Attempt to delete the entrypoint snapshot via kubectl; expect
    ...    the admission webhook to deny the request while a linked-clone volume exists.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${snapshot_name} =    get_entrypoint_snapshot_name_from_clone    ${clone_volume_name}
    ${src_volume_name} =    get_src_volume_name_from_clone    ${clone_volume_name}
    ${err} =    Run Keyword And Expect Error    *
    ...    Run command    kubectl delete snapshots.longhorn.io -n ${LONGHORN_NAMESPACE} ${snapshot_name}
    Should Contain    ${err}    admission webhook

Delete volume ${volume_id} as src should fail
    [Documentation]    Attempt to delete the source volume via kubectl; expect the
    ...    admission webhook to deny the request while linked-clone volumes exist.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${err} =    Run Keyword And Expect Error    *
    ...    Run command    kubectl delete volumes.longhorn.io -n ${LONGHORN_NAMESPACE} ${volume_name}
    Should Contain    ${err}    admission webhook

Decrease volume ${volume_id} replica count to ${count} should fail
    [Documentation]    Attempt to patch the source volume's numberOfReplicas below
    ...    the number of its linked-clone volumes; expect the webhook to deny it.
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${err} =    Run Keyword And Expect Error    *
    ...    Run command    kubectl patch volumes.longhorn.io -n ${LONGHORN_NAMESPACE} ${volume_name} --type=merge -p '{"spec":{"numberOfReplicas": ${count}}}'
    Should Contain    ${err}    admission webhook

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
# No-snapshot creation
# ---------------------------------------------------------------------------

Create linked clone volume ${clone_id} from volume ${src_id} without snapshot name
    [Documentation]    Create a linked-clone volume specifying only the source
    ...    volume name.  Longhorn auto-creates the entrypoint snapshot.
    [Arguments]    &{config}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    ${src_size} =    get_volume_size    ${src_volume_name}
    create_volume    ${clone_volume_name}    size=${src_size}    dataEngine=v2
    ...    cloneMode=linked-clone    dataSource=vol://${src_volume_name}    &{config}

Verify linked clone volume ${clone_id} has entrypoint snapshot label set
    [Documentation]    Assert the linked-clone-source-snapshot label is set on
    ...    the clone volume, confirming Longhorn auto-created the snapshot.
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    verify_linked_clone_entrypoint_snapshot_label_set    ${clone_volume_name}

Verify all replicas of volume ${src_id} are referenced by clone ${clone_id}
    [Documentation]    Assert that every replica of the src volume is referenced
    ...    by at least one clone replica's linkedCloneSrcReplicaName field.
    ${src_volume_name} =    generate_name_with_suffix    volume    ${src_id}
    ${clone_volume_name} =    generate_name_with_suffix    volume    ${clone_id}
    verify_all_src_replicas_referenced_by_clone    ${src_volume_name}    ${clone_volume_name}
