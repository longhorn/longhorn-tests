*** Settings ***
Documentation    Negative Test Cases

Test Tags    negative

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

Test Setup    Set test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Power Off Node And Longhorn Not Force Delete Terminating Statefulset Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Set setting default-replica-count to 2
    And Set setting node-down-pod-deletion-policy to ${node_down_pod_deletion_policy}
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
    And Cleanup test resources

Power Off Node And Longhorn Force Delete Terminating Statefulset Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Set setting default-replica-count to 2
    And Set setting node-down-pod-deletion-policy to ${node_down_pod_deletion_policy}
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
    And Cleanup test resources

Power Off Node And Longhorn Not Force Delete Terminating Deployment Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Set setting default-replica-count to 2
    And Set setting node-down-pod-deletion-policy to ${node_down_pod_deletion_policy}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=2
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
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
    And Cleanup test resources

Power Off Node And Longhorn Force Delete Terminating Deployment Pod
    [Arguments]    ${node_down_pod_deletion_policy}
    Given Set setting default-replica-count to 2
    And Set setting node-down-pod-deletion-policy to ${node_down_pod_deletion_policy}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}    numberOfReplicas=2
    And Create persistentvolumeclaim 0 using RWO volume with longhorn-test storageclass
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
    And Cleanup test resources

*** Test Cases ***    NODE-DOWN-POD-DELETION-POLICY
Node Down And Longhorn Not Force Delete Terminating StatefulSet Pod
    [Tags]    node-down
    [Template]    Power Off Node And Longhorn Not Force Delete Terminating Statefulset Pod
        do-nothing
        delete-deployment-pod

Node Down And Longhorn Force Delete Terminating StatefulSet Pod
    [Tags]    node-down
    [Template]    Power Off Node And Longhorn Force Delete Terminating Statefulset Pod
        delete-statefulset-pod
        delete-both-statefulset-and-deployment-pod

Node Down And Longhorn Not Force Delete Terminating Deployment Pod
    [Tags]    node-down
    [Template]    Power Off Node And Longhorn Not Force Delete Terminating Deployment Pod
        do-nothing
        delete-statefulset-pod

Node Down And Longhorn Force Delete Terminating Deployment Pod
    [Tags]    node-down
    [Template]    Power Off Node And Longhorn Force Delete Terminating Deployment Pod
        delete-deployment-pod
        delete-both-statefulset-and-deployment-pod
