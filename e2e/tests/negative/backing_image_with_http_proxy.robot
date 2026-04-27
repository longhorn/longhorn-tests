*** Settings ***
Test Tags    regression    backing-image    proxy

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/backing_image.resource
Resource    ../keywords/proxy.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Keywords ***
Setup proxy testing environment
    Set up test environment
    Deploy squid proxy server
    Deploy Kyverno policy

Cleanup proxy testing environment
    Remove Kyverno policy
    Remove squid proxy server
    Cleanup test resources

*** Test Cases ***
Backing image creation works with HTTP proxy enabled
    [Tags]    backing-image    proxy    regression
    [Documentation]    Test for https://github.com/longhorn/longhorn/issues/12779
    ...                Verify backing images can be created when HTTP_PROXY env vars are injected.
    ...                Uses Kyverno to inject proxy env vars into backing image data source pods.

    [Setup]    Setup proxy testing environment
    [Teardown]    Cleanup proxy testing environment
    Given Create backing image bi-test    url=https://cchien-backing-image.s3.us-west-1.amazonaws.com/400MB.qcow2    minNumberOfCopies=3    wait=False
    When Wait backing image bi-test data source pod running
    And Check backing image bi-test data source pod has proxy env vars
    When Wait for all disk file status of backing image bi-test are ready
    Then Verify all disk file status of backing image bi-test are ready

    When Create volume 0 with    backingImage=bi-test    numberOfReplicas=3
    And Attach volume 0 to node 0
    And Wait for volume 0 healthy

    Then Detach volume 0
    And Delete volume 0
    And Delete backing image bi-test
