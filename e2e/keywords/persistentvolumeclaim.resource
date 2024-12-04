*** Settings ***
Documentation    PersistentVolumeClaim Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/persistentvolumeclaim_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create persistentvolumeclaim ${claim_id} using ${volume_type} volume
    [Arguments]    &{config}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_persistentvolumeclaim    ${claim_name}    ${volume_type}    &{config}

Create persistentvolumeclaim ${claim_id} using ${volume_type} volume with ${sc_name} storageclass
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_persistentvolumeclaim    ${claim_name}    ${volume_type}    ${sc_name}

Delete persistentvolumeclaim ${claim_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    delete_persistentvolumeclaim    ${claim_name}

Delete persistentvolumeclaim for volume ${volume_id}
    ${claim_name} =    generate_name_with_suffix    volume    ${volume_id}
    delete_persistentvolumeclaim    ${claim_name}

Assert persistentvolumeclaim ${claim_id} requested size remains ${size} for at least ${period} seconds
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    FOR    ${i}    IN RANGE    ${period}
        ${expected_size_byte} =    convert_size_to_bytes    ${size}    to_str=True
        ${current_size_byte} =    get_claim_requested_size    ${claim_name}
        Should Be Equal    ${current_size_byte}    ${expected_size_byte}
        Sleep    1
    END
