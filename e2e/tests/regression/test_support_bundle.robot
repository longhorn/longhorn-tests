*** Settings ***
Documentation    Support Bundle Test Cases

Test Tags    regression

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/node.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/support_bundle.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test Support Bundle Respects Log-Path Setting When Collecting Logs
    [Tags]    support bundle
    [Documentation]    Test Support Bundle Respects Log-Path Setting
    ...                Issue: https://github.com/longhorn/longhorn/issues/11522
    When Run command on node    0
    ...    sudo rm -rf /tmp/longhorn/logs && sudo mkdir -p /tmp/longhorn/logs
    And Run command on node    1
    ...    sudo rm -rf /tmp/longhorn/logs && sudo mkdir -p /tmp/longhorn/logs
    And Run command on node    2
    ...    sudo rm -rf /tmp/longhorn/logs && sudo mkdir -p /tmp/longhorn/logs    
    And Setting log-path is set to /tmp/longhorn/logs/
    And Enable v2 data engine and add block disks
    Then Delete v2 instance manager on node 0
    And Delete v2 instance manager on node 1
    And Delete v2 instance manager on node 2
    And Wait for Longhorn components all running

    When Create support bundle and download
    And Get host log list on path /tmp/longhorn/logs on node 0
    And Support bundle logs of node 0 should contain host logs
    And Get host log list on path /tmp/longhorn/logs on node 1
    And Support bundle logs of node 1 should contain host logs
    And Get host log list on path /tmp/longhorn/logs on node 2
    And Support bundle logs of node 2 should contain host logs
