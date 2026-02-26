*** Settings ***
Documentation    Compare Longhorn Components Resource Usage

Test Tags    manual    regression    negative    resource-usage

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/metrics.resource

*** Test Cases ***
Compare Longhorn components resource usage
    Check Longhorn components resource usage
