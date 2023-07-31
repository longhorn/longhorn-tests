---
title: Test Longhorn deployment on RKE2 v1.24- with CIS-1.6 profile
---

## Related issue

This test was created in response to [2292](https://github.com/longhorn/longhorn/issues/2292), which used CSI-1.5.
However, RKE2 generally does not recommend or encourage using CIS-1.5 in favor of CIS1.6.

## Scenario

1. Prepare 1 control plane node and 3 worker nodes.
2. Install RKE2 v1.24 with CIS-1.6 profile on 1 control plane node.

```shell
sudo su -

systemctl disable firewalld # On a supporting OS.
systemctl stop firewalld # On a supporting OS.

yum install iscsi-initiator-utils # Or the OS equivalent.
systemctl enable --now iscsid

curl -sfL https://get.rke2.io | INSTALL_RKE2_CHANNEL=v1.24 sh -

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
profile: "cis-1.6"
EOF

systemctl start rke2-server.service

SERVER_NODE_TOKEN=`cat /var/lib/rancher/rke2/server/node-token`
```

3. Install RKE2 v1.24 with CIS-1.6 profile on 3 worker nodes.

```shell
sudo su -

systemctl disable firewalld # On a supporting OS.
systemctl stop firewalld # On a supporting OS.

yum install iscsi-initiator-utils # Or the OS equivalent.
systemctl enable --now iscsid

curl -sfL https://get.rke2.io | INSTALL_RKE2_CHANNEL=v1.24 INSTALL_RKE2_TYPE="agent" sh -

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
server: https://$CONTROL_PLANE_NODE_IP_ADDRESS:9345
token: $SERVER_NODE_TOKEN
profile: "cis-1.6"
EOF

systemctl start rke2-agent.service
```

4. Prepare the `longhorn-values.yaml`.

```yaml
enablePSP: true
```

5. Test install Longhorn by helm without problem. (These commands assume a pre-release chart. When testing a released
chart, use `helm repo add` etc.)

```shell
git clone https://github.com/longhorn/longhorn.git
cd longhorn
git checkout $VERSION_TO_TEST

helm install --namespace longhorn-system longhorn ./chart
```

6. Prepare the `longhorn-values.yaml` again.

```yaml
enablePSP: true
ingress:
  enabled: true
  annotations:
    foo: bar
```

7. Test upgrade Longhorn by helm without problem.

```shell
helm upgrade --namespace longhorn-system --values longhorn-values.yaml longhorn ./chart
```

8. Verify the upgrade "worked" by checking for the deployed ingress.

```shell
kubectl get ingress -n longhorn-system
```

9. Test uninstall Longhorn by helm without problem.

```shell
helm uninstall longhorn --namespace longhorn-system
```

10. Test install Longhorn by kubectl without problem.

```shell
kubectl apply -f deploy/podsecuritypolicy.yaml
kubectl apply -f deploy/longhorn.yaml
```

11. Uncomment all Pod Security Policy related lines from deploy/uninstall.yaml.

12. Test uninstall Longhorn by kubectl without problem.

```shell
kubectl apply -f uninstall/uninstall.yaml
kubectl delete -f deploy/longhorn.yaml
kubectl delete -f uninstall/uninstall.yaml
```
