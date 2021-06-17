---
title: Test Instance Manager Streaming Connection Recovery
---

## Related issue
https://github.com/longhorn/longhorn/issues/2561

## Test Step
**Given** A cluster with Longhorn 

*And* create a volume and attach it to a pod.

*And* `exec` into a longhorn manager pod and kill the connection with an engine or replica instance manager pod. The connections are instance manager pods' IP with port `8500`.
````
$ kl exec -it longhorn-manager-5z8zn -- bash

root@longhorn-manager-5z8zn:/# ss
Netid                    State                     Recv-Q                     Send-Q                                           Local Address:Port                                            Peer Address:Port
tcp                      ESTAB                     0                          0                                                  10.42.1.124:59414                                            10.42.1.123:8500
tcp                      ESTAB                     0                          0                                                  10.42.1.124:39096                                           52.36.54.134:https
tcp                      ESTAB                     0                          0                                                  10.42.1.124:45302                                              10.43.0.1:https
tcp                      ESTAB                     0                          0                                                  10.42.1.124:34124                                            10.42.1.122:8500
root@longhorn-manager-5z8zn:/# ss -K dst 10.42.1.122:8500
Netid                    State                     Recv-Q                     Send-Q                                            Local Address:Port                                            Peer Address:Port
tcp                      ESTAB                     0                          0                                                   10.42.1.124:34124                                            10.42.1.122:8500
root@longhorn-manager-5z8zn:/# exit
````

**Then** Check the longhorn manager pod log. There must be following logs:
```
[longhorn-manager-5z8zn] time="2021-06-17T11:16:37Z" level=error msg="error receiving next item in engine watch: rpc error: code = Unavailable desc = transport is closing" controller=longhorn-instance-manager instance manager=instance-manager-e-285962e9 node=shuo-cluster-0-worker-3
......
[longhorn-manager-5z8zn] time="2021-06-17T11:16:38Z" level=error msg="instance manager monitor streaming continuously errors receiving items for 10 times, will stop the monitor itself" controller=longhorn-instance-manager instance manager=instance-manager-e-285962e9 node=shuo-cluster-0-worker-3
```

*And* verify the volume still works fine.

*And* verify the volume can be detached and reattached.
