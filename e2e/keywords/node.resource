*** Settings ***
Documentation       Physical Node Keywords

Library             ../libs/keywords/volume_keywords.py
Library             ../libs/keywords/node_keywords.py

*** Keywords ***
During replica rebuilding, reboot the volume attached node
    reboot_volume_attached_node    ${volume_name}

During replica rebuilding, reboot the replica node
    reboot_node_with_replica    ${volume_name}
