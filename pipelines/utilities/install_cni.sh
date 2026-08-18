install_k3s_cni(){
  case "${TF_VAR_cni:-default}" in
    default)
      return 0
      ;;
    calico)
      install_k3s_calico
      ;;
    cilium)
      install_k3s_cilium
      ;;
    *)
      echo "Unsupported K3s CNI: ${TF_VAR_cni}" >&2
      return 1
      ;;
  esac
}

install_k3s_calico(){
  local calico_work_dir
  local calico_manifest
  local enable_ipv4=true
  local enable_ipv6=false
  local ipv4_pool_cidr=10.42.0.0/16
  local ipv6_pool_cidr=

  if [[ "${TF_VAR_network_stack:-ipv4}" == "ipv6" ]]; then
    enable_ipv4=false
    enable_ipv6=true
    ipv4_pool_cidr=none
    ipv6_pool_cidr=fd00:10::/56
  fi

  calico_work_dir=$(mktemp -d)
  calico_manifest="${calico_work_dir}/calico.yaml"

  curl -fsSL -o "${calico_manifest}" \
    https://raw.githubusercontent.com/projectcalico/calico/v3.32.0/manifests/calico.yaml || { rm -rf "${calico_work_dir}"; return 1; }

  if [[ "$(yq 'select(.kind == "ConfigMap" and .metadata.name == "calico-config") | .metadata.name' "${calico_manifest}")" != "calico-config" ]]; then
    echo "Calico config map is missing from the manifest" >&2
    rm -rf "${calico_work_dir}"
    return 1
  fi
  if [[ "$(yq 'select(.kind == "DaemonSet" and .metadata.name == "calico-node") | .metadata.name' "${calico_manifest}")" != "calico-node" ]]; then
    echo "Calico node daemon set is missing from the manifest" >&2
    rm -rf "${calico_work_dir}"
    return 1
  fi

  export CALICO_ENABLE_IPV4="${enable_ipv4}"
  export CALICO_ENABLE_IPV6="${enable_ipv6}"
  export CALICO_IPV4POOL_CIDR="${ipv4_pool_cidr}"
  export CALICO_IPV6POOL_CIDR="${ipv6_pool_cidr}"

  yq -i '
    with(select(.kind == "ConfigMap" and .metadata.name == "calico-config");
      .data.cni_network_config |= (
        sub("__CNI_MTU__", "\"__CNI_MTU__\"") |
        from_json |
        .plugins[0].container_settings.allow_ip_forwarding = true |
        .plugins[0].ipam.assign_ipv4 = strenv(CALICO_ENABLE_IPV4) |
        .plugins[0].ipam.assign_ipv6 = strenv(CALICO_ENABLE_IPV6) |
        to_json |
        sub("\"__CNI_MTU__\"", "__CNI_MTU__")
      )
    ) |
    with(select(.kind == "DaemonSet" and .metadata.name == "calico-node");
      (.spec.template.spec.containers[] | select(.name == "calico-node") | .env) += [
        {"name": "CALICO_IPV4POOL_CIDR", "value": strenv(CALICO_IPV4POOL_CIDR)}
      ] |
      (.spec.template.spec.containers[] | select(.name == "calico-node") | .env[] | select(.name == "FELIX_IPV6SUPPORT") | .value) = strenv(CALICO_ENABLE_IPV6)
    )
  ' "${calico_manifest}" || { rm -rf "${calico_work_dir}"; return 1; }

  if [[ "${enable_ipv6}" == "true" ]]; then
    yq -i '
      with(select(.kind == "DaemonSet" and .metadata.name == "calico-node");
        (.spec.template.spec.containers[] | select(.name == "calico-node") | .env) += [
          {"name": "IP6", "value": "autodetect"},
          {"name": "CALICO_IPV6POOL_CIDR", "value": strenv(CALICO_IPV6POOL_CIDR)},
          {"name": "CALICO_IPV6POOL_NAT_OUTGOING", "value": "true"}
        ] |
        (.spec.template.spec.containers[] | select(.name == "calico-node") | .env[] | select(.name == "CALICO_IPV6POOL_VXLAN") | .value) = "Always"
      )
    ' "${calico_manifest}" || { rm -rf "${calico_work_dir}"; return 1; }
  fi

  kubectl apply -f "${calico_manifest}" || { rm -rf "${calico_work_dir}"; return 1; }
  if [[ "${enable_ipv6}" == "true" ]]; then
    # Calico v3.32 ignores CALICO_IPV6POOL_VXLAN when the IPv4 pool is disabled.
    local retry=0
    local max_retry=24
    until kubectl get ippool.crd.projectcalico.org/default-ipv6-ippool >/dev/null 2>&1; do
      if [[ "${retry}" -ge "${max_retry}" ]]; then
        echo "Timed out waiting for the default Calico IPv6 IPPool" >&2
        rm -rf "${calico_work_dir}"
        return 1
      fi
      retry=$((retry + 1))
      sleep 5
    done
    kubectl patch ippool.crd.projectcalico.org/default-ipv6-ippool \
      --type=merge -p '{"spec":{"vxlanMode":"Always"}}' || { rm -rf "${calico_work_dir}"; return 1; }
  fi
  rm -rf "${calico_work_dir}"
}

install_k3s_cilium(){
  local enable_ipv4=true
  local enable_ipv6=false
  local underlay_protocol=ipv4

  if [[ "${TF_VAR_network_stack:-ipv4}" == "ipv6" ]]; then
    enable_ipv4=false
    enable_ipv6=true
    underlay_protocol=ipv6
  fi

  helm upgrade --install cilium oci://quay.io/cilium/charts/cilium \
    --version 1.19.5 \
    --set operator.replicas=1 \
    --set underlayProtocol="${underlay_protocol}" \
    --set hostFirewall.enabled=false \
    --set endpointRoutes.enabled=true \
    --set ipam.mode=kubernetes \
    --set ipv4.enabled="${enable_ipv4}" \
    --set ipv6.enabled="${enable_ipv6}" \
    --set k8s.requireIPv4PodCIDR="${enable_ipv4}" \
    --set k8s.requireIPv6PodCIDR="${enable_ipv6}" \
    --namespace kube-system \
    --wait \
    --timeout 10m
}

wait_for_cluster_nodes_registered(){
  local expected_nodes
  local node_count
  local retry=0
  local max_retry=120

  expected_nodes=$((${TF_VAR_lh_aws_instance_count_controlplane:-1} + ${TF_VAR_lh_aws_instance_count_worker:-3}))
  while true; do
    node_count=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
    if [[ "${node_count}" -ge "${expected_nodes}" ]]; then
      break
    fi
    if [[ "${retry}" -ge "${max_retry}" ]]; then
      echo "Timed out waiting for ${expected_nodes} nodes to register" >&2
      return 1
    fi
    retry=$((retry + 1))
    echo "Waiting for ${expected_nodes} nodes to register (${node_count}/${expected_nodes})"
    sleep 5
  done
}

wait_for_k3s_cni(){
  case "${TF_VAR_cni:-default}" in
    calico)
      kubectl rollout status daemonset/calico-node -n kube-system --timeout=10m || return 1
      kubectl rollout status deployment/calico-kube-controllers -n kube-system --timeout=10m || return 1
      ;;
    cilium)
      kubectl rollout status daemonset/cilium -n kube-system --timeout=10m || return 1
      kubectl rollout status deployment/cilium-operator -n kube-system --timeout=10m || return 1
      if kubectl get daemonset/cilium-envoy -n kube-system >/dev/null 2>&1; then
        kubectl rollout status daemonset/cilium-envoy -n kube-system --timeout=10m || return 1
      fi
      ;;
  esac
}

wait_for_cluster_nodes_ready(){
  kubectl wait --for=condition=Ready nodes --all --timeout=10m
}

setup_k3s_cni(){
  if [[ "${TF_VAR_network_stack:-ipv4}" == "ipv6" && "${DISTRO}" != "sles" ]]; then
    echo "IPv6 K3s CNI provisioning is supported only on SLES" >&2
    return 1
  fi

  install_k3s_cni || return 1
  wait_for_cluster_nodes_registered || return 1
  wait_for_k3s_cni || return 1
  wait_for_cluster_nodes_ready || return 1
}

setup_rke2_cni(){
  # RKE2 installs the configured CNI; this only verifies cluster readiness.
  wait_for_cluster_nodes_registered || return 1
  wait_for_cluster_nodes_ready || return 1
}

setup_cni(){
  if [[ "${LONGHORN_TEST_CLOUDPROVIDER}" != "aws" ]]; then
    return 0
  fi

  case "${TF_VAR_k8s_distro_name}" in
    k3s)
      setup_k3s_cni
      ;;
    rke2)
      setup_rke2_cni
      ;;
    *)
      return 0
      ;;
  esac
}
