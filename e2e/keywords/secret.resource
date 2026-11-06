*** Settings ***
Documentation    Secret Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/secret_keywords.py

*** Keywords ***
Create crypto secret
    create_secret

Create dummy registry secret ${secret_id}
    ${secret_name} =    generate_name_with_suffix    registry-secret    ${secret_id}
    create_registry_secret    ${secret_name}
    RETURN    ${secret_name}
