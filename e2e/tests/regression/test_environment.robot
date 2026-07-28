*** Settings ***
Documentation    Environment Test Cases

Test Tags    regression    environment

Resource    ../keywords/variables.resource
Resource    ../keywords/common.resource
Resource    ../keywords/setting.resource
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
    [Tags]    non-default-namespace
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
    And And Run command
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
    Then Run command in pod and expect output
    ...    ${instance_manager_pod}    ${LONGHORN_NAMESPACE}
    ...    nc -zv 127.0.0.1 8500
    ...    succeeded

    # Step 6: Install grpcurl inside the instance manager pod
    And Run command in pod
    ...    ${instance_manager_pod}    ${LONGHORN_NAMESPACE}
    ...    curl -fsSL https://github.com/fullstorydev/grpcurl/releases/download/v1.9.3/grpcurl_1.9.3_linux_x86_64.tar.gz | tar -xz -C /tmp && chmod +x /tmp/grpcurl

    # Step 7: Plaintext gRPC must be rejected
    ${random_suffix_1} =    Evaluate    __import__('uuid').uuid4().hex[:8]
    Run command in pod and expect output
    ...    ${instance_manager_pod}    ${LONGHORN_NAMESPACE}
    ...    /tmp/grpcurl -plaintext -connect-timeout 5 -d '{"spec":{"name":"pwn-${random_suffix_1}","binary":"/bin/bash","args":["-c","id"],"portCount":0}}' '[127.0.0.1]:8500' ProcessManagerService/ProcessCreate
    ...    context deadline exceeded

    # Step 8: Unauthenticated TLS (no client certificate) must be rejected
    ${random_suffix_2} =    Evaluate    __import__('uuid').uuid4().hex[:8]
    Run command in pod and expect output
    ...    ${instance_manager_pod}    ${LONGHORN_NAMESPACE}
    ...    /tmp/grpcurl -insecure -connect-timeout 5 -d '{"spec":{"name":"pwn-${random_suffix_2}","binary":"/bin/bash","args":["-c","id"],"portCount":0}}' '[127.0.0.1]:8500' ProcessManagerService/ProcessCreate
    ...    context deadline exceeded

    # Step 9: gRPC server presents a valid TLS certificate
    Run command in pod and expect output
    ...    ${instance_manager_pod}    ${LONGHORN_NAMESPACE}
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
