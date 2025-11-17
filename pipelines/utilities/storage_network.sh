#!/bin/bash

set -x

source pipelines/utilities/longhorn_status.sh

if [[ "${TF_VAR_network_stack}" == "ipv6" ]]; then
  NAD_NAME="demo-fd00-168-0-0"
else
  NAD_NAME="demo-192-168-0-0"
fi

echo "Using NAD: $NAD_NAME"

create_nad_without_storage_network(){
  kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/v4.0.2/deployments/multus-daemonset.yml
  kubectl apply -f - <<EOF
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: demo-172-16-0-0
  namespace: kube-system
spec:
  config: '{"cniVersion":"0.3.1","type":"cluster"}'
EOF
}

deploy_multus_thin_plugin_daemonset(){
  curl -O "https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/${TF_VAR_multus_version}/deployments/multus-daemonset.yml"
  sed -Ei 's@"kubeconfig":.+@"kubeconfig": "/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d/multus.kubeconfig"@g' multus-daemonset.yml
  yq e -i 'select(.kind == "DaemonSet" and .metadata.name == "kube-multus-ds").spec.template.spec.containers[0].args += "--multus-kubeconfig-file-host=/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d/multus.kubeconfig"' multus-daemonset.yml
  yq e -i "select(.kind == \"DaemonSet\" and .metadata.name == \"kube-multus-ds\").spec.template.spec.containers[0].image=\"ghcr.io/k8snetworkplumbingwg/multus-cni:${TF_VAR_multus_version}\"" multus-daemonset.yml
  yq e -i "select(.kind == \"DaemonSet\" and .metadata.name == \"kube-multus-ds\").spec.template.spec.initContainers[0].image=\"ghcr.io/k8snetworkplumbingwg/multus-cni:${TF_VAR_multus_version}\"" multus-daemonset.yml
  sed -Ei 's@path: /etc/cni/net.d@path: /var/lib/rancher/k3s/agent/etc/cni/net.d@g' multus-daemonset.yml
  sed -Ei 's@path: /opt/cni/bin@path: /var/lib/rancher/k3s/data/cni@g' multus-daemonset.yml
  kubectl apply -f multus-daemonset.yml
}

deploy_multus_thick_plugin_daemonset(){
  curl -O https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/v4.0.2/deployments/multus-daemonset-thick.yml
  sed -Ei '/"logLevel":/a\        "logFile": "/var/log/multus.log",\n        "kubeconfig": "/var/lib/rancher/k3s/agent/kubelet.kubeconfig",' multus-daemonset-thick.yml
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

cat << EOF > nad-fd00-168-0-0.yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: demo-fd00-168-0-0
  namespace: kube-system
spec:
  config: '{
      "cniVersion": "0.3.1",
      "type": "flannel",
      "subnetFile": "/run/flannel/multus-subnet-fd00:168.0.0.env",
      "dataDir": "/var/lib/cni/multus-subnet-fd00.168.0.0",
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
kubectl apply -f nad-fd00-168-0-0.yaml

# for testing endpoint-network-for-rwx-volume
# create a second nad that reuses the same flannel overlay as nad1
# just with a different nad name
cat << EOF > nad-172-16-0-0.yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: demo-172-16-0-0
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
kubectl apply -f nad-172-16-0-0.yaml

cat << EOF > nad-fd00-172-16-0.yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: demo-fd00-172-16-0
  namespace: kube-system
spec:
  config: '{
      "cniVersion": "0.3.1",
      "type": "flannel",
      "subnetFile": "/run/flannel/multus-subnet-fd00:168.0.0.env",
      "dataDir": "/var/lib/cni/multus-subnet-fd00.168.0.0",
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
kubectl apply -f nad-fd00-172-16-0.yaml
}

update_storage_network_setting(){
  kubectl -n longhorn-system patch -p "{\"value\": \"kube-system/${NAD_NAME}\"}" --type=merge setting.longhorn.io/storage-network
}

validate_storage_network_setting_taking_effect(){
  kubectl get pods -n longhorn-system -l longhorn.io/component=instance-manager -oyaml | yq '.items[0].metadata'

  kubectl get pods -n longhorn-system -l longhorn.io/component=instance-manager -oyaml | yq '.items[0].metadata' | grep 'k8s.v1.cni.cncf.io/network-status'
  if [ $? -ne 0 ]; then
    echo "No k8s.v1.cni.cncf.io/network-status annotation found"
    exit 1
  fi

  kubectl get pods -n longhorn-system -l longhorn.io/component=instance-manager -oyaml | yq '.items[0].metadata' | grep "kube-system/${NAD_NAME}"
  if [ $? -ne 0 ]; then
    echo "No kube-system/${NAD_NAME} network attachment definition found"
    exit 1
  fi

  kubectl get pods -n longhorn-system -l longhorn.io/component=instance-manager -oyaml | yq '.items[0].metadata' | grep "k8s.v1.cni.cncf.io/networks: '\[{\"namespace\": \"kube-system\", \"name\": \"${NAD_NAME}\", \"interface\": \"lhnet1\"}\]'"
  if [ $? -ne 0 ]; then
    echo "No network with lhnet1 interface found"
    exit 1
  fi
}

enable_storage_network_setting(){
  LONGHORN_NAMESPACE="longhorn-system"
  update_storage_network_setting
  wait_longhorn_status_running
  validate_storage_network_setting_taking_effect
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  if declare -f "$1" > /dev/null; then
    "$@"
  else
    echo "Function '$1' not found"
    exit 1
  fi
fi
