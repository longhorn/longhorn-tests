*** Settings ***
Documentation    Encrypted Volume Test Cases

Test Tags    encrypted    volume

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
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/host.resource
Resource    ../keywords/engine_image.resource
Resource    ../keywords/replica.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Assert replica backend file sizes for volume ${volume_id} are ${expected_size}
    [Documentation]    Verify replica backend head image file sizes for a raw (non-PVC) Longhorn volume.
    ${expected_bytes} =    convert_size_to_bytes    ${expected_size}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    ${replicas} =    get_replicas    ${volume_name}
    FOR    ${replica}    IN    @{replicas}
        ${node_id} =    Set Variable    ${replica}[spec][nodeID]
        ${dir_name} =    Set Variable    ${replica}[spec][dataDirectoryName]
        ${cmd} =    Set Variable
        ...    find /var/lib/longhorn/replicas/${dir_name}/ -maxdepth 1 -name 'volume-head-*.img' -exec stat -c%s {} \\;
        Wait Until Keyword Succeeds    ${RETRY_COUNT}    ${RETRY_INTERVAL}
        ...    Check replica file size on node    ${cmd}    ${node_id}    ${expected_bytes}    ${volume_name}
    END

Check replica file size on node
    [Arguments]    ${cmd}    ${node_id}    ${expected_bytes}    ${volume_name}
    ${result} =    execute_command_on_node    ${cmd}    ${node_id}
    Should Be Equal As Integers    ${result.strip()}    ${expected_bytes}
    ...    msg=Replica backend file on node ${node_id} for volume ${volume_name}: expected ${expected_bytes} B, got ${result.strip()} B

Assert block device size in deployment pod for deployment ${deployment_id} is ${size}
    ${expected_bytes} =    convert_size_to_bytes    ${size}    to_str=True
    ${deployment_name} =    generate_name_with_suffix    deployment    ${deployment_id}
    ${pod_name} =    get_workload_pod_name    ${deployment_name}
    ${cmd} =    Set Variable    blockdev --getsize64 /dev/longhorn/longhorn-testblk
    ${result} =    pod_exec    ${pod_name}    default    ${cmd}
    Should Be Equal As Integers    ${result.strip()}    ${expected_bytes}
    ...    msg=Block device size in pod ${pod_name}: expected ${expected_bytes} B, got ${result.strip()} B

*** Test Cases ***
Test Encrypted Volume Basic
    [Tags]    rwo    rwx
    [Documentation]    Test basic encrypted volume operations for both RWO and RWX volumes.
    ...                Deployment 0 = RWO, Deployment 1 = RWX.
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1Gi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=1Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 1040MiB
        Assert replica file size of deployment 1 is 1040MiB
    END
    And Write 100 MB data to file data.txt in deployment 0
    And Write 100 MB data to file data.txt in deployment 1
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
        Assert replica file size of deployment 0 is 1040MiB
        Assert replica file size of deployment 1 is 1040MiB
    END
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

Test Encrypted Volume Online Expansion
    [Tags]    rwo    rwx    expansion
    [Documentation]    Test online expansion for both RWO and RWX encrypted volumes.
    ...                Deployment 0 = RWO, Deployment 1 = RWX.
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=50MiB
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=50MiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 10 MB data to file data.txt in deployment 0
    And Write 10 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Expand deployment 0 volume to 100 MiB
    And Expand deployment 1 volume to 100 MiB
    Then Wait for deployment 0 volume size expanded
    And Wait for deployment 1 volume size expanded
    And Check deployment 0 pods did not restart
    And Check deployment 1 pods did not restart
    And Check no sharemanager pod of deployment 1 recreation
    # NOTE: With the new engine (v1.12+), the 16 MiB LUKS header is pre-allocated
    # in the replica backend file (replica size = requested size + 16 MiB).
    # The dm-crypt device therefore presents the full requested size to the workload.
    # Therefore, a 100 MiB requested volume results in a 100 MiB dm-crypt device.
    And Assert disk size in instance manager pod for deployment 0 is 100MiB
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 100MiB

    When Scale down deployment 0 to detach volume
    And Scale down deployment 1 to detach volume
    And Scale up deployment 0 to attach volume
    And Scale up deployment 1 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Wait for workloads pods stable    deployment 0
    And Wait for workloads pods stable    deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

Test Encrypted RWO Block Volume Online Expansion
    [Tags]    rwo    expansion    block-volume
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto    storage_size=50MiB
    And Create deployment 0 with block persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Make block device filesystem in deployment 0
    And Mount block device on /data in deployment 0
    And Write 10 MB data to file data1.txt in deployment 0
    Then Check deployment 0 data in file data1.txt is intact

    When Expand deployment 0 volume to 100 MiB
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    # Verify the actual disk size in the instance manager pod.
    # NOTE: With the new engine (v1.12+), the 16 MiB LUKS header is pre-allocated
    # in the replica backend file (replica size = requested size + 16 MiB).
    # The dm-crypt device therefore presents the full requested size to the workload.
    # Therefore, a 100 MiB requested volume results in a 100 MiB dm-crypt device.
    And Assert disk size in instance manager pod for deployment 0 is 100MiB
    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    Then Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Mount block device on /data in deployment 0
    And Write 60 MB data to file data2.txt in deployment 0
    Then Check deployment 0 data in file data2.txt is intact

Test Encrypted Block Volume Creation Size
    [Tags]    rwo    block-volume
    [Documentation]    Test Plan: New Block Volume Creation (RWO, v1 + v2)
    ...
    ...                Create a 1 GiB encrypted Block-mode volume.
    ...                Note: RWX + volumeMode=Block is not supported – Longhorn's share manager
    ...                      uses NFS which cannot expose a raw block device to the workload.
    ...
    ...                Expected:
    ...                  - blockdev --getsize64 inside the pod shows exactly
    ...                    1073741824 bytes (1 GiB) – the full requested size is usable.
    ...                  - (v1 only) The backend replica image file on the worker node is exactly
    ...                    1024 MiB + 16 MiB = 1040 MiB (1090519040 bytes).
    ...                    For v2 the replica backend format differs; only the block device size
    ...                    is verified (similar issue: https://github.com/longhorn/longhorn/issues/9205).
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volumeMode=Block    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1Gi
    And Create deployment 0 with block persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    Then Assert block device size in deployment pod for deployment 0 is 1Gi
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 1040MiB
    END

Test Encrypted Volume Creation Size
    [Tags]    rwo    rwx
    [Documentation]    Test Plan: New Volume Creation (RWO + RWX)
    ...
    ...                Create a 1024 MiB encrypted volume with the current (new) engine image.
    ...                Deployment 0 = RWO, Deployment 1 = RWX.
    ...
    ...                Expected:
    ...                  - The dm-crypt device inside the instance manager (RWO) shows 1024 MiB.
    ...                  - The dm-crypt device inside the share manager pod (RWX) shows 1024 MiB.
    ...                  - The backend replica image file on the worker node is exactly
    ...                    1024 MiB + 16 MiB = 1040 MiB (1090519040 bytes).
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1024MiB
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=1024MiB
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    Then Assert disk size in instance manager pod for deployment 0 is 1024MiB
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 1024MiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 1040MiB
        Assert replica file size of deployment 1 is 1040MiB
    END

Test Encrypted Volume Expansion
    [Tags]    rwo    rwx    expansion
    [Documentation]    Test Plan: Volume Expansion – new engine path (RWO + RWX)
    ...
    ...                Create a 1 GiB encrypted volume (new engine), write 100 MiB of data,
    ...                then expand to 2 GiB. Deployment 0 = RWO, Deployment 1 = RWX.
    ...
    ...                Expected after expansion:
    ...                  - Instance manager (RWO) shows 2 GiB.
    ...                  - Share manager pod (RWX) shows 2 GiB; pod is NOT recreated.
    ...                  - Replica image file on the worker node shows 2 GiB + 16 MiB = 2064 MiB.
    ...                  - Previously written data is intact.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1Gi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=1Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 100 MB data to file data.txt in deployment 0
    And Write 100 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Expand deployment 0 volume to 2GiB
    And Expand deployment 1 volume to 2GiB
    Then Wait for deployment 0 volume size expanded
    And Wait for deployment 1 volume size expanded
    And Check deployment 0 pods did not restart
    And Check deployment 1 pods did not restart
    And Check no sharemanager pod of deployment 1 recreation
    And Assert disk size in instance manager pod for deployment 0 is 2GiB
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 2GiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 2064MiB
        Assert replica file size of deployment 1 is 2064MiB
    END
    And Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

Test Encrypted Volume Upgrade
    [Tags]    rwo    rwx    expansion    replica-rebuild    engine-upgrade    old-engine
    [Documentation]    Test Plan: Old Engine – Expansion + Replica Rebuild + Engine Upgrade (RWO + RWX)
    ...
    ...                - Requires LONGHORN_STABLE_VERSION to be set (2-stage upgrade CI pipeline).
    ...                - Covers old-engine (v1.11) expansion, replica rebuild, and engine upgrade
    ...                  behaviors in a single Longhorn uninstall/reinstall/upgrade cycle.
    ...                - Deployment 0 = RWO, Deployment 1 = RWX.
    ...
    ...                Steps:
    ...                  - 1. Install stable Longhorn (v1.11) and create 1 GiB encrypted
    ...                       RWO (deployment 0) and RWX (deployment 1) volumes.
    ...                  - 2. Verify old-engine initial state:
    ...                       - Device = 1024 MiB - 16 MiB = 1008 MiB.
    ...                       - Replica file = 1 GiB (no extra 16 MiB).
    ...                  - 3. Write 100 MiB of data. Upgrade Longhorn to v1.12+ keeping old engine.
    ...                  - 4. Verify old engine semantics are preserved (same as step 2).
    ...                  - 5. (Backup/Restore) Back up old-engine volumes before upgrade,
    ...                       restore as encrypted=True after upgrade; verify new-engine sizing:
    ...                       - Device = 1 GiB (full, 16 MiB pre-allocated in backend).
    ...                       - Replica file = 1 GiB + 16 MiB = 1040 MiB.
    ...                       - Data integrity preserved.
    ...                  - 6. (Expansion) Expand to 2 GiB; verify:
    ...                       - Device = 2048 MiB - 16 MiB = 2032 MiB.
    ...                       - Replica file = 2 GiB; share manager pod NOT recreated.
    ...                  - 7. (Replica Rebuild) Delete one replica per volume; verify:
    ...                       - Rebuilt replica file = 2 GiB (old engine: no extra 16 MiB).
    ...                  - 8. (Engine Upgrade, if CUSTOM_LONGHORN_ENGINE_IMAGE is set)
    ...                       Upgrade both volumes to the new engine; verify:
    ...                       - Device = 2 GiB (full usable size).
    ...                       - Replica file = 2 GiB + 16 MiB = 2064 MiB.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    ${LONGHORN_STABLE_VERSION} =    Get Environment Variable    LONGHORN_STABLE_VERSION    default=
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Skip    Environment variable LONGHORN_STABLE_VERSION is not set
    ELSE IF    not '${LONGHORN_STABLE_VERSION}'.startswith('v1.11.')
        Skip    This test only applies to the v1.11.x → v1.12+ upgrade path; got stable version ${LONGHORN_STABLE_VERSION}
    END

    Given Setting deleting-confirmation-flag is set to true
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn stable version
    And Set default backupstore
    And Enable v2 data engine and add block disks

    When Create crypto secret
    And Create storageclass longhorn-crypto-stable with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto-stable    storage_size=1Gi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto-stable    storage_size=1Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    # Verify old-engine initial state before Longhorn upgrade
    Then Assert disk size in instance manager pod for deployment 0 is 1008MiB
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 1008MiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 1024MiB
        Assert replica file size of deployment 1 is 1024MiB
    END

    When Write 100 MB data to file data.txt in deployment 0
    And Write 100 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    # Take backups before upgrade (old-engine v1.11: no LUKS pre-allocation)
    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    And Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume

    # Upgrade Longhorn system to v1.12+ but keep both volumes on the old engine image
    When Setting concurrent-automatic-engine-upgrade-per-node-limit is set to 0
    And Upgrade Longhorn to custom version
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy

    # Verify old engine semantics are preserved after Longhorn upgrade
    Then Assert disk size in instance manager pod for deployment 0 is 1008MiB
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 1008MiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 1024MiB
        Assert replica file size of deployment 1 is 1024MiB
    END

    # --- Backup/Restore: pre-upgrade backup → new-engine restore (after upgrade) ---
    # Restore pre-upgrade (v1.11 old-engine) backups with new Longhorn (v1.12+).
    # New Longhorn provisions the restored volume with new-engine semantics:
    # 16 MiB pre-allocated in the backend → device = full 1 GiB, replica = 1040 MiB.
    # v2 data engine does not support encrypted volume CSI mounting via luksOpen;
    # the backup/restore encrypted path is therefore skipped for v2.
    # https://github.com/longhorn/longhorn/issues/13163.
    IF    '${DATA_ENGINE}' == 'v1'
        Create volume 2 from backup 0 of deployment 0 volume    size=1Gi    encrypted=True    dataEngine=${DATA_ENGINE}
        Create volume 3 from backup 1 of deployment 1 volume    size=1Gi    encrypted=True    dataEngine=${DATA_ENGINE}
        Wait for volume 2 healthy
        Wait for volume 3 healthy
        Create deployment 2 with volume 2    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto
        Create deployment 3 with volume 3    sc_name=longhorn-crypto-stable    node_stage_secret_name=longhorn-crypto
        Wait for volume of deployment 2 healthy
        Wait for volume of deployment 3 healthy
        Assert disk size in instance manager pod for deployment 2 is 1Gi
        Assert disk size in instance manager pod for deployment 3 is 1Gi
        Assert replica file size of deployment 2 is 1040MiB
        Assert replica file size of deployment 3 is 1040MiB
        Check deployment 2 data in file data.txt is intact compared to deployment 0
        Check deployment 3 data in file data.txt is intact compared to deployment 1
    END

    # --- Old engine: Volume Expansion ---
    When Expand deployment 0 volume to 2GiB
    And Expand deployment 1 volume to 2GiB
    Then Wait for deployment 0 volume size expanded
    And Wait for deployment 1 volume size expanded
    And Check deployment 0 pods did not restart
    And Check deployment 1 pods did not restart
    And Assert disk size in instance manager pod for deployment 0 is 2032MiB
    And Check no sharemanager pod of deployment 1 recreation
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 2032MiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 2048MiB
        Assert replica file size of deployment 1 is 2048MiB
    END
    And Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    # --- Old engine: Replica Rebuild (at 2 GiB) ---
    When Delete replica of deployment 0 volume on replica node
    And Wait until volume of deployment 0 replica rebuilding completed on replica node
    Then Wait for volume of deployment 0 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 2048MiB
    END
    And Check deployment 0 data in file data.txt is intact

    When Delete replica of deployment 1 volume on replica node
    And Wait until volume of deployment 1 replica rebuilding completed on replica node
    Then Wait for volume of deployment 1 healthy
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 2048MiB
    END
    And Check deployment 1 data in file data.txt is intact

    # --- Engine Upgrade (only if CUSTOM_LONGHORN_ENGINE_IMAGE is set, v1 only) ---
    ${CUSTOM_LONGHORN_ENGINE_IMAGE} =    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default=
    IF    '${CUSTOM_LONGHORN_ENGINE_IMAGE}' != '' and '${DATA_ENGINE}' == 'v1'
        # Upgrade both volumes to the new engine image
        Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
        Wait for volume of deployment 0 healthy
        Wait for volume of deployment 1 healthy
        # After engine upgrade: device = 2 GiB (full), replica = 2 GiB + 16 MiB = 2064 MiB
        Assert disk size in instance manager pod for deployment 0 is 2GiB
        Assert encrypted disk size in sharemanager pod for deployment 1 is 2GiB
        Assert replica file size of deployment 0 is 2064MiB
        Assert replica file size of deployment 1 is 2064MiB
        Check deployment 0 data in file data.txt is intact
        Check deployment 1 data in file data.txt is intact
    END

Test Encrypted Volume Replica Rebuild
    [Tags]    rwo    rwx    replica-rebuild
    [Documentation]    Test Plan: Replica Rebuild – new engine path (RWO + RWX)
    ...
    ...                Create a 1 GiB encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1) with the new engine.
    ...                Write 100 MiB of data to each, then delete one replica per volume
    ...                to trigger a rebuild.
    ...
    ...                Expected after rebuild:
    ...                  - Rebuild completes successfully (volume returns to healthy).
    ...                  - The dm-crypt device size is unchanged: 1024 MiB (RWO instance manager)
    ...                    and 1024 MiB (RWX share manager pod).
    ...                  - The newly rebuilt replica file size is 1024 MiB + 16 MiB = 1040 MiB,
    ...                    matching the existing replicas (v1 only).
    ...                  - Data integrity (md5sum / checksum) is intact.
    Given Create crypto secret
    When Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1Gi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=1Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 100 MB data to file data.txt in deployment 0
    And Write 100 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Delete replica of deployment 0 volume on replica node
    And Wait until volume of deployment 0 replica rebuilding completed on replica node
    Then Wait for volume of deployment 0 healthy
    And Assert disk size in instance manager pod for deployment 0 is 1024MiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 0 is 1040MiB
    END
    And Check deployment 0 data in file data.txt is intact

    When Delete replica of deployment 1 volume on replica node
    And Wait until volume of deployment 1 replica rebuilding completed on replica node
    Then Wait for volume of deployment 1 healthy
    And Assert encrypted disk size in sharemanager pod for deployment 1 is 1024MiB
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 1 is 1040MiB
    END
    And Check deployment 1 data in file data.txt is intact

Test Encrypted Volume Backup Restore To Encrypted Volume
    [Tags]    rwo    rwx    backup    restore
    [Documentation]    Test Plan: Backup Restore – restore as encrypted (RWO + RWX)
    ...
    ...                Create a 1 GiB encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1), write 100 MiB of data to each, take backups.
    ...                Restore each backup to a new encrypted volume.
    ...                Deployment 0 = RWO source, Deployment 1 = RWX source.
    ...                Deployment 2 = restored from dep 0 backup, Deployment 3 = restored from dep 1 backup.
    ...
    ...                Expected:
    ...                  - Restored volumes' dm-crypt device shows exactly 1 GiB.
    ...                  - Restored volumes' replica backend file is exactly 1024 MiB + 16 MiB.
    ...                  - The 100 MiB payload checksum matches the original.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    IF    '${DATA_ENGINE}' == 'v2'
        Skip    v2 data engine does not support encrypted volume restore with encrypted=True (https://github.com/longhorn/longhorn/issues/13163)
    END
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1Gi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=1Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 100 MB data to file data.txt in deployment 0
    And Write 100 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    When Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume

    # Restore to new encrypted volumes (encrypted=True)
    When Create volume 2 from backup 0 of deployment 0 volume    size=1Gi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Create volume 3 from backup 1 of deployment 1 volume    size=1Gi    encrypted=True    dataEngine=${DATA_ENGINE}
    And Wait for volume 2 detached
    And Wait for volume 3 detached
    # Mount the restored volumes via deployments so that CSI opens the LUKS container.
    # Must use longhorn-crypto SC (with node-stage-secret-ref) so luksOpen is triggered.
    And Create deployment 2 with volume 2    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto
    And Create deployment 3 with volume 3    sc_name=longhorn-crypto    node_stage_secret_name=longhorn-crypto
    And Wait for volume of deployment 2 healthy
    And Wait for volume of deployment 3 healthy
    Then Assert disk size in instance manager pod for deployment 2 is 1Gi
    And Assert disk size in instance manager pod for deployment 3 is 1Gi
    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica file size of deployment 2 is 1040MiB
        Assert replica file size of deployment 3 is 1040MiB
    END
    And Check deployment 2 data in file data.txt is intact compared to deployment 0
    And Check deployment 3 data in file data.txt is intact compared to deployment 1

Test Encrypted Volume Backup Restore To Unencrypted Volume
    [Tags]    rwo    rwx    backup    restore
    [Documentation]    Test Plan: Backup Restore – restore as unencrypted (RWO + RWX)
    ...
    ...                Create a 1 GiB encrypted RWO volume (deployment 0) and RWX volume
    ...                (deployment 1), write 100 MiB of data to each, take backups, then
    ...                restore each as an unencrypted volume (encrypted=False).
    ...                Deployment 0 = RWO source, Deployment 1 = RWX source.
    ...                Volume 2 = restored from dep 0 backup, Volume 3 = restored from dep 1 backup.
    ...
    ...                Expected:
    ...                  - Since encrypted=False, Longhorn does not pre-allocate extra 16 MiB.
    ...                    The replica backend file is exactly 1 GiB (no LUKS pre-allocation),
    ...                    compared to 1 GiB + 16 MiB for an encrypted=True restore.
    ...                  - Note: Longhorn's CSI node plugin decides whether to call luksOpen
    ...                    based on the Longhorn volume's spec.encrypted field (via Longhorn API),
    ...                    not the PV's nodeStageSecretRef. For encrypted=False volumes, luksOpen
    ...                    is never called; the raw LUKS-encrypted backup data cannot be mounted
    ...                    as a filesystem. Only backend file size is verified here.
    ...                - Issue: https://github.com/longhorn/longhorn/issues/9205
    Given Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=1Gi
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-crypto    storage_size=1Gi
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 100 MB data to file data.txt in deployment 0
    And Write 100 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    When Create backup 1 for deployment 1 volume
    And Verify backup list contains backup no error for deployment 1 volume
    # Restore as unencrypted: no 16 MiB pre-allocation in the backend.
    # Replica backend file size = 1 GiB (unlike encrypted=True which is 1 GiB + 16 MiB).
    When Create volume 2 from backup 0 of deployment 0 volume    size=1Gi    encrypted=False    dataEngine=${DATA_ENGINE}
    And Create volume 3 from backup 1 of deployment 1 volume    size=1Gi    encrypted=False    dataEngine=${DATA_ENGINE}
    Then Wait for volume 2 healthy
    And Wait for volume 3 healthy
    # v1 only: v2 replica backend uses a different format (no .img files)
    IF    '${DATA_ENGINE}' == 'v1'
        Assert replica backend file sizes for volume 2 are 1Gi
        Assert replica backend file sizes for volume 3 are 1Gi
    END
