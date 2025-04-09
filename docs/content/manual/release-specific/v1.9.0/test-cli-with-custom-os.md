---
title: Test CLI compatibility with custom OS
---

## Related issue
https://github.com/longhorn/longhorn/issues/10676

## Test CLI compatibility with custom OS

**Given** Kubernetes cluster running on custom OS (based on Linux) not explicitly listed [here](https://github.com/longhorn/cli/blob/40b81007971033276c5d548d704ec0f9689f5fa0/pkg/utils/os.go#L18-L32)

**When** Run check using CLI tool `longhornctl check preflight`

**Then** The check should complete without operating system not supported error.

**And** No pods in the DaemonSet should be in a failed state.