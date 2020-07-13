---
title: Priority Class Default Setting
---
There are three different cases we need to test when the user inputs a default setting for `Priority Class`:
1. Install `Longhorn` with no `priority-class` set in the default settings. The `Priority Class` setting should be empty after the installation completes according to the `longhorn-ui`, and the default `Priority` of all `Pods` in the `longhorn-system` namespace should be `0`:
```
~ kubectl -n longhorn-system describe pods | grep Priority
# should be repeated many times
Priority:     0
```
2. Install `Longhorn` with a nonexistent `priority-class` in the default settings. The system should fail to come online. The `Priority Class` setting should be set and the status of the `Daemon Set` for the `longhorn-manager` should indicate that the reason it failed was due to an invalid `Priority Class`:
```
~ kubectl -n longhorn-system describe lhs priority-class
Name:         priority-class
...
Value:                 nonexistent-priority-class
...
~ kubectl -n longhorn-system describe daemonset.apps/longhorn-manager
Name:           longhorn-manager
...
  Priority Class Name:  nonexistent-priority-class
Events:
  Type     Reason            Age                From                  Message
  ----     ------            ----               ----                  -------
  Normal   SuccessfulCreate  23s                daemonset-controller  Created pod: longhorn-manager-gbskd
  Normal   SuccessfulCreate  23s                daemonset-controller  Created pod: longhorn-manager-9s7mg
  Normal   SuccessfulCreate  23s                daemonset-controller  Created pod: longhorn-manager-gtl2j
  Normal   SuccessfulDelete  17s                daemonset-controller  Deleted pod: longhorn-manager-9s7mg
  Normal   SuccessfulDelete  17s                daemonset-controller  Deleted pod: longhorn-manager-gbskd
  Normal   SuccessfulDelete  17s                daemonset-controller  Deleted pod: longhorn-manager-gtl2j
  Warning  FailedCreate      4s (x14 over 15s)  daemonset-controller  Error creating: pods "longhorn-manager-" is forbidden: no PriorityClass with name nonexistent-priority-class was found
```
3. Install `Longhorn` with a valid `priority-class` in the default settings. The `Priority Class` setting should be set according to the `longhorn-ui`, and all the `Pods` in the `longhorn-system` namespace should have the right `Priority` set:
```
~ kubectl -n longhorn-system describe pods | grep Priority
# should be repeated many times
Priority:             2000001000
Priority Class Name:  system-node-critical
