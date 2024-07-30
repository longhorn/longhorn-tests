*** Settings ***
Documentation    Single replica node down

Test Tags    manual_test_case

Resource    ../keywords/common.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/recurringjob.resource
Resource    ../keywords/statefulset.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/host.resource

Test Setup    Set test environment
Test Teardown    Cleanup test resources include off nodes

*** Variables ***
${LOOP_COUNT}    1
${RETRY_COUNT}    300
${RETRY_INTERVAL}    1
${DATA_ENGINE}    v1

*** Test Cases ***
Single Replica Node Down Deletion Policy do-nothing With RWO Volume Replica Locate On Replica Node
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Set setting node-down-pod-deletion-policy to do-nothing
    When Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data in deployment 0

    # Delete replicas to have the volume with its only replica located on different nodes.
    And Update volume of deployment 0 replica count to 1
    And Delete replica of deployment 0 volume on replica node
    And Delete replica of deployment 0 volume on volume node
    And Power off volume node of deployment 0
    Then Wait for volume of deployment 0 stuck in state attaching
    And Wait for deployment 0 pod stuck in Terminating on the original node

    When Power on off node
    And Wait for deployment 0 pods stable
    And Check deployment 0 pod is Running on another node
    Then Check deployment 0 data in file data is intact

Single Replica Node Down Deletion Policy do-nothing With RWO Volume Replica Locate On Volume Node
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Set setting node-down-pod-deletion-policy to do-nothing
    When Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data in deployment 0

    # Delete replicas to have the volume with its only replica located on the same node.
    And Update volume of deployment 0 replica count to 1
    And Delete replica of deployment 0 volume on all replica node
    And Power off volume node of deployment 0
    Then Wait for volume of deployment 0 faulted
    And Wait for deployment 0 pod stuck in Terminating on the original node

    When Power on off node
    And Wait for deployment 0 pods stable
    And Check deployment 0 pod is Running on the original node
    Then Check deployment 0 data in file data is intact

Single Replica Node Down Deletion Policy delete-deployment-pod With RWO Volume Replica Locate On Replica Node
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Set setting node-down-pod-deletion-policy to delete-deployment-pod
    When Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data in deployment 0

    # Delete replicas to have the volume with its only replica located on different nodes.
    And Update volume of deployment 0 replica count to 1
    And Delete replica of deployment 0 volume on replica node
    And Delete replica of deployment 0 volume on volume node
    And Power off volume node of deployment 0
    Then Wait for volume of deployment 0 attaching

    And Wait for deployment 0 pods stable
    Then Check deployment 0 data in file data is intact
    And Power on off node

Single Replica Node Down Deletion Policy delete-deployment-pod With RWO Volume Replica Locate On Volume Node
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Set setting node-down-pod-deletion-policy to delete-deployment-pod
    When Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Write 100 MB data to file data in deployment 0

    # Delete replicas to have the volume with its only replica located on the same node
    And Update volume of deployment 0 replica count to 1
    And Delete replica of deployment 0 volume on all replica node
    And Power off volume node of deployment 0
    Then Wait for volume of deployment 0 faulted
    And Wait for deployment 0 pod stuck in ContainerCreating on another node

    When Power on off node
    And Wait for deployment 0 pods stable
    And Check deployment 0 pod is Running on the original node
    Then Check deployment 0 data in file data is intact

Single Replica Node Down Deletion Policy delete-both-statefulset-and-deployment-pod With RWO Volume Replica Locate On Replica Node
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Set setting node-down-pod-deletion-policy to delete-both-statefulset-and-deployment-pod
    When Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Wait for volume of statefulset 0 healthy
    And Write 100 MB data to file data in statefulset 0

    # Delete replicas to have the volume with its only replica located on different nodes.
    And Update volume of statefulset 0 replica count to 1
    And Delete replica of statefulset 0 volume on replica node
    And Delete replica of statefulset 0 volume on volume node
    And Power off volume node of statefulset 0
    Then Wait for volume of statefulset 0 attaching

    And Wait for statefulset 0 pods stable
    Then Check statefulset 0 data in file data is intact
    And Power on off node

Single Replica Node Down Deletion Policy delete-both-statefulset-and-deployment-pod With RWO Volume Replica Locate On Volume Node
    Given Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Set setting node-down-pod-deletion-policy to delete-both-statefulset-and-deployment-pod
    When Create statefulset 0 using RWO volume with longhorn-test storageclass
    And Wait for volume of statefulset 0 healthy
    And Write 100 MB data to file data in statefulset 0

    # Delete replicas to have the volume with its only replica located on the same.
    And Update volume of statefulset 0 replica count to 1
    And Delete replica of statefulset 0 volume on all replica node
    And Power off volume node of statefulset 0
    Then Wait for volume of statefulset 0 faulted
    And Wait for statefulset 0 pod stuck in ContainerCreating on another node

    When Power on off node
    And Wait for statefulset 0 pods stable
    And Check statefulset 0 pod is Running on the original node
    Then Check statefulset 0 data in file data is intact
