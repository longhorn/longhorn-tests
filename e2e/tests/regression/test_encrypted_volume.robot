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

Test Encrypted Volume Backup Restore To Encrypted Volume
    [Arguments]    ${volume_type}
    [Documentation]    Test Plan: Backup Restore – restore as encrypted
    ...
    ...                Create a 512 Mi encrypted volume (deployment 0), write 256 Mi of data to each, take backups.
    ...                Restore each backup to a new encrypted volume.
    ...                Deployment 1 = restored from dep 0 backup.
    ...
    ...                Expected:
    ...                  - Restored volumes' dm-crypt device shows exactly 512 Mi.
    ...                  - Restored volumes' replica backend file is exactly 512 Mi + 16 Mi.
    ...                  - The 256 Mi payload checksum matches the original.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=${volume_type}    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 256 MB data to file data.txt in deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Record file data.txt checksum in deployment 0 as checksum 0

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume

    # Restore to new encrypted volumes (encrypted=True)
    When Create volume 1 from backup 0 of deployment 0 volume    accessMode=${volume_type}    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached
    # Mount the restored volumes via deployments so that CSI opens the LUKS container.
    # Must use longhorn-crypto SC (with node-stage-secret-ref) so luksOpen is triggered.
    And Create deployment 1 with volume 1    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment 1 healthy
    Then Assert disk size in instance manager for deployment 1    expected_disk_size=512Mi

    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 528Mi
    END
    And Check deployment 1 file data.txt checksum matches checksum 0

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

Test Encrypted RWO Volume Backup Restore To Encrypted Volume
    [Tags]    rwo    backup    restore
    [Template]    Test Encrypted Volume Backup Restore To Encrypted Volume
        RWO

Test Encrypted RWX Volume Backup Restore To Encrypted Volume
    [Tags]    rwx    backup    restore
    [Template]    Test Encrypted Volume Backup Restore To Encrypted Volume
        RWX

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
    [Tags]    rwo    backing-image    encrypted    clone    skip
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

Test Encrypted Volume Upgrade - Initial State Verification
    [Tags]    rwo    rwx    block-volume    upgrade
    [Documentation]    Scenario A + E: Baseline verification covering Manager Upgrade
    ...                (old engine preserved) and a subsequent Live Engine Upgrade,
    ...                across 3 volume types (RWO Filesystem, RWX Filesystem, RWO Block).
    ...                  - init-rwo: RWO Filesystem, 512 Mi
    ...                  - init-rwx: RWX Filesystem, 512 Mi
    ...                  - init-block: RWO Block, 512 Mi
    ...
    ...                Applies to BOTH v1 and v2 data engines, with different
    ...                LONGHORN_STABLE_VERSION requirements:
    ...                  - v1: LONGHORN_STABLE_VERSION must be v1.11.x
    ...                  - v2: LONGHORN_STABLE_VERSION must be v1.11.x OR exactly v1.12.0
    ...
    ...                Part A (Manager Upgrade Only, Old Engine Preserved):
    ...                  - device = requested_size - 16 Mi
    ...                  - replica = requested_size (v1 ONLY; not asserted for v2)
    ...                  - Verified both before AND after the Longhorn manager upgrade.
    ...
    ...                v2 data engine has no live engine upgrade. All deployments are
    ...                scaled down (detached) before "Upgrade Longhorn to custom version"
    ...                and scaled back up (reattached) afterward, so each v2 volume
    ...                adopts the upgraded v2 instance manager. This does NOT apply to v1.
    ...
    ...                Part E (Live Engine Upgrade, 512 Mi baseline) — v1 ONLY:
    ...                  - device = 512 Mi (full size), replica = 528 Mi
    ...                  - v2 has no equivalent step; Part E is skipped entirely for v2.
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set.
    ...                - Part E requires CUSTOM_LONGHORN_ENGINE_IMAGE to be set; if not
    ...                  set, it is skipped but Part A still runs.
    ...
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=

    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
            Skip    For DATA_ENGINE=v1, this test only applies to v1.11.x; got stable version ${LONGHORN_STABLE_VERSION}
        END
    ELSE IF    '${DATA_ENGINE}' == 'v2'
        IF    not ('${LONGHORN_STABLE_VERSION}'.startswith('v1.11.') or '${LONGHORN_STABLE_VERSION}' == 'v1.12.0')
            Skip    For DATA_ENGINE=v2, this test only applies to v1.11.x or exactly v1.12.0; got stable version ${LONGHORN_STABLE_VERSION}
        END
    END

    # ==================== Setup ====================
    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks

    # ==================== Create 3 Volumes (RWO Filesystem, RWX Filesystem, RWO Block) ====================
    When Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    And Create persistentvolumeclaim init-rwo    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment init-rwo with persistentvolumeclaim init-rwo

    And Create persistentvolumeclaim init-rwx    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment init-rwx with persistentvolumeclaim init-rwx

    And Create persistentvolumeclaim init-block    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment init-block with block persistentvolumeclaim init-block

    Then Wait for volume of deployment init-rwo healthy
    And Wait for volume of deployment init-rwx healthy
    And Wait for volume of deployment init-block healthy

    When Write 256 MB data to file data.txt in deployment init-rwo
    And Write 256 MB data to file data.txt in deployment init-rwx
    Then Check deployment init-rwo data in file data.txt is intact
    And Check deployment init-rwx data in file data.txt is intact

    # ==================== Part A: Pre-Upgrade Verification (Old Engine, 512 Mi) ====================
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment init-rwo    expected_disk_size=496Mi
        And Assert replica file size of deployment init-rwo is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment init-rwo    expected_disk_size=496Mi    raw_size=512Mi
    END

    And Assert encrypted disk size in sharemanager pod for deployment init-rwx is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment init-rwx is 512Mi
    END

    And Assert block device size in deployment pod for deployment init-block is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment init-block is 512Mi
    END

    # ==================== Upgrade Longhorn (Manager Only, Keep Old Engine) ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0

    FOR    ${name}    IN    init-rwo    init-rwx    init-block
        Check volume endpoint on node of deployment ${name}
    END

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    init-rwo    init-rwx    init-block
            Scale down deployment ${name} to detach volume
        END
    END

    When Upgrade Longhorn to custom version

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    init-rwo    init-rwx    init-block
            Scale up deployment ${name} to attach volume
        END
    END

    And Wait for volume of deployment init-rwo healthy
    And Wait for volume of deployment init-rwx healthy
    And Wait for volume of deployment init-block healthy

    FOR    ${name}    IN    init-rwo    init-rwx    init-block
        Check volume endpoint on node of deployment ${name}
    END

    # ==================== Part A: Post-Upgrade Verification (Old Engine Preserved) ====================
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment init-rwo    expected_disk_size=496Mi
        And Assert replica file size of deployment init-rwo is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment init-rwo    expected_disk_size=496Mi    raw_size=512Mi
    END

    And Assert encrypted disk size in sharemanager pod for deployment init-rwx is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment init-rwx is 512Mi
    END

    And Assert block device size in deployment pod for deployment init-block is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment init-block is 512Mi
    END

    # ==================== Part E: Live Engine Upgrade (512 Mi Baseline, v1 ONLY) ====================
    IF    '${DATA_ENGINE}' == 'v1' and '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != ''
        Then Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        And Wait for volume of deployment init-rwo healthy
        And Wait for volume of deployment init-rwx healthy
        And Wait for volume of deployment init-block healthy

        Then Assert disk size in instance manager for deployment init-rwo    expected_disk_size=512Mi
        And Assert replica file size of deployment init-rwo is 528Mi
        And Check deployment init-rwo data in file data.txt is intact

        Then Assert encrypted disk size in sharemanager pod for deployment init-rwx is 512Mi
        And Assert replica file size of deployment init-rwx is 528Mi
        And Check deployment init-rwx data in file data.txt is intact

        Then Assert block device size in deployment pod for deployment init-block is 512Mi
        And Assert replica file size of deployment init-block is 528Mi
    END

Test Encrypted Volume Upgrade - Replica Rebuild
    [Tags]    rwo    rwx    replica-rebuild    engine-upgrade    old-engine    v1
    [Documentation]    Scenario B + D: Replica Rebuild verification across BOTH the OLD
    ...                and the NEW engine, using 2 volumes (RWO + RWX) fixed at 512 Mi.
    ...                Volumes are created directly at 512 Mi (NOT via Expansion), to keep
    ...                this case focused purely on Replica Rebuild — Expansion itself, and
    ...                Replica Rebuild immediately following an Expansion, are tested
    ...                independently in the "Expansion And Engine Upgrade" test case.
    ...                  - rebuild-rwo: RWO Filesystem, 512 Mi
    ...                  - rebuild-rwx: RWX Filesystem, 512 Mi
    ...
    ...                Round 1 — Replica Rebuild after Manager Upgrade:
    ...                  - v1: Runs under the OLD engine (device = 496 Mi, rebuilt replica = 512 Mi).
    ...                  - v2: Volumes MUST be detached before Manager Upgrade and reattached
    ...                        afterward. Thus, they run on the upgraded v2 instance manager
    ...                        (encrypted device = 496 Mi, raw size = 512 Mi).
    ...
    ...                Round 2 — Replica Rebuild under NEW engine (after Live Engine Upgrade):
    ...                  - device = 512 Mi (full size), rebuilt replica = 528 Mi
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set (v1.11.x).
    ...                - Only applies to the v1 data engine.
    ...                - Round 2 requires CUSTOM_LONGHORN_ENGINE_IMAGE to be set; if not
    ...                  set, Round 2 is skipped but Round 1 still runs.
    ...
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=

    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
            Skip    For DATA_ENGINE=v1, this test only applies to v1.11.x; got stable version ${LONGHORN_STABLE_VERSION}
        END
    ELSE IF    '${DATA_ENGINE}' == 'v2'
        IF    not ('${LONGHORN_STABLE_VERSION}'.startswith('v1.11.') or '${LONGHORN_STABLE_VERSION}' == 'v1.12.0')
            Skip    For DATA_ENGINE=v2, this test only applies to v1.11.x or exactly v1.12.0; got stable version ${LONGHORN_STABLE_VERSION}
        END
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks
    And Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    # ==================== Create 2 Volumes (RWO + RWX, fixed at 512 Mi) ====================
    When Create persistentvolumeclaim rebuild-rwo    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment rebuild-rwo with persistentvolumeclaim rebuild-rwo
    And Create persistentvolumeclaim rebuild-rwx    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment rebuild-rwx with persistentvolumeclaim rebuild-rwx

    Then Wait for volume of deployment rebuild-rwo healthy
    And Wait for volume of deployment rebuild-rwx healthy

    When Write 256 MB data to file data.txt in deployment rebuild-rwo
    And Write 256 MB data to file data.txt in deployment rebuild-rwx
    Then Check deployment rebuild-rwo data in file data.txt is intact
    And Check deployment rebuild-rwx data in file data.txt is intact

    # ==================== Precondition: Upgrade Longhorn Manager (Keep Old Engine) ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0
    Check volume endpoint on node of deployment rebuild-rwo
    Check volume endpoint on node of deployment rebuild-rwx

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    rebuild-rwo    rebuild-rwx
            Scale down deployment ${name} to detach volume
        END
    END

    When Upgrade Longhorn to custom version

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    rebuild-rwo    rebuild-rwx
            Scale up deployment ${name} to attach volume
        END
    END


    And Wait for volume of deployment rebuild-rwo healthy
    And Wait for volume of deployment rebuild-rwx healthy
    Check volume endpoint on node of deployment rebuild-rwo
    Check volume endpoint on node of deployment rebuild-rwx

    # ==================== Round 1: Replica Rebuild after Manager Upgrade (v1: OLD Engine, v2: Upgraded Manager) ====================
    When Delete replica of deployment rebuild-rwo volume on replica node
    Then Wait until volume of deployment rebuild-rwo replica rebuilding completed on replica node
    And Wait for volume of deployment rebuild-rwo healthy

    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment rebuild-rwo    expected_disk_size=496Mi
        And Assert replica file size of deployment rebuild-rwo is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment rebuild-rwo    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Check deployment rebuild-rwo data in file data.txt is intact

    When Delete replica of deployment rebuild-rwx volume on replica node
    Then Wait until volume of deployment rebuild-rwx replica rebuilding completed on replica node
    And Wait for volume of deployment rebuild-rwx healthy

    Then Assert encrypted disk size in sharemanager pod for deployment rebuild-rwx is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        And Assert replica file size of deployment rebuild-rwx is 512Mi
    END
    And Check deployment rebuild-rwx data in file data.txt is intact


    # ==================== Round 2: Replica Rebuild under NEW Engine , v1 only ====================
    IF    '${DATA_ENGINE}' == 'v1' and '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != ''
        Then Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        And Wait for volume of deployment rebuild-rwo healthy
        And Wait for volume of deployment rebuild-rwx healthy

        Then Assert disk size in instance manager for deployment rebuild-rwo    expected_disk_size=512Mi
        And Assert replica file size of deployment rebuild-rwo is 528Mi
        Then Assert encrypted disk size in sharemanager pod for deployment rebuild-rwx is 512Mi
        And Assert replica file size of deployment rebuild-rwx is 528Mi

        When Delete replica of deployment rebuild-rwo volume on replica node
        Then Wait until volume of deployment rebuild-rwo replica rebuilding completed on replica node
        And Wait for volume of deployment rebuild-rwo healthy
        Then Assert disk size in instance manager for deployment rebuild-rwo    expected_disk_size=512Mi
        And Assert replica file size of deployment rebuild-rwo is 528Mi
        And Check deployment rebuild-rwo data in file data.txt is intact

        When Delete replica of deployment rebuild-rwx volume on replica node
        Then Wait until volume of deployment rebuild-rwx replica rebuilding completed on replica node
        And Wait for volume of deployment rebuild-rwx healthy
        Then Assert encrypted disk size in sharemanager pod for deployment rebuild-rwx is 512Mi
        And Assert replica file size of deployment rebuild-rwx is 528Mi
        And Check deployment rebuild-rwx data in file data.txt is intact
    END

Test Encrypted Volume Upgrade - Expansion And Engine Upgrade
    [Tags]    rwo    rwx    expansion    replica-rebuild    upgrade
    [Documentation]    Scenario A + C + E + B (post-Expansion variant): Full lifecycle
    ...                verification — Manager Upgrade (old engine preserved) → Expansion
    ...                under OLD engine (512 Mi → 768 Mi) → Replica Rebuild verification
    ...                (post-Expansion, old engine) → Live Engine Upgrade (768 Mi baseline)
    ...                → Expansion under NEW engine (768 Mi → 896 Mi) → Replica Rebuild
    ...                verification (post-Expansion, new engine).
    ...                  - expand-rwo: RWO Filesystem
    ...                  - expand-rwx: RWX Filesystem
    ...
    ...                Expansion is verified TWICE, to confirm disk/replica size
    ...                calculation is correct under BOTH the old and the new engine:
    ...                  - Part C1 (v1: Old Engine, v2: Upgraded Manager, 512 Mi → 768 Mi):
    ...                      device = 752 Mi, replica = 768 Mi (replica size checked on v1 only)
    ...                  - Part C2 (New Engine, 768 Mi → 896 Mi):
    ...                      device = 896 Mi, replica = 912 Mi
    ...
    ...                Replica Rebuild is ALSO verified immediately after EACH Expansion,
    ...                to cover the edge case where a rebuild happens right after a size
    ...                change (distinct from the standalone "Replica Rebuild" case, which
    ...                covers rebuild on volumes at a STATIC size):
    ...                  - Part B1 (post-C1, v1: Old Engine, v2: Upgraded Manager, 768 Mi): rebuilt replica,
    ...                    device = 752 Mi, replica = 768 Mi
    ...                  - Part B2 (post-C2, New Engine, 896 Mi): rebuilt replica,
    ...                    device = 896 Mi, replica = 912 Mi
    ...
    ...                Part A (Manager Upgrade Only, Old Engine Preserved, 512 Mi):
    ...                  - device = 496 Mi, replica = 512 Mi
    ...                  - Verified both before AND after the Longhorn manager upgrade.
    ...
    ...                Part E (Live Engine Upgrade, 768 Mi baseline):
    ...                  - device = 768 Mi (full size), replica = 784 Mi
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set (v1.11.x).
    ...                - Applies to BOTH v1 and v2 data engines.
    ...                - Part E, Part C2, and Part B2 (Live Engine Upgrade and post-actions) are v1 ONLY.
    ...                - For v1, Part E / C2 / B2 require CUSTOM_LONGHORN_ENGINE_IMAGE to
    ...                  be set; if not set, they are skipped but Part A / C1 / B1 still run.
    ...
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=

    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
            Skip    For DATA_ENGINE=v1, this test only applies to v1.11.x; got stable version ${LONGHORN_STABLE_VERSION}
        END
    ELSE IF    '${DATA_ENGINE}' == 'v2'
        IF    not ('${LONGHORN_STABLE_VERSION}'.startswith('v1.11.') or '${LONGHORN_STABLE_VERSION}' == 'v1.12.0')
            Skip    For DATA_ENGINE=v2, this test only applies to v1.11.x or exactly v1.12.0; got stable version ${LONGHORN_STABLE_VERSION}
        END
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks
    And Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    When Create persistentvolumeclaim expand-rwo    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment expand-rwo with persistentvolumeclaim expand-rwo
    And Create persistentvolumeclaim expand-rwx    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment expand-rwx with persistentvolumeclaim expand-rwx

    Then Wait for volume of deployment expand-rwo healthy
    And Wait for volume of deployment expand-rwx healthy

    When Write 256 MB data to file data.txt in deployment expand-rwo
    And Write 256 MB data to file data.txt in deployment expand-rwx
    Then Check deployment expand-rwo data in file data.txt is intact
    And Check deployment expand-rwx data in file data.txt is intact

    # ==================== Part A: Pre-Upgrade Verification (Old Engine, 512 Mi) ====================
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=496Mi
        And Assert replica file size of deployment expand-rwo is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment expand-rwx is 512Mi
    END


    # ==================== Upgrade Longhorn (Manager Only, Keep Old Engine) ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0
    And Check volume endpoint on node of deployment expand-rwo
    And Check volume endpoint on node of deployment expand-rwx

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    expand-rwo    expand-rwx
            Scale down deployment ${name} to detach volume
        END
    END

    When Upgrade Longhorn to custom version

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    expand-rwo    expand-rwx
            Scale up deployment ${name} to attach volume
        END
    END


    And Wait for volume of deployment expand-rwo healthy
    And Wait for volume of deployment expand-rwx healthy
    Check volume endpoint on node of deployment expand-rwo
    Check volume endpoint on node of deployment expand-rwx

    # ==================== Part A: Post-Upgrade Verification (Old Engine Preserved) ====================
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=496Mi
        And Assert replica file size of deployment expand-rwo is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 496Mi
    IF    '${DATA_ENGINE}' == 'v1'
        And Assert replica file size of deployment expand-rwx is 512Mi
    END

    # ==================== Part C1: Expansion after Manager Upgrade (v1: OLD Engine, v2: Upgraded Manager) (512 Mi → 768 Mi) ====================
    When Expand deployment expand-rwo volume to 768Mi
    And Expand deployment expand-rwx volume to 768Mi
    Then Wait for deployment expand-rwo volume size expanded
    And Wait for deployment expand-rwx volume size expanded
    And Check deployment expand-rwo pods did not restart
    And Check deployment expand-rwx pods did not restart
    IF    '${DATA_ENGINE}' == 'v1'
        And Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=752Mi
        And Assert replica file size of deployment expand-rwo is 768Mi
    ELSE
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=752Mi    raw_size=768Mi
    END
    And Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 752Mi    
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment expand-rwx is 768Mi
    END
    And Check deployment expand-rwo data in file data.txt is intact
    And Check deployment expand-rwx data in file data.txt is intact

    # ==================== Part B1: Replica Rebuild (Post-Expansion, v1: OLD Engine, v2: Upgraded Manager, 768 Mi) ====================
    When Delete replica of deployment expand-rwo volume on replica node
    Then Wait until volume of deployment expand-rwo replica rebuilding completed on replica node
    And Wait for volume of deployment expand-rwo healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=752Mi
        And Assert replica file size of deployment expand-rwo is 768Mi
    ELSE
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=752Mi    raw_size=768Mi
    END
    And Check deployment expand-rwo data in file data.txt is intact

    When Delete replica of deployment expand-rwx volume on replica node
    Then Wait until volume of deployment expand-rwx replica rebuilding completed on replica node
    And Wait for volume of deployment expand-rwx healthy
    Then Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 752Mi
    IF    '${DATA_ENGINE}' == 'v1'
        And Assert replica file size of deployment expand-rwx is 768Mi
    END
    And Check deployment expand-rwx data in file data.txt is intact

    # ==================== Part E: Live Engine Upgrade (768 Mi Baseline , v1 only) ====================
    IF    '${DATA_ENGINE}' == 'v1' and '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != ''
        Then Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        And Wait for volume of deployment expand-rwo healthy
        And Wait for volume of deployment expand-rwx healthy

        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=768Mi
        And Assert replica file size of deployment expand-rwo is 784Mi
        And Check deployment expand-rwo data in file data.txt is intact

        Then Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 768Mi
        And Assert replica file size of deployment expand-rwx is 784Mi
        And Check deployment expand-rwx data in file data.txt is intact

        # ==================== Part C2: Expansion under NEW Engine (768 Mi → 896 Mi) ====================
        When Expand deployment expand-rwo volume to 896Mi
        And Expand deployment expand-rwx volume to 896Mi
        Then Wait for deployment expand-rwo volume size expanded
        And Wait for deployment expand-rwx volume size expanded
        And Check deployment expand-rwo pods did not restart
        And Check deployment expand-rwx pods did not restart

        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=896Mi
        And Assert replica file size of deployment expand-rwo is 912Mi
        And Check deployment expand-rwo data in file data.txt is intact

        Then Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 896Mi
        And Assert replica file size of deployment expand-rwx is 912Mi
        And Check deployment expand-rwx data in file data.txt is intact

        # ==================== Part B2: Replica Rebuild (Post-Expansion, NEW Engine, 896 Mi) ====================
        When Delete replica of deployment expand-rwo volume on replica node
        Then Wait until volume of deployment expand-rwo replica rebuilding completed on replica node
        And Wait for volume of deployment expand-rwo healthy
        Then Assert disk size in instance manager for deployment expand-rwo    expected_disk_size=896Mi
        And Assert replica file size of deployment expand-rwo is 912Mi
        And Check deployment expand-rwo data in file data.txt is intact

        When Delete replica of deployment expand-rwx volume on replica node
        Then Wait until volume of deployment expand-rwx replica rebuilding completed on replica node
        And Wait for volume of deployment expand-rwx healthy
        Then Assert encrypted disk size in sharemanager pod for deployment expand-rwx is 896Mi
        And Assert replica file size of deployment expand-rwx is 912Mi
        And Check deployment expand-rwx data in file data.txt is intact
    END

Test Encrypted Volume Upgrade - Workload Reattach
    [Tags]    rwo    rwx    reattach    upgrade
    [Documentation]    Scenario F: Verifies that after Longhorn upgrade, volumes can be
    ...                correctly detached and reattached to a workload (e.g. via pod
    ...                deletion / rescheduling), and that data + encryption remain intact
    ...                across the reattach cycle.
    ...                  - reattach-rwo: RWO Filesystem
    ...                  - reattach-rwx: RWX Filesystem
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=

    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks
    And Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    When Create persistentvolumeclaim reattach-rwo    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment reattach-rwo with persistentvolumeclaim reattach-rwo
    And Create persistentvolumeclaim reattach-rwx    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment reattach-rwx with persistentvolumeclaim reattach-rwx

    Then Wait for volume of deployment reattach-rwo healthy
    And Wait for volume of deployment reattach-rwx healthy

    When Write 256 MB data to file data.txt in deployment reattach-rwo
    And Write 256 MB data to file data.txt in deployment reattach-rwx
    Then Check deployment reattach-rwo data in file data.txt is intact
    And Check deployment reattach-rwx data in file data.txt is intact

    # ==================== Upgrade Longhorn ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0
    And Check volume endpoint on node of deployment reattach-rwo
    And Check volume endpoint on node of deployment reattach-rwx

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    reattach-rwo    reattach-rwx
            Scale down deployment ${name} to detach volume
        END
    END
    And Upgrade Longhorn to custom version
    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    reattach-rwo    reattach-rwx
            Scale up deployment ${name} to attach volume
        END
    END
    And Wait for volume of deployment reattach-rwo healthy
    And Wait for volume of deployment reattach-rwx healthy

    # ==================== Reattach: Delete Workload Pod and Verify Reattach ====================
    When Scale down deployment reattach-rwo to detach volume
    Then Scale up deployment reattach-rwo to attach volume
    And Wait for volume of deployment reattach-rwo healthy
    And Check deployment reattach-rwo data in file data.txt is intact

    When Scale down deployment reattach-rwx to detach volume
    Then Scale up deployment reattach-rwx to attach volume
    And Wait for volume of deployment reattach-rwx healthy
    And Check deployment reattach-rwx data in file data.txt is intact

    # ==================== Reattach: Delete Workload Pod and Verify Reattach under NEW Engine , v1 only ====================
    IF    '${DATA_ENGINE}' == 'v1' and '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != ''
        Then Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        And Wait for volume of deployment reattach-rwo healthy
        And Wait for volume of deployment reattach-rwx healthy

        When Scale down deployment reattach-rwo to detach volume
        Then Scale up deployment reattach-rwo to attach volume
        And Wait for volume of deployment reattach-rwo healthy
        And Check deployment reattach-rwo data in file data.txt is intact

        When Scale down deployment reattach-rwx to detach volume
        Then Scale up deployment reattach-rwx to attach volume
        And Wait for volume of deployment reattach-rwx healthy
        And Check deployment reattach-rwx data in file data.txt is intact
    END

Test Encrypted Volume Upgrade - Backup And Restore
    [Tags]    rwo    rwx    backup    restore    upgrade
    [Documentation]    Scenario G: Verifies that after Longhorn upgrade, encrypted volumes
    ...                can be restored correctly, with data integrity and
    ...                encryption preserved across the backup/restore cycle.
    ...                  - backup-src-rwo: RWO Filesystem (backup source)
    ...                  - backup-src-rwx: RWX Filesystem (backup source)
    ...                  - restore-rwo: RWO Filesystem (restored from backup-src-rwo)
    ...                  - restore-rwx: RWX Filesystem (restored from backup-src-rwx)
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=

    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
            Skip    For DATA_ENGINE=v1, this test only applies to v1.11.x; got stable version ${LONGHORN_STABLE_VERSION}
        END
    ELSE IF    '${DATA_ENGINE}' == 'v2'
        IF    not ('${LONGHORN_STABLE_VERSION}'.startswith('v1.11.') or '${LONGHORN_STABLE_VERSION}' == 'v1.12.0')
            Skip    For DATA_ENGINE=v2, this test only applies to v1.11.x or exactly v1.12.0; got stable version ${LONGHORN_STABLE_VERSION}
        END
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks
    And Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    When Create persistentvolumeclaim backup-src-rwo    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment backup-src-rwo with persistentvolumeclaim backup-src-rwo
    And Create persistentvolumeclaim backup-src-rwx    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment backup-src-rwx with persistentvolumeclaim backup-src-rwx

    Then Wait for volume of deployment backup-src-rwo healthy
    And Wait for volume of deployment backup-src-rwx healthy

    When Write 256 MB data to file data.txt in deployment backup-src-rwo
    And Write 256 MB data to file data.txt in deployment backup-src-rwx
    Then Check deployment backup-src-rwo data in file data.txt is intact
    And Record file data.txt checksum in deployment backup-src-rwo as checksum backup-src-rwo
    And Check deployment backup-src-rwx data in file data.txt is intact
    And Record file data.txt checksum in deployment backup-src-rwx as checksum backup-src-rwx

    # ==================== Create Backup ====================
    When Create backup 0 for deployment backup-src-rwo volume
    And Create backup 0 for deployment backup-src-rwx volume
    Then Verify backup list contains backup no error for deployment backup-src-rwo volume
    And Verify backup list contains backup no error for deployment backup-src-rwx volume

    # ==================== Upgrade Longhorn ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0
    And Check volume endpoint on node of deployment backup-src-rwo
    And Check volume endpoint on node of deployment backup-src-rwx

    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    backup-src-rwo    backup-src-rwx
            Scale down deployment ${name} to detach volume
        END
    END
    When Upgrade Longhorn to custom version
    IF    '${DATA_ENGINE}' == 'v2'
        FOR    ${name}    IN    backup-src-rwo    backup-src-rwx
            Scale up deployment ${name} to attach volume
        END
    END
    And Wait for volume of deployment backup-src-rwo healthy
    And Wait for volume of deployment backup-src-rwx healthy

    # ==================== Restore Backup to New Volumes ====================
    # Deployment restore-rwo: Restore from Backup 0 (RWO Filesystem)
    When Create volume restore-rwo from backup 0 of deployment backup-src-rwo volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume restore-rwo detached
    And Create deployment restore-rwo with volume restore-rwo    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Wait for volume of deployment restore-rwo healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment restore-rwo    expected_disk_size=512Mi
        And Assert replica file size of deployment restore-rwo is 528Mi
    ELSE
        Then Assert disk size in instance manager for deployment restore-rwo    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Check deployment restore-rwo file data.txt checksum matches checksum backup-src-rwo

    # Deployment restore-rwx: Restore from Backup 0 (RWX Filesystem)
    When Create volume restore-rwx from backup 0 of deployment backup-src-rwx volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume restore-rwx detached
    And Create deployment restore-rwx with volume restore-rwx    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto

    And Wait for volume of deployment restore-rwx healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment restore-rwx    expected_disk_size=512Mi
        And Assert replica file size of deployment restore-rwx is 528Mi
    ELSE
        Then Assert disk size in instance manager for deployment restore-rwx    expected_disk_size=496Mi    raw_size=512Mi
    END
    And Check deployment restore-rwx file data.txt checksum matches checksum backup-src-rwx

Test Encrypted Volume Upgrade - DR Volume
    [Tags]    rwo    dr-volume    expansion    replica-rebuild    backup    restore    upgrade
    [Documentation]    Scenario H: DR (Standby) Volume behavior across a Longhorn upgrade.
    ...                Covers 3 gaps NOT addressed by the other upgrade test cases:
    ...                  1. Creating a DR volume AFTER upgrade from a backup taken BEFORE
    ...                     the upgrade (cross-version DR compatibility).
    ...                  2. DR volume size auto-tracking after the source volume is
    ...                     expanded and a new backup is taken.
    ...                  3. Restoring a POST-expansion backup to a plain (non-DR) volume.
    ...
    ...                Entities:
    ...                  - vol-a: source volume created BEFORE the upgrade (512 Mi RWO).
    ...                    The old Longhorn engine binary is preserved on vol-a until it is
    ...                    explicitly live-upgraded in Part E. (DATA_ENGINE=v1 only).
    ...                  - dr-a: DR volume created from vol-a's PRE-upgrade backup, AFTER
    ...                    the upgrade — tests cross-version backup compatibility
    ...                  - bk-a: plain (non-DR) volume restored from vol-a's POST-expansion
    ...                    backup — tests restoring an already-expanded backup
    ...                  - vol-b: source volume created AFTER the Longhorn manager upgrade
    ...                    (512 Mi RWO). Since the manager itself is already upgraded,
    ...                    vol-b is a brand-new volume and therefore ALWAYS gets the
    ...                    NEW-engine default from the upgraded manager — this does NOT
    ...                    depend on CUSTOM_LONGHORN_ENGINE_IMAGE, which only controls
    ...                    the LIVE upgrade of an already-running volume like vol-a.
    ...                  - dr-b / bk-b: same roles as dr-a / bk-a, but for vol-b
    ...                  - size assertions differ:
    ...                  - old-engine: raw = PVC,        disk = PVC − 16Mi
    ...                  - new-engine: raw = PVC + 16Mi, disk = PVC
    ...
    ...                Applies to BOTH v1 and v2 data engines, with different
    ...                LONGHORN_STABLE_VERSION requirements:
    ...                  - v1: LONGHORN_STABLE_VERSION must be v1.11.x
    ...                  - v2: LONGHORN_STABLE_VERSION must be v1.11.x OR exactly v1.12.0
    ...
    ...                v2 has no live engine upgrade concept for either existing or new
    ...                volumes. vol-a is scaled down (detached) before "Upgrade Longhorn
    ...                to custom version" and scaled back up (reattached) afterward, so
    ...                it adopts the upgraded v2 instance manager. This does NOT apply to v1.
    ...
    ...                For v1 ONLY, a Live Engine Upgrade is additionally performed on
    ...                vol-a (the pre-existing volume) right after Gap 3 completes, to
    ...                verify a running volume can transition to the new engine live.
    ...                Requires CUSTOM_LONGHORN_ENGINE_IMAGE; if not set, this step is
    ...                skipped, but vol-a stays on the OLD engine for the rest of the test
    ...                while vol-b (created afterward) still runs on the NEW engine by
    ...                default — this asymmetry is intentional and documents the real
    ...                behavioral difference between existing vs newly-created volumes.
    ...
    ...                - Issues: https://github.com/longhorn/longhorn/issues/9205
    ...                          https://github.com/longhorn/longhorn/issues/13163
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=

    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
            Skip    For DATA_ENGINE=v1, this test only applies to v1.11.x; got stable version ${LONGHORN_STABLE_VERSION}
        END
    ELSE IF    '${DATA_ENGINE}' == 'v2'
        IF    not ('${LONGHORN_STABLE_VERSION}'.startswith('v1.11.') or '${LONGHORN_STABLE_VERSION}' == 'v1.12.0')
            Skip    For DATA_ENGINE=v2, this test only applies to v1.11.x or exactly v1.12.0; got stable version ${LONGHORN_STABLE_VERSION}
        END
    END

    # ==================== Setup ====================
    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks
    And Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}

    # ==================== vol-a: Create BEFORE Upgrade, Write Data, Backup ====================
    When Create persistentvolumeclaim vol-a    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment vol-a with persistentvolumeclaim vol-a
    And Wait for volume of deployment vol-a healthy
    And Write 256 MB data to file data.txt in deployment vol-a
    Then Check deployment vol-a data in file data.txt is intact

    # Pre-upgrade backup 0 — this is the backup used later to test CROSS-VERSION DR compatibility
    When Create backup 0 for deployment vol-a volume
    Then Verify backup list contains backup no error for deployment vol-a volume

    # ==================== Pre-Upgrade Verification (Old Engine, 512 Mi) ====================
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=496Mi
        And Assert replica file size of deployment vol-a is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=496Mi    raw_size=512Mi
    END

    # ==================== Upgrade Longhorn (Manager Only, Keep Old Engine for v1) ====================
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0
    And Check volume endpoint on node of deployment vol-a

    IF    '${DATA_ENGINE}' == 'v2'
        When Scale down deployment vol-a to detach volume
        Then Wait for volume of deployment vol-a detached
    END

    When Upgrade Longhorn to custom version

    IF    '${DATA_ENGINE}' == 'v2'
        And Scale up deployment vol-a to attach volume
    END

    And Wait for volume of deployment vol-a healthy
    And Check volume endpoint on node of deployment vol-a
    Then Check deployment vol-a data in file data.txt is intact

    # ==================== Post-Manager-Upgrade Verification (Old Engine Preserved for v1) ====================
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=496Mi
        And Assert replica file size of deployment vol-a is 512Mi
    ELSE
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=496Mi    raw_size=512Mi
    END

    # ==================== Part E: Live Engine Upgrade of vol-a (v1 ONLY) ====================
    # Verifies an EXISTING, already-attached volume can transition to the new engine
    # live, without needing to be recreated.
    IF    '${DATA_ENGINE}' == 'v1' and '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != ''
        Then Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        And Wait for volume of deployment vol-a healthy
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=512Mi
        And Assert replica file size of deployment vol-a is 528Mi
        And Check deployment vol-a data in file data.txt is intact
    END

    # ==================== Gap 1: DR-A from a PRE-Upgrade Backup (Cross-Version Compatibility) ====================
    When Create DR volume dr-a from backup 0 of deployment vol-a volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume dr-a restoration from backup 0 of deployment vol-a volume completed

    # ==================== Replica Rebuild on vol-a (Post-Upgrade, Pre-Expansion) ====================
    When Delete replica of deployment vol-a volume on replica node
    Then Wait until volume of deployment vol-a replica rebuilding completed on replica node
    And Wait for volume of deployment vol-a healthy
    And Check deployment vol-a data in file data.txt is intact

    # ==================== Gap 2: Expand vol-a, Take New Backup, Verify DR-A Auto-Tracks Size ====================
    When Write 256 MB data to file data.txt in deployment vol-a
    Then Check deployment vol-a data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-a as checksum vol-a-2

    When Expand deployment vol-a volume to 768Mi
    Then Wait for deployment vol-a volume size expanded
    And Check deployment vol-a pods did not restart

    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=768Mi
        And Assert replica file size of deployment vol-a is 784Mi
    ELSE
        Then Assert disk size in instance manager for deployment vol-a    expected_disk_size=752Mi    raw_size=768Mi
    END
    And Check deployment vol-a data in file data.txt is intact

    # Post-expansion backup — this is the backup used later to test restoring an
    # ALREADY-EXPANDED backup (Gap 3, via bk-a)
    When Create backup 1 for deployment vol-a volume
    Then Verify backup list contains backup no error for deployment vol-a volume
    And Wait for volume dr-a restoration from backup 1 of deployment vol-a volume completed
    And Wait for volume dr-a size to be 768Mi

    # ==================== Activate DR-A, Attach, Verify Data ====================
    When Activate DR volume dr-a
    Then Wait for volume dr-a detached
    And Create deployment dr-a with volume dr-a    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment dr-a healthy
    Then Check deployment dr-a file data.txt checksum matches checksum vol-a-2

    # ==================== Gap 3: Restore the POST-Expansion Backup to a Plain Volume (bk-a) ====================
    When Create volume bk-a from backup 1 of deployment vol-a volume    size=768Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume bk-a detached
    And Create deployment bk-a with volume bk-a    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment bk-a healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment bk-a    expected_disk_size=768Mi
    ELSE
        Then Assert disk size in instance manager for deployment bk-a    expected_disk_size=752Mi    raw_size=768Mi
    END
    And Check deployment bk-a file data.txt checksum matches checksum vol-a-2

    # ==================== vol-b: Fully New Volume, Created AFTER the Manager Upgrade ====================
    # Runs UNCONDITIONALLY (v1 and v2 alike, regardless of CUSTOM_LONGHORN_ENGINE_IMAGE).
    # The Longhorn manager is already upgraded at this point, so any brand-new volume
    # naturally gets the NEW-engine default — this has nothing to do with whether an
    # EXISTING volume (vol-a) was live-upgraded above.
    When Create persistentvolumeclaim vol-b    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=512Mi
    And Create deployment vol-b with persistentvolumeclaim vol-b
    And Wait for volume of deployment vol-b healthy
    And Write 256 MB data to file data.txt in deployment vol-b
    Then Check deployment vol-b data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-b as checksum vol-b-1

    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment vol-b    expected_disk_size=512Mi
        And Assert replica file size of deployment vol-b is 528Mi
    ELSE
        # vol-b was created by the NEW upgraded Longhorn manager.
        # New-engine allocation:            raw = PVC + 16Mi, disk = raw - 16Mi = PVC.
        # Contrast with vol-a (old engine): raw = PVC       , disk = raw - 16Mi = PVC - 16Mi.
        Then Assert disk size in instance manager for deployment vol-b    expected_disk_size=512Mi    raw_size=528Mi
    END

    # ---- DR-B from vol-b's first backup (both backup and DR created fully post-upgrade) ----
    When Create backup 0 for deployment vol-b volume
    Then Verify backup list contains backup no error for deployment vol-b volume
    And Create DR volume dr-b from backup 0 of deployment vol-b volume    size=512Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume dr-b restoration from backup 0 of deployment vol-b volume completed

    # ---- Replica rebuild on vol-b before expansion ----
    When Delete replica of deployment vol-b volume on replica node
    Then Wait until volume of deployment vol-b replica rebuilding completed on replica node
    And Wait for volume of deployment vol-b healthy
    And Check deployment vol-b data in file data.txt is intact

    # ---- Expand vol-b, verify DR-B auto-tracks size ----
    When Write 256 MB data to file data.txt in deployment vol-b
    Then Check deployment vol-b data in file data.txt is intact
    And Record file data.txt checksum in deployment vol-b as checksum vol-b-2

    When Expand deployment vol-b volume to 768Mi
    Then Wait for deployment vol-b volume size expanded
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment vol-b    expected_disk_size=768Mi
        And Assert replica file size of deployment vol-b is 784Mi
    ELSE
        Then Assert disk size in instance manager for deployment vol-b    expected_disk_size=768Mi    raw_size=784Mi
    END
    And Check deployment vol-b data in file data.txt is intact

    When Create backup 1 for deployment vol-b volume
    Then Verify backup list contains backup no error for deployment vol-b volume
    And Wait for volume dr-b restoration from backup 1 of deployment vol-b volume completed
    And Wait for volume dr-b size to be 768Mi

    # ---- Activate DR-B, attach, verify data ----
    When Activate DR volume dr-b
    Then Wait for volume dr-b detached
    And Create deployment dr-b with volume dr-b    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment dr-b healthy
    Then Check deployment dr-b file data.txt checksum matches checksum vol-b-2

    # ---- Restore vol-b's post-expansion backup to a plain volume (bk-b) ----
    When Create volume bk-b from backup 1 of deployment vol-b volume    size=768Mi    encrypted=True    dataEngine=${DATA_ENGINE}
    Then Wait for volume bk-b detached
    And Create deployment bk-b with volume bk-b    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto    node_publish_secret_name=longhorn-crypto
    And Wait for volume of deployment bk-b healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Then Assert disk size in instance manager for deployment bk-b    expected_disk_size=768Mi
    ELSE
        Then Assert disk size in instance manager for deployment bk-b    expected_disk_size=768Mi    raw_size=784Mi
    END
    And Check deployment bk-b file data.txt checksum matches checksum vol-b-2
