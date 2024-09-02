*** Settings ***
Documentation       Longhorn replica related keywords

Library             ../libs/keywords/common_keywords.py
Library             ../libs/keywords/replica_keywords.py

*** Keywords ***
Volume ${volume_id} replica ${setting_name} should be ${setting_value}
    ${volume_name} =    generate_name_with_suffix    volume    ${volume_id}
    validate_replica_setting    ${volume_name}    ${setting_name}    ${setting_value}
