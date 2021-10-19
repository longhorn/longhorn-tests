---
title: 1. Deployment of Longhorn
---

Installation
------------
Longhorn v1.1.2 and above - Support Kubernetes 1.18+

Longhorn v1.0.0 to v1.1.1 - Support Kubernetes 1.14+. Default 1.16+

1.  Install using Rancher Apps & MarketPlace App (Default)
    
2.  Install using Helm chart from [https://github.com/longhorn/longhorn/tree/master/chart](https://github.com/longhorn/longhorn/tree/master/chart)
    
3.  Install using YAML from [https://github.com/longhorn/longhorn/blob/master/deploy/longhorn.yaml](https://github.com/longhorn/longhorn/blob/master/deploy/longhorn.yaml)
    

Note: Longhorn UI can scale to multiple instances for HA purposes.

  

Uninstallation
--------------

Make sure all the CRDs and other resources are cleaned up, following the uninstallation instruction.
https://longhorn.io/docs/1.2.2/deploy/uninstall/

Customizable Default Settings
-----------------------------

[https://longhorn.io/docs/1.2.2/references/settings/](https://longhorn.io/docs/1.2.2/references/settings/)

Make sure the settings are updated if it’s the fresh installation of Longhorn.

Tests
----------------

| **S.No** | **Scenario** | **Steps** | **Expected Result**|
| --- | --- | --- | --- |
| 1   | Deploy Longhorn using Yaml | 1.  Create a k8s/k3s cluster with 3 workers nodes.<br>2.  Deploy Longhorn using the Yaml file available [https://github.com/longhorn/longhorn/blob/master/deploy/longhorn.yaml](https://github.com/longhorn/longhorn/blob/master/deploy/longhorn.yaml)  <br>    `kubectl apply -f [https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml](https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml)`<br>3.  Verify the app gets deployed successfully.  <br>    `kubectl get pods n longhorn system` | *  The below daemonset should be deployed successfully. <pre>engine-image-ei- , longhorn-csi-plugin, longhorn-manager</pre>*   The below deployment should be deployed successfully.  <pre>    csi-attacher, csi-provisioner, csi-resizer, csi-snapshotter, longhorn-driver-deployer, longhorn-ui</pre>*   The Instance-manager-e, Instance-manager-r pods should be deployed on the each worker node.<br>*   The below services should be deployed  <pre>    csi-attacher, csi-provisioner, csi-resizer, csi-snapshotter, longhorn-backend, longhorn-frontend</pre>*   The below crds should be deployed.  <br>    [backingimagedatasources.longhorn.io](http://backingimagedatasources.longhorn.io)  <br>    [backingimagemanagers.longhorn.io](http://backingimagemanagers.longhorn.io)  <br>    [backingimages.longhorn.io](http://backingimages.longhorn.io)  <br>    [backups.longhorn.io](http://backups.longhorn.io)  <br>    [backuptargets.longhorn.io](http://backuptargets.longhorn.io)  <br>    [backupvolumes.longhorn.io](http://backupvolumes.longhorn.io)  <br>    [engineimages.longhorn.io](http://engineimages.longhorn.io)  <br>    [engines.longhorn.io](http://engines.longhorn.io)  <br>    [instancemanagers.longhorn.io](http://instancemanagers.longhorn.io)  <br>    [nodes.longhorn.io](http://nodes.longhorn.io)  <br>    [recurringjobs.longhorn.io](http://recurringjobs.longhorn.io)  <br>    [replicas.longhorn.io](http://replicas.longhorn.io)  <br>    [settings.longhorn.io](http://settings.longhorn.io)  <br>    [sharemanagers.longhorn.io](http://sharemanagers.longhorn.io)  <br>    [volumes.longhorn.io](http://volumes.longhorn.io) |
| 2   | Deploy Longhorn using Helm chart | 1.  Create a k8s/k3s cluster with 3 workers nodes.<br>2.  As per the instructions [https://github.com/longhorn/longhorn/tree/master/chart](https://github.com/longhorn/longhorn/tree/master/chart) deploy the Longhorn app. | *  The below daemonset should be deployed successfully. <pre>engine-image-ei- , longhorn-csi-plugin, longhorn-manager</pre>*   The below deployment should be deployed successfully.  <pre>    csi-attacher, csi-provisioner, csi-resizer, csi-snapshotter, longhorn-driver-deployer, longhorn-ui</pre>*   The Instance-manager-e, Instance-manager-r pods should be deployed on the each worker node.<br>*   The below services should be deployed  <pre>    csi-attacher, csi-provisioner, csi-resizer, csi-snapshotter, longhorn-backend, longhorn-frontend</pre>*   The below crds should be deployed.  <br>    [backingimagedatasources.longhorn.io](http://backingimagedatasources.longhorn.io)  <br>    [backingimagemanagers.longhorn.io](http://backingimagemanagers.longhorn.io)  <br>    [backingimages.longhorn.io](http://backingimages.longhorn.io)  <br>    [backups.longhorn.io](http://backups.longhorn.io)  <br>    [backuptargets.longhorn.io](http://backuptargets.longhorn.io)  <br>    [backupvolumes.longhorn.io](http://backupvolumes.longhorn.io)  <br>    [engineimages.longhorn.io](http://engineimages.longhorn.io)  <br>    [engines.longhorn.io](http://engines.longhorn.io)  <br>    [instancemanagers.longhorn.io](http://instancemanagers.longhorn.io)  <br>    [nodes.longhorn.io](http://nodes.longhorn.io)  <br>    [recurringjobs.longhorn.io](http://recurringjobs.longhorn.io)  <br>    [replicas.longhorn.io](http://replicas.longhorn.io)  <br>    [settings.longhorn.io](http://settings.longhorn.io)  <br>    [sharemanagers.longhorn.io](http://sharemanagers.longhorn.io)  <br>    [volumes.longhorn.io](http://volumes.longhorn.io) | 
| 3   | Deploy Longhorn in Rancher | 1.  Create a k8s/k3s cluster with 3 workers nodes on Rancher cluster.<br>2.  Go to Apps and marketplace and deploy Longhorn with default values | *   The Longhorn and Longhorn CRDs should be installed as two packages.<br>*   The Longhorn app should start display on the cluster explorer.<br>*   The Link to access the Longhorn UI should work properly.<br>*   Verify all the components are available by clicking on the installed apps. |
