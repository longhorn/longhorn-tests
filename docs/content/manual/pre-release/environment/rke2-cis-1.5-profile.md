---
title: Test Longhorn Deployment on RKE2 with CIS-1.5 profile
---

## Related issue

https://github.com/longhorn/longhorn/issues/2292

Longhorn v1.1.1 should work on RKE2 with CIS-1.5 profile

## Scenario
1. Prepare 1 control plane node and 3 worker nodes
2. Install RKE2 with CIS-1.5 profile on 1 control plane node
```shell
sudo su -

systemctl disable firewalld
systemctl stop firewalld

curl -sfL https://get.rke2.io | sh -

systemctl enable rke2-server.service

cat << EOF > /etc/sysctl.d/60-rke2-cis.conf
vm.panic_on_oom=0
vm.overcommit_memory=1
kernel.panic=10
kernel.panic_on_oops=1
EOF
sudo systemctl restart systemd-sysctl

useradd -r -c "etcd user" -s /sbin/nologin -M etcd

mkdir -p /etc/rancher/rke2/
cat << EOF > /etc/rancher/rke2/config.yaml
profile: "cis-1.5"
EOF

systemctl start rke2-server.service

SERVER_NODE_TOKEN=`cat /var/lib/rancher/rke2/server/node-token`
```
3. Install RKE2 with CIS-1.5 profile on 3 worker nodes
```shell
sudo su -

systemctl disable firewalld
systemctl stop firewalld

curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" sh -

systemctl enable rke2-agent.service

cat << EOF > /etc/sysctl.d/60-rke2-cis.conf
vm.panic_on_oom=0
vm.overcommit_memory=1
kernel.panic=10
kernel.panic_on_oops=1
EOF
sudo systemctl restart systemd-sysctl

mkdir -p /etc/rancher/rke2/
cat << EOF > /etc/rancher/rke2/config.yaml
server: https://<CONTROL_PLANE_NODE_IP_ADDRESS>:9345
token: $SERVER_NODE_TOKEN
profile: "cis-1.5"
EOF

systemctl start rke2-agent.service
```

4. Test install Longhorn by helm without problem
```shell
helm repo add longhorn https://charts.longhorn.io
helm repo update

helm install longhorn/longhorn \
    --name longhorn \
    --namespace longhorn-system \
    --create-namespace
```
5. Prepare the longhorn-values.yaml
```yaml
ingress:
  enabled: true
  annotations:
    foo: bar
```
6. Test upgrade Longhorn by helm without problem
```shell
helm upgrade longhorn longhorn/longhorn \
    --namespace longhorn-system \
    --values longhorn-values.yaml
```
7. Test uninstall Longhorn by helm without problem
```shell
helm uninstall longhorn --namespace longhorn-system
```
8. Test install Longhorn by kubectl without problem
```shell
kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.1/deploy/longhorn.yaml
```
9. Test uninstall Longhorn by kubectl without problem
```shell
kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.1/uninstall/uninstall.yaml
kubectl delete -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.1/deploy/longhorn.yaml
kubectl delete -f https://raw.githubusercontent.com/longhorn/longhorn/v1.1.1/uninstall/uninstall.yaml
```
