*** Settings ***
Documentation    PersistentVolumeClaim Keywords

Library    Collections
Library    ../libs/keywords/common_keywords.py
Library    ../libs/keywords/persistentvolumeclaim_keywords.py
Library    ../libs/keywords/volume_keywords.py

*** Keywords ***
Create persistentvolumeclaim ${claim_id}
    [Arguments]    &{config}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_persistentvolumeclaim    ${claim_name}    &{config}

Create persistentvolumeclaim ${cloned_claim_id} from persistentvolumeclaim ${source_claim_id}
    [Arguments]    &{config}
    ${cloned_claim_name} =    generate_name_with_suffix    claim    ${cloned_claim_id}
    ${source_claim_name} =    generate_name_with_suffix    claim    ${source_claim_id}
    create_persistentvolumeclaim    ${cloned_claim_name}    dataSourceName=${source_claim_name}    dataSourceKind=PersistentVolumeClaim    &{config}

Create persistentvolumeclaim ${claim_id} from csi volume snapshot ${csi_volume_snapshot_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${csi_volume_snapshot_id}
    create_persistentvolumeclaim    ${claim_name}    dataSourceName=${csi_volume_snapshot_name}    dataSourceKind=VolumeSnapshot

Create persistentvolumeclaim in Block volume mode ${claim_id}
    [Arguments]    &{config}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_persistentvolumeclaim    ${claim_name}    volume_mode=Block    &{config}

Wait for volume of persistentvolumeclaim ${claim_id} to be created
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${volume_name} =    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    wait_for_volume_to_be_created    ${volume_name}

Wait for volume of persistentvolumeclaim ${claim_id} cloning to complete
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${volume_name} =    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    wait_for_volume_clone_status_completed    ${volume_name}

Wait for volume of persistentvolumeclaim ${claim_id} healthy
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${volume_name} =    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    wait_for_volume_healthy    ${volume_name}

Wait for volume of persistentvolumeclaim ${claim_id} degraded
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${volume_name} =    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    wait_for_volume_degraded    ${volume_name}

Wait for volume of persistentvolumeclaim ${claim_id} detached
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${volume_name} =    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    wait_for_volume_detached    ${volume_name}

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

Assert persistentvolumeclaim ${claim_id} is using storageclass ${storageclass_name}
   ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
   ${current_storageclass} =    get_pvc_storageclass_name    ${claim_name}
   Should Be Equal    ${current_storageclass}    ${storageclass_name}

Expand persistentvolumeclaim ${claim_id} size to ${size}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    expand_persistentvolumeclaim_size_to    ${claim_name}    ${size}

Wait for volume of persistentvolumeclaim ${claim_id} size to be ${size}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    ${volume_name} =    get_volume_name_from_persistentvolumeclaim    ${claim_name}
    wait_for_volume_expand_to_size    ${volume_name}    ${size}
