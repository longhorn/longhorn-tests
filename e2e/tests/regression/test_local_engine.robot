*** Settings ***
Documentation    Local data engine end-to-end test

Test Tags    regression    coretest    local-engine
# A healthy test finishes in 2-4 minutes. The library waits are unbounded
# retry loops, so a stuck test must fail here instead of hanging the run.
Test Timeout    15 minutes

Resource    ../../keywords/variables.resource
Resource    ../../keywords/local_engine.resource
Resource    ../../keywords/longhorn.resource
Resource    ../../keywords/workload.resource

Suite Setup       Set up local engine test
Suite Teardown    Clean up local engine suite
Test Teardown     Clean up local engine test

*** Test Cases ***
Test Local Engine CSI Volume Lifecycle
    [Documentation]    Verify the local engine lifecycle on a dedicated LVM disk.
    ...    1. Adding an LVM disk initializes its PV and VG through the local instance manager.
    ...    2. CSI provisions and attaches a one-replica local volume on that disk.
    ...    3. I/O continues without restarting the workload while the local instance manager restarts.
    ...    4. Data remains intact across CSI detach and reattach.
    ...    5. Deleting the PVC removes the LV, and deleting the disk removes it from the Node CR.
    Given Use local engine provisioning mode    thick
    And Use local engine storage layout    per-disk
    And Add and verify local engine test disk
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file local-engine-data in deployment 0
    Then Check deployment 0 data in file local-engine-data is intact

    When Restart local instance manager during sustained I/O
    Then Check deployment 0 data in file local-engine-data is intact
    And Verify local engine CSI workload backend

    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    And Wait for volume of persistentvolumeclaim 0 healthy
    Then Check deployment 0 data in file local-engine-data is intact
    And Verify local engine CSI workload backend

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk

Test Local Engine Resize And Independent Disks
    [Tags]    resize    storage-layout    per-disk
    [Documentation]    Verify resize and independent per-disk VG behavior.
    ...    1. Two LVM disks on one node become independent schedulable VGs.
    ...    2. A CSI volume is forced onto the second disk.
    ...    3. The LV and filesystem expand through CSI without losing data.
    ...    4. Sustained verified I/O survives a local instance-manager restart.
    Given Use local engine provisioning mode    thick
    And Use local engine storage layout    per-disk
    And Require second local engine test disk
    And Add and verify independent local engine test disks
    And Disable first local engine test disk scheduling
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend on second disk

    When Write 64 MB data to file resize-data in deployment 0
    And Expand local engine CSI workload to 3Gi
    Then Check deployment 0 data in file resize-data is intact

    When Restart local instance manager during sustained I/O
    Then Check deployment 0 data in file resize-data is intact
    And Verify local engine CSI workload backend on second disk

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify independent local engine test disks

Test Local Engine Pooled Per Node Layout
    [Tags]    storage-layout    per-node
    [Documentation]    Verify multiple disks form one schedulable node VG.
    ...    1. The first PV remains the representative and a second PV extends its VG.
    ...    2. Only the representative reports pooled capacity and receives the replica.
    ...    3. Layout changes are rejected while the node has multiple LVM disks.
    ...    4. The representative cannot be removed before the member disks.
    Given Use local engine provisioning mode    thin
    And Use local engine storage layout    per-node
    And Require second local engine test disk
    And Add and verify local engine test disk
    And Create local engine CSI workload with provisioning mode    thin
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file pooled-layout-data in deployment 0
    And Add and verify pooled local engine member disk
    Then Verify local engine storage layout change is rejected    per-disk
    And Check deployment 0 data in file pooled-layout-data is intact
    And Verify local engine CSI workload backend

    When Delete local engine CSI workload and verify backend cleanup
    Then Verify local engine representative disk removal is rejected
    And Delete and verify independent local engine test disks

Test Local Engine Capacity Scheduling And Metrics
    [Tags]    capacity    metrics
    [Documentation]    Verify capacity-aware placement and complete local storage metrics.
    ...    1. The CSI provisioner advertises the LVM VG's capacity for its node.
    ...    2. Kubernetes schedules an unpinned pod onto the only node with local capacity.
    ...    3. Capacity, usage, reservation, throughput, IOPS, and latency are exported.
    Given Use local engine provisioning mode    thick
    And Use local engine storage layout    per-disk
    And Add and verify local engine test disk
    And Create capacity-aware local engine CSI workload
    Then Verify local engine CSI workload backend

    When Verify local engine capacity and I/O metrics
    Then Verify local engine CSI workload backend

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk

Test Local Engine Thick Provisioning
    [Tags]    provisioning-mode    thick
    [Documentation]    Verify the default StorageClass mode creates a thick LV without a thin pool.
    Given Use local engine provisioning mode    thick
    And Use local engine storage layout    per-disk
    And Add and verify local engine test disk
    And Create local engine CSI workload
    When Write 64 MB data to file provisioning-mode-data in deployment 0
    Then Verify local engine CSI workload backend
    And Verify local engine provisioning backend    thick

    When Delete local engine CSI workload and verify backend cleanup
    Then Verify local engine thin pool is absent
    And Delete and verify local engine test disk

Test Local Engine Thin Provisioning
    [Tags]    provisioning-mode    thin
    [Documentation]    Verify thin provisioning, zeroing, accounting, and final pool removal.
    Given Use local engine provisioning mode    thin
    And Use local engine storage layout    per-disk
    And Add and verify local engine test disk
    And Create local engine CSI workload with provisioning mode    thin
    When Write 64 MB data to file provisioning-mode-data in deployment 0
    Then Verify local engine CSI workload backend
    And Verify local engine provisioning backend    thin

    When Delete local engine CSI workload and verify backend cleanup
    Then Verify local engine thin pool is absent
    And Delete and verify local engine test disk

Test Local Engine Volume Spec Validation
    [Tags]    validation
    [Documentation]    Verify the admission webhook rejects local data engine volume
    ...    specs the engine cannot serve, so an unsupported volume never reaches a
    ...    v1 or v2 code path.
    ...    1. The engine is single-copy and node-bound, so more than one replica and
    ...       any data locality other than strict-local are refused.
    ...    2. Shared access and migration have no meaning for a node-local device.
    ...    3. Encryption and backing images are not implemented yet and must fail
    ...       explicitly rather than be silently ignored.
    ...    4. Only the blockdev frontend is supported.
    ...
    ...    No disk is required: every case is rejected before scheduling.
    Given Use local engine provisioning mode    thick
    And Use local engine storage layout    per-disk
    Then Create local engine volume 0 should be rejected    exactly one replica    numberOfReplicas=${3}
    And Create local engine volume 0 should be rejected    strict-local    dataLocality=disabled
    And Create local engine volume 0 should be rejected    shared access or migration    accessMode=RWX
    And Create local engine volume 0 should be rejected    shared access or migration    migratable=${True}
    And Create local engine volume 0 should be rejected    do not support encryption    encrypted=${True}
    And Create local engine volume 0 should be rejected    do not support backing images    backingImage=local-engine-no-such-image
    And Create local engine volume 0 should be rejected    blockdev    frontend=iscsi

Test Local Engine Node Reboot With Attached Thick Volume
    [Tags]    reboot    provisioning-mode    thick
    # A node reboot adds the VM restart, k3s, and Longhorn coming back.
    [Timeout]    30 minutes
    [Documentation]    Verify an attached thick local volume survives a reboot of its node.
    ...    1. Thick LVs are created with host autoactivation off, so the host leaves
    ...       the LV inactive at boot and the instance manager must bring it back.
    ...    2. After the reboot the volume returns to healthy on the same LV without a
    ...       manual detach, and the workload's data is intact.
    Given Use local engine provisioning mode    thick
    And Use local engine storage layout    per-disk
    And Add and verify local engine test disk
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file reboot-data in deployment 0
    And Reboot volume node of deployment 0
    And Wait for longhorn ready
    Then Wait for volume of persistentvolumeclaim 0 healthy
    And Verify local engine CSI workload backend
    And Wait for deployment 0 pods stable
    And Check deployment 0 data in file reboot-data is intact

    When Write 64 MB data to file post-reboot-data in deployment 0
    Then Check deployment 0 data in file post-reboot-data is intact
    And Check deployment 0 data in file reboot-data is intact

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk

Test Local Engine Node Reboot With Attached Thin Volume
    [Tags]    reboot    provisioning-mode    thin
    [Timeout]    30 minutes
    [Documentation]    Verify an attached thin local volume survives a reboot of its node.
    ...    Whether the host activates thin LVs at boot depends on its LVM
    ...    configuration; the instance manager must not rely on it.
    Given Use local engine provisioning mode    thin
    And Use local engine storage layout    per-disk
    And Add and verify local engine test disk
    And Create local engine CSI workload with provisioning mode    thin
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file reboot-data in deployment 0
    And Reboot volume node of deployment 0
    And Wait for longhorn ready
    Then Wait for volume of persistentvolumeclaim 0 healthy
    And Verify local engine CSI workload backend
    And Wait for deployment 0 pods stable
    And Check deployment 0 data in file reboot-data is intact

    When Write 64 MB data to file post-reboot-data in deployment 0
    Then Check deployment 0 data in file post-reboot-data is intact
    And Check deployment 0 data in file reboot-data is intact

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk
