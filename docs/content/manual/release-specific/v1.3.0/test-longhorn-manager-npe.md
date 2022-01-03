---
title: Test longhorn manager NPE caused by backup creation 
---

### Test step
1. Add the following rule to the ClusterRole `longhorn-test-role`:
```yaml
- apiGroups: ["longhorn.io"]
  resources: ["*"]
  verbs: ["*"]
```
2. Put the below test case into the integration test work directory then run it. 
```python
import random
import string
import time

import common

from common import client, volume_name  # NOQA
from backupstore import set_random_backupstore # NOQA


Mi = (1024 * 1024)
Gi = (1024 * Mi)

LH_API_GROUP = "longhorn.io"
LH_API_VERSION = "v1beta1"
LH_NAMESPACE = "longhorn-system"
LHE_PLURAL = "engines"
LHB_PLURAL = "backups"

def test_backup_npe(client, volume_name, set_random_backupstore):  # NOQA
    host_id = common.get_self_host_id()

    client.create_volume(name=volume_name, size=str(2*Gi), numberOfReplicas=3)
    volume = common.wait_for_volume_detached(client, volume_name)

    volume.attach(hostId=host_id)
    volume = common.wait_for_volume_healthy(client, volume_name)

    common.create_backup(client, volume_name)

    volume.detach()
    common.wait_for_volume_detached(client, volume_name)

    snap_name = "non-existing-snapshot"

    cr_api = common.get_custom_object_api_client()

    lhb_name = "backup-test-" + "".join(random.choice(
        string.ascii_lowercase + string.digits) for _ in range(6))
    lhb_manifest = {
        'kind': 'Backup',
        'apiVersion': LH_API_GROUP+'/'+LH_API_VERSION,
        'metadata': {
            'name': lhb_name,
            'labels': {
                'backup-volume': volume_name,
            },
            'namespace': LH_NAMESPACE,
        },
        'spec': {
            'snapshotName': snap_name,
        },
    }

    for i in range(50):
        volume = client.by_id_volume(volume_name)
        engine_name = common.get_volume_engine(volume).name
        try:
            cr_api.create_namespaced_custom_object(group=LH_API_GROUP,
                                                   version=LH_API_VERSION,
                                                   namespace=LH_NAMESPACE,
                                                   plural=LHB_PLURAL,
                                                   body=lhb_manifest)
            cr_api.delete_namespaced_custom_object(group=LH_API_GROUP,
                                                   version=LH_API_VERSION,
                                                   namespace=LH_NAMESPACE,
                                                   plural=LHE_PLURAL,
                                                   name=engine_name)
        except Exception as e:
            print("exception creating lhb or deleting lhe %s\n" % e)
        time.sleep(1)
        try:
            cr_api.delete_namespaced_custom_object(group=LH_API_GROUP,
                                                   version=LH_API_VERSION,
                                                   namespace=LH_NAMESPACE,
                                                   plural=LHB_PLURAL,
                                                   name=lhb_name)
        except Exception as e:
            print("exception deleting lhb %s\n" % e)
        time.sleep(1)

    common.delete_backup_volume(client, volume_name)
    client.delete(volume)
```

Notice:
If you want to run this test in v1.2.x, please modify `LH_API_VERSION` from `v1beta2` to `v1beta1`.

---
GitHub Issue: https://github.com/longhorn/longhorn/issues/3484