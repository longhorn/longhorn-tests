deploy_multus_thin_plugin_daemonset(){
  curl -O "https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/${TF_VAR_multus_version}/deployments/multus-daemonset.yml"
  sed -Ei 's@"kubeconfig":.+@"kubeconfig": "/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d/multus.kubeconfig"@g' multus-daemonset.yml
  yq e -i 'select(.kind == "DaemonSet" and .metadata.name == "kube-multus-ds").spec.template.spec.containers[0].args += "--multus-kubeconfig-file-host=/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d/multus.kubeconfig"' multus-daemonset.yml
  yq e -i "select(.kind == \"DaemonSet\" and .metadata.name == \"kube-multus-ds\").spec.template.spec.containers[0].image=\"ghcr.io/k8snetworkplumbingwg/multus-cni:${TF_VAR_multus_version}\"" multus-daemonset.yml
  yq e -i "select(.kind == \"DaemonSet\" and .metadata.name == \"kube-multus-ds\").spec.template.spec.initContainers[0].image=\"ghcr.io/k8snetworkplumbingwg/multus-cni:${TF_VAR_multus_version}\"" multus-daemonset.yml
  sed -Ei 's@path: /etc/cni/net.d@path: /var/lib/rancher/k3s/agent/etc/cni/net.d@g' multus-daemonset.yml
  sed -Ei 's@path: /opt/cni/bin@path: /var/lib/rancher/k3s/data/current/bin@g' multus-daemonset.yml
  kubectl apply -f multus-daemonset.yml
}

deploy_multus_thick_plugin_daemonset(){
  curl -O https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/v4.0.2/deployments/multus-daemonset-thick.yml
  yq e -i 'select(.kind == "DaemonSet" and .metadata.name == "kube-multus-ds").spec.template.spec.containers[0].volumeMounts += {"name": "cnibin", "mountPath": "/opt/cni/bin"}' multus-daemonset-thick.yml
  yq e -i "select(.kind == \"DaemonSet\" and .metadata.name == \"kube-multus-ds\").spec.template.spec.containers[0].image=\"ghcr.io/k8snetworkplumbingwg/multus-cni:${TF_VAR_multus_version}-thick\"" multus-daemonset-thick.yml
  yq e -i "select(.kind == \"DaemonSet\" and .metadata.name == \"kube-multus-ds\").spec.template.spec.initContainers[0].image=\"ghcr.io/k8snetworkplumbingwg/multus-cni:${TF_VAR_multus_version}-thick\"" multus-daemonset-thick.yml
  kubectl apply -f multus-daemonset-thick.yml
}

deploy_network_attachment_definition(){
cat << EOF > nad-192-168-0-0.yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: demo-192-168-0-0
  namespace: kube-system
spec:
  config: '{
      "cniVersion": "0.3.1",
      "type": "flannel",
      "subnetFile": "/run/flannel/multus-subnet-192.168.0.0.env",
      "dataDir": "/var/lib/cni/multus-subnet-192.168.0.0",
      "delegate": {
        "type": "ipvlan",
        "master": "eth1",
        "mode": "l3",
          "capabilities": {
            "ips": true
        }
      },
      "kubernetes": {
          "kubeconfig": "/etc/cni/net.d/multus.d/multus.kubeconfig"
      }
    }'
EOF
kubectl apply -f nad-192-168-0-0.yaml
}


update_storage_network_setting(){
  kubectl -n longhorn-system patch -p '{"value": "kube-system/demo-192-168-0-0"}' --type=merge setting.longhorn.io/storage-network
}