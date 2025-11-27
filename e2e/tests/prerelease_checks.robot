*** Settings ***
Documentation    Pre-release Checks Test Case

Test Tags    2-stage-upgrade    upgrade    uninstall    pre-release    recurring-job    non-default-namespace

Library    OperatingSystem

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/backup.resource
Resource    ../keywords/backupstore.resource
Resource    ../keywords/snapshot.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/orphan.resource
Resource    ../keywords/support_bundle.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/system_backup.resource
Resource    ../keywords/engine_image.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/setting.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Variables ***
${test_v2_only}    false

*** Test Cases ***
Pre-release Checks
    [Documentation]    Pre-release Checks
    ...    1. Uninstall existing Longhorn
    ...    2. Install stable version of Longhorn
    ...    3. Create volumes and backups
    ...    4. Upgrade Longhorn
    ...    5. Upgrade volume engine images
    ...    6. Trigger replica rebuilding
    ...    7. Detach/Re-attach volumes
    ...    8. Restore backups
    ...    9. Uninstall Longhorn
    ...    10. Re-install Longhorn back for subsequent tests
    # if Longhorn stable version is provided or Longhorn is required to be installed in a non-default namespace,
    # uninstall the existing Longhorn and install/configure the desired version of Longhorn
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        Given Setting deleting-confirmation-flag is set to true
        And Uninstall Longhorn
        And Check Longhorn CRD removed

        And Install Longhorn stable version    longhorn_namespace=${LONGHORN_NAMESPACE}
        And Set default backupstore
        And Enable v2 data engine and add block disks
    ELSE IF    '${LONGHORN_NAMESPACE}' != 'longhorn-system'
        Given Setting deleting-confirmation-flag is set to true
        And Uninstall Longhorn
        And Check Longhorn CRD removed

        And Install Longhorn    longhorn_namespace=${LONGHORN_NAMESPACE}
        And Set default backupstore
        And Enable v2 data engine and add block disks
    END

    # after correct version of Longhorn is installed, start the test

    # (0) disable auto salvage to allow faulted volumes to be revealed
    Given Setting auto-salvage is set to false

    IF    '${test_v2_only}' == 'false'

        # (1) create a volume with revision counter enabled
        When Setting disable-revision-counter is set to {"v1":"false"}
        And Create volume vol-revision-enabled with    size=1Gi    dataEngine=v1
        And Attach volume vol-revision-enabled
        And Wait for volume vol-revision-enabled healthy
        And Write data data-vol-revision-enabled 256 MB to volume vol-revision-enabled

        # (2) create a volume with revision counter disabled
        When Setting disable-revision-counter is set to {"v1":"false"}
        And Create volume vol-revision-disabled with    size=1Gi    dataEngine=v1
        And Attach volume vol-revision-disabled
        And Wait for volume vol-revision-disabled healthy
        And Write data data-vol-revision-disabled 256 MB to volume vol-revision-disabled

        # (3) create a volume used by a pod
        Given Create volume vol-pod with    size=3Gi    dataEngine=v1
        And Create persistentvolume for volume vol-pod
        And Create persistentvolumeclaim for volume vol-pod
        And Create pod vol-pod using volume vol-pod
        And Wait for pod vol-pod running
        And Write 1024 MB data to file data.txt in pod vol-pod

        # (4) create a volume used by a statefulset
        When Create storageclass longhorn-test with    dataEngine=v1
        And Create statefulset ss-upgrade using RWO volume with longhorn-test storageclass
        And Wait for volume of statefulset ss-upgrade healthy
        And Write 1024 MB data to file data.txt in statefulset ss-upgrade

        # (5) create a strict-local volume
        When Create volume vol-strict-local with    size=1Gi    dataEngine=v1
        And Attach volume vol-strict-local
        And Wait for volume vol-strict-local healthy
        And Write data data-vol-strict-local 256 MB to volume vol-strict-local
    
        # (6) create a rwx workload
        When Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
        And Create deployment deploy-upgrade with persistentvolumeclaim 0
        And Wait for volume of deployment deploy-upgrade attached and healthy
        And Write 1024 MB data to file data.txt in deployment deploy-upgrade

        # (7) create a volume with a backing image
        When Create backing image bi-v1 with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=v1
        And Create volume vol-bi with    size=3Gi    backingImage=bi-v1
        And Create persistentvolume for volume vol-bi
        And Create persistentvolumeclaim for volume vol-bi
        And Create pod vol-pod-bi using volume vol-bi
        And Wait for pod vol-pod-bi running
        And Check file guests/catparrot.gif exists in pod vol-pod-bi
        And Write 1024 MB data to file data.txt in pod vol-pod-bi

        # (8) create a volume to be detached
        When Create volume vol-detach with    size=1Gi    dataEngine=v1
        And Attach volume vol-detach
        And Wait for volume vol-detach healthy
        And Write data data-vol-detach 256 MB to volume vol-detach
        And Detach volume vol-detach
        And Wait for volume vol-detach detached
    
        # (9) create a volume for replica rebuilding after upgrade
        When Create volume vol-rebuild with    dataEngine=v1
        And Attach volume vol-rebuild
        And Wait for volume vol-rebuild healthy
        And Write data data-vol-rebuild to volume vol-rebuild
    
        # (10) create a volume with recurring jobs
        When Create volume vol-recurring with    size=1Gi    dataEngine=v1
        And Attach volume vol-recurring
        And Wait for volume vol-recurring healthy
        Then Create snapshot and backup recurringjob for volume vol-recurring
        And Check recurringjobs for volume vol-recurring work

        # (11) create a volume that is never attached before upgrade
        And Create volume vol-never-attach with    size=1Gi    dataEngine=v1

        # (12) create custom resources
        # support bundle
        And Create support bundle
        # system backup
        And Create system backup 0
        # orphaned replica
        And Create volume v1 with    size=1Gi    dataEngine=v1
        And Attach volume v1
        And Wait for volume v1 healthy
        And Write data 0 256 MB to volume v1
        And Create orphan replica for volume v1
        And Wait for orphan count to be 1

        # (13) create snapshot
        And Create snapshot snapshot-v1 of volume v1
        And Write data 1 256 MB to volume v1

        # (14) create backup
        And Create backup backup-v1 for volume v1

    END

    # use DATA_ENGINE to control whether to test v2 volumes in the test
    # because v1.8.x v2 volumes aren't compatible with v1.7.x ones
    # we have to manually decide whether to include v2 volumes
    # based on what upgrade path we're testing
    IF    "${DATA_ENGINE}" == "v2"

        # (1) create a v2 volume that is never attached before upgrade
        When Create volume v2-vol-never-attach with    size=1Gi    dataEngine=v2

        # (2) create a v2 volume with data
        And Create volume v2 with    size=1Gi    dataEngine=v2
        And Attach volume v2
        And Wait for volume v2 healthy
        And Write data 0 256 MB to volume v2

        # (3) create a v2 volume used by a deployment
        When Create storageclass longhorn-test-v2 with    dataEngine=v2
        And Create persistentvolumeclaim pvc-v2    volume_type=RWO    sc_name=longhorn-test-v2
        And Create deployment deploy-v2-upgrade with persistentvolumeclaim pvc-v2
        And Wait for volume of deployment deploy-v2-upgrade attached and healthy
        And Write 1024 MB data to file data.txt in deployment deploy-v2-upgrade

        # (4) create a v2 volume with a backing image
        When Create backing image bi-v2 with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=v2
        And Create volume vol-bi-v2 with    size=3Gi    backingImage=bi-v2    dataEngine=v2
        And Create persistentvolume for volume vol-bi-v2
        And Create persistentvolumeclaim for volume vol-bi-v2
        And Create pod vol-pod-bi-v2 using volume vol-bi-v2
        And Wait for pod vol-pod-bi-v2 running
        And Check file guests/catparrot.gif exists in pod vol-pod-bi-v2
        And Write 1024 MB data to file data.txt in pod vol-pod-bi-v2

        # (5) create v2 snapshot
        And Create snapshot snapshot-v2 of volume v2
        And Write data 1 256 MB to volume v2

        # (6) create v2 backup
        And Create backup backup-v2 for volume v2

        # upgrading Longhorn with attached v2 volumes is not allowed
        And Detach volume v2
        And Wait for volume v2 detached
        And Delete pod vol-pod-bi-v2
        And Wait for volume vol-bi-v2 detached
        And Scale down deployment deploy-v2-upgrade to detach volume

    END

    # system upgrade
    ${LONGHORN_TRANSIENT_VERSION}=    Get Environment Variable    LONGHORN_TRANSIENT_VERSION    default=''
    IF    '${LONGHORN_TRANSIENT_VERSION}' != ''
        When Upgrade Longhorn to transient version
    END
    ${LONGHORN_STABLE_VERSION}=    Get Environment Variable    LONGHORN_STABLE_VERSION    default=''
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        When Upgrade Longhorn to custom version
    END

    # do post system upgrade checks

    # (0) check v1 instance manager pods didn't restart
    Then Check v1 instance manager pods did not restart

    IF    '${test_v2_only}' == 'false'

        # (1-1) check the data integrity of the volume with revision counter enabled
        And Check volume vol-revision-enabled data is intact
        And Check volume vol-revision-enabled works

        # (2-1) check the data integrity of the volume with revision counter disabled
        And Check volume vol-revision-disabled data is intact
        And Check volume vol-revision-disabled works

        # (3-1) check pod didn't restart and the data integrity of the volume used by a pod
        And Check pod vol-pod did not restart
        And Check pod vol-pod data in file data.txt is intact
        And Check pod vol-pod works

        # (4-1) check statefulset pod didn't restart and the data integrity of the volume used by a statefulset
        And Check statefulset ss-upgrade pods did not restart
        And Check statefulset ss-upgrade data in file data.txt is intact
        And Check statefulset ss-upgrade works

        # (5-1) check the data integrity of the strict-local volume
        And Check volume vol-strict-local data is intact
        And Check volume vol-strict-local works

        # (6-1) check deployment pod didn't restart and the data integrity of the volume of the rwx workload
        And Check deployment deploy-upgrade pods did not restart
        And Check deployment deploy-upgrade data in file data.txt is intact
        And Check deployment deploy-upgrade works

        # (7-1) check pod didn't restart and the data integrity of the volume with a backing image
        And Check pod vol-pod-bi did not restart
        And Check file guests/catparrot.gif exists in pod vol-pod-bi
        And Check pod vol-pod-bi data in file data.txt is intact
        And Check pod vol-pod-bi works

    END

    # volume engines upgrade
    IF    '${LONGHORN_STABLE_VERSION}' != ''
        ${CUSTOM_LONGHORN_ENGINE_IMAGE}=    Get Environment Variable    CUSTOM_LONGHORN_ENGINE_IMAGE    default='undefined'
        When Upgrade v1 volumes engine to ${CUSTOM_LONGHORN_ENGINE_IMAGE}
    END

    # do post engine upgrade checks

    IF    '${test_v2_only}' == 'false'

        # (1-2) check the data integrity of the volume with revision counter enabled
        Then Check volume vol-revision-enabled data is intact
        And Check volume vol-revision-enabled works
    
        # (2-2) check the data integrity of the volume with revision counter disabled
        And Check volume vol-revision-disabled data is intact
        And Check volume vol-revision-disabled works

        # (3-2) check pod didn't restart and the data integrity of the volume used by a pod
        And And Check pod vol-pod did not restart
        And Check pod vol-pod data in file data.txt is intact
        And Check pod vol-pod works

       # (4-2) check statefulset pod didn't restart and the data integrity of the volume used by a statefulset
        And Check statefulset ss-upgrade pods did not restart
        And Check statefulset ss-upgrade data in file data.txt is intact
        And Check statefulset ss-upgrade works

        # (5-2) check the data integrity of the strict-local volume
        And Check volume vol-strict-local data is intact
        And Check volume vol-strict-local works

        # (6-2) check deployment pod didn't restart and the data integrity of the volume of the rwx workload
        And Check deployment deploy-upgrade pods did not restart
        And Check deployment deploy-upgrade data in file data.txt is intact
        And Check deployment deploy-upgrade works

        # (7-2) check pod didn't restart and the data integrity of the volume with a backing image
        And Check pod vol-pod-bi did not restart
        And Check file guests/catparrot.gif exists in pod vol-pod-bi
        And Check pod vol-pod-bi data in file data.txt is intact
        And Check pod vol-pod-bi works

        # (8) check the detached volume can be attached after upgrade
        When attach volume vol-detach
        Then wait for volume vol-detach healthy
        And Check volume vol-detach data is intact
        And Check volume vol-detach works

        # (9) trigger replica rebuilding after upgrade
        When Delete volume vol-rebuild replica on node 1
        Then Wait until volume vol-rebuild replica rebuilding started on node 1
        And Wait until volume vol-rebuild replica rebuilding completed on node 1
        And Wait for volume vol-rebuild healthy
        And Check volume vol-rebuild data is intact

        # (10) check recurring jobs are working after upgrade
        And Check recurringjobs for volume vol-recurring work

        # (11) check a volume that is never attached can be attached after upgrade
        When Attach volume vol-never-attach
        Then Wait for volume vol-never-attach attached
        And Wait for volume vol-never-attach healthy
        And Check volume vol-never-attach works

        # (12) delete custom resources
        And Cleanup orphans
        And Delete system backup 0

        # (13) revert snapshot
        And Check volume v1 data is data 1
        When Detach volume v1
        And Wait for volume v1 detached
        And Attach volume v1 in maintenance mode
        And Wait for volume v1 healthy
        And Revert volume v1 to snapshot snapshot-v1
        And Detach volume v1
        And Wait for volume v1 detached
        And Attach volume v1
        And Wait for volume v1 healthy
        And Check volume v1 data is data 0

        # (14) restore volume from backup
        When Create volume vol-restore from backup backup-v1 of volume v1    size=1Gi
        Then Wait for volume vol-restore restoration from backup backup-v1 of volume v1 start
        And Wait for volume vol-restore detached
        And Attach volume vol-restore
        And Check volume vol-restore data is backup backup-v1 of volume v1

        # (15) check a volume can be detached and re-attached
        When Detach volume vol-rebuild
        And Wait for volume vol-rebuild detached
        Then Attach volume vol-rebuild
        And Wait for volume vol-rebuild healthy
        And Check volume vol-rebuild data is intact

        # (16) check a new volume with a backing image can be created
        When Create volume new-vol-bi with    size=3Gi    backingImage=bi-v1
        And Create persistentvolume for volume new-vol-bi
        And Create persistentvolumeclaim for volume new-vol-bi
        And Create pod new-vol-pod-bi using volume new-vol-bi
        And Wait for pod new-vol-pod-bi running
        And Check file guests/catparrot.gif exists in pod new-vol-pod-bi
        And Write 1024 MB data to file data.txt in pod new-vol-pod-bi

    END

    IF    "${DATA_ENGINE}" == "v2"

        # (1) check a volume that is never attached can be attached after upgrade
        When Attach volume v2-vol-never-attach
        Then Wait for volume v2-vol-never-attach attached
        And Wait for volume v2-vol-never-attach healthy
        And Check volume v2-vol-never-attach works

        # (2) check the data integrity of a volume with data
        When Attach volume v2
        Then Wait for volume v2 attached
        And Wait for volume v2 healthy
        And Check volume v2 data is intact
        And Check volume v2 works

        # (3) check the data integrity of the volume used by a deployment
        When Scale up deployment deploy-v2-upgrade to attach volume
        And Check deployment deploy-v2-upgrade data in file data.txt is intact
        And Check deployment deploy-v2-upgrade works

        # (4) check the data integrity of the volume with a backing image
        When Create pod vol-pod-bi-v2 using volume vol-bi-v2
        And Wait for pod vol-pod-bi-v2 running
        And Check file guests/catparrot.gif exists in pod vol-pod-bi-v2
        And Check pod vol-pod-bi-v2 data in file data.txt is intact
        And Check pod vol-pod-bi-v2 works

        # (5) revert v2 snapshot
        When Detach volume v2
        And Wait for volume v2 detached
        And Attach volume v2 in maintenance mode
        And Wait for volume v2 healthy
        And Revert volume v2 to snapshot snapshot-v2
        And Detach volume v2
        And Wait for volume v2 detached
        And Attach volume v2
        And Wait for volume v2 healthy
        And Check volume v2 data is data 0

        # (6) restore v2 volume from backup
        When Create volume vol-restore-v2 from backup backup-v2 of volume v2    size=1Gi    dataEngine=v2
        Then Wait for volume vol-restore-v2 restoration from backup backup-v2 of volume v2 start
        And Wait for volume vol-restore-v2 detached
        And Attach volume vol-restore-v2
        And Check volume vol-restore-v2 data is backup backup-v2 of volume v2

        # (7) trigger v2 replica rebuilding after upgrade
        When Delete volume v2 replica on node 1
        Then Wait until volume v2 replica rebuilding started on node 1
        And Wait until volume v2 replica rebuilding completed on node 1
        And Wait for volume v2 healthy
        And Check volume v2 data is data 0

        # (8) check a new v2 volume with a backing image can be created
        When Create volume new-vol-bi-v2 with    size=3Gi    backingImage=bi-v2    dataEngine=v2
        And Create persistentvolume for volume new-vol-bi-v2
        And Create persistentvolumeclaim for volume new-vol-bi-v2
        And Create pod new-vol-pod-bi-v2 using volume new-vol-bi-v2
        And Wait for pod new-vol-pod-bi-v2 running
        And Check file guests/catparrot.gif exists in pod new-vol-pod-bi-v2
        And Write 1024 MB data to file data.txt in pod new-vol-pod-bi-v2
    END

    # test uninstalling Longhorn
    Then Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    # install Longhorn back for subsequent tests
    And Install Longhorn
