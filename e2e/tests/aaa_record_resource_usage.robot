*** Settings ***
Documentation    Record Longhorn Components Resource Usage

Test Tags    manual    regression    negative    resource-usage

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/metrics.resource

*** Test Cases ***
Record Longhorn components resource usage
    Get Longhorn components resource usage
