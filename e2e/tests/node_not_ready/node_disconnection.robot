*** Settings ***
Documentation     Test the Longhorn resillence if cluster node network disconnection
...               Manual test case: https://longhorn.github.io/longhorn-tests/manual/pre-release/node-not-ready/node-disconnection/node-disconnection/
Resource          ../../keywords/common.resource
Resource          ../../keywords/engine.resource
Resource          ../../keywords/replica.resource
Resource          ../../keywords/node.resource
Resource          ../../keywords/volume.resource
Resource          ../../keywords/setting.resource

Suite Setup    set_test_suite_environment

Test setup    set_test_environment    ${TEST NAME}

#Test Teardown    cleanup_resources

*** Variable ***
${volume_size_gb}=    2
${volume_type}=    RWO

*** Test Cases ***
Node with no replica and non-2 replica volume attached and the volume attach on no replica node and during writing data
    [Documentation]    Case 1-1
    [Tags]    NodeNetworkPartition    2Replicas    AttachReplicaSameNode    AbnormalNoReplicaNode    AbnormalNoAttachedNode    DataWriting
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 3
    And Update the auto-salvage setting to false

    When During writing data into mount point interrupt node 3 network for 100 seconds

    Then Node 3 should have 0 volume replica
    And Node 3 state should be Ready
    And Volume state should be faulted
    And Engine state should be stopped
    And All replicas state should be stopped
    [Teardown]    Run Keywords   Update the auto-salvage setting to true
    ...           AND            Teardown

Node with replica and 3 replica volume attached and during writing data
    [Documentation]    Case 1-2
    [Tags]    NodeNetworkPartition    3Replicas    AttachReplicaSameNode    AbnormalReplicaNode    AbnormalAttachedNode    DataWriting
    Given A ${volume_size_gb} GB ${volume_type} volume with 3 replicas
    And Attach volume to node 1
    And Update the auto-salvage setting to false

    When During writing data into mount point interrupt node 1 network for 100 seconds

    Then Node 1 should have 1 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    [Teardown]    Run Keywords   Update the auto-salvage setting to true
    ...           AND            Teardown


Node with no replica and non-2 replica volume attached and the volume attach on no replica node
    [Documentation]    Case 2-1
    [Tags]    NodeNetworkPartition    RWO    2Replicas    AttachReplicaSameNode    AbnormalNoReplicaNode    AbnormalNoAttachedNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 2 replicas
    And Attach volume to node 3
    And Update the auto-salvage setting to false

    When Interrupt node 3 network for 100 seconds

    Then Node 3 should have 0 volume replica
    And Node 3 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    [Teardown]    Run Keywords   Update the auto-salvage setting to true
    ...           AND            Teardown

Node with replica and 3 replica volume attached
    [Documentation]    Case 2-2
    [Tags]    NodeNetworkPartition    3Replicas    AttachReplicaSameNode    AbnormalReplicaNode    AbnormalAttachedNode
    Given A ${volume_size_gb} GB ${volume_type} volume with 3 replicas
    And Attach volume to node 1
    And Update the auto-salvage setting to false

    When Interrupt node 1 network for 100 seconds

    Then Node 1 should have 1 volume replica
    And Node 1 state should be Ready
    And Volume state should be healthy
    And Engine state should be running
    And All replicas state should be running
    [Teardown]    Run Keywords   Update the auto-salvage setting to true
    ...           AND            Teardown
