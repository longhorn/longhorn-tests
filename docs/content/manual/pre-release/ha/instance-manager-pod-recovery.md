---
title: Instance manager pod recovery [[#870](https://github.com/longhorn/longhorn/issues/870)]
---
1. Create and attach a volume.
2. Set an invalid value (Too large to crash the instance manager pods. e.g., 10) for `Guaranteed Engine CPU`.
3. Verify instance(engine/replica) manager pods will be recreated again and again.
4. Check the managers' log. (Use `kubetail longhorn-manager -n longhorn-system`). Make sure there is no NPE error logs like:
```
[longhorn-manager-67nhs] E1112 21:58:14.037140       1 runtime.go:69] Observed a panic: "send on closed channel" (send on closed channel)
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/vendor/k8s.io/apimachinery/pkg/util/runtime/runtime.go:76
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/vendor/k8s.io/apimachinery/pkg/util/runtime/runtime.go:65
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/vendor/k8s.io/apimachinery/pkg/util/runtime/runtime.go:51
[longhorn-manager-67nhs] /usr/local/go/src/runtime/panic.go:679
[longhorn-manager-67nhs] /usr/local/go/src/runtime/chan.go:252
[longhorn-manager-67nhs] /usr/local/go/src/runtime/chan.go:127
......
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/controller/instance_manager_controller.go:223
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/vendor/k8s.io/apimachinery/pkg/util/wait/wait.go:152
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/vendor/k8s.io/apimachinery/pkg/util/wait/wait.go:153
[longhorn-manager-67nhs] /go/src/github.com/longhorn/longhorn-manager/vendor/k8s.io/apimachinery/pkg/util/wait/wait.go:88
[longhorn-manager-67nhs] /usr/local/go/src/runtime/asm_amd64.s:1357
[longhorn-manager-67nhs] panic: send on closed channel [recovered]
[longhorn-manager-67nhs] panic: send on closed channel
......
```
5. Set `Guaranteed Engine CPU` to 0.25 and wait for all instance manager pods running.
6. Delete and recreate the volume. Then verify the volume works fine.
7. Repeat step1 to step6 for 3 times.
