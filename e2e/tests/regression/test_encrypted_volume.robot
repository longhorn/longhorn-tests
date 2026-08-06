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

*** Keywords ***
Test Encrypted Volume Basic
    [Arguments]    ${volume_type}
    [Documentation]    Test basic encrypted volume operations for both RWO and RWX volumes.
    ...                Deployment 0 = RWO, Deployment 1 = RWX.
    ...
    ...                Expected sizes for a 512 Mi volume:
    ...                    - Replica backend file = 528 Mi (requested + 16 Mi pre-allocated).
    ...                    - v2 data engine: Replica backend N/A (format differs, only device size is verified).
    ...                    - dm-crypt device (RWO instance manager) = 512 Mi (full requested size).
    ...                    - dm-crypt device (RWX sharemanager pod) = 512 Mi (full requested size).
    ...                    - Mounted filesystem (workload pod, RWO/RWX) = ~512 Mi (accounting for filesystem overhead).
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=${volume_type}    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 528Mi
    END
    # Verify sizes at different layers: backend replica → dm-crypt device → mounted filesystem
    IF    '${volume_type}' == 'RWO'
        And Assert disk size in instance manager for deployment 0    expected_disk_size=512Mi
    ELSE IF    '${volume_type}' == 'RWX'
        And Assert encrypted disk size in sharemanager pod for deployment 0 is 512Mi
    END

    And Write 256 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 528Mi
    END
    # Re-verify sizes after scale down/up cycle
    IF    '${volume_type}' == 'RWO'
        And Assert disk size in instance manager for deployment 0    expected_disk_size=512Mi
    ELSE IF    '${volume_type}' == 'RWX'
        And Assert encrypted disk size in sharemanager pod for deployment 0 is 512Mi
    END
    Then Check deployment 0 data in file data.txt is intact

Test Encrypted Volume Cloning
    [Arguments]    ${volume_type}
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim source-pvc    volume_type=${volume_type}    sc_name=longhorn-crypto    storage_size=512Mi
    And Wait for volume of persistentvolumeclaim source-pvc to be created
    And Wait for volume of persistentvolumeclaim source-pvc detached

    And Create deployment source-deployment with persistentvolumeclaim source-pvc
    And Wait for volume of deployment source-deployment healthy
    And Wait for workloads pods stable    deployment source-deployment
    And Write 256 MB data to file data.txt in deployment source-deployment
    And Record file data.txt checksum in deployment source-deployment as checksum source-pvc


    When Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc    volume_type=${volume_type}    sc_name=longhorn-crypto    storage_size=512Mi
    And Wait for volume of persistentvolumeclaim cloned-pvc detached

    And Create deployment cloned-deployment with persistentvolumeclaim cloned-pvc
    And Wait for volume of deployment cloned-deployment healthy
    And Wait for workloads pods stable    deployment cloned-deployment

    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment cloned-deployment is 528Mi
    END
    
    IF    '${volume_type}' == 'RWO'
        And Assert disk size in instance manager for deployment cloned-deployment    expected_disk_size=512Mi
    ELSE IF    '${volume_type}' == 'RWX'
        And Assert encrypted disk size in sharemanager pod for deployment cloned-deployment is 512Mi
    END
    And Check deployment cloned-deployment file data.txt checksum matches checksum source-pvc

Test Encrypted Volume Expansion
    [Arguments]    ${volume_type}
    [Documentation]    Test Plan: Volume Expansion – new engine path
    ...
    ...                Create a 512 Mi encrypted volume (new engine), write 256 Mi of data,
    ...                then expand to 768 Mi.
    ...
    ...                Expected after expansion:
    ...                  - Instance manager (RWO) shows 768 Mi.
    ...                  - Share manager pod (RWX) shows 768 Mi; pod is NOT recreated.
    ...                  - Replica image file on the worker node shows 768 Mi + 16 Mi = 784 Mi.
    ...                  - Previously written data is intact.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=${volume_type}    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 256 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Expand deployment 0 volume to 768Mi
    Then Wait for deployment 0 volume size expanded

    And Check deployment 0 pods did not restart
    IF    '${volume_type}' == 'RWX'
        And Check no sharemanager pod of deployment 0 recreation
    END

    IF    '${volume_type}' == 'RWO'
        And Assert disk size in instance manager for deployment 0    expected_disk_size=768Mi
    ELSE IF    '${volume_type}' == 'RWX'
        And Assert encrypted disk size in sharemanager pod for deployment 0 is 768Mi
    END

    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 784Mi
    END
    And Check deployment 0 data in file data.txt is intact

Test Encrypted Volume Replica Rebuild
    [Arguments]    ${volume_type}
    [Documentation]    Test Plan: Replica Rebuild – new engine path
    ...
    ...                Create a 512 Mi encrypted volume (deployment 0).
    ...                Write 256 Mi of data, then delete one replica to trigger a rebuild.
    ...
    ...                Expected after rebuild:
    ...                  - Rebuild completes successfully (volume returns to healthy).
    ...                    The dm-crypt device size is unchanged: 512 Mi (RWO instance manager)
    ...                    and 512 Mi (RWX share manager pod).
    ...                  - The newly rebuilt replica file size is 512 Mi + 16 Mi = 528 Mi,
    ...                    matching the existing replicas (v1 only).
    ...                  - Data integrity (md5sum / checksum) is intact.
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=${volume_type}    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 256 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact

    When Delete replica of deployment 0 volume on replica node
    And Wait until volume of deployment 0 replica rebuilding completed on replica node
    Then Wait for volume of deployment 0 healthy

    IF    '${volume_type}' == 'RWO'
        And Assert disk size in instance manager for deployment 0    expected_disk_size=512Mi
    ELSE IF    '${volume_type}' == 'RWX'
        And Assert encrypted disk size in sharemanager pod for deployment 0 is 512Mi
    END

    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 528Mi
    END
    And Check deployment 0 data in file data.txt is intact

*** Test Cases ***
Test Encrypted RWO Volume Basic
    [Tags]    rwo
    [Template]    Test Encrypted Volume Basic
        RWO

Test Encrypted RWX Volume Basic
    [Tags]    rwx
    [Template]    Test Encrypted Volume Basic
        RWX

Test Encrypted RWO Volume Cloning
    [Tags]    rwo
    [Template]    Test Encrypted Volume Cloning
        RWO

Test Encrypted RWX Volume Cloning
    [Tags]    rwx
    [Template]    Test Encrypted Volume Cloning
        RWX

Test Encrypted Volume Snapshot Clone
    [Tags]    rwo    snapshot    clone
    [Documentation]    Test creating an encrypted volume from another encrypted volume's snapshot.
    ...
    ...                Steps:
    ...                  1. Create a 512 Mi encrypted RWO volume (deployment 0).
    ...                  2. Write 256 MB of data and record checksum.
    ...                  3. Take a snapshot (snapshot 0).
    ...                  4. Create a new encrypted volume (volume 1) from snapshot 0.
    ...                  5. Attach the new volume to deployment 1 via the crypto StorageClass.
    ...                  6. Verify data integrity and size.
    ...
    ...                Expected (v1 data engine):
    ...                  - Source volume: dm-crypt device = 512 Mi, replica = 528 Mi.
    ...                  - Cloned volume: dm-crypt device = 512 Mi, replica = 528 Mi.
    ...                  - Data checksum matches original.
    ...
    ...                Expected (v2 data engine):
    ...                  - Source volume: dm-crypt device = 512 Mi.
    ...                  - Cloned volume: dm-crypt device = 512 Mi.
    ...                  - Data checksum matches original.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 256 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0

    # Verify source volume size
    And Assert disk size in instance manager for deployment 0    expected_disk_size=512Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 528Mi
    END

    # Create snapshot from source volume
    When Create snapshot 0 for deployment 0 volume
    And Wait for snapshot 0 of deployment 0 volume ready

    # Create new encrypted volume from snapshot
    When Create volume 1 from snapshot 0 of deployment 0 volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached

    # Attach cloned volume to new deployment with crypto SC (to trigger luksOpen)
    And Create deployment 1 with volume 1    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Wait for volume of deployment 1 healthy

    # Verify cloned volume size and data integrity
    Then Check deployment 1 file data.txt checksum matches checksum 0
    And Assert disk size in instance manager for deployment 1    expected_disk_size=512Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 528Mi
    END

Test Encrypted RWO Volume Expansion
    [Tags]    rwo    expansion
    [Template]    Test Encrypted Volume Expansion
        RWO

Test Encrypted RWX Volume Expansion
    [Tags]    rwx    expansion
    [Template]    Test Encrypted Volume Expansion
        RWX

Test Encrypted RWO Block Volume Online Expansion
    [Tags]    rwo    expansion    block-volume
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with block persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Make block device filesystem in deployment 0
    And Mount block device on /data in deployment 0
    And Write 256 MB data to file data1.txt in deployment 0
    Then Check deployment 0 data in file data1.txt is intact

    When Expand deployment 0 volume to 768Mi
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    # Verify the actual disk size in the instance manager pod.
    # NOTE: With the new engine (v1.12+), the 16 Mi LUKS header is pre-allocated
    # in the replica backend file (replica size = requested size + 16 Mi).
    # The dm-crypt device therefore presents the full requested size to the workload.
    # Therefore, after expansion to 768 Mi, the dm-crypt device shows 768 Mi.
    And Assert disk size in instance manager for deployment 0    expected_disk_size=768Mi
    And Assert block device size in deployment pod for deployment 0 is 768Mi
    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    Then Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Mount block device on /data in deployment 0
    And Write 384 MB data to file data2.txt in deployment 0
    Then Check deployment 0 data in file data2.txt is intact

Test Encrypted RWO Volume Replica Rebuild
    [Tags]    rwo    replica-rebuild
    [Template]    Test Encrypted Volume Replica Rebuild
        RWO

Test Encrypted RWX Volume Replica Rebuild
    [Tags]    rwx    replica-rebuild
    [Template]    Test Encrypted Volume Replica Rebuild
        RWX

Test Encrypted Volume Backup Restore To Encrypted Volume
    [Tags]    rwo    rwx    backup    restore
    [Documentation]    Test Plan: Backup Restore – restore as encrypted (RWO + RWX)
    ...
    ...                Create a 512 Mi encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1), write 256 Mi of data to each, take backups.
    ...                Restore each backup to a new encrypted volume.
    ...                Deployment 0 = RWO source, Deployment 1 = RWX source.
    ...                Deployment 2 = restored from dep 0 backup, Deployment 3 = restored from dep 1 backup.
    ...
    ...                Expected:
    ...                  - Restored volumes' dm-crypt device shows exactly 512 Mi.
    ...                  - Restored volumes' replica backend file is exactly 512 Mi + 16 Mi.
    ...                  - The 256 Mi payload checksum matches the original.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 256 MB data to file data.txt in deployment 0
    And Write 256 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0
    And Record file data.txt checksum in deployment 1 as checksum 1

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    When Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume

    # Restore to new encrypted volumes (encrypted=True)
    When Create volume 2 from backup 0 of deployment 0 volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Create volume 3 from backup 1 of deployment 1 volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Wait for volume 2 detached
    And Wait for volume 3 detached
    # Mount the restored volumes via deployments so that CSI opens the LUKS container.
    # Must use longhorn-crypto SC (with node-stage-secret-ref) so luksOpen is triggered.
    And Create deployment 2 with volume 2    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Create deployment 3 with volume 3    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Wait for volume of deployment 2 healthy
    And Wait for volume of deployment 3 healthy
    Then Assert disk size in instance manager for deployment 2    expected_disk_size=512Mi
    And Assert disk size in instance manager for deployment 3    expected_disk_size=512Mi
    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 528Mi
        Assert replica file size of deployment 3 is 528Mi
    END
    And Check deployment 2 file data.txt checksum matches checksum 0
    And Check deployment 3 file data.txt checksum matches checksum 1

Test Encrypted Volume Backup Restore To Unencrypted Volume
    [Tags]    rwo    rwx    backup    restore
    [Documentation]    Test Plan: Backup Restore – restore as unencrypted (RWO + RWX)
    ...
    ...                Create a 512 Mi encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1), write 256 Mi of data to each, take backups, then
    ...                restore each as an unencrypted volume (encrypted=False).
    ...                Deployment 0 = RWO source, Deployment 1 = RWX source.
    ...                Volume 2 = restored from dep 0 backup, Volume 3 = restored from dep 1 backup.
    ...
    ...                Expected:
    ...                  - Since encrypted=False, Longhorn does not pre-allocate extra 16 Mi.
    ...                    The replica backend file is exactly 512 Mi (no LUKS pre-allocation),
    ...                    compared to 512 Mi + 16 Mi for an encrypted=True restore.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    ...                - Issue: https://github.com/longhorn/longhorn/issues/13234
    Skip    This test case implementation is blocked by https://github.com/longhorn/longhorn/issues/13234.
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 256 MB data to file data.txt in deployment 0
    And Write 256 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    When Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume
    When Create volume 2 from backup 0 of deployment 0 volume    size=512Mi    encrypted=False    dataEngine=${DATA_ENGINE}
    And Create volume 3 from backup 1 of deployment 1 volume    size=512Mi    encrypted=False    dataEngine=${DATA_ENGINE}
    Then Wait for volume 2 detached
    And Wait for volume 3 detached
    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of volume 2 is 512Mi
        Assert replica file size of volume 3 is 512Mi
    END

Test Encrypted Volume Upgrade
    [Tags]    rwo    rwx    block-volume    expansion    replica-rebuild    engine-upgrade    old-engine
    [Documentation]    Test Plan: Old Engine – LUKS Header Pre-allocation across Volume Modes + Upgrade
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set.
    ...                - Covers old-engine (v1.11) LUKS header sizing behavior across ALL volume modes.
    ...                - Each deployment is dedicated to a specific test scenario for better isolation.
    ...                - v2 data engine has no live engine upgrade. All deployments are scaled down (detached)
    ...                  before the Longhorn upgrade and scaled back up (reattached) afterward 
    ...                  so each volume adopts the upgraded v2 instance manager.
    ...
    ...                Deployment Layout:
    ...                  - Deployment 0: RWO Filesystem (initial state + replica rebuild at 512 Mi)
    ...                  - Deployment 1: RWX Filesystem (initial state + replica rebuild at 512 Mi)
    ...                  - Deployment 2: RWO Block (initial state + engine upgrade)
    ...                  - Deployment 3: RWO Filesystem (expansion + replica rebuild at 768 Mi)
    ...                  - Deployment 4: RWX Filesystem (expansion + replica rebuild at 768 Mi)
    ...                  - Deployment 5: RWO Filesystem (workload reattach test)
    ...                  - Deployment 6: RWX Filesystem (workload reattach test)
    ...                  - Deployment 7: RWO Filesystem (backup/restore with new-engine semantics)
    ...                  - Deployment 8: RWX Filesystem (backup/restore with new-engine semantics)
    ...
    ...                Test Scenarios:
    ...                  A. Initial State Verification (deployments 0-4):
    ...                     - Old engine: device = requested_size - 16 Mi, replica = requested_size
    ...
    ...                  B. Replica Rebuild at 512 Mi (deployments 0, 1):
    ...                     - Verify rebuilt replica = 512 Mi (old engine)
    ...
    ...                  C. Expansion (deployments 3, 4):
    ...                     - Expand 512 Mi → 768 Mi
    ...                     - Device = 752 Mi, replica = 768 Mi (old engine)
    ...
    ...                  D. Replica Rebuild at 768 Mi (deployments 3, 4):
    ...                     - Verify rebuilt replica = 768 Mi (old engine)
    ...
    ...                  E. Engine Upgrade (deployments 0-4, v1 only):
    ...                     - After upgrade: device = full size, replica = requested_size + 16 Mi
    ...
    ...                  F. Workload Reattach test (deployments 5, 6):
    ...                     - Test old-engine and new-engine workload reattach behavior
    ...                     - Old engine: device = 496 Mi, replica = 512 Mi
    ...                     - New engine: device = 512 Mi, replica = 528 Mi
    ...
    ...                  G. Backup/Restore (deployments 7, 8):
    ...                     - Restore pre-upgrade backups with new-engine semantics
    ...                     - v1: Device = 512 Mi, replica = 528 Mi
    ...                     - v2: Device (encrypted) = 496 Mi, raw device = 512 Mi
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

    # Deployment 0: RWO Filesystem (initial state + replica rebuild at 512 Mi)
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0

    # Deployment 1: RWX Filesystem (initial state + replica rebuild at 512 Mi)
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment 1 with persistentvolumeclaim 1

    # Deployment 2: RWO Block (initial state + engine upgrade)
    And Create persistentvolumeclaim 2    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment 2 with block persistentvolumeclaim 2

    # Deployment 3: RWO Filesystem (expansion + replica rebuild at 768 Mi)
    And Create persistentvolumeclaim 3    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment 3 with persistentvolumeclaim 3

    # Deployment 4: RWX Filesystem (expansion + replica rebuild at 768 Mi)
    And Create persistentvolumeclaim 4    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment 4 with persistentvolumeclaim 4

    # Deployment 5: RWO Filesystem (initial state + workload reattach at 512 Mi)
    And Create persistentvolumeclaim 5    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment 5 with persistentvolumeclaim 5

    # Deployment 6: RWX Filesystem (initial state + workload reattach at 512 Mi)
    And Create persistentvolumeclaim 6    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
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
    When Write 256 MB data to file data.txt in deployment 0
    And Write 256 MB data to file data.txt in deployment 1
    And Write 256 MB data to file data.txt in deployment 3
    And Write 256 MB data to file data.txt in deployment 4
    And Write 256 MB data to file data.txt in deployment 5
    And Write 256 MB data to file data.txt in deployment 6

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
    # Deployment 0 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    Then Assert disk size in instance manager for deployment 0    expected_disk_size=496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 512Mi
    END

    # Deployment 1 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 512Mi
    END

    # Deployment 2 (RWO Block): blockdev = 496 Mi, replica = 512 Mi
    And Assert block device size in deployment pod for deployment 2 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 512Mi
    END

    # Deployment 3 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert disk size in instance manager for deployment 3    expected_disk_size=496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 512Mi
    END

    # Deployment 4 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 4 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 4 is 512Mi
    END

    # Deployment 5 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert disk size in instance manager for deployment 5    expected_disk_size=496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 5 is 512Mi
    END

    # Deployment 6 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 6 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 6 is 512Mi
    END

    # ==================== Upgrade Longhorn (Keep Old Engine) ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0

    FOR    ${i}    IN RANGE    7
        Check volume endpoint on node of deployment ${i}
    END

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${i}    IN RANGE    7
            Scale down deployment ${i} to detach volume
        END
    END

    When Upgrade Longhorn to custom version

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${i}    IN RANGE    7
            Scale up deployment ${i} to attach volume
        END
    END

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
    # Deployment 0 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    Then Assert disk size in instance manager for deployment 0    expected_disk_size=496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 512Mi
    END

    # Deployment 1 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 512Mi
    END

    # Deployment 2 (RWO Block): blockdev = 496 Mi, replica = 512 Mi
    And Assert block device size in deployment pod for deployment 2 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 512Mi
    END

    # Deployment 3 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert disk size in instance manager for deployment 3    expected_disk_size=496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 512Mi
    END

    # Deployment 4 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 4 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 4 is 512Mi
    END

    # Deployment 5 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert disk size in instance manager for deployment 5    expected_disk_size=496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 5 is 512Mi
    END

    # Deployment 6 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 6 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 6 is 512Mi
    END

    # ==================== Replica Rebuild at 512 Mi (Deployment 0, 1) ====================
    # Test replica rebuild on old engine at original size (512 Mi)
    When Delete replica of deployment 0 volume on replica node
    Then Wait until volume of deployment 0 replica rebuilding completed on replica node
    And Wait for volume of deployment 0 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 512Mi
    END
    And Check deployment 0 data in file data.txt is intact

    When Delete replica of deployment 1 volume on replica node
    Then Wait until volume of deployment 1 replica rebuilding completed on replica node
    And Wait for volume of deployment 1 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 512Mi
    END
    And Check deployment 1 data in file data.txt is intact

    # ==================== Expansion (Deployment 3, 4) ====================
    # Expand dedicated deployments from 512 Mi to 768 Mi
    When Expand deployment 3 volume to 768Mi
    And Expand deployment 4 volume to 768Mi
    Then Wait for deployment 3 volume size expanded
    And Wait for deployment 4 volume size expanded
    And Check deployment 3 pods did not restart
    And Check deployment 4 pods did not restart

    # After expansion: device = 752 Mi, replica = 768 Mi (old engine)
    And Assert disk size in instance manager for deployment 3    expected_disk_size=752Mi
    And Assert encrypted disk size in sharemanager pod for deployment 4 is 752Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 768Mi
        Assert replica file size of deployment 4 is 768Mi
    END
    And Check deployment 3 data in file data.txt is intact
    And Check deployment 4 data in file data.txt is intact

    # ==================== Replica Rebuild at 768 Mi (Deployment 3, 4) ====================
    # Test replica rebuild on old engine after expansion (768 Mi)
    When Delete replica of deployment 3 volume on replica node
    Then Wait until volume of deployment 3 replica rebuilding completed on replica node
    And Wait for volume of deployment 3 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 3 is 768Mi
    END
    And Check deployment 3 data in file data.txt is intact

    When Delete replica of deployment 4 volume on replica node
    Then Wait until volume of deployment 4 replica rebuilding completed on replica node
    And Wait for volume of deployment 4 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 4 is 768Mi
    END
    And Check deployment 4 data in file data.txt is intact

    # ==================== Workload Reattach at 512 Mi (Deployment 5, 6) ====================
    # Test workload reattach on old engine at original size (512 Mi)
    Then Scale down deployment 5 to detach volume
    And Scale up deployment 5 to attach volume
    Then Wait for volume of deployment 5 healthy
    And Wait for workloads pods stable    deployment 5
    # Deployment 5 (RWO Filesystem): device = 496 Mi, replica = 512 Mi
    IF    '${DATA_ENGINE}' == 'v1'
        And Assert disk size in instance manager for deployment 5    expected_disk_size=496Mi
        Assert replica file size of deployment 5 is 512Mi
    ELSE
        And Assert disk size in instance manager for deployment 5    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Check deployment 5 data in file data.txt is intact

    Then Scale down deployment 6 to detach volume
    And Scale up deployment 6 to attach volume
    Then Wait for volume of deployment 6 healthy
    And Wait for workloads pods stable    deployment 6
    # Deployment 6 (RWX Filesystem): device = 496 Mi, replica = 512 Mi
    And Assert encrypted disk size in sharemanager pod for deployment 6 is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 6 is 512Mi
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
        # Deployment 0 (RWO Filesystem, 512 Mi):
        # device = 512 Mi, replica = 512 Mi + 16 Mi = 528 Mi
        When Delete replica of deployment 0 volume on replica node
        Then Wait until volume of deployment 0 replica rebuilding completed on replica node
        And Wait for volume of deployment 0 healthy
        Then Assert disk size in instance manager for deployment 0    expected_disk_size=512Mi
        And Assert replica file size of deployment 0 is 528Mi
        And Check deployment 0 data in file data.txt is intact

        # Deployment 1 (RWX Filesystem, 512 Mi):
        # device = 512 Mi, replica = 512 Mi + 16 Mi = 528 Mi
        When Delete replica of deployment 1 volume on replica node
        Then Wait until volume of deployment 1 replica rebuilding completed on replica node
        And Wait for volume of deployment 1 healthy
        Then Assert encrypted disk size in sharemanager pod for deployment 1 is 512Mi
        And Assert replica file size of deployment 1 is 528Mi
        And Check deployment 1 data in file data.txt is intact

        # Deployment 2 (RWO Block, 512 Mi):
        # blockdev = 512 Mi, replica = 512 Mi + 16 Mi = 528 Mi
        Then Assert block device size in deployment pod for deployment 2 is 512Mi
        And Assert replica file size of deployment 2 is 528Mi

        # Deployment 3 (RWO Filesystem, 768 Mi after expansion):
        # device = 768 Mi, replica = 768 Mi + 16 Mi = 784 Mi
        Then Assert disk size in instance manager for deployment 3    expected_disk_size=768Mi
        And Assert replica file size of deployment 3 is 784Mi
        And Check deployment 3 data in file data.txt is intact

        # Deployment 4 (RWX Filesystem, 768 Mi after expansion):
        # device = 768 Mi, replica = 768 Mi + 16 Mi = 784 Mi
        Then Assert encrypted disk size in sharemanager pod for deployment 4 is 768Mi
        And Assert replica file size of deployment 4 is 784Mi
        And Check deployment 4 data in file data.txt is intact

        # Test workload reattach on new engine at original size (512 Mi)
        Then Scale down deployment 5 to detach volume
        And Scale up deployment 5 to attach volume
        Then Wait for volume of deployment 5 healthy
        And Wait for workloads pods stable    deployment 5
        # Deployment 5 (RWO Filesystem, 512 Mi):
        # device = 512 Mi, replica = 512 Mi + 16 Mi = 528 Mi
        Then Assert disk size in instance manager for deployment 5    expected_disk_size=512Mi
        And Assert replica file size of deployment 5 is 528Mi
        And Check deployment 5 data in file data.txt is intact

        Then Scale down deployment 6 to detach volume
        And Scale up deployment 6 to attach volume
        Then Wait for volume of deployment 6 healthy
        And Wait for workloads pods stable    deployment 6
        # Deployment 6 (RWX Filesystem, 512 Mi):
        # device = 512 Mi, replica = 512 Mi + 16 Mi = 528 Mi
        Then Assert encrypted disk size in sharemanager pod for deployment 6 is 512Mi
        And Assert replica file size of deployment 6 is 528Mi
        And Check deployment 6 data in file data.txt is intact
    END

    # ==================== Backup/Restore (Deployment 7, 8) =============================
    # Restore pre-upgrade (v1.11 old-engine) backups with new Longhorn (v1.12+).
    # New Longhorn provisions the restored volume with new-engine semantics:
    # v1: 16 Mi pre-allocated in the backend → device = full 512 Mi, replica = 528 Mi.
    # v2: encrypted device = 496 Mi (requested - 16 Mi), raw device = 512 Mi.
    # https://longhorn.io/docs/1.12.1/important-notes/#luks2-header-overhead-for-existing-encrypted-volumes

    # Deployment 7: Restore from Backup 0 (RWO Filesystem)
    When Create volume 7 from backup 0 of deployment 0 volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume 7 detached
    And Create deployment 7 with volume 7    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Wait for volume of deployment 7 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment 7    expected_disk_size=512Mi
        And Assert replica file size of deployment 7 is 528Mi
    ELSE
        Then Assert disk size in instance manager for deployment 7    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Check deployment 7 file data.txt checksum matches checksum 0

    # Deployment 8: Restore from Backup 1 (RWX Filesystem)
    When Create volume 8 from backup 1 of deployment 1 volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume 8 detached
    And Create deployment 8 with volume 8    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Wait for volume of deployment 8 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment 8    expected_disk_size=512Mi
        And Assert replica file size of deployment 8 is 528Mi
    ELSE
        Then Assert disk size in instance manager for deployment 8    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Check deployment 8 file data.txt checksum matches checksum 1

Test Encrypted Volume Upgrade For v2
    [Tags]    rwo    expansion    replica-rebuild    upgrade    dr-volume    backup    restore    v2
    [Documentation]    Test Plan: v2 Data Engine – Upgrade Behavior (v1.11.3/v1.12.0 → v1.12.1/master-head)
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set.
    ...                - Only applies to the v2 data engine.
    ...                - Sizes in this automated version use 512 Mi / 768 Mi 
    ...                - v2 has no live-volume engine upgrade like v1. To make an already-attached v2
    ...                  volume adopt the upgraded v2 instance manager, the workload must be
    ...                  scaled down (detach) so the old instance manager pod can be replaced,
    ...                  then scaled back up (reattach). Volume/Workload A is scaled down
    ...                  BEFORE the Longhorn upgrade.
    ...
    ...                Entities:
    ...                  - Volume/Workload A: created BEFORE the upgrade (512 Mi RWO)
    ...                  - DR-A: DR (Standby) volume created from volume A's backup, AFTER
    ...                    the upgrade
    ...                  - bk-A: volume restored (non-standby) from volume A's post-expansion
    ...                    backup
    ...                  - Volume/Workload B: created AFTER the upgrade (512 Mi RWO)
    ...                  - DR-B: DR (Standby) volume created from volume B's backup, AFTER
    ...                    the upgrade
    ...                  - bk-B: volume restored (non-standby) from volume B's post-expansion
    ...                    backup
    ...
    ...                Steps (see also the manual test plan referenced by the issues below):
    ...                  - 1.  Install Longhorn v1.11.3 or v1.12.0.
    ...                  - 2.  Create a 512 Mi v2 encrypted volume A with workload A.
    ...                  - 3.  Scale down workload A and wait for volume A to be detached.
    ...                  - 4.  Upgrade Longhorn to master-head/v1.12.1; wait for all pods ready.
    ...                  - 5.  Scale up workload A.
    ...                  - 6.  Check volume A data is correct, and that /dev/mapper/<volume>
    ...                      (raw) size on the host equals volume A's size.
    ...                  - 7.  Create a DR volume DR-A from volume A (via a backup).
    ...                  - 8.  Delete a replica of volume A and wait for it to be healthy.
    ...                  - 9.  Check volume A data is correct.
    ...                  - 10. Expand volume A to 768 Mi.
    ...                  - 11. Create backup A and check DR-A size expands to volume A's size.
    ...                  - 12. Activate DR-A and attach it to workload DR-A.
    ...                  - 13. Check the data in DR-A is correct.
    ...                  - 14. Restore backup A to volume bk-A; check its data is correct.
    ...                  - 15. Create a 512 Mi v2 encrypted volume B with workload B, using the
    ...                      already-upgraded v2 instance manager. Wait for it to be running.
    ...                  - 16. Check /dev/mapper/<volume>-encrypted size on host == volume B size.
    ...                  - 17. Write data to volume B and save the checksum.
    ...                  - 18. Create a DR volume DR-B.
    ...                  - 19. Expand volume B to 768 Mi.
    ...                  - 20. Write more data to volume B and save the checksum.
    ...                  - 21. Wait for /dev/mapper/<volume>-encrypted size to be 768 Mi.
    ...                  - 22. Scale down/up workload B.
    ...                  - 23. Check the encrypted device size is 768 Mi and data is correct.
    ...                  - 24. Create backup B and check DR-B size expands to volume B's size.
    ...                  - 25. Delete a replica of volume B; wait for it to be rebuilt.
    ...                  - 26. Activate DR-B and attach it to workload DR-B.
    ...                  - 27. Check the data in DR-B is correct.
    ...                  - 28. Restore backup B to volume bk-B; check its data is correct.
    ...
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    IF    '${DATA_ENGINE}' != 'v2'
        Skip    This test only applies to the v2 data engine
    END
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    ELSE IF    not ('${LONGHORN_STABLE_VERSION}'.startswith('v1.11.') or '${LONGHORN_STABLE_VERSION}' == 'v1.12.0')
        Skip    This test only applies to the v1.11.3/v1.12.0 → v1.12.1/master-head upgrade path; got stable version ${LONGHORN_STABLE_VERSION}
    END

    # ==================== Step 1: Setup ====================
    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks
    And Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    # ==================== Step 2: Volume A + Workload A, write data, save checksum ====================
    When Create persistentvolumeclaim vol-a    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment vol-a with persistentvolumeclaim vol-a
    And Wait for volume of deployment vol-a healthy
    And Write 256 MB data to file data.txt in deployment vol-a
    Then Check deployment vol-a data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-a as checksum vol-a-1

    # ==================== Step 3: Scale down workload A and wait for volume A detached ====================
    When Scale down deployment vol-a to detach volume
    Then Wait for volume of deployment vol-a detached

    # ==================== Step 4: Upgrade Longhorn to master-head/v1.12.1 ====================
    When Upgrade Longhorn to custom version
    And Wait for Longhorn components all running

    # ==================== Step 5: Scale up workload A ====================
    When Scale up deployment vol-a to attach volume
    Then Wait for volume of deployment vol-a healthy
    And Wait for workloads pods stable    deployment vol-a

    # ==================== Step 6: Check volume A data and raw device size ====================
    Then Check deployment vol-a data in file data.txt is intact
    # /dev/mapper/<volume> (raw, pre-encryption) == volume A size
    And Assert disk size in instance manager for deployment vol-a    expected_disk_size=496Mi    raw_size=512Mi

    # ==================== Step 7: Write more data to volume A, save checksum ====================
    When Write 256 MB data to file data.txt in deployment vol-a
    Then Check deployment vol-a data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-a as checksum vol-a-2

    # ==================== Step 8: Create DR volume DR-A from volume A ====================
    # A DR (Standby) volume is created from an existing backup of the source volume.
    When Create backup 0 for deployment vol-a volume
    And Verify backup list contains backup no error for deployment vol-a volume
    And Create DR volume dr-a from backup 0 of deployment vol-a volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume dr-a restoration from backup 0 of deployment vol-a volume completed

    # ==================== Step 9-10: Delete a replica of volume A, wait healthy, check data ====================
    When Delete replica of deployment vol-a volume on replica node
    Then Wait until volume of deployment vol-a replica rebuilding completed on replica node
    And Wait for volume of deployment vol-a healthy
    And Check deployment vol-a data in file data.txt is intact

    # ==================== Step 11: Expand volume A to 768 Mi ====================
    When Expand deployment vol-a volume to 768Mi
    Then Wait for deployment vol-a volume size expanded
    And Check deployment vol-a pods did not restart

    # ==================== Step 12: Create backup A; DR-A size should expand to volume A's size ====================
    When Create backup 1 for deployment vol-a volume
    And Verify backup list contains backup no error for deployment vol-a volume
    Then Wait for volume dr-a restoration from backup 1 of deployment vol-a volume completed
    And Wait for volume dr-a size to be 768Mi

    # ==================== Step 13-14: Activate DR-A, attach to workload DR-A, check data ====================
    When Activate DR volume dr-a
    Then Wait for volume dr-a detached
    And Create deployment dr-a with volume dr-a    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment dr-a healthy
    Then Check deployment dr-a file data.txt checksum matches checksum vol-a-2

    # ==================== Step 15: Restore backup A to volume bk-A; check data ====================
    When Create volume bk-a from backup 1 of deployment vol-a volume    size=768Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume bk-a detached
    And Create deployment bk-a with volume bk-a    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment bk-a healthy
    Then Check deployment bk-a file data.txt checksum matches checksum vol-a-2

    # ==================== Step 16-17: Volume B + Workload B, created with the upgraded v2 image ====================
    When Create persistentvolumeclaim vol-b    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment vol-b with persistentvolumeclaim vol-b
    And Wait for volume of deployment vol-b healthy
    Then Assert disk size in instance manager for deployment vol-b    expected_disk_size=512Mi

    # ==================== Step 18: Write data to volume B, save checksum ====================
    When Write 256 MB data to file data.txt in deployment vol-b
    Then Check deployment vol-b data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-b as checksum vol-b-1

    # ==================== Step 19: Create DR volume DR-B ====================
    When Create backup 0 for deployment vol-b volume
    And Verify backup list contains backup no error for deployment vol-b volume
    And Create DR volume dr-b from backup 0 of deployment vol-b volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume dr-b restoration from backup 0 of deployment vol-b volume completed

    # ==================== Step 20: Expand volume B to 768 Mi ====================
    When Expand deployment vol-b volume to 768Mi
    Then Wait for deployment vol-b volume size expanded

    # ==================== Step 21-22: Write more data to volume B, verify encrypted device size ====================
    When Write 256 MB data to file data.txt in deployment vol-b
    Then Check deployment vol-b data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-b as checksum vol-b-2
    And Assert disk size in instance manager for deployment vol-b    expected_disk_size=768Mi

    # ==================== Step 23-24: Scale down/up workload B, verify size and data ====================
    When Scale down deployment vol-b to detach volume
    And Scale up deployment vol-b to attach volume
    Then Wait for volume of deployment vol-b healthy
    And Wait for workloads pods stable    deployment vol-b
    And Assert disk size in instance manager for deployment vol-b    expected_disk_size=768Mi
    And Check deployment vol-b data in file data.txt is intact

    # ==================== Step 25: Create backup B; DR-B size should expand to volume B's size ====================
    When Create backup 1 for deployment vol-b volume
    And Verify backup list contains backup no error for deployment vol-b volume
    Then Wait for volume dr-b restoration from backup 1 of deployment vol-b volume completed
    And Wait for volume dr-b size to be 768Mi

    # ==================== Step 26: Delete a replica of volume B; wait for rebuild ====================
    When Delete replica of deployment vol-b volume on replica node
    Then Wait until volume of deployment vol-b replica rebuilding completed on replica node
    And Wait for volume of deployment vol-b healthy

    # ==================== Step 27-28: Activate DR-B, attach to workload DR-B, check data ====================
    When Activate DR volume dr-b
    Then Wait for volume dr-b detached
    And Create deployment dr-b with volume dr-b    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment dr-b healthy
    Then Check deployment dr-b file data.txt checksum matches checksum vol-b-2

    # ==================== Step 29: Restore backup B to volume bk-B; check data ====================
    When Create volume bk-b from backup 1 of deployment vol-b volume    size=768Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume bk-b detached
    And Create deployment bk-b with volume bk-b    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment bk-b healthy
    Then Check deployment bk-b file data.txt checksum matches checksum vol-b-2

Test Encrypted DR Volume Activation
    [Tags]    rwo    dr-volume    backup    restore
    [Documentation]    Test Plan: Encrypted DR Volume – create, restore, activate (RWO)
    ...
    ...                - Create a 512 Mi encrypted RWO volume (deployment 0), 
    ...                - Write 256 Mi of data, and take a backup.
    ...                - Create an encrypted DR (standby) volume from that backup
    ...                - Wait for the initial restoration to complete while the volume stays in Standby mode, then activate it.
    ...                - Finally attach the activated volume and verify data is intact.
    ...
    ...                - Issue: https://github.com/longhorn/longhorn/issues/13163
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 256 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume

    When Create DR volume 1 from backup 0 of deployment 0 volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume 1 restoration from backup 0 of deployment 0 volume completed

    When Activate DR volume 1
    Then Wait for volume 1 detached

    And Create deployment 1 with volume 1    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment 1 healthy
    Then Assert disk size in instance manager for deployment 1    expected_disk_size=512Mi
    And Check deployment 1 file data.txt checksum matches checksum 0

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
