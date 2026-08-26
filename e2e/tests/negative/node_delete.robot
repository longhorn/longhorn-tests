*** Settings ***
Documentation    Negative Test Cases

Test Tags    node-delete    negative

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/host.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/workload.resource
Resource    ../keywords/k8s.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/node.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/volume.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Delete Volume Node While Replica Rebuilding
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting node-down-pod-deletion-policy is set to do-nothing
    And Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Write 2048 MB data to file data in deployment 0
    And Write 2048 MB data to file data in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on volume node
        And Wait until volume of deployment 0 replica rebuilding started on volume node
        And Delete volume of deployment 0 volume node

        Then Wait for volume of deployment 0 attached and unknown
        And Add deleted node back
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data is intact

        When Delete replica of deployment 1 volume on volume node
        And Wait until volume of deployment 1 replica rebuilding started on volume node
        And Delete volume of deployment 1 volume node

        Then Wait for volume of deployment 1 attached and unknown
        And Add deleted node back
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data is intact
    END

Delete Replica Node While Replica Rebuilding
    [Arguments]    ${RWX_VOLUME_FAST_FAILOVER}
    Given Setting node-down-pod-deletion-policy is set to do-nothing
    And Setting rwx-volume-fast-failover is set to ${RWX_VOLUME_FAST_FAILOVER}
    And Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Write 2048 MB data to file data in deployment 0
    And Write 2048 MB data to file data in deployment 1

    FOR    ${i}    IN RANGE    ${LOOP_COUNT}
        When Delete replica of deployment 0 volume on replica node
        And Wait until volume of deployment 0 replica rebuilding started on replica node
        And Delete volume of deployment 0 replica node

        Then Wait for volume of deployment 0 attached and degraded
        And Add deleted node back
        And Wait for volume of deployment 0 attached and healthy
        And Wait for deployment 0 pods stable
        And Check deployment 0 data in file data is intact

        When Delete replica of deployment 1 volume on replica node
        And Wait until volume of deployment 1 replica rebuilding started on replica node
        And Delete volume of deployment 1 replica node

        Then Wait for volume of deployment 1 attached and degraded
        And Add deleted node back
        And Wait for volume of deployment 1 attached and healthy
        And Wait for deployment 1 pods stable
        And Check deployment 1 data in file data is intact
    END

*** Test Cases ***
Delete Volume Node While Replica Rebuilding With RWX Fast Failover Enabled
    Delete Volume Node While Replica Rebuilding    RWX_VOLUME_FAST_FAILOVER=true

Delete Volume Node While Replica Rebuilding With RWX Fast Failover Disabled
    Delete Volume Node While Replica Rebuilding    RWX_VOLUME_FAST_FAILOVER=false

Delete Replica Node While Replica Rebuilding With RWX Fast Failover Enabled
    Delete Replica Node While Replica Rebuilding    RWX_VOLUME_FAST_FAILOVER=true

Delete Replica Node While Replica Rebuilding With RWX Fast Failover Disabled
    Delete Replica Node While Replica Rebuilding    RWX_VOLUME_FAST_FAILOVER=false

Delete Node While Kubernetes Node Is Gone Should Succeed
    [Documentation]    Verify that deleting nodes.longhorn.io does not fail due to KubernetesNodeGone.
    ...
    ...    Issue: https://github.com/longhorn/longhorn/issues/13494
    ...
    ...    1. Given a cluster with N nodes.
    ...    2. And a volume with N replicas.
    ...    3. And the volume is detached.
    ...    4. When shutdown node A and delete the Kubernetes Node object without Longhorn node eviction.
    ...    5. Then the ready condition of Longhorn Node CR A eventually turns to false.
    ...    6. And the Node CR A is not deletable because of scheduling is enabled, and there is replica scheduled to this node.
    ...    7. When disable node scheduling on Node CR A.
    ...    8. Then the Node CR A is updated without any issue.
    ...    9. When delete engines and replicas on node A.
    ...    10. And delete Node CR A.
    ...    11. Then Node CR A is deleted without any issue.
    Given Create volume 0 with    size=1Gi    numberOfReplicas=3    dataEngine=${DATA_ENGINE}
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy
    And Detach volume 0

    When Power off node 2
    And Delete node 2
    Then Wait for Longhorn node 2 down

    And Delete Longhorn node 2 should fail

    When Disable node 2 scheduling
    And Run command    kubectl delete engines.longhorn.io -n longhorn-system -l longhornnode=${NODE_2} --ignore-not-found=true
    And Run command    kubectl delete replicas.longhorn.io -n longhorn-system -l longhornnode=${NODE_2} --ignore-not-found=true
    Then Delete Longhorn node 2
