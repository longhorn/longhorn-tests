---
title: Test Instance Manager IP Sync
---


## Test step:
1. Launch longhorn system
2. Create and attach a volume
3. Follow this [doc](https://github.com/longhorn/longhorn/wiki/dev:-How-to-modify-the-status-subresource-with-%60kubectl-edit%60-(CRD)) to manually modify the IP of one instance-manager-r. e.g., 
    ```
    curl -k -XPATCH -H "Accept: application/json" -H "Content-Type: application/merge-patch+json" -H "Authorization: Bearer kubeconfig-xxxxxx" --data '{"status":{"ip":"1.1.1.1"}}' https://172.104.72.64/k8s/clusters/c-znrxc/apis/longhorn.io/v1beta1/namespaces/longhorn-system/instancemanagers/instance-manager-r-63ece607/status
    ```
    1. Notice that the bearer token `kubeconfig-xxx` can be found in your kube config file
    2. Remember to add `/status` at the end of the URL
4. Verify the IP of the instance manager still matches the pod IP
5. Verify the volume can be detached.
