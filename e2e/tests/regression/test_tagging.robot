*** Settings ***
Documentation    Tagging Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/node.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Tag Scheduling
    [Tags]    coretest    replica
    [Documentation]    Test scheduling with tags
    Given Setting replica-soft-anti-affinity is set to true
    And Set node 0 tags    main    storage
    And Set node 1 tags    fallback    storage
    And Set node 2 tags    main    storage

    And Set node 0 disks tags    ssd    nvme
    And Set node 1 disks tags    ssd    nvme
    And Set node 2 disks tags    m2    nvme

    ${empty_node_selector}=    Create List
    ${empty_disk_selector}=    Create List
    ${fallback_storage_node_selector}=    Create List    fallback    storage
    ${main_storage_node_selector}=    Create List    main    storage
    ${fallback_storage_node_selector}=    Create List    fallback    storage
    ${ssd_nvme_disk_selector}=    Create List    ssd    nvme
    ${m2_nvme_disk_selector}=    Create List    m2    nvme

    # Case 1: Don't specify any tags, replica should be scheduled to 3 nodes.
    When Create volume 0 with    nodeSelector=${empty_node_selector}    diskSelector=${empty_disk_selector}    dataEngine=${DATA_ENGINE}
    And Wait for volume 0 detached
    And Attach volume 0
    And Wait for volume 0 healthy
    Then Volume 0 should have running replicas on node 0
    And Volume 0 should have running replicas on node 1
    And Volume 0 should have running replicas on node 2

    # Case 2: Use disk tags to select two nodes for all replicas.
    When Create volume 1 with    nodeSelector=${empty_node_selector}    diskSelector=${ssd_nvme_disk_selector}    dataEngine=${DATA_ENGINE}
    And Wait for volume 1 detached
    And Attach volume 1
    And Wait for volume 1 healthy
    Then Volume 1 should have running replicas on node 0
    And Volume 1 should have running replicas on node 1
    And Volume 1 should have 0 running replicas on node 2

    # Case 3: Use node tags to select two nodes for all replicas.
    When Create volume 2 with    nodeSelector=${main_storage_node_selector}    diskSelector=${empty_disk_selector}    dataEngine=${DATA_ENGINE}
    And Wait for volume 2 detached
    And Attach volume 2
    And Wait for volume 2 healthy
    Then Volume 2 should have running replicas on node 0
    And Volume 2 should have 0 running replicas on node 1
    And Volume 2 should have running replicas on node 2

    # Case 4: Combine node and disk tags to schedule all replicas on one node.
    When Create volume 3 with    nodeSelector=${main_storage_node_selector}    diskSelector=${ssd_nvme_disk_selector}    dataEngine=${DATA_ENGINE}
    And Wait for volume 3 detached
    And Attach volume 3
    And Wait for volume 3 healthy
    Then Volume 3 should have running replicas on node 0
    And Volume 3 should have 0 running replicas on node 1
    And Volume 3 should have 0 running replicas on node 2
