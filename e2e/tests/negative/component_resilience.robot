*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/sharemanager.resource
Resource    ../keywords/k8s.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${RWX_VOLUME_FAST_FAILOVER}    false
${DATA_ENGINE}    v1

*** Keywords ***
Delete instance-manager of volume ${volume_id} and wait for recover
    When Delete instance-manager of volume ${volume_id}
    And Wait for volume ${volume_id} degraded
    And Wait for volume ${volume_id} healthy
    And Check volume ${volume_id} data is intact

Delete instance-manager of deployment ${deployment_id} volume and wait for recover
    When Delete instance-manager of deployment ${deployment_id} volume
    And Wait for volume of deployment ${deployment_id} attached and degraded
    And Wait for volume of deployment ${deployment_id} healthy    
    And Wait for deployment ${deployment_id} pods stable
    And Check deployment ${deployment_id} data in file data.txt is intact

*** Test Cases ***
Test Longhorn components recovery
    [Documentation]    -- Manual test plan --
    ...                Test data setup:
    ...                    Deploy Longhorn on a 3 nodes cluster.
    ...                    Create volume 0 using Longhorn API.
    ...                    Create volume 1 with backing image.
    ...                    Create a RWO volume using the Longhorn storage class(deployment 0)
    ...                    Create a RWX volume using the Longhorn storage class(deployment 1)
    ...
    ...                    Write some data in all the volumes created and record the data.
    ...                    Have all the volumes in attached state.
    ...
    ...                Test steps:
    ...                    Delete one pod of all the Longhorn components like longhorn-manager, ui, csi components etc and verify they are able to recover.
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0

    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 100 MB data to file data.txt in deployment 0

    IF    '${DATA_ENGINE}' == 'v1'
        When Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
        And Create volume 1 with    backingImage=bi    dataEngine=${DATA_ENGINE}
        And Attach volume 1
        And Wait for volume 1 healthy
        And Write data to volume 1
    
        When Create storageclass longhorn-test-1 with    dataEngine=${DATA_ENGINE}
        And Create persistentvolumeclaim 1 using RWX volume with longhorn-test-1 storageclass
        And Create deployment 1 with persistentvolumeclaim 1
        And Write 100 MB data to file data.txt in deployment 1
    END

    When Delete Longhorn DaemonSet longhorn-csi-plugin pod on node 1    
    And Delete Longhorn Deployment csi-attacher pod on node 1
    And Delete Longhorn Deployment csi-provisioner pod on node 1
    And Delete Longhorn Deployment csi-resizer pod on node 1
    And Delete Longhorn Deployment csi-snapshotter pod on node 1
    And Delete Longhorn DaemonSet longhorn-manager pod on node 1    
    And Delete Longhorn DaemonSet engine-image pod on node 1
    And Delete Longhorn component instance-manager pod on node 1
    And Delete Longhorn Deployment longhorn-ui pod
    And Delete Longhorn Deployment longhorn-driver-deployer pod

    Then Wait for Longhorn components all running
    And Wait for volume 0 healthy
    And Check volume 0 data is intact
    And Wait for deployment 0 pods stable
    And And Check deployment 0 data in file data.txt is intact
    IF    '${DATA_ENGINE}' == 'v1'
        And Check volume 1 data is intact
        And Wait for deployment 1 pods stable
        And And Check deployment 1 data in file data.txt is intact
    END

Test Longhorn volume recovery
    [Documentation]    -- Manual test plan --
    ...                Test data setup:
    ...                    Deploy Longhorn on a 3 nodes cluster.
    ...                    Create volume 0 using Longhorn API.
    ...
    ...                    Write some data in the volume created and compute the md5sum.
    ...                    Have the volume in attached state.
    ...
    ...                Test steps:
    ...                    Delete the IM of the volume and make sure volume recovers. Check the data as well.
    ...                    Start replica rebuilding for the aforementioned volume, and delete the IM-e while it is rebuilding. Verify the recovered volumes.
    Given Create volume 0 with    dataEngine=${DATA_ENGINE}
    And Attach volume 0
    And Wait for volume 0 healthy
    And Write data to volume 0
    Then Delete instance-manager of volume 0 and wait for recover

    When Delete volume 0 replica on replica node
    And Wait until volume 0 replica rebuilding started on replica node
    Then Delete instance-manager of volume 0 and wait for recover

Test Longhorn backing image volume recovery
    [Documentation]    -- Manual test plan --
    ...                Test data setup:
    ...                    Deploy Longhorn on a 3 nodes cluster.
    ...                    Create volume 0 with backing image.
    ...
    ...                    Write some data in the volume created and compute the md5sum.
    ...                    Have the volume in attached state.
    ...
    ...                Test steps:
    ...                    Delete the IM of the volume and make sure volume recovers. Check the data as well.
    ...                    Start replica rebuilding for the aforementioned volume, and delete the IM-e while it is rebuilding. Verify the recovered volume.    
    ...                    Delete the backing image manager pod and verify the pod gets recreated.    
    IF    '${DATA_ENGINE}' == 'v1'
        When Create backing image bi with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
        And Create volume 0 with    backingImage=bi    dataEngine=${DATA_ENGINE}
        And Attach volume 0
        And Wait for volume 0 healthy
        And Write data to volume 0
        Then Delete instance-manager of volume 0 and wait for recover
    
        When Delete volume 0 replica on replica node
        And Wait until volume 0 replica rebuilding started on replica node
        Then Delete instance-manager of volume 0 and wait for recover

        When Delete backing image managers and wait for recreation
        Then Wait backing image managers running
    END

Test Longhorn dynamic provisioned RWX volume recovery
    [Documentation]    -- Manual test plan --
    ...                Test data setup:
    ...                    Deploy Longhorn on a 3 nodes cluster.
    ...                    Create a RWX volume using the Longhorn storage class
    ...
    ...                    Write some data in the volume created and compute the md5sum.
    ...                    Have the volume in attached state.
    ...
    ...                Test steps:
    ...                    Delete the IM of the volume and make sure volume recovers. Check the data as well.
    ...                    Start replica rebuilding for the aforementioned volume, and delete the IM-e while it is rebuilding. Verify the recovered volume.
    ...                    Delete the Share-manager pod and verify the RWX volume is able recover. Verify the data too.
    IF    '${DATA_ENGINE}' == 'v1'
        When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
        And Create persistentvolumeclaim 0 using RWX volume with longhorn-test storageclass
        And Create deployment 0 with persistentvolumeclaim 0
        And Write 500 MB data to file data.txt in deployment 0
        Then Delete instance-manager of deployment 0 volume and wait for recover

        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuilding started on replica node
        Then Delete instance-manager of deployment 0 volume and wait for recover

        When Delete sharemanager of deployment 0 and wait for recreation
        And Wait for sharemanager of deployment 0 running
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data.txt is intact
    END

Test Longhorn dynamic provisioned RWO volume recovery
    [Documentation]    -- Manual test plan --
    ...                Test data setup:
    ...                    Deploy Longhorn on a 3 nodes cluster.
    ...                    Create a RWO volume using the Longhorn storage class
    ...
    ...                    Write some data in the volume created and compute the md5sum.
    ...                    Have the volume in attached state.
    ...
    ...                Test steps:
    ...                    Delete the IM of the volume and make sure volume recovers. Check the data as well.
    ...                    Start replica rebuilding for the aforementioned volume, and delete the IM-e while it is rebuilding. Verify the recovered volume.
    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 500 MB data to file data.txt in deployment 0
    Then Delete instance-manager of deployment 0 volume and wait for recover
    
    When Delete replica of deployment 0 volume on replica node
    And Wait until volume of deployment 0 replica rebuilding started on replica node
    Then Delete instance-manager of deployment 0 volume and wait for recover
