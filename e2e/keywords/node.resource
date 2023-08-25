*** Settings ***
Documentation       Physical Node Keywords

Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/node_keywords.py

*** Keywords ***
During replica rebuilding, reboot volume node
    reboot_volume_node    ${volume_name}

During replica rebuilding, reboot replica node
    reboot_replica_node    ${volume_name}
