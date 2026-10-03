*** Settings ***
Documentation    Environment Test Cases

Test Tags    regression    environment

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
Resource    ../keywords/volume.resource
Resource    ../keywords/host.resource
Resource    ../keywords/longhorn.resource
Resource    ../keywords/storageclass.resource
Resource    ../keywords/deployment.resource
Resource    ../keywords/persistentvolumeclaim.resource
Resource    ../keywords/workload.resource

Test Setup    Set up test environment
Test Teardown    Cleanup test resources

*** Test Cases ***
Test IPv4 Only Environment
    [Tags]    uninstall
    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    # add ipv6.disable=1 to GRUB_CMDLINE_LINUX
    # then update grub
    Given Run command on node    0
    ...    sudo sed -i 's/^GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="ipv6.disable=1 /' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    1
    ...    sudo sed -i 's/^GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="ipv6.disable=1 /' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    2
    ...    sudo sed -i 's/^GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="ipv6.disable=1 /' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    # reboot to make updated grub take effect
    And Restart all worker nodes

    When Install Longhorn
    Then Wait for Longhorn components all running

    # re-enable ipv6 by removing ipv6.disable=1 in GRUB_CMDLINE_LINUX
    # then update grub
    And Run command on node    0
    ...    sudo sed -i 's/ipv6\.disable=1 //g' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    1
    ...    sudo sed -i 's/ipv6\.disable=1 //g' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    And Run command on node    2
    ...    sudo sed -i 's/ipv6\.disable=1 //g' /etc/default/grub && sudo update-grub || sudo grub2-mkconfig -o /boot/grub2/grub.cfg
    # reboot to make reverted grub take effect
    And Restart all worker nodes
    And Wait for longhorn ready

Test RWX Fast Failover In Non-default Longhorn Namespace
    [Tags]    non-default-namespace    uninstall
    [Documentation]    Issue: https://github.com/longhorn/longhorn/issues/12244
    ${LONGHORN_INSTALL_METHOD}=    Get Environment Variable    LONGHORN_INSTALL_METHOD    default=manifest
    IF    '${LONGHORN_INSTALL_METHOD}' != 'manifest' and '${LONGHORN_INSTALL_METHOD}' != 'helm'
        Skip    Unsupported install method: ${LONGHORN_INSTALL_METHOD}
    END

    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed

    When Install Longhorn    longhorn_namespace=longhorn-custom
    And Wait for Longhorn components all running
    IF    '${DATA_ENGINE}' == 'v2'
        And Enable v2 data engine and add block disks
    END
    And Setting rwx-volume-fast-failover is set to true

    Then Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Wait for volume of deployment 0 healthy
    And Wait for deployment 0 pods stable
    And Write 128 MB data to file data.txt in deployment 0
    And Check deployment 0 data in file data.txt is intact

    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check Longhorn CRD removed
    And Install Longhorn
    And Wait for Longhorn components all running

Test mTLS Support
    [Tags]    uninstall
    [Documentation]    Verify that Longhorn instance manager enforces mTLS when the
    ...                longhorn-grpc-tls secret is present.
    ...
    ...                Issue: https://github.com/longhorn/longhorn/issues/7787
    ...
    ...                Steps:
    ...                1. Uninstall Longhorn.
    ...                2. Create the longhorn-grpc-tls secret from the upstream template.
    ...                3. Reinstall Longhorn.
    ...                4. Obtain an instance manager pod name on node 0.
    ...                5. Verify TCP port 8500 is reachable inside the pod.
    ...                6. Install grpcurl inside the instance manager pod.
    ...                7. Confirm plaintext (unencrypted) gRPC is rejected.
    ...                8. Confirm unauthenticated TLS (no client cert) is rejected.
    ...                9. Confirm the gRPC server presents a valid TLS certificate.
    ...                10. Create RWO and RWX workloads and verify data integrity.
    ...                11. uninstall mtls enable Lonhorn and reinstall normal Longhorn.

    # Step 1: Uninstall Longhorn
    Given Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed

    # Step 2: Create the longhorn-grpc-tls secret
    And Run command
    ...    kubectl create ns ${LONGHORN_NAMESPACE}
    And Run command
    ...    kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn-tests/refs/heads/master/test_framework/templates/longhorn-grpc-tls.yml

    # Step 3: Install Longhorn
    When Install Longhorn
    And Enable v2 data engine and add block disks
    And Wait for Longhorn components all running

    # Step 4: Get an instance manager pod on node 0
    ${instance_manager_pod} =    Get ${DATA_ENGINE} instance manager pod on node 0

    # Step 5: Verify TCP port 8500 is reachable
    Then Run command in pod ${LONGHORN_NAMESPACE}/${instance_manager_pod} and expect output
    ...    nc -zv 127.0.0.1 8500
    ...    succeeded

    # Step 6: Install grpcurl inside the instance manager pod
    And Run command in pod ${LONGHORN_NAMESPACE}/${instance_manager_pod}
    ...    curl -fsSL https://github.com/fullstorydev/grpcurl/releases/download/v1.9.3/grpcurl_1.9.3_linux_x86_64.tar.gz | tar -xz -C /tmp && chmod +x /tmp/grpcurl

    # Step 7: Plaintext gRPC must be rejected
    ${random_suffix_1} =    Evaluate    __import__('uuid').uuid4().hex[:8]
    Run command in pod ${LONGHORN_NAMESPACE}/${instance_manager_pod} and expect output
    ...    /tmp/grpcurl -plaintext -connect-timeout 5 -d '{"spec":{"name":"pwn-${random_suffix_1}","binary":"/bin/bash","args":["-c","id"],"portCount":0}}' '[127.0.0.1]:8500' ProcessManagerService/ProcessCreate
    ...    context deadline exceeded

    # Step 8: Unauthenticated TLS (no client certificate) must be rejected
    ${random_suffix_2} =    Evaluate    __import__('uuid').uuid4().hex[:8]
    Run command in pod ${LONGHORN_NAMESPACE}/${instance_manager_pod} and expect output
    ...    /tmp/grpcurl -insecure -connect-timeout 5 -d '{"spec":{"name":"pwn-${random_suffix_2}","binary":"/bin/bash","args":["-c","id"],"portCount":0}}' '[127.0.0.1]:8500' ProcessManagerService/ProcessCreate
    ...    context deadline exceeded

    # Step 9: gRPC server presents a valid TLS certificate
    Run command in pod ${LONGHORN_NAMESPACE}/${instance_manager_pod} and expect output
    ...    timeout 5 openssl s_client -connect 127.0.0.1:8500
    ...    CONNECTED.*subject=.*issuer=

    # Step 10: Workloads still function correctly under mTLS
    When Create storageclass longhorn-test with    dataEngine=${DATA_ENGINE}
    And Create persistentvolumeclaim 0    volume_type=RWO    sc_name=longhorn-test
    And Create persistentvolumeclaim 1    volume_type=RWX    sc_name=longhorn-test
    And Create deployment 0 with persistentvolumeclaim 0
    And Create deployment 1 with persistentvolumeclaim 1
    And Wait for volume of deployment 0 healthy
    And Wait for volume of deployment 1 healthy
    And Write 128 MB data to file data.txt in deployment 0
    And Write 128 MB data to file data.txt in deployment 1
    Then Check deployment 0 data in file data.txt is intact
    And Check deployment 1 data in file data.txt is intact

    # Step 11: Clean up — uninstall mtls enabled Longhorn and reinstall normal Longhorn
    And Setting deleting-confirmation-flag is set to true
    And Uninstall Longhorn
    And Check all Longhorn CRD removed
    And Install Longhorn
    And Wait for Longhorn components all running

Test Upgrade Responder Collects V2 Data Engine Info
    [Documentation]
    ...    Verify that the upgrade-responder checkupgrade payload collected by
    ...    Longhorn includes the v2 data engine metrics fields
    ...
    ...    Issues: https://github.com/longhorn/longhorn/issues/14027
    ...            https://github.com/longhorn/longhorn/issues/6033
    ...            https://github.com/longhorn/longhorn/issues/12941
    ...
    ...    Origin manual test:
    ...    docs/content/manual/release-specific/v1.6.0/test-upgrade-responder-collect-spdk-related-info.md
    ...
    ...    InfluxDB field keys verified under measurement "upgrade_request",
    ...    database "longhorn_upgrade_responder":
    ...      - longhorn_v2_data_engine_cpu_cores               (longhornV2DataEngineCpuCores)
    ...      - longhorn_v2_data_engine_hugepage_size            (longhornV2DataEngineHugepageSize)
    ...      - longhorn_v2_data_engine_hugepage_enabled         (longhornV2DataEngineHugepageEnabled)
    ...      - longhorn_v2_data_engine_interrupt_mode_enabled   (longhornV2DataEngineInterruptModeEnabled)
    ...      - longhorn_v2_data_engine_cpu_isolation_enabled    (longhornV2DataEngineCPUIsolationEnabled)
    ...      - longhorn_v2_data_engine_iobuf_small_pool_size    (longhornV2DataEngineIobufSmallPoolSize)
    ...      - longhorn_v2_data_engine_iobuf_large_pool_size    (longhornV2DataEngineIobufLargePoolSize)
    ...      - longhorn_v2_data_engine_number_of_cpu_cores      (longhornV2DataEngineNumberOfCPUCores)
    ...
    ...    Test steps:
    ...    1. Deploy the upgrade-responder stack locally by cloning the longhorn/longhorn
    ...       repository and running dev/upgrade-responder/install.sh, which stands up
    ...       upgrade-responder, influxdb, and grafana in the "default" namespace.
    ...    2. Set setting upgrade-responder-url to
    ...       http://longhorn-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade
    ...       so Longhorn's upgrade checker targets the local upgrade-responder instance.
    ...    3. Create a v2 volume.
    ...    4. Restart longhorn-manager pods to trigger an immediate check-upgrade request
    ...       instead of waiting for the hourly upgradeCheckInterval.
    ...    5. Poll the influxdb database until the check-upgrade payload is recorded.
    ...    6. Verify all longhorn_v2_data_engine_* fields listed above exist in the
    ...       influxdb database.
    ...    7. Verify longhorn_disk_block_count and longhorn_volume_backend_store_driver_v2_count
    ...       equals the number of v2 volumes created.
    IF    '${DATA_ENGINE}' == 'v1'
        Skip    Test only validate on v2 data engine
    END

    When Run command
    ...    rm -rf /tmp/longhorn-upgrade-responder-src && git clone --depth 1 https://github.com/longhorn/longhorn.git /tmp/longhorn-upgrade-responder-src
    ${install_output} =    Run command
    ...    cd /tmp/longhorn-upgrade-responder-src/dev/upgrade-responder && ./install.sh
    Should Contain    ${install_output}    Deployment longhorn-upgrade-responder is running.
    Should Contain    ${install_output}    Deployment influxdb is running.

    And Setting upgrade-responder-url is set to http://longhorn-upgrade-responder.default.svc.cluster.local:8314/v1/checkupgrade

    ${worker_nodes} =    get_worker_nodes
    ${expected_block_disk_count} =    Get Length    ${worker_nodes}

    And Create volume 0 with    dataEngine=v2

    And Rollout restart daemonset longhorn-manager in namespace longhorn-system

    ${influxdb_pod} =    Run command
    ...    kubectl get pod -n default -l app=influxdb -o jsonpath="{.items[0].metadata.name}"

    ${field_keys} =    Set Variable    ${EMPTY}
    FOR    ${i}    IN RANGE    ${RETRY_COUNT}
        ${field_keys} =    Run command
        ...    kubectl exec -n default ${influxdb_pod} -- influx -execute 'SHOW FIELD KEYS FROM upgrade_request' -database="longhorn_upgrade_responder"
        ${found} =    Run Keyword And Return Status
        ...    Should Contain    ${field_keys}    longhorn_v2_data_engine_number_of_cpu_cores
        IF    ${found}
            BREAK
        END
        Sleep    ${RETRY_INTERVAL}min
    END

    Then Should Contain    ${field_keys}    longhorn_disk_block_count
    # the value in longhorn_disk_block_count should equal to the number of volume using the V2 engine.
    And Run command and wait for output
    ...    kubectl exec -n default ${influxdb_pod} -- influx -execute 'SELECT "longhorn_disk_block_count" FROM "upgrade_request" ORDER BY time DESC LIMIT 1' -database="longhorn_upgrade_responder" | tail -n 1 | awk '{print $NF}'
    ...    1

    And Should Contain    ${field_keys}    longhorn_volume_data_engine_v2_count
    # the value in longhorn_volume_data_engine_v2_count should equal to the number of volume using the V2 engine.
    Run command and wait for output
    ...    kubectl exec -n default ${influxdb_pod} -- influx -execute 'SELECT "longhorn_volume_data_engine_v2_count" FROM "upgrade_request" ORDER BY time DESC LIMIT 1' -database="longhorn_upgrade_responder" | tail -n 1 | awk '{print $NF}'
    ...    1

    And Should Contain    ${field_keys}    longhorn_v2_data_engine_cpu_cores
    #And Should Contain    ${field_keys}    longhorn_v2_data_engine_interrupt_mode_enabled
    #And Should Contain    ${field_keys}    longhorn_v2_data_engine_cpu_isolation_enabled
    And Should Contain    ${field_keys}    longhorn_v2_data_engine_iobuf_small_pool_size
    And Should Contain    ${field_keys}    longhorn_v2_data_engine_iobuf_large_pool_size
    And Should Contain    ${field_keys}    longhorn_v2_data_engine_number_of_cpu_cores
    And Should Contain    ${field_keys}    longhorn_v2_data_engine_hugepage_size
    # longhorn_block_type_disk_driver could be one of the following values:
    # longhorn_block_type_disk_driver_aio_count,
    # longhorn_block_type_disk_driver_nvme_count,
    # longhorn_block_type_disk_driver_virtio_scsi_count,
    # longhorn_block_type_disk_driver_virtio_blk_count,
    # longhorn_block_type_disk_driver_virtio_pci_count
    And Should Contain    ${field_keys}    longhorn_block_type_disk_driver

    # longhorn_v2_data_engine_hugepage_enabled, longhorn_v2_data_engine_interrupt_mode_enabled and longhorn_v2_data_engine_cpu_isolation_enabled
    # are tags rather than fields
    And Run command and wait for output
    ...    kubectl exec -n default ${influxdb_pod} -- influx -execute 'SHOW TAG KEYS FROM upgrade_request' -database="longhorn_upgrade_responder" | grep longhorn_v2_data_engine_hugepage_enabled
    ...    longhorn_v2_data_engine_hugepage_enabled
    And Run command and wait for output
    ...    kubectl exec -n default ${influxdb_pod} -- influx -execute 'SHOW TAG KEYS FROM upgrade_request' -database="longhorn_upgrade_responder" | grep longhorn_v2_data_engine_interrupt_mode_enabled
    ...    longhorn_v2_data_engine_interrupt_mode_enabled
    And Run command and wait for output
    ...    kubectl exec -n default ${influxdb_pod} -- influx -execute 'SHOW TAG KEYS FROM upgrade_request' -database="longhorn_upgrade_responder" | grep longhorn_v2_data_engine_cpu_isolation_enabled
    ...    longhorn_v2_data_engine_cpu_isolation_enabled
