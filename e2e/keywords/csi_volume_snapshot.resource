*** Settings ***
Documentation    CSI Volume Snapshot Keywords

Library    ../libs/keywords/csi_volume_snapshot_keywords.py

*** Keywords ***
Create csi volume snapshot class ${snapshot_class_id}
    [Arguments]    &{config}
    ${csi_volume_snapshot_class_name} =    generate_name_with_suffix    csi-volume-snapshot-class    ${snapshot_class_id}
    create_csi_volume_snapshot_class    ${csi_volume_snapshot_class_name}    &{config}

Create csi volume snapshot ${snapshot_id} for persistentvolumeclaim ${claim_id}
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${snapshot_id}
    ${claim_name} =    generate_name_with_suffix    claim    ${claim_id}
    create_csi_volume_snapshot    ${csi_volume_snapshot_name}    ${claim_name}

Delete csi volume snapshot ${snapshot_id}
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${snapshot_id}
    ${longhorn_snapshot_name} =    get_longhorn_snapshot_name_associated_with_csi_volume_snapshot    ${csi_volume_snapshot_name}
    Set Test Variable    ${longhorn_snapshot_name}
    delete_csi_volume_snapshot    ${csi_volume_snapshot_name}

Wait for csi volume snapshot ${snapshot_id} to be ready
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${snapshot_id}
    wait_for_csi_volume_snapshot_to_be_ready    ${csi_volume_snapshot_name}

Delete CSI volume snapshot ${snapshot_id} forcibly
    ${csi_volume_snapshot_name} =    generate_name_with_suffix    csi-volume-snapshot    ${snapshot_id}
    force_delete_volumesnapshot    ${csi_volume_snapshot_name}
