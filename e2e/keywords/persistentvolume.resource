*** Settings ***
Documentation    PersistentVolume Keywords

Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/persistentvolume_keywords.py

*** Keywords ***
Delete persistentvolume for volume ${volume_id}
    ${pv_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_persistentvolume    ${pv_name}
