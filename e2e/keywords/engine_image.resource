*** Settings ***
Documentation       Longhorn engine image related keywords

Library             ../libs/keywords/engine_image_keywords.py

*** Keywords ***
Create compatible engine image
    ${compatible_engine_image_name} =    deploy_compatible_engine_image
    Set Test Variable    ${compatible_engine_image_name}
