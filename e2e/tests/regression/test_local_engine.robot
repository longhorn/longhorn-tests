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
    ...    1. Adding an LVM disk turns its device into a volume group through the local instance manager.
    ...    2. CSI provisions and attaches a one-replica local volume on that disk.
    ...    3. I/O continues without restarting the workload while the local instance manager restarts.
    ...    4. Data remains intact across CSI detach and reattach.
    ...    5. Deleting the PVC removes the LV, and deleting the disk removes it from the Node CR.
    Given Use local engine provisioning mode    thick
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

Test Local Engine Disk Registration By Device Alias
    [Tags]    disk
    [Documentation]    Verify an LVM disk works when registered by a stable udev alias of its device.
    ...    1. The disk is added by its /dev/disk/by-id (or by-path) link instead of the kernel name.
    ...    2. The volume group forms on the underlying device and the disk becomes schedulable.
    ...    3. A CSI volume is provisioned on the aliased disk and holds data.
    ...    4. Deleting the disk by the alias removes its VG and PV and leaves the device without LVM signatures.
    Given Use local engine provisioning mode    thick
    And Use stable device alias for local engine test disk
    And Add and verify local engine test disk
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file alias-data in deployment 0
    Then Check deployment 0 data in file alias-data is intact

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk
    Then Verify local engine test disk device is clean

Test Local Engine Volume Resize
    [Tags]    resize
    [Documentation]    Verify a local volume expands in place.
    ...    1. The LV and filesystem expand through CSI without losing data.
    ...    2. Sustained verified I/O survives a local instance-manager restart afterwards.
    Given Use local engine provisioning mode    thick
    And Add and verify local engine test disk
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file resize-data in deployment 0
    And Expand local engine CSI workload to 3Gi
    Then Check deployment 0 data in file resize-data is intact

    When Restart local instance manager during sustained I/O
    Then Check deployment 0 data in file resize-data is intact
    And Verify local engine CSI workload backend

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk

Test Local Engine Multi-Device Volume Group
    [Tags]    disk    multi-device
    [Documentation]    Verify that an LVM disk path listing several devices becomes one volume group.
    ...    1. The disk path names both test devices separated by ";".
    ...    2. Both devices become physical volumes of one tagged volume group, whose UUID is the disk UUID
    ...       and whose capacity spans both devices.
    ...    3. A CSI volume works on the disk and holds data.
    ...    4. Deleting the disk removes the volume group and leaves both devices without LVM signatures.
    Given Use local engine provisioning mode    thick
    And Require second local engine test disk
    And Add and verify multi-device local engine test disk
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file multi-device-data in deployment 0
    Then Check deployment 0 data in file multi-device-data is intact

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk
    Then Verify local engine test disk device is clean

Test Local Engine Disk Path Validation
    [Tags]    disk    validation
    [Documentation]    Verify the node admission webhook's rules for LVM disk paths on one registered disk.
    ...    1. The path of a registered disk cannot change: devices cannot be added to or removed
    ...    from a volume group in place, so a new path is rejected and the disk keeps the old one.
    ...    2. A device belongs to exactly one LVM disk: a second disk listing the same device,
    ...    and a disk listing a device twice, are rejected.
    Given Use local engine provisioning mode    thick
    And Require second local engine test disk
    And Add and verify local engine test disk
    Then Verify local engine test disk path change is rejected    ${LOCAL_ENGINE_SECOND_DISK_PATH}
    And Verify local engine test disk path change is rejected    ${LOCAL_ENGINE_DISK_PATH};${LOCAL_ENGINE_SECOND_DISK_PATH}
    And Verify registering local engine test disk device again is rejected

    When Delete and verify local engine test disk

Test Local Engine Rejects Non-Empty Device
    [Tags]    disk    validation
    [Documentation]    Verify that a device carrying a filesystem is not turned into a volume group.
    ...    1. The disk whose device has an ext4 filesystem is reported not ready and names the device.
    ...    2. Removing the disk and wiping the device leaves the device clean.
    [Teardown]    Clean up local engine test and wipe second test disk device
    Given Use local engine provisioning mode    thick
    And Require second local engine test disk
    And Format second local engine test disk device
    When Add second local engine test disk and expect it not ready    existing filesystem or partition table
    And Remove second local engine test disk
    And Wipe second local engine test disk device
    Then Verify local engine test disk device is clean    ${LOCAL_ENGINE_SECOND_DISK_PATH}

Test Local Engine Capacity Scheduling And Metrics
    [Tags]    capacity    metrics
    [Documentation]    Verify capacity-aware placement and complete local storage metrics.
    ...    1. The CSI provisioner advertises the LVM VG's capacity for its node.
    ...    2. Kubernetes schedules an unpinned pod onto the only node with local capacity.
    ...    3. Capacity, usage, reservation, throughput, IOPS, and latency are exported.
    Given Use local engine provisioning mode    thick
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
    And Add and verify local engine test disk
    And Create local engine CSI workload
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file reboot-data in deployment 0
    And Reboot volume node of deployment 0
    And Check local instance managers follow LVM disks on all worker nodes
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
    And Add and verify local engine test disk
    And Create local engine CSI workload with provisioning mode    thin
    Then Verify local engine CSI workload backend

    When Write 64 MB data to file reboot-data in deployment 0
    And Reboot volume node of deployment 0
    And Check local instance managers follow LVM disks on all worker nodes
    Then Wait for volume of persistentvolumeclaim 0 healthy
    And Verify local engine CSI workload backend
    And Wait for deployment 0 pods stable
    And Check deployment 0 data in file reboot-data is intact

    When Write 64 MB data to file post-reboot-data in deployment 0
    Then Check deployment 0 data in file post-reboot-data is intact
    And Check deployment 0 data in file reboot-data is intact

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk

Test Local Engine Instance Manager Follows LVM Disk
    [Tags]    instance-manager
    [Documentation]    Verify a node runs a local instance manager only while it has an LVM disk.
    ...    1. With the local engine enabled and no LVM disk, the test node has no local
    ...       instance manager, and no worker node without an LVM disk has one.
    ...    2. Adding the LVM disk creates the local instance manager and the disk
    ...       initializes through it.
    ...    3. A CSI volume works on that disk.
    ...    4. Deleting the last LVM disk removes the local instance manager again.
    Given Use local engine provisioning mode    thick
    Then Check local instance manager is absent on local engine test node
    And Check local instance managers follow LVM disks on all worker nodes

    When Add and verify local engine test disk
    Then Check local instance manager is running on local engine test node
    And Check local instance managers follow LVM disks on all worker nodes

    When Create local engine CSI workload
    And Write 64 MB data to file instance-manager-data in deployment 0
    Then Verify local engine CSI workload backend
    And Check deployment 0 data in file instance-manager-data is intact

    When Delete local engine CSI workload and verify backend cleanup
    And Delete and verify local engine test disk
    Then Check local instance manager is absent on local engine test node
    And Check local instance managers follow LVM disks on all worker nodes
