*** Settings ***
Documentation    Encrypted Volume Test Cases

Test Tags    regression    encrypted

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/host.resource
Resource    ../keywords/engine_image.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Encrypted Volume Basic
    [Tags]    rwo    rwx
    [Documentation]    Test basic encrypted volume operations for both RWO and RWX volumes.
    ...                Deployment 0 = RWO, Deployment 1 = RWX.
    ...
    ...                Expected sizes for a 100 Mi volume:
    ...                    - Replica backend file = 116 Mi (requested + 16 Mi pre-allocated).
    ...                    - v2 data engine: Replica backend N/A (format differs, only device size is verified).
    ...                    - dm-crypt device (RWO instance manager) = 100 Mi (full requested size).
    ...                    - dm-crypt device (RWX sharemanager pod) = 100 Mi (full requested size).
    ...                    - Mounted filesystem (workload pod, RWO/RWX) = ~100 Mi (accounting for filesystem overhead).
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 116Mi
        Assert replica file size of deployment 1 is 116Mi
    END
    # Verify sizes at different layers: backend replica → dm-crypt device → mounted filesystem
    And Assert disk size in instance manager pod for deployment 0 is 100Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 100Mi
    And Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Scale down deployment 0 to detach volume
    And Scale down deployment 1 to detach volume
    And Scale up deployment 0 to attach volume
    And Scale up deployment 1 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Wait for workloads pods stable    deployment 0
    And Wait for workloads pods stable    deployment 1
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 116Mi
        Assert replica file size of deployment 1 is 116Mi
    END
    # Re-verify sizes after scale down/up cycle
    And Assert disk size in instance manager pod for deployment 0 is 100Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 100Mi
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

Test Encrypted Volume Cloning
    [Tags]    rwo    rwx
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim source-rwo-pvc    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim source-rwx-pvc    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Wait for volume of persistentvolumeclaim source-rwo-pvc to be created
    And Wait for volume of persistentvolumeclaim source-rwx-pvc to be created
    And Wait for volume of persistentvolumeclaim source-rwo-pvc detached
    And Wait for volume of persistentvolumeclaim source-rwx-pvc detached

    And Create deployment source-rwo-deployment with persistentvolumeclaim source-rwo-pvc
    And Create deployment source-rwx-deployment with persistentvolumeclaim source-rwx-pvc
    And Wait for volume of deployment source-rwo-deployment healthy
    And Wait for volume of deployment source-rwx-deployment healthy
    And Wait for workloads pods stable    deployment source-rwo-deployment
    And Wait for workloads pods stable    deployment source-rwx-deployment
    And Write 10 MB data to file data.txt in deployment source-rwo-deployment
    And Write 10 MB data to file data.txt in deployment source-rwx-deployment
    And Record file data.txt checksum in deployment source-rwo-deployment as checksum source-rwo-pvc
    And Record file data.txt checksum in deployment source-rwx-deployment as checksum source-rwx-pvc


    When Create persistentvolumeclaim cloned-rwo-pvc from persistentvolumeclaim source-rwo-pvc    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim cloned-rwx-pvc from persistentvolumeclaim source-rwx-pvc    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Wait for volume of persistentvolumeclaim cloned-rwo-pvc detached
    And Wait for volume of persistentvolumeclaim cloned-rwx-pvc detached

    And Create deployment cloned-rwo-deployment with persistentvolumeclaim cloned-rwo-pvc
    And Create deployment cloned-rwx-deployment with persistentvolumeclaim cloned-rwx-pvc

    And Wait for volume of deployment cloned-rwo-deployment healthy
    And Wait for volume of deployment cloned-rwx-deployment healthy
    And Wait for workloads pods stable    deployment cloned-rwo-deployment
    And Wait for workloads pods stable    deployment cloned-rwx-deployment
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment cloned-rwo-deployment is 116Mi
        Assert replica file size of deployment cloned-rwx-deployment is 116Mi
    END
    And Assert disk size in instance manager pod for deployment cloned-rwo-deployment is 100Mi
    And Assert encrypted disk size in sharemanager pod for deployment cloned-rwx-deployment is 100Mi
    And Check deployment cloned-rwo-deployment file data.txt checksum matches checksum source-rwo-pvc
    And Check deployment cloned-rwx-deployment file data.txt checksum matches checksum source-rwx-pvc

Test Encrypted Volume Snapshot Clone
    [Tags]    rwo    snapshot    clone
    [Documentation]    Test creating an encrypted volume from another encrypted volume's snapshot.
    ...
    ...                Steps:
    ...                  1. Create a 100 Mi encrypted RWO volume (deployment 0).
    ...                  2. Write 10 MB of data and record checksum.
    ...                  3. Take a snapshot (snapshot 0).
    ...                  4. Create a new encrypted volume (volume 1) from snapshot 0.
    ...                  5. Attach the new volume to deployment 1 via the crypto StorageClass.
    ...                  6. Verify data integrity and size.
    ...
    ...                Expected (v1 data engine):
    ...                  - Source volume: dm-crypt device = 100 Mi, replica = 116 Mi.
    ...                  - Cloned volume: dm-crypt device = 100 Mi, replica = 116 Mi.
    ...                  - Data checksum matches original.
    ...
    ...                Expected (v2 data engine):
    ...                  - Source volume: dm-crypt device = 84 Mi (requested - 16 Mi).
    ...                  - Cloned volume: dm-crypt device = 84 Mi (requested - 16 Mi).
    ...                  - Data checksum matches original.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 10 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0

    # Verify source volume size
    Assert disk size in instance manager pod for deployment 0 is 100Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 116Mi
    END

    # Create snapshot from source volume
    When Create snapshot 0 for deployment 0 volume
    And Wait for snapshot 0 of deployment 0 volume ready

    # Create new encrypted volume from snapshot
    When Create volume 1 from snapshot 0 of deployment 0 volume    size=100Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached

    # Attach cloned volume to new deployment with crypto SC (to trigger luksOpen)
    And Create deployment 1 with volume 1    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto
    And Wait for volume of deployment 1 healthy

    # Verify cloned volume size and data integrity
    Then Check deployment 1 file data.txt checksum matches checksum 0
    And Assert disk size in instance manager pod for deployment 1 is 100Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 116Mi
    END

Test Encrypted Volume Expansion
    [Tags]    rwo    rwx    expansion
    [Documentation]    Test Plan: Volume Expansion – new engine path (RWO + RWX)
    ...
    ...                Create a 100 Mi encrypted volume (new engine), write 10 Mi of data,
    ...                then expand to 200 Mi. Deployment 0 = RWO, Deployment 1 = RWX.
    ...
    ...                Expected after expansion:
    ...                  - Instance manager (RWO) shows 200 Mi.
    ...                  - Share manager pod (RWX) shows 200 Mi; pod is NOT recreated.
    ...                  - Replica image file on the worker node shows 200 Mi + 16 Mi = 216 Mi.
    ...                  - Previously written data is intact.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Expand deployment 0 volume to 200Mi
    And Expand deployment 1 volume to 200Mi
    Then Wait for deployment 0 volume size expanded
    And Wait for deployment 1 volume size expanded
    And Check deployment 0 pods did not restart
    And Check deployment 1 pods did not restart
    And Check no sharemanager pod of deployment 1 recreation
    And Assert disk size in instance manager pod for deployment 0 is 200Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 200Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 216Mi
        Assert replica file size of deployment 1 is 216Mi
    END
    And Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

Test Encrypted RWO Block Volume Online Expansion
    [Tags]    rwo    expansion    block-volume
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with block persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Make block device filesystem in deployment 0
    And Mount block device on /data in deployment 0
    And Write 10 MB data to file data1.txt in deployment 0
    Then Check deployment 0 data in file data1.txt is intact

    When Expand deployment 0 volume to 200 Mi
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    # Verify the actual disk size in the instance manager pod.
    # NOTE: With the new engine (v1.12+), the 16 Mi LUKS header is pre-allocated
    # in the replica backend file (replica size = requested size + 16 Mi).
    # The dm-crypt device therefore presents the full requested size to the workload.
    # Therefore, after expansion to 200 Mi, the dm-crypt device shows 200 Mi.
    And Assert disk size in instance manager pod for deployment 0 is 200Mi
    And Assert block device size in deployment pod for deployment 0 is 200Mi
    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    Then Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Mount block device on /data in deployment 0
    And Write 60 MB data to file data2.txt in deployment 0
    Then Check deployment 0 data in file data2.txt is intact

Test Encrypted Volume Replica Rebuild
    [Tags]    rwo    rwx    replica-rebuild
    [Documentation]    Test Plan: Replica Rebuild – new engine path (RWO + RWX)
    ...
    ...                Create a 100 Mi encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1) with the new engine.
    ...                Write 10 Mi of data to each, then delete one replica per volume
    ...                to trigger a rebuild.
    ...
    ...                Expected after rebuild:
    ...                  - Rebuild completes successfully (volume returns to healthy).
    ...                  - The dm-crypt device size is unchanged: 100 Mi (RWO instance manager)
    ...                    and 100 Mi (RWX share manager pod).
    ...                  - The newly rebuilt replica file size is 100 Mi + 16 Mi = 116 Mi,
    ...                    matching the existing replicas (v1 only).
    ...                  - Data integrity (md5sum / checksum) is intact.
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Delete replica of deployment 0 volume on replica node
    And Wait until volume of deployment 0 replica rebuilding completed on replica node
    Then Wait for volume of deployment 0 healthy
    And Assert disk size in instance manager pod for deployment 0 is 100Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 116Mi
    END
    And Check deployment 0 data in file data.txt is intact

    When Delete replica of deployment 1 volume on replica node
    And Wait until volume of deployment 1 replica rebuilding completed on replica node
    Then Wait for volume of deployment 1 healthy
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 100Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 116Mi
    END
    And Check deployment 1 data in file data.txt is intact

Test Encrypted Volume Backup Restore To Encrypted Volume
    [Tags]    rwo    rwx    backup    restore
    [Documentation]    Test Plan: Backup Restore – restore as encrypted (RWO + RWX)
    ...
    ...                Create a 100 Mi encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1), write 10 Mi of data to each, take backups.
    ...                Restore each backup to a new encrypted volume.
    ...                Deployment 0 = RWO source, Deployment 1 = RWX source.
    ...                Deployment 2 = restored from dep 0 backup, Deployment 3 = restored from dep 1 backup.
    ...
    ...                Expected:
    ...                  - Restored volumes' dm-crypt device shows exactly 100 Mi.
    ...                  - Restored volumes' replica backend file is exactly 100 Mi + 16 Mi.
    ...                  - The 10 Mi payload checksum matches the original.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support encrypted volume restore with encrypted=True (https://github.com/longhorn/longhorn/issues/13163)
    END
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0
    And Record file data.txt checksum in deployment 1 as checksum 1

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    When Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume

    # Restore to new encrypted volumes (encrypted=True)
    When Create volume 2 from backup 0 of deployment 0 volume    size=100Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Create volume 3 from backup 1 of deployment 1 volume    size=100Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Wait for volume 2 detached
    And Wait for volume 3 detached
    # Mount the restored volumes via deployments so that CSI opens the LUKS container.
    # Must use longhorn-crypto SC (with node-stage-secret-ref) so luksOpen is triggered.
    And Create deployment 2 with volume 2    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto
    And Create deployment 3 with volume 3    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto
    And Wait for volume of deployment 2 healthy
    And Wait for volume of deployment 3 healthy
    Then Assert disk size in instance manager pod for deployment 2 is 100Mi
    And Assert disk size in instance manager pod for deployment 3 is 100Mi
    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 116Mi
        Assert replica file size of deployment 3 is 116Mi
    END
    And Check deployment 2 file data.txt checksum matches checksum 0
    And Check deployment 3 file data.txt checksum matches checksum 1

Test Encrypted Volume Backup Restore To Unencrypted Volume
    [Tags]    rwo    rwx    backup    restore
    [Documentation]    Test Plan: Backup Restore – restore as unencrypted (RWO + RWX)
    ...
    ...                Create a 100 Mi encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1), write 10 Mi of data to each, take backups, then
    ...                restore each as an unencrypted volume (encrypted=False).
    ...                Deployment 0 = RWO source, Deployment 1 = RWX source.
    ...                Volume 2 = restored from dep 0 backup, Volume 3 = restored from dep 1 backup.
    ...
    ...                Expected:
    ...                  - Since encrypted=False, Longhorn does not pre-allocate extra 16 Mi.
    ...                    The replica backend file is exactly 100 Mi (no LUKS pre-allocation),
    ...                    compared to 100 Mi + 16 Mi for an encrypted=True restore.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    ...                - Issue: https://github.com/longhorn/longhorn/issues/13234
    Skip    This test case implementation is blocked by https://github.com/longhorn/longhorn/issues/13234.
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=100Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    When Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume
    When Create volume 2 from backup 0 of deployment 0 volume    size=100Mi    encrypted=False    dataEngine=${DATA_ENGINE}
    And Create volume 3 from backup 1 of deployment 1 volume    size=100Mi    encrypted=False    dataEngine=${DATA_ENGINE}
    Then Wait for volume 2 detached
    And Wait for volume 3 detached
    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of volume 2 is 100Mi
        Assert replica file size of volume 3 is 100Mi
    END

Test Encrypted Volume Upgrade
    [Tags]    rwo    rwx    block-volume    expansion    replica-rebuild    engine-upgrade    old-engine
    [Documentation]    Test Plan: Old Engine – LUKS Header Pre-allocation across Volume Modes + Upgrade
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set.
    ...                - Covers old-engine (v1.11) LUKS header sizing behavior across ALL volume modes.
    ...                - Each deployment is dedicated to a specific test scenario for better isolation.
    ...
    ...                Deployment Layout:
    ...                  - Deployment 0: RWO Filesystem (initial state + replica rebuild at 100 Mi)
    ...                  - Deployment 1: RWX Filesystem (initial state + replica rebuild at 100 Mi)
    ...                  - Deployment 2: RWO Block (initial state + engine upgrade)
    ...                  - Deployment 3: RWO Filesystem (expansion + replica rebuild at 200 Mi)
    ...                  - Deployment 4: RWX Filesystem (expansion + replica rebuild at 200 Mi)
    ...                  - Deployment 5: RWO Filesystem (workload reattach test)
    ...                  - Deployment 6: RWX Filesystem (workload reattach test)
    ...                  - Deployment 7: RWO Filesystem (backup/restore with new-engine semantics)
    ...                  - Deployment 8: RWX Filesystem (backup/restore with new-engine semantics)
    ...
    ...                Test Scenarios:
    ...                  A. Initial State Verification (deployments 0-4):
    ...                     - Old engine: device = requested_size - 16 Mi, replica = requested_size
    ...
    ...                  B. Replica Rebuild at 100 Mi (deployments 0, 1):
    ...                     - Verify rebuilt replica = 100 Mi (old engine)
    ...
    ...                  C. Expansion (deployments 3, 4):
    ...                     - Expand 100 Mi → 200 Mi
    ...                     - Device = 184 Mi, replica = 200 Mi (old engine)
    ...
    ...                  D. Replica Rebuild at 200 Mi (deployments 3, 4):
    ...                     - Verify rebuilt replica = 200 Mi (old engine)
    ...
    ...                  E. Engine Upgrade (deployments 0-4, v1 only):
    ...                     - After upgrade: device = full size, replica = requested_size + 16 Mi
    ...
    ...                  F. Workload Reattach test (deployments 5, 6):
    ...                     - Test old-engine and new-engine workload reattach behavior
    ...                     - Old engine: device = 84 Mi, replica = 100 Mi
    ...                     - New engine: device = 100 Mi, replica = 116 Mi
    ...
    ...                  G. Backup/Restore (deployments 5, 6):
    ...                     - Restore pre-upgrade backups with new-engine semantics
    ...                     - Device = 100 Mi, replica = 116 Mi
    ...
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    ELSE IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
        Skip    This test only applies to the v1.11.x → v1.12+ upgrade path; got stable version ${LONGHORN_STABLE_VERSION}
    END

    # ==================== Setup ====================
    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks

    # ==================== Create All Volumes (Pre-Upgrade) ====================
    When Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    # Deployment 0: RWO Filesystem (initial state + replica rebuild at 100 Mi)
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 0 with persistentvolumeclaim 0

    # Deployment 1: RWX Filesystem (initial state + replica rebuild at 100 Mi)
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 1 with persistentvolumeclaim 1

    # Deployment 2: RWO Block (initial state + engine upgrade)
    And Create persistentvolumeclaim 2    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 2 with block persistentvolumeclaim 2

    # Deployment 3: RWO Filesystem (expansion + replica rebuild at 200 Mi)
    And Create persistentvolumeclaim 3    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 3 with persistentvolumeclaim 3

    # Deployment 4: RWX Filesystem (expansion + replica rebuild at 200 Mi)
    And Create persistentvolumeclaim 4    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 4 with persistentvolumeclaim 4

    # Deployment 5: RWO Filesystem (initial state + workload reattach at 100 Mi)
    And Create persistentvolumeclaim 5    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 5 with persistentvolumeclaim 5

    # Deployment 6: RWX Filesystem (initial state + workload reattach at 100 Mi)
    And Create persistentvolumeclaim 6    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=100Mi
    And Create deployment 6 with persistentvolumeclaim 6

    Then Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Wait for volume of deployment 2 healthy
    And Wait for volume of deployment 3 healthy
    And Wait for volume of deployment 4 healthy
    And Wait for volume of deployment 5 healthy
    And Wait for volume of deployment 6 healthy

    # ==================== Pre-Upgrade: Write Data & Backup ====================
    # Write data to filesystem deployments for data integrity verification
    When Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    And Write 10 MB data to file data.txt in deployment 3
    And Write 10 MB data to file data.txt in deployment 4
    And Write 10 MB data to file data.txt in deployment 5
    And Write 10 MB data to file data.txt in deployment 6

    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact
    And Check deployment 3 data in file data.txt is intact
    And Check deployment 4 data in file data.txt is intact
    And Check deployment 5 data in file data.txt is intact
    And Check deployment 6 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0
    And Record file data.txt checksum in deployment 1 as checksum 1

    # Create backups for later restore testing
    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    And Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume

    # ==================== Pre-Upgrade: Initial State Verification ====================
    # All deployments should show old-engine semantics: device = requested_size - 16 Mi
    # Deployment 0 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    Then Assert disk size in instance manager pod for deployment 0 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 100Mi
    END

    # Deployment 1 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 100Mi
    END

    # Deployment 2 (RWO Block): blockdev = 84 Mi, replica = 100 Mi
    And Assert block device size in deployment pod for deployment 2 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 100Mi
    END

    # Deployment 3 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert disk size in instance manager pod for deployment 3 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 100Mi
    END

    # Deployment 4 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 4 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 4 is 100Mi
    END

    # Deployment 5 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert disk size in instance manager pod for deployment 5 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 5 is 100Mi
    END

    # Deployment 6 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 6 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 6 is 100Mi
    END

    # ==================== Upgrade Longhorn (Keep Old Engine) ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0

    FOR    ${i}    IN RANGE    7
        Check volume endpoint on node of deployment ${i}
    END

    When Upgrade Longhorn to custom version
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Wait for volume of deployment 2 healthy
    And Wait for volume of deployment 3 healthy
    And Wait for volume of deployment 4 healthy
    And Wait for volume of deployment 5 healthy
    And Wait for volume of deployment 6 healthy

    FOR    ${i}    IN RANGE    7
        Check volume endpoint on node of deployment ${i}
    END

    # ==================== Post-Upgrade: Initial State Verification ====================
    # Verify old engine semantics are preserved after Longhorn system upgrade
    # Deployment 0 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    Then Assert disk size in instance manager pod for deployment 0 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 100Mi
    END

    # Deployment 1 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 100Mi
    END

    # Deployment 2 (RWO Block): blockdev = 84 Mi, replica = 100 Mi
    And Assert block device size in deployment pod for deployment 2 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 100Mi
    END

    # Deployment 3 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert disk size in instance manager pod for deployment 3 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 100Mi
    END

    # Deployment 4 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 4 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 4 is 100Mi
    END

    # Deployment 5 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert disk size in instance manager pod for deployment 5 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 5 is 100Mi
    END

    # Deployment 6 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 6 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 6 is 100Mi
    END

    # ==================== Replica Rebuild at 100 Mi (Deployment 0, 1) ====================
    # Test replica rebuild on old engine at original size (100 Mi)
    When Delete replica of deployment 0 volume on replica node
    Then Wait until volume of deployment 0 replica rebuilding completed on replica node
    And Wait for volume of deployment 0 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 100Mi
    END
    And Check deployment 0 data in file data.txt is intact

    When Delete replica of deployment 1 volume on replica node
    Then Wait until volume of deployment 1 replica rebuilding completed on replica node
    And Wait for volume of deployment 1 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 100Mi
    END
    And Check deployment 1 data in file data.txt is intact

    # ==================== Expansion (Deployment 3, 4) ====================
    # Expand dedicated deployments from 100 Mi to 200 Mi
    When Expand deployment 3 volume to 200Mi
    And Expand deployment 4 volume to 200Mi
    Then Wait for deployment 3 volume size expanded
    And Wait for deployment 4 volume size expanded
    And Check deployment 3 pods did not restart
    And Check deployment 4 pods did not restart

    # After expansion: device = 184 Mi, replica = 20 Mi (old engine)
    And Assert disk size in instance manager pod for deployment 3 is 184Mi
    And Check no sharemanager pod of deployment 4 recreation
    And Assert encrypted disk size in sharemanager pod for deployment 4 is 184Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 200Mi
        Assert replica file size of deployment 4 is 200Mi
    END
    And Check deployment 3 data in file data.txt is intact
    And Check deployment 4 data in file data.txt is intact

    # ==================== Replica Rebuild at 200 Mi (Deployment 3, 4) ====================
    # Test replica rebuild on old engine after expansion (200 Mi)
    When Delete replica of deployment 3 volume on replica node
    Then Wait until volume of deployment 3 replica rebuilding completed on replica node
    And Wait for volume of deployment 3 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 200Mi
    END
    And Check deployment 3 data in file data.txt is intact

    When Delete replica of deployment 4 volume on replica node
    Then Wait until volume of deployment 4 replica rebuilding completed on replica node
    And Wait for volume of deployment 4 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 4 is 200Mi
    END
    And Check deployment 4 data in file data.txt is intact

    # ==================== Workload Reattach at 100 Mi (Deployment 5, 6) ====================
    # Test workload reattach on old engine at original size (100 Mi)
    Then Scale down deployment 5 to detach volume
    And Scale up deployment 5 to attach volume
    Then Wait for volume of deployment 5 healthy
    And Wait for workloads pods stable    deployment 5
    # Deployment 5 (RWO Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert disk size in instance manager pod for deployment 5 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 5 is 100Mi
    END
    And Check deployment 5 data in file data.txt is intact

    Then Scale down deployment 6 to detach volume
    And Scale up deployment 6 to attach volume
    Then Wait for volume of deployment 6 healthy
    And Wait for workloads pods stable    deployment 6
    # Deployment 6 (RWX Filesystem): device = 84 Mi, replica = 100 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 6 is 84Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 6 is 100Mi
    END
    And Check deployment 6 data in file data.txt is intact

    # ==================== Engine Upgrade (Deployment 0-4, v1 only) ====================
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=
    IF    '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != '' and '${DATA_ENGINE}' == 'v1'
        # Upgrade all volumes to the new engine image
        Then Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        And Wait for volume of deployment 0 healthy
        And Wait for volume of deployment 1 healthy
        And Wait for volume of deployment 2 healthy
        And Wait for volume of deployment 3 healthy
        And Wait for volume of deployment 4 healthy
        And Wait for volume of deployment 5 healthy
        And Wait for volume of deployment 6 healthy

        # Test replica rebuild on new engine at original size (Deployment 0, 1)
        # Deployment 0 (RWO Filesystem, 100 Mi):
        # device = 100 Mi, replica = 100 Mi + 16 Mi = 116 Mi
        When Delete replica of deployment 0 volume on replica node
        Then Wait until volume of deployment 0 replica rebuilding completed on replica node
        And Wait for volume of deployment 0 healthy
        Then Assert disk size in instance manager pod for deployment 0 is 100Mi
        And Assert replica file size of deployment 0 is 116Mi
        And Check deployment 0 data in file data.txt is intact

        # Deployment 1 (RWX Filesystem, 100 Mi):
        # device = 100 Mi, replica = 100 Mi + 16 Mi = 116 Mi
        When Delete replica of deployment 1 volume on replica node
        Then Wait until volume of deployment 1 replica rebuilding completed on replica node
        And Wait for volume of deployment 1 healthy
        Then Assert encrypted disk size in sharemanager pod for deployment 1 is 100Mi
        And Assert replica file size of deployment 1 is 116Mi
        And Check deployment 1 data in file data.txt is intact

        # Deployment 2 (RWO Block, 100 Mi):
        # blockdev = 100 Mi, replica = 100 Mi + 16 Mi = 116 Mi
        Then Assert block device size in deployment pod for deployment 2 is 100Mi
        And Assert replica file size of deployment 2 is 116Mi

        # Deployment 3 (RWO Filesystem, 200 Mi after expansion):
        # device = 200 Mi, replica = 200 Mi + 16 Mi = 216 Mi
        Then Assert disk size in instance manager pod for deployment 3 is 200Mi
        And Assert replica file size of deployment 3 is 216Mi
        And Check deployment 3 data in file data.txt is intact

        # Deployment 4 (RWX Filesystem, 200 Mi after expansion):
        # device = 200 Mi, replica = 200 Mi + 16 Mi = 216 Mi
        Then Assert encrypted disk size in sharemanager pod for deployment 4 is 200Mi
        And Assert replica file size of deployment 4 is 216Mi
        And Check deployment 4 data in file data.txt is intact

        # Test workload reattach on new engine at original size (100 Mi)
        Then Scale down deployment 5 to detach volume
        And Scale up deployment 5 to attach volume
        Then Wait for volume of deployment 5 healthy
        And Wait for workloads pods stable    deployment 5
        # Deployment 5 (RWO Filesystem, 100 Mi):
        # device = 100 Mi, replica = 100 Mi + 16 Mi = 116 Mi
        Then Assert disk size in instance manager pod for deployment 5 is 100Mi
        And Assert replica file size of deployment 5 is 116Mi
        And Check deployment 5 data in file data.txt is intact

        Then Scale down deployment 6 to detach volume
        And Scale up deployment 6 to attach volume
        Then Wait for volume of deployment 6 healthy
        And Wait for workloads pods stable    deployment 6
        # Deployment 6 (RWX Filesystem, 100 Mi):
        # device = 100 Mi, replica = 100 Mi + 16 Mi = 116 Mi
        Then Assert encrypted disk size in sharemanager pod for deployment 6 is 100Mi
        And Assert replica file size of deployment 6 is 116Mi
        And Check deployment 6 data in file data.txt is intact
    END

    # ==================== Backup/Restore (Deployment 7, 8) =============================
    # Restore pre-upgrade (v1.11 old-engine) backups with new Longhorn (v1.12+).
    # New Longhorn provisions the restored volume with new-engine semantics:
    # 16 Mi pre-allocated in the backend → device = full 100 Mi, replica = 116 Mi.

    # Deployment 7: Restore from Backup 0 (RWO Filesystem)
    When Create volume 7 from backup 0 of deployment 0 volume    size=100Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume 7 detached
    And Create deployment 7 with volume 7    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto
    And Wait for volume of deployment 7 healthy
    Then Assert disk size in instance manager pod for deployment 7 is 100Mi
    And Assert replica file size of deployment 7 is 116Mi
    And Check deployment 7 file data.txt checksum matches checksum 0

    # Deployment 8: Restore from Backup 1 (RWX Filesystem)
    When Create volume 8 from backup 1 of deployment 1 volume    size=100Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume 8 detached
    And Create deployment 8 with volume 8    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto
    And Wait for volume of deployment 8 healthy
    Then Assert disk size in instance manager pod for deployment 8 is 100Mi
    And Assert replica file size of deployment 8 is 116Mi
    And Check deployment 8 file data.txt checksum matches checksum 1

Test Encrypted Volume With Encrypted Backing Image Clone
    [Tags]    rwo    backing-image    encrypted    skip
    [Documentation]    Test creating encrypted volume using an encrypted BackingImage clone.
    ...
    ...                **IMPLEMENTATION STATUS: TO BE IMPLEMENTED**
    ...
    ...                This test case is designed to verify that a Longhorn volume using an
    ...                encrypted BackingImage clone combined with an encrypted StorageClass
    ...                can be successfully mounted by a Pod.
    ...
    ...                **Test Goal:**
    ...                Verify encrypted volume creation using encrypted BackingImage clone.
    ...
    ...                **Reproduce Steps:**
    ...                1. Create source backing image "parrot" from URL
    ...                   (https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2)
    ...                2. Create crypto secret "longhorn-crypto" in longhorn-system namespace
    ...                3. Create encrypted clone backing image "parrot-cloned-encrypted"
    ...                   using sourceType=clone with encryption parameters:
    ...                   - sourceType: clone
    ...                   - sourceParameters:
    ...                     - backing-image: parrot
    ...                     - encryption: encrypt
    ...                     - secret: longhorn-crypto
    ...                     - secret-namespace: longhorn-system
    ...                4. Create encrypted StorageClass "longhorn-crypto-global" with:
    ...                   - encrypted: "true"
    ...                   - backingImage: "parrot-cloned-encrypted"
    ...                   - CSI secret references for provisioner/node-publish/node-stage
    ...                5. Create 5 GiB RWO PVC "longhorn-backing-image-pvc" from that StorageClass
    ...                6. Create Pod using the PVC
    ...                7. Assert Pod is running successfully (volume mounted)
    ...                8. Write data to verify volume is functional
    ...
    ...                **Expected Results:**
    ...                - Pod should be in Running state
    ...                - Volume should be mounted and accessible inside the Pod
    ...                - Data written to the volume can be read back successfully
    ...
    ...                **Implementation Notes:**
    ...                - Need to implement keyword: "Create encrypted clone backing image"
    ...                  This keyword should use kubectl apply to create BackingImage CR
    ...                  with sourceType=clone and encryption parameters
    ...                - The implementation should extend backing_image.py to support
    ...                  sourceType="clone" via kubectl (not REST API)
    ...                - Consider adding to rest.py or crd.py depending on architecture
    ...
    ...                **Reference CR Example:**
    ...                apiVersion: longhorn.io/v1beta2
    ...                kind: BackingImage
    ...                metadata:
    ...                  name: parrot-cloned-encrypted
    ...                  namespace: longhorn-system
    ...                spec:
    ...                  sourceType: clone
    ...                  sourceParameters:
    ...                    backing-image: parrot
    ...                    encryption: encrypt
    ...                    secret: longhorn-crypto
    ...                    secret-namespace: longhorn-system
    Skip    Implementation pending: encrypted clone backing image keyword not yet implemented