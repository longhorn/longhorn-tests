---
title: Setup and test storage network when Multus version is above v4.0.0
---

## Related issue
https://github.com/longhorn/longhorn/issues/6953

## Test storage network

### Create AWS instances
**Given** Create VPC.
- VPC only
- IPv4 CIDR 10.0.0.0/16

*And* Create an internet gateway.
- Attach to VPC

*And* Add the internet gateway to the VPC `Main route table`, `Routes`.
- Destination 0.0.0.0/0

*And* Create 2 subnets in the VPC.
- Subnet-1: 10.0.1.0/24
- Subnet-2: 10.0.2.0/24

*And* Launch 3 EC2 instances.
- Use the created VPC
- Use subnet-1 for network interface 1
- Use subnet-2 for network interface 2
- Disable `Auto-assign public IP`
- Add security group inbound rule to allow `All traffic` from `Anywhere-IPv4`
- Stop `Source/destination check`

*And* Create 3 elastic IPs.

*And* Associate one of the elastic IP to one of the EC2 instance network interface 1.
- Repeat for the other 2 EC2 instances with the remain elastic IPs.


### Setup instances

#### Thin Plugin

**Given** K3s K8s cluster installed on EC2 instances.

*And* Deploy Multus DaemonSet on the control-plane node.
- Download YAML.
  ```
  curl -O https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/v4.0.2/deployments/multus-daemonset.yml
  ```
- Edit YAML.
  ```
  diff --git a/deployments/multus-daemonset.yml b/deployments/multus-daemonset.yml
  index ab626a66..a7228942 100644
  --- a/deployments/multus-daemonset.yml
  +++ b/deployments/multus-daemonset.yml
  @@ -145,7 +145,7 @@ data:
             ]
           }
         ],
  -      "kubeconfig": "/etc/cni/net.d/multus.d/multus.kubeconfig"
  +      "kubeconfig": "/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d/multus.kubeconfig"
       }
   ---
   apiVersion: apps/v1
  @@ -179,12 +179,13 @@ spec:
         serviceAccountName: multus
         containers:
         - name: kube-multus
  -        image: ghcr.io/k8snetworkplumbingwg/multus-cni:snapshot
  +        image: ghcr.io/k8snetworkplumbingwg/multus-cni:v4.0.2
           command: ["/thin_entrypoint"]
           args:
           - "--multus-conf-file=auto"
           - "--multus-autoconfig-dir=/host/etc/cni/net.d"
           - "--cni-conf-dir=/host/etc/cni/net.d"
  +        - "--multus-kubeconfig-file-host=/var/lib/rancher/k3s/agent/etc/cni/net.d/multus.d/multus.kubeconfig"
           resources:
             requests:
               cpu: "100m"
  @@ -222,10 +223,10 @@ spec:
         volumes:
           - name: cni
             hostPath:
  -            path: /etc/cni/net.d
  +            path: /var/lib/rancher/k3s/agent/etc/cni/net.d
           - name: cnibin
             hostPath:
  -            path: /opt/cni/bin
  +            path: /var/lib/rancher/k3s/data/current/bin
           - name: multus-cfg
             configMap:
               name: multus-cni-config
  ```
- Apply YAML to K8s cluster.
  ```
  kubectl apply -f multus-daemonset.yml.new
  ```

*And* Download `ipvlan` and put to K3s binaries path to all cluster nodes.
```
curl -OL https://github.com/containernetworking/plugins/releases/download/v1.3.0/cni-plugins-linux-amd64-v1.3.0.tgz
tar -zxvf cni-plugins-linux-amd64-v1.3.0.tgz
cp ipvlan /var/lib/rancher/k3s/data/current/bin/
```

*And* Setup flannels on all cluster nodes.
```
# Update nodes eth1 IP to N1, N2, N3
N1="10.0.2.95"
N2="10.0.2.139"
N3="10.0.2.158"
NODES=(${N1} ${N2} ${N3})

STORAGE_NETWORK_PREFIX="192.168"

ETH1_IP=`ip a | grep eth1 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*'  | awk '{print $2}'`

count=1
for n in "${NODES[@]}"; do
    [[ ${ETH1_IP} != $n ]] && ((count=count+1)) && continue

    NET=$count
    break
done

cat << EOF > /run/flannel/multus-subnet-${STORAGE_NETWORK_PREFIX}.0.0.env
FLANNEL_NETWORK=${STORAGE_NETWORK_PREFIX}.0.0/16
FLANNEL_SUBNET=${STORAGE_NETWORK_PREFIX}.${NET}.0/24
FLANNEL_MTU=1472
FLANNEL_IPMASQ=true
EOF
```
*And* Setup routes on all cluster nodes.
```
# Update nodes eth1 IP to N1, N2, N3
N1="10.0.2.95"
N2="10.0.2.139"
N3="10.0.2.158"

STORAGE_NETWORK_PREFIX="192.168"
ACTION="add"

ETH1_IP=`ip a | grep eth1 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*'  | awk '{print $2}'`

[[ ${ETH1_IP} != ${N1} ]] && ip r ${ACTION} ${STORAGE_NETWORK_PREFIX}.1.0/24 via ${N1} dev eth1
[[ ${ETH1_IP} != ${N2} ]] && ip r ${ACTION} ${STORAGE_NETWORK_PREFIX}.2.0/24 via ${N2} dev eth1
[[ ${ETH1_IP} != ${N3} ]] && ip r ${ACTION} ${STORAGE_NETWORK_PREFIX}.3.0/24 via ${N3} dev eth1
```

*And* Deploy `NetworkAttachmentDefinition`.
```
cat << EOF > nad-192-168-0-0.yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: demo-192-168-0-0
  namespace: kube-system
  #namespace: longhorn-system
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
```


#### Thick Plugin

**Given** K3s K8s cluster installed on EC2 instances.

*And* (For K3s) Establish symbolic links on all cluster nodes.
  ```bash
  ln -s /var/lib/rancher/k3s/agent/etc/cni/net.d /etc/cni
  ln -s /var/lib/rancher/k3s/data/current/bin /opt/cni
  ```

*And* Deploy Multus DaemonSet on the control-plane node.
- Download YAML.
  ```
  curl -O https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/v4.0.2/deployments/multus-daemonset-thick.yml
  ```
- Edit YAML.
  ```
  diff --git a/deployments/multus-daemonset-thick.yml b/deployments/multus-daemonset-thick.yml
  index eaa92ece..c895651b 100644
  --- a/deployments/multus-daemonset-thick.yml
  +++ b/deployments/multus-daemonset-thick.yml
  @@ -152,7 +152,7 @@ spec:
         serviceAccountName: multus
         containers:
           - name: kube-multus
  -          image: ghcr.io/k8snetworkplumbingwg/multus-cni:snapshot-thick
  +          image: ghcr.io/k8snetworkplumbingwg/multus-cni:v4.0.2-thick
             command: [ "/usr/src/multus-cni/bin/multus-daemon" ]
             resources:
               requests:
  @@ -183,9 +183,11 @@ spec:
               - name: hostroot
                 mountPath: /hostroot
                 mountPropagation: HostToContainer
  +            - name: cnibin
  +              mountPath: /opt/cni/bin
         initContainers:
           - name: install-multus-binary
  -          image: ghcr.io/k8snetworkplumbingwg/multus-cni:snapshot-thick
  +          image: ghcr.io/k8snetworkplumbingwg/multus-cni:v4.0.2-thick
             command:
               - "cp"
               - "/usr/src/multus-cni/bin/multus-shim"
  ```
- Apply YAML to K8s cluster.
  ```
  kubectl apply -f multus-daemonset-thick.yml
  ```

*And* Download `ipvlan` and put to K3s binaries path to all cluster nodes.
```
curl -OL https://github.com/containernetworking/plugins/releases/download/v1.3.0/cni-plugins-linux-amd64-v1.3.0.tgz
tar -zxvf cni-plugins-linux-amd64-v1.3.0.tgz
cp ipvlan /var/lib/rancher/k3s/data/current/bin/
```

*And* Setup flannels on all cluster nodes.
```
# Update nodes eth1 IP to N1, N2, N3
N1="10.0.2.95"
N2="10.0.2.139"
N3="10.0.2.158"
NODES=(${N1} ${N2} ${N3})

STORAGE_NETWORK_PREFIX="192.168"

ETH1_IP=`ip a | grep eth1 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*'  | awk '{print $2}'`

count=1
for n in "${NODES[@]}"; do
    [[ ${ETH1_IP} != $n ]] && ((count=count+1)) && continue

    NET=$count
    break
done

cat << EOF > /run/flannel/multus-subnet-${STORAGE_NETWORK_PREFIX}.0.0.env
FLANNEL_NETWORK=${STORAGE_NETWORK_PREFIX}.0.0/16
FLANNEL_SUBNET=${STORAGE_NETWORK_PREFIX}.${NET}.0/24
FLANNEL_MTU=1472
FLANNEL_IPMASQ=true
EOF
```
*And* Setup routes on all cluster nodes.
```
# Update nodes eth1 IP to N1, N2, N3
N1="10.0.2.95"
N2="10.0.2.139"
N3="10.0.2.158"

STORAGE_NETWORK_PREFIX="192.168"
ACTION="add"

ETH1_IP=`ip a | grep eth1 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*'  | awk '{print $2}'`

[[ ${ETH1_IP} != ${N1} ]] && ip r ${ACTION} ${STORAGE_NETWORK_PREFIX}.1.0/24 via ${N1} dev eth1
[[ ${ETH1_IP} != ${N2} ]] && ip r ${ACTION} ${STORAGE_NETWORK_PREFIX}.2.0/24 via ${N2} dev eth1
[[ ${ETH1_IP} != ${N3} ]] && ip r ${ACTION} ${STORAGE_NETWORK_PREFIX}.3.0/24 via ${N3} dev eth1
```

*And* Deploy `NetworkAttachmentDefinition`.
```
cat << EOF > nad-192-168-0-0.yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: demo-192-168-0-0
  namespace: kube-system
  #namespace: longhorn-system
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
```


### Test storage network
**Given** Longhorn deployed.

**When** Update storage network setting value to `kube-system/demo-192-168-0-0`.

**Then** Instance manager pods should restart.

*And* Should have storage network in `k8s.v1.cni.cncf.io/network-status` instance manager pods annotations.
- Should have 2 network in `k8s.v1.cni.cncf.io/network-status` annotation
- `kube-system/demo-192-168-0-0` should exist in `k8s.v1.cni.cncf.io/network-status` annotation
- `kube-system/demo-192-168-0-0` should use `lhnet1` interface.
- `kube-system/demo-192-168-0-0` should be in `192.168.0.0/16` subnet.
*And* Should be able to create/attach/detach/delete volumes successfully.
- Example:
  ```
  Annotations:  k8s.v1.cni.cncf.io/network-status:
                  [{
                      "name": "cbr0",
                      "interface": "eth0",
                      "ips": [
                          "10.42.2.35"
                      ],
                      "mac": "26:a7:d3:0d:af:68",
                      "default": true,
                      "dns": {}
                  },{
                      "name": "kube-system/demo-192-168-0-0",
                      "interface": "lhnet1",
                      "ips": [
                          "192.168.2.230"
                      ],
                      "mac": "02:d3:d9:0b:2e:50",
                      "dns": {}
                  }]
                k8s.v1.cni.cncf.io/networks: [{"namespace": "kube-system", "name": "demo-192-168-0-0", "interface": "lhnet1"}]
  ```
- Should see engine/replica `storageIP` in `192.168.0.0` subnet.
