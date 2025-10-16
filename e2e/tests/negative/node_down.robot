*** Settings ***
Documentation    Negative Test Cases

Test Tags    manual    negative    node-down

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/backing_image.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Power Off Node And Longhorn Not Force Delete Terminating Statefulset Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Setting default-replica-count is set to {"v1":"2","v2":"2"}
    And Setting node-down-pod-deletion-policy is set to ${node_down_pod_deletion_policy}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0
    
    When Power off volume node of statefulset 0
    And Sleep    300
    Then Check Longhorn node Ready state on power off node is False
    And Wait for statefulset 0 pod stuck in Terminating on the original node

    When Power on off nodes
    Then Wait for longhorn ready
    And Wait for statefulset 0 pods stable
    And Check statefulset 0 data in file data is intact

Power Off Node And Longhorn Force Delete Terminating Statefulset Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Setting default-replica-count is set to {"v1":"2","v2":"2"}
    And Setting node-down-pod-deletion-policy is set to ${node_down_pod_deletion_policy}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Write 100 MB data to file data in statefulset 0

    When Power off volume node of statefulset 0
    And Sleep    300
    Then Check Longhorn node Ready state on power off node is False
    And Wait for statefulset 0 pod is Running on another node
    And Wait for statefulset 0 pods stable
    And Check statefulset 0 data in file data is intact

    When Power on off nodes
    Then Wait for longhorn ready

Power Off Node And Longhorn Not Force Delete Terminating Deployment Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Setting default-replica-count is set to {"v1":"2","v2":"2"}
    And Setting node-down-pod-deletion-policy is set to ${node_down_pod_deletion_policy}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 100 MB data to file data in deployment 0
    
    When Power off volume node of deployment 0
    And Sleep    300
    Then Check Longhorn node Ready state on power off node is False
    And Wait for deployment 0 pod stuck in Terminating on the original node
    And Wait for deployment 0 pod stuck In ContainerCreating on another node

    When Force delete deployment 0 pod on the original node
    Then Wait for deployment 0 pod is Running on another node
    And Wait for deployment 0 pods stable
    And Check deployment 0 data in file data is intact

    When Power on off nodes
    Then Wait for longhorn ready

Power Off Node And Longhorn Force Delete Terminating Deployment Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Setting default-replica-count is set to {"v1":"2","v2":"2"}
    And Setting node-down-pod-deletion-policy is set to ${node_down_pod_deletion_policy}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=2
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Write 100 MB data to file data in deployment 0

    When Power off volume node of deployment 0
    And Sleep    300
    Then Check Longhorn node Ready state on power off node is False
    And Wait for deployment 0 pod is Running on another node
    And Wait for deployment 0 pods stable
    And Check deployment 0 data in file data is intact

    When Power on off nodes
    Then Wait for longhorn ready

*** Test Cases ***    NODE-DOWN-POD-DELETION-POLICY
Test Node Down Pod Deletion Policy Set To do-nothing And Longhorn Not Force Delete Terminating StatefulSet Pod
    Power Off Node And Longhorn Not Force Delete Terminating Statefulset Pod    do-nothing

Test Node Down Pod Deletion Policy Set To delete-deployment-pod And Longhorn Not Force Delete Terminating StatefulSet Pod
    Power Off Node And Longhorn Not Force Delete Terminating Statefulset Pod    delete-deployment-pod

Test Node Down Pod Deletion Policy Set To delete-statefulset-pod And Longhorn Force Delete Terminating StatefulSet Pod
    Power Off Node And Longhorn Force Delete Terminating Statefulset Pod    delete-statefulset-pod

Test Node Down Pod Deletion Policy Set To delete-both-statefulset-and-deployment-pod And Longhorn Force Delete Terminating StatefulSet Pod
    Power Off Node And Longhorn Force Delete Terminating Statefulset Pod    delete-both-statefulset-and-deployment-pod

Test Node Down Pod Deletion Policy Set To do-nothing And Longhorn Not Force Delete Terminating Deployment Pod
    Power Off Node And Longhorn Not Force Delete Terminating Deployment Pod    do-nothing

Test Node Down Pod Deletion Policy Set To delete-statefulset-pod And Longhorn Not Force Delete Terminating Deployment Pod
    Power Off Node And Longhorn Not Force Delete Terminating Deployment Pod    delete-statefulset-pod

Test Node Down Pod Deletion Policy Set To delete-deployment-pod And Longhorn Force Delete Terminating Deployment Pod
    Power Off Node And Longhorn Force Delete Terminating Deployment Pod    delete-deployment-pod

Test Node Down Pod Deletion Policy Set To delete-both-statefulset-and-deployment-pod And Longhorn Force Delete Terminating Deployment Pod
    Power Off Node And Longhorn Force Delete Terminating Deployment Pod    delete-both-statefulset-and-deployment-pod

Test Backing Image On Two Nodes Down
    [Tags]    backing-image
    [Documentation]    Test backing image behavior when two nodes are powered off.
    ...                Related Issue:
    ...                https://github.com/longhorn/longhorn/issues/2006
    ...                https://github.com/longhorn/longhorn/issues/2295
    ...                https://github.com/longhorn/longhorn/issues/2530
    ...                - Disable node soft anti-affinity and set replica-replenishment-wait-interval to a large value.
    ...                - Create a backing image and wait for it to be ready on the first disk.
    ...                - Create two volumes using the backing image and attach them to two different nodes.
    ...                - Verify the backing image disk state map contains disks of all replicas and are running.
    ...                - Verify backing image content and write random data to both volumes.
    ...                - Power off two nodes: one containing a volume engine, another with the other volume's replicas.
    ...                - Verify related backing image disk file state becomes Unknown for the down node, one volume is Degraded but serving, the other becomes Unknown.
    ...                - Power on the node with the engine and verify recovery, data integrity and backing image reuse.
    ...
    ...                Available test backing image URLs:
    ...                - https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2
    ...                - https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.raw
    ...                - https://cloud-images.ubuntu.com/minimal/releases/focal/release-20200729/ubuntu-20.04-minimal-cloudimg-amd64.img
    ...                - https://github.com/rancher/k3os/releases/download/v0.11.0/k3os-amd64.iso
    Given Setting replica-replenishment-wait-interval is set to 600
    And Setting replica-soft-anti-affinity is set to false

    When Create backing image bi-down with    url=https://longhorn-backing-image.s3-us-west-1.amazonaws.com/parrot.qcow2    dataEngine=${DATA_ENGINE}    minNumberOfCopies=3
    And Create volume 0 with    backingImage=bi-down    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Create volume 1 with    backingImage=bi-down    dataEngine=${DATA_ENGINE}    numberOfReplicas=3
    And Attach volume 0 to node 0
    And Attach volume 1 to node 1
    And Wait for volume 0 healthy
    And Wait for volume 1 healthy
    Then Verify all disk file status of backing image bi-down are ready
    And Write data to volume 0
    And Write data to volume 1

    When Power off volume 0 volume node
    And Power off node 2
    Then Wait for disk file status of backing image bi-down are expected    expected_ready_count=1    expected_unknown_count=2
    And Wait for volume 0 attached and unknown
    And Wait for volume 1 degraded
    And Check volume 1 data is intact

    When Power on off nodes
    Then Wait for volume 0 healthy
    And Wait for volume 1 healthy
    And Check volume 0 data is intact
    And Check volume 1 data is intact
    And Wait backing image managers running
    And Delete volume 0
    And Delete volume 1
    And Delete backing image bi-down
