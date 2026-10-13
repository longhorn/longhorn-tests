*** Settings ***
Documentation    Vault key provider for encrypted volumes (phase 1).
...
...              Encrypted volumes whose Secret selects CRYPTO_KEY_PROVIDER vault keep one
...              generated passphrase per volume in the in-cluster Vault fixture
...              (deploy/vault/vault.yaml); the Secret carries only connection details.
...              The tests are engine agnostic and run on every data engine.
...              Tracking issue: https://github.com/longhorn/longhorn/issues/3026

Test Tags    regression    encrypted    vault

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/vault.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/sharemanager.resource

Test Setup    Set up vault test environment
Test Teardown    Cleanup vault test resources

*** Variables ***
${CSI_PLUGIN_LABEL}    app=longhorn-csi-plugin

*** Keywords ***
Set up vault test environment
    [Documentation]    Deploy the Vault fixture, which also writes the encryption Secret that
    ...                configures the provider. A vault StorageClass names that Secret with
    ...                encryptionSecret and carries no csi.storage.k8s.io references.
    Set up test environment
    Deploy vault fixture
    ${secret_name} =    Get encryption secret name
    Set Test Variable    ${ENCRYPTION_SECRET}    ${secret_name}

Create vault storageclass
    [Documentation]    An encrypted StorageClass with no csi.storage.k8s.io references, whose
    ...                encryptionSecret names the one Secret holding the configuration.
    Create storageclass longhorn-crypto with    encrypted=true    dataEngine=${DATA_ENGINE}    encryptionSecret=${ENCRYPTION_SECRET}

Cleanup vault test resources
    Run Keyword If Test Failed    Run Keyword And Ignore Error    Collect vault diagnostics
    Run Keyword And Ignore Error    Restore vault availability
    Cleanup test resources
    Cleanup vault keys

Create vault encrypted deployment ${deployment_id} with ${size} of data
    [Documentation]    A vault-encrypted RWO volume behind a deployment, with data written and
    ...                the Vault entry and Volume CR state checked.
    When Create persistentvolumeclaim ${deployment_id}    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment ${deployment_id} with persistentvolumeclaim ${deployment_id}
    And Wait for volume of deployment ${deployment_id} healthy
    And Wait for workloads pods stable    deployment ${deployment_id}
    And Write ${size} MB data to file data.txt in deployment ${deployment_id}
    Then Check deployment ${deployment_id} data in file data.txt is intact
    And Assert vault holds key of deployment ${deployment_id} volume
    And Assert deployment ${deployment_id} volume encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=True    keyVersion=1

Create vault encrypted RWX deployment ${deployment_id} with ${size} of data
    [Documentation]    A vault-encrypted non-migratable RWX volume behind a deployment: the
    ...                share manager pod fetches the key from Vault itself, formats and opens
    ...                the device, and the Volume CR records the state the share manager
    ...                controller derives from the running pod.
    When Create persistentvolumeclaim ${deployment_id}    volume_type=RWX    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment ${deployment_id} with persistentvolumeclaim ${deployment_id}
    And Wait for volume of deployment ${deployment_id} healthy
    And Wait for workloads pods stable    deployment ${deployment_id}
    And Wait for sharemanager pod of deployment ${deployment_id} running
    And Write ${size} MB data to file data.txt in deployment ${deployment_id}
    Then Check deployment ${deployment_id} data in file data.txt is intact
    And Assert encrypted disk size in sharemanager pod for deployment ${deployment_id} is 512Mi
    And Assert vault holds key of deployment ${deployment_id} volume
    And Assert deployment ${deployment_id} volume encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=True

*** Test Cases ***
Test Vault Encrypted Volume Basic
    [Documentation]    A vault-encrypted RWO volume gets its own generated key in Vault, no
    ...                passphrase appears in the Secret, the Volume CR records the provider
    ...                and the initialized flag, and the volume reopens with the stored key
    ...                after a detach.
    Given Create vault storageclass
    When Create vault encrypted deployment 0 with 128 of data
    And Create vault encrypted deployment 1 with 16 of data
    Then Assert vault keys of deployment 0 and deployment 1 volumes are different

    When Scale down deployment 0 to detach volume
    And Scale up deployment 0 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Assert deployment 0 volume encryption    provider=vault    initialized=True    keyVersion=1

Test Vault Encrypted Volume Cloning
    [Documentation]    A CSI clone names no snapshot, so the volume controller takes the clone
    ...                snapshot on the source first and only then has a version to copy. The
    ...                clone's data is a byte copy of that moment, LUKS header included, so it
    ...                opens with the source's key, written under the clone's own name.
    Given Create vault storageclass
    And Create persistentvolumeclaim source-pvc    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Create deployment source-deployment with persistentvolumeclaim source-pvc
    And Wait for volume of deployment source-deployment healthy
    And Wait for workloads pods stable    deployment source-deployment
    And Write 128 MB data to file data.txt in deployment source-deployment
    And Record file data.txt checksum in deployment source-deployment as checksum source

    When Create persistentvolumeclaim cloned-pvc from persistentvolumeclaim source-pvc    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    And Wait for volume of persistentvolumeclaim cloned-pvc detached
    And Create deployment cloned-deployment with persistentvolumeclaim cloned-pvc
    And Wait for volume of deployment cloned-deployment healthy
    And Wait for workloads pods stable    deployment cloned-deployment
    Then Check deployment cloned-deployment file data.txt checksum matches checksum source
    And Assert vault holds key of deployment cloned-deployment volume
    And Assert vault keys of deployment source-deployment and deployment cloned-deployment volumes are equal
    And Assert deployment cloned-deployment volume encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=True    keyVersion=1

Test Vault Encrypted Volume Snapshot Clone
    [Documentation]    A volume created from a snapshot opens with the version of the source's
    ...                key that the Snapshot CR records, which is what makes a snapshot taken
    ...                before a future rotation still cloneable.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    And Record file data.txt checksum in deployment 0 as checksum 0
    When Create snapshot 0 for deployment 0 volume
    And Wait for snapshot 0 of deployment 0 volume ready
    Then Assert snapshot 0 of deployment 0 volume records encryption key version 1

    When Create volume 1 from snapshot 0 of deployment 0 volume    size=512Mi    encrypted=True    encryptionProvider=vault    encryptionSecretName=${ENCRYPTION_SECRET}    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached
    Then Assert volume 1 encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=False    keyVersion=1
    And Assert vault key of volume 1 equals key of deployment 0 volume

    When Create deployment 1 with volume 1    sc_name=longhorn-crypto
    And Wait for volume of deployment 1 healthy
    And Wait for workloads pods stable    deployment 1
    Then Check deployment 1 file data.txt checksum matches checksum 0
    And Assert volume 1 encryption    provider=vault    initialized=True

Test Vault Encrypted Volume Backup Restore
    [Documentation]    A completed backup gets its own entry in Vault, holding the key its data
    ...                is encrypted with, and a restore reads that entry rather than the
    ...                volume's.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    And Record file data.txt checksum in deployment 0 as checksum 0
    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    Then Assert vault holds key of backup 0 of deployment 0 volume
    And Assert vault key of backup 0 equals key of deployment 0 volume

    When Create volume 1 from backup 0 of deployment 0 volume    accessMode=RWO    size=512Mi    encrypted=True    encryptionProvider=vault    encryptionSecretName=${ENCRYPTION_SECRET}    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached
    And Create deployment 1 with volume 1    sc_name=longhorn-crypto
    And Wait for volume of deployment 1 healthy
    And Wait for workloads pods stable    deployment 1
    Then Check deployment 1 file data.txt checksum matches checksum 0
    And Assert vault key of volume 1 equals key of deployment 0 volume

Test Vault Encrypted Backup Restores After Its Volume Is Deleted
    [Documentation]    This is why a backup owns its key. Deleting a volume destroys the
    ...                volume's entry; if a restore read that entry, every backup ever taken
    ...                from the volume would restore cleanly and then refuse to open. The
    ...                backup's own entry survives, so the restore still opens.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    And Record file data.txt checksum in deployment 0 as checksum 0
    ${volume_name} =    Get volume name of deployment 0
    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    # Resolve the backup by name now: everything that maps the workload to its
    # volume is about to be deleted, which is the point of the test.
    ${backup_name} =    Get backup name of backup 0 of deployment 0 volume
    Then Assert vault holds key of backup named ${backup_name}

    When Delete deployment 0
    And Delete persistentvolumeclaim 0
    Then Wait for vault key of volume ${volume_name} destroyed
    And Assert vault holds key of backup named ${backup_name}

    When Create volume 1 from backup 0 of deleted volume ${volume_name}    accessMode=RWO    size=512Mi    encrypted=True    encryptionProvider=vault    encryptionSecretName=${ENCRYPTION_SECRET}    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached
    And Create deployment 1 with volume 1    sc_name=longhorn-crypto
    And Wait for volume of deployment 1 healthy
    And Wait for workloads pods stable    deployment 1
    Then Check deployment 1 file data.txt checksum matches checksum 0

Test Vault Encrypted Volume Key Is Destroyed On Delete
    [Documentation]    The volume controller destroys the key before releasing the finalizer,
    ...                so a deleted volume leaves nothing behind in the store.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 16 of data
    ${volume_name} =    Get volume name of deployment 0
    When Delete deployment 0
    And Delete persistentvolumeclaim 0
    Then Wait for vault key of volume ${volume_name} destroyed

Test Vault Encrypted Backup Key Is Destroyed With The Backup
    [Documentation]    The backup's entry goes with its Backup CR, so a deleted backup leaves
    ...                no passphrase behind either.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 16 of data
    When Create backup 0 for deployment 0 volume
    And Verify backup list contains backup no error for deployment 0 volume
    Then Assert vault holds key of backup 0 of deployment 0 volume
    When Delete backup 0 of deployment 0 volume
    Then Assert vault holds no key of backup 0 of deployment 0 volume

Test Vault Encrypted Volume Waits For Vault Before Its Engine Starts
    [Documentation]    The key is stored before the engine starts, so a volume created while
    ...                Vault is unreachable never attaches: it has no key version, no endpoint,
    ...                and an EncryptionKey condition saying why. When Vault comes back the
    ...                key is stored and the volume attaches by itself.
    Given Create vault storageclass
    And Make vault unavailable
    When Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto    storage_size=512Mi
    # The pod cannot become ready while Vault is down, which is the point, so the
    # deployment is created without waiting for it.
    And Create deployment 0 with persistentvolumeclaim 0    wait=${False}
    Then Wait for deployment 0 pod stuck in ContainerCreating
    And Assert deployment 0 volume encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=False    keyVersion=0
    And Assert deployment 0 volume encryption condition is False

    When Make vault available
    Then Wait for deployment 0 volume encryption key stored
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Assert deployment 0 volume encryption condition is True
    And Write 16 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

Test Vault Encrypted Volume Rejects An Unknown Encryption Secret
    [Documentation]    An encryptionSecret that names no Secret is rejected at admission, so a
    ...                typo in a StorageClass fails at creation instead of surfacing later as a
    ...                mount failure on some node.
    Given Create storageclass longhorn-crypto-typo with    encrypted=true    dataEngine=${DATA_ENGINE}    encryptionSecret=no-such-secret
    When Create persistentvolumeclaim typo    volume_type=RWO    sc_name=longhorn-crypto-typo    storage_size=512Mi    wait_for_bound=${False}
    Then Wait for persistentvolumeclaim typo event containing secretName
    And Assert persistentvolumeclaim typo has no volume

Test Vault Encrypted Volume Expansion
    [Documentation]    Online expansion fetches the key from Vault for the cryptsetup resize;
    ...                the data stays intact and the key entry is unchanged.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    When Expand deployment 0 volume to 768Mi
    Then Wait for deployment 0 volume size expanded
    And Check deployment 0 pods did not restart
    And Check deployment 0 data in file data.txt is intact
    And Assert deployment 0 volume encryption    provider=vault    initialized=True    keyVersion=1

Test Vault Encrypted Volume Provider Mismatch Is Rejected
    [Documentation]    Cloning a vault volume into a StorageClass whose Secret selects the
    ...                secret provider is rejected at CreateVolume: the copied LUKS header can
    ...                only be unlocked with the source's key, which that provider cannot supply.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 16 of data
    And Create crypto secret longhorn-crypto-literal
    And Create storageclass longhorn-crypto-literal with    encrypted=true    dataEngine=${DATA_ENGINE}    cryptoSecretName=longhorn-crypto-literal
    When Create persistentvolumeclaim mismatch from persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto-literal    storage_size=512Mi    wait_for_bound=${False}
    Then Wait for persistentvolumeclaim mismatch event containing key provider
    And Assert persistentvolumeclaim mismatch has no volume
    # The pending clone holds the cloning-protection finalizer on its source PVC;
    # remove it here so the source can be deleted by the common cleanup.
    [Teardown]    Run Keywords    Delete persistentvolumeclaim mismatch    AND    Cleanup vault test resources

Test Vault Encrypted Volume Fails Closed When Key Is Deleted
    [Documentation]    A LUKS device whose key is gone from Vault is never formatted: the
    ...                attach is refused with an explicit error until the key is back, then the
    ...                data is intact.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    And Record vault key of deployment 0 volume as key 0
    When Scale down deployment 0 to detach volume
    And Delete vault key of deployment 0 volume
    And Get test start time
    And Scale deployment 0 to 1
    Then Wait for deployment 0 pod stuck in ContainerCreating
    And Any ${CSI_PLUGIN_LABEL} Pods Log Should Have LUKS header but no key In Container longhorn-csi-plugin After Test Start

    When Restore vault key of deployment 0 volume from key 0
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact

Test Vault Encrypted Volume Fails Closed When Key Is Corrupted
    [Documentation]    A wrong passphrase in Vault cannot open the device and never formats
    ...                it; restoring the recorded key brings the data back.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    And Record vault key of deployment 0 volume as key 0
    When Scale down deployment 0 to detach volume
    And Corrupt vault key of deployment 0 volume
    And Scale deployment 0 to 1
    Then Wait for deployment 0 pod stuck in ContainerCreating

    When Restore vault key of deployment 0 volume from key 0
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Assert deployment 0 volume encryption    provider=vault    initialized=True

Test Vault Encrypted Volume Waits For Vault During Attach
    [Documentation]    With Vault unreachable a new attach waits in ContainerCreating with the
    ...                data intact and completes once Vault is back.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    When Scale down deployment 0 to detach volume
    And Make vault unavailable
    And Scale deployment 0 to 1
    Then Wait for deployment 0 pod stuck in ContainerCreating

    When Make vault available
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact

Test Vault Encrypted Volume Keeps Serving IO During Vault Outage
    [Documentation]    Vault is only contacted while opening a device: a mounted volume keeps
    ...                reading and writing while Vault is down.
    Given Create vault storageclass
    And Create vault encrypted deployment 0 with 128 of data
    When Make vault unavailable
    And Write 64 MB data to file outage.txt in deployment 0
    Then Check deployment 0 data in file outage.txt is intact
    And Check deployment 0 data in file data.txt is intact
    And Check deployment 0 pods did not restart
    [Teardown]    Run Keywords    Make vault available    AND    Cleanup vault test resources

Test Vault Encrypted RWX Volume Basic
    [Tags]    rwx
    [Documentation]    A vault-encrypted RWX volume is served by the share manager, which gets
    ...                the volume's generated key from Vault with its own projected token; no
    ...                passphrase reaches the share manager pod. The volume survives a
    ...                detach and reattach with the data intact.
    Given Create vault storageclass
    When Create vault encrypted RWX deployment 0 with 128 of data
    Then Assert no crypto secret exists
    And Assert sharemanager pod of deployment 0 has no PASSPHRASE env

    When Scale down deployment 0 to detach volume
    And Wait for sharemanager pod of deployment 0 deleted
    And Scale up deployment 0 to attach volume
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Assert encrypted disk size in sharemanager pod for deployment 0 is 512Mi
    And Assert deployment 0 volume encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=True

Test Vault Encrypted RWX Volume Concurrent Writers
    [Tags]    rwx
    [Documentation]    Two deployments share one vault-encrypted RWX volume through the same
    ...                share manager; what one writes the other reads.
    Given Create vault storageclass
    And Create vault encrypted RWX deployment 0 with 128 of data
    When Create deployment 1 with persistentvolumeclaim 0
    And Wait for workloads pods stable    deployment 1
    And Record file data.txt checksum in deployment 0 as checksum 0
    Then Check deployment 1 file data.txt checksum matches checksum 0
    When Write 64 MB data to file second.txt in deployment 1
    And Record file second.txt checksum in deployment 1 as checksum 1
    Then Check deployment 0 file second.txt checksum matches checksum 1

Test Vault Encrypted RWX Volume Survives Share Manager Pod Restart
    [Tags]    rwx
    [Documentation]    A recreated share manager pod fetches the same key from Vault, opens the
    ...                existing LUKS device and exports it again; the data is intact and the
    ...                device is not formatted a second time.
    Given Create vault storageclass
    And Create vault encrypted RWX deployment 0 with 128 of data
    When Delete sharemanager pod of deployment 0
    And Wait for sharemanager pod of deployment 0 recreation
    And Wait for sharemanager pod of deployment 0 running
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact
    And Assert deployment 0 volume encryption    provider=vault    secretName=${ENCRYPTION_SECRET}    initialized=True
    And Write 64 MB data to file after-restart.txt in deployment 0
    And Check deployment 0 data in file after-restart.txt is intact

Test Vault Encrypted RWX Volume Expansion
    [Tags]    rwx    expansion
    [Documentation]    Online expansion of a vault-encrypted RWX volume: the share manager
    ...                fetches the key again to resize the LUKS mapping, the pod is not
    ...                recreated, and the data is intact.
    Given Create vault storageclass
    And Create vault encrypted RWX deployment 0 with 128 of data
    When Expand deployment 0 volume to 768Mi
    Then Wait for deployment 0 volume size expanded
    And Check no sharemanager pod of deployment 0 recreation
    And Assert encrypted disk size in sharemanager pod for deployment 0 is 768Mi
    And Check deployment 0 data in file data.txt is intact
    And Write 384 MB data to file after-expansion.txt in deployment 0
    And Check deployment 0 data in file after-expansion.txt is intact

Test Vault Encrypted RWX Volume Fails Closed When Key Is Deleted
    [Tags]    rwx
    [Documentation]    A LUKS device whose key is gone from Vault is never formatted by the
    ...                share manager: the share is not exported and the workload waits until
    ...                the key is back, then the data is intact.
    Given Create vault storageclass
    And Create vault encrypted RWX deployment 0 with 128 of data
    And Record vault key of deployment 0 volume as key 0
    When Scale down deployment 0 to detach volume
    And Wait for sharemanager pod of deployment 0 deleted
    And Delete vault key of deployment 0 volume
    And Scale deployment 0 to 1
    Then Wait for deployment 0 pod stuck in ContainerCreating
    And Assert vault holds no key of deployment 0 volume

    When Restore vault key of deployment 0 volume from key 0
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact

Test Vault Encrypted RWX Volume Waits For Vault During Attach
    [Tags]    rwx
    [Documentation]    With Vault unreachable the share manager cannot open the device; the
    ...                workload waits in ContainerCreating with the data intact and comes up
    ...                once Vault is back.
    Given Create vault storageclass
    And Create vault encrypted RWX deployment 0 with 128 of data
    When Scale down deployment 0 to detach volume
    And Wait for sharemanager pod of deployment 0 deleted
    And Make vault unavailable
    And Scale deployment 0 to 1
    Then Wait for deployment 0 pod stuck in ContainerCreating

    When Make vault available
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    Then Check deployment 0 data in file data.txt is intact

Test Vault Encrypted RWX Volume Keeps Serving IO During Vault Outage
    [Tags]    rwx
    [Documentation]    The share manager contacts Vault only while opening or resizing the
    ...                device: an exported share keeps reading and writing while Vault is down.
    Given Create vault storageclass
    And Create vault encrypted RWX deployment 0 with 128 of data
    When Make vault unavailable
    And Write 64 MB data to file outage.txt in deployment 0
    Then Check deployment 0 data in file outage.txt is intact
    And Check deployment 0 data in file data.txt is intact
    And Check deployment 0 pods did not restart
    [Teardown]    Run Keywords    Make vault available    AND    Cleanup vault test resources
