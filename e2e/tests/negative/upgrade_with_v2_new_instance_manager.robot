*** Settings ***
Documentation    Negative Test Cases

Test Tags   v2-upgrade    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/node.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/secret.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Check v2 upgrade test prerequisites
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' == ''
        Fail    Environment variable LONGHORN_STABLE_VERSION is not set
    END

    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

Prepare v2 upgrade environment
    [Arguments]    ${interrupt_mode}=${False}
    Check v2 upgrade test prerequisites

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn stable version
    IF    ${interrupt_mode}
        Setting data-engine-interrupt-mode-enabled is set to {"v2":"true"}
    END
    And Enable v2 data engine and add block disks
    And Wait for longhorn ready
    And Setting replica-replenishment-wait-interval is set to 3600
    And Set default backupstore

Prepare attached v2 volume ${volume_id} with ${replica_count} replicas
    Create volume ${volume_id} with    dataEngine=v2    numberOfReplicas=${replica_count}
    Attach volume ${volume_id} to node 0
    Wait for volume ${volume_id} healthy
    Write data to volume ${volume_id}

Wait for instance manager upgrade relocation node for volume name ${volume_name} on node ${node_name}
    ${relocation_node}=    wait_for_instance_manager_upgrade_relocation_for_volume_name    ${volume_name}    ${node_name}
    [Return]    ${relocation_node}

*** Test Cases ***
Test System V2 Upgrade With Instance Manager Upgrade
    # This test takes longer because of the larger number of volumes in the cluster.
    [Documentation]    Verify that attached v2 volumes stay healthy during system upgrade
    ...    when the target version supports v2 instance manager upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create one v2 volume on each worker node, wait for each volume to become healthy, and write data to each volume.
    ...    4. Upgrade Longhorn to the custom version under test and wait for Longhorn to become ready again.
    ...    5. Verify all instance managers are running with the default target image.
    ...    6. Verify all upgraded attached v2 volumes remain healthy and their data stays intact.
    Given Prepare v2 upgrade environment
    ${worker_nodes}=    get_worker_nodes
    ${worker_count}=    Get Length    ${worker_nodes}

    FOR    ${i}    IN RANGE    ${worker_count}
        And Create volume vol${i} with    dataEngine=v2
        And Attach volume vol${i} to node ${i}
        And Wait for volume vol${i} healthy
        And Write data to volume vol${i}
    END

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed

    FOR    ${i}    IN RANGE    ${worker_count}
        And Wait for volume vol${i} healthy
        And Check volume vol${i} data is intact
    END


Test System V2 Upgrade With Instance Manager Live Upgrade
    [Documentation]    Verify that a single v2 volume maintains I/O and stays attached during instance manager live upgrade.
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create one v2 RWO PVC with 3 replicas and a deployment on node 0.
    ...    3. Start volume monitoring and continuous fio writes with CRC32C verification.
    ...    4. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade while fio is running.
    ...    5. Wait for all v2 instance managers to use the default target image and finish upgrading.
    ...    6. Verify the volume is healthy and its attachment and enginefrontend remain on node 0.
    ...    7. Continue I/O for 3 minutes after upgrade, stop fio, and verify data integrity.
    ...    8. Verify the workload pod did not restart and the volume never detached during the test.
    Given Prepare v2 upgrade environment
    And Create storageclass longhorn-test with    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    ...    args=apk add --no-cache fio && sleep infinity
    ...    node_selector={"kubernetes.io/hostname":"${NODE_0}"}
    And Wait for volume of deployment 0 healthy
    And Wait for workloads pods stable    deployment 0
    And Mark volume monitoring start time for deployment 0

    When Start fio write with crc32c verify in deployment 0
    Then Volume of deployment 0 engine CR and enginefrontend CR should be on same node

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume of deployment 0 healthy
    And Volume of deployment 0 should be attached to node 0
    And Volume of deployment 0 enginefrontend CR should be on node 0
    And Sleep    3 minutes

    When Stop fio in deployment 0
    Then Verify fio crc32c data in deployment 0 have no errors
    And Check deployment 0 pods did not restart
    And Volume of deployment 0 should never have detached during test


Test System V2 Upgrade With Instance Manager Upgrade With Single Interrupt Mode Volume
    [Documentation]    Verify that a single attached v2 volume stays healthy during live instance manager upgrade in interrupt mode.
    ...    Test steps
    ...    1. Install the stable Longhorn version and enable interrupt mode before enabling the v2 data engine.
    ...    2. Add block disks, create one attached v2 volume with 3 replicas, and write data to it.
    ...    3. Upgrade Longhorn to the custom version and enable instance manager automatic upgrade.
    ...    4. Wait for all v2 instance managers to use the default target image and finish upgrading.
    ...    5. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment    interrupt_mode=${True}
    And Prepare attached v2 volume 0 with 3 replicas

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact


Test System V2 Upgrade With Instance Manager Upgrade With Single Encrypted RWO Volume
    [Documentation]    Verify that a single encrypted v2 RWO volume stays healthy during live instance manager upgrade.
    ...    Test steps
    ...    1. Install the stable Longhorn version, enable the v2 data engine, and add block disks.
    ...    2. Create a crypto secret and one encrypted v2 RWO PVC with 3 replicas.
    ...    3. Create a deployment using the PVC and write data through the workload.
    ...    4. Upgrade Longhorn to the custom version while the volume remains attached and enable instance manager automatic upgrade.
    ...    5. Wait for all v2 instance managers to use the default target image and finish upgrading.
    ...    6. Verify the volume is healthy and its data stays intact.
    Given Prepare v2 upgrade environment
    And Create crypto secret
    And Create storageclass longhorn-crypto with    encrypted=true    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-crypto
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Check deployment 0 data in file data.txt is intact


Test System V2 Upgrade With Instance Manager Upgrade with RWX Volume
    [Documentation]    Verify that a v2 RWX volume stays healthy during system upgrade
    ...    when the target version supports v2 instance manager upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create a v2 RWX storage class, provision an RWX PVC and deployment, then write data through the workload.
    ...    4. Upgrade Longhorn to the custom version under test and wait for Longhorn to become ready again.
    ...    5. Verify all instance managers are running with the default target image.
    ...    6. Verify the upgraded RWX volume remains healthy and its data stays intact.
    Given Prepare v2 upgrade environment

    When Create storageclass longhorn-test-rwx with    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test-rwx
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 100 MB data to file data.txt in deployment 0

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Check deployment 0 data in file data.txt is intact


Test System V2 Upgrade With RWO Volume Expansion
    [Documentation]    Verify that attached v2 RWO volumes can be expanded
    ...    while their instance managers are being upgraded during a Longhorn system upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create a v2 RWO PVC (2GiB) with pod and write file data to it.
    ...    4. Upgrade Longhorn, enable v2 instance manager automatic upgrade.
    ...    5. Wait for the RWO volume's instance manager upgrade to start (engine relocation begins).
    ...    6. Trigger volume expansion from 2GiB to 3Gi while the instance manager upgrade is in progress.
    ...    7. Wait for all instance manager upgrades to complete.
    ...    8. Verify the volume reaches the expanded size, becomes healthy, and file data remains intact.
    Given Prepare v2 upgrade environment
    And Create storageclass longhorn-test-rwo with    dataEngine=v2    numberOfReplicas=3
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test-rwo    storage_size=2GiB
    And Create pod 0 using persistentvolumeclaim 0
    And Wait for pod 0 running
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Write 100 MB data to file data.txt in pod 0

    # Get volume name and engine node before upgrade
    ${claim_name}=    generate_name_with_suffix    claim    0
    ${volume_name}=    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    ${source_engine_node}=    get_volume_node    ${volume_name}

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true

    # Wait for volume's IM upgrade to start (engine relocation begins)
    And Wait for instance manager upgrade relocation node for volume name ${volume_name} on node ${source_engine_node}

    # Now expand while IM upgrade is in progress
    When Expand persistentvolumeclaim 0 size to 3Gi

    # Wait for instance manager upgrades to complete before checking sizes
    # (during migration there are 2 engines which causes size check to fail)
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed

    # Verify volume expanded and data is intact
    Then Wait for volume of persistentvolumeclaim 0 size to be 3Gi
    And Wait for volume of persistentvolumeclaim 0 healthy
    And Check pod 0 data in file data.txt is intact


Test System V2 Upgrade With RWX Volume Expansion
    [Documentation]    Verify that attached v2 RWX volumes can be expanded
    ...    while their instance managers are being upgraded during a Longhorn system upgrade.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create a v2 RWX PVC (2GiB) with deployment and write file data to it.
    ...    4. Upgrade Longhorn, enable v2 instance manager automatic upgrade.
    ...    5. Get the RWX backing Longhorn volume name.
    ...    6. Wait for that volume's instance manager upgrade to start (engine relocation begins).
    ...    7. Trigger volume expansion from 2GiB to 3Gi while the instance manager upgrade is in progress.
    ...    8. Wait for all instance manager upgrades to complete.
    ...    9. Verify the volume reaches the expanded size, becomes healthy, and file data remains intact.
    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        Log To Console    Running RWX volume expansion upgrade iteration ${i+1}/${LOOP_COUNT}
        Given Prepare v2 upgrade environment
        And Create storageclass longhorn-test-rwx with    dataEngine=v2    numberOfReplicas=3
        And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test-rwx    storage_size=2GiB
        And Create deployment 0 with persistentvolumeclaim 0
        And Wait for volume of persistentvolumeclaim 0 healthy
        And Write 100 MB data to file data.txt in deployment 0

        # Get RWX backing volume name and engine node before upgrade
        ${claim_name}=    generate_name_with_suffix    claim    0
        ${volume_name}=    get_volume_name_from_persistentvolumeclaim    ${claim_name}
        ${source_engine_node}=    get_volume_node    ${volume_name}

        When Upgrade Longhorn to custom version
        Then Wait for longhorn ready
        And Setting allow-instance-manager-automatic-upgrade is set to true

        # Wait for RWX volume's IM upgrade to start (engine relocation begins)
        And Wait for instance manager upgrade relocation node for volume name ${volume_name} on node ${source_engine_node}

        # Now expand while IM upgrade is in progress
        When Expand deployment 0 volume to 3Gi

        # Wait for instance manager upgrades to complete before checking sizes
        # (during migration there are 2 engines which causes size check to fail)
        And Wait for all v2 instance managers running with default image
        And Wait for all v2 instance manager upgrades completed

        # Verify volume expanded and data is intact
        Then Wait for deployment 0 volume size expanded
        And Wait for volume of persistentvolumeclaim 0 healthy
        And Check deployment 0 data in file data.txt is intact

        # Clean up before uninstalling Longhorn in the next iteration.
        And Delete deployment 0
        And Delete persistentvolumeclaim 0
        And Delete storageclass longhorn-test-rwx
    END


Test System V2 Upgrade With Instance Manager Upgrade DR Volume
    [Documentation]    Verify that a v2 DR volume continues to function across system upgrade
    ...    with instance manager upgrade by completing both the initial restore and a
    ...    post-upgrade incremental restore from the source volume.
    ...    Test steps
    ...    1. Uninstall the existing Longhorn system and install the stable version for upgrade testing.
    ...    2. Enable the v2 data engine, add block disks, and wait for Longhorn to become ready.
    ...    3. Create 1 attached v2 source volume, wait for it to become healthy, and write data to it.
    ...    4. Create a backup for the source volume, create a v2 DR volume from that backup, and wait for the initial DR restore to complete.
    ...    5. Upgrade Longhorn to the custom version under test and wait for Longhorn to become ready again.
    ...    6. Verify all instance managers are running with the default target image.
    ...    7. Write more data to the source volume, create another backup, and verify the DR volume completes the post-upgrade incremental restore.
    Given Prepare v2 upgrade environment
    And Prepare attached v2 volume 0 with 3 replicas
    And Create backup 0 for volume 0
    And Wait for backup 0 of volume 0 to exist in backup list
    And Create DR volume 1 from backup 0 of volume 0    dataEngine=v2
    And Wait for volume 1 restoration from backup 0 of volume 0 completed

    When Upgrade Longhorn to custom version
    Then Wait for longhorn ready
    And Setting allow-instance-manager-automatic-upgrade is set to true
    And Wait for all v2 instance managers running with default image
    And Wait for all v2 instance manager upgrades completed
    And Wait for volume 0 healthy
    And Check volume 0 data is intact

    When Write data 1 to volume 0
    And Volume 0 backup 1 should be able to create
    And Wait for volume 1 restoration from backup 1 of volume 0 start
    Then Wait for volume 1 restoration from backup 1 of volume 0 completed
    And Activate DR volume 1
    And Attach volume 1 to healthy node
    And Wait for volume 1 healthy
    And Check volume 1 data is backup 1 of volume 0
