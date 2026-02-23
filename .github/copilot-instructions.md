# GitHub Copilot Instructions for Longhorn E2E Test Development

This file provides guidelines for AI assistants (GitHub Copilot) when implementing automated Robot Framework test cases in the `e2e/` folder.

---

## General Principles

### Keyword Reuse
**Always reuse existing keywords as much as possible.**

- Before creating new keywords, check [`e2e/keywords/*.resource`](../e2e/keywords) for existing keywords
- Only create new keywords when existing ones cannot fulfill the requirement
- When extending existing keywords with new parameters, use `&{config}` for flexible optional parameters

### Test Structure
- Follow the existing test patterns in [`e2e/tests/`](../e2e/tests)
- Include proper test setup and teardown
- Add `Issue: https://github.com/longhorn/longhorn/issues/<issue_number>` to the `[Documentation]` block for better tracking
- Add the origin manual test steps to the `[Documentation]` block if available 

---

## Keyword Selection Guidelines

### Longhorn Resource Operations
Use existing keywords from [e2e/keywords/*.resource](../e2e/keywords)

### Custom Host Commands
When the test requires **highly customized operations** like executing specific commands on a host, use the **host command keyword set**:

**Available host command keywords from [e2e/keywords/host.resource](../e2e/keywords/host.resource):**

1. **`Run command on node`**
   - Use for: Basic command execution on a specific node
   - Parameters: `${node_id}`, `${command}`
   - Example:
```
Run command on node    0
...    rm /var/lib/longhorn/longhorn-disk.cfg
```

2. **`Run command on node ${node_id} and not expect output`**
   - Use for: Execute command and verify specific output is NOT present
   - Parameters: `${node_id}`, `${command}`, `${unexpected_output}`
   - Example:
```
Run command on node 0 and not expect output
...    dmesg
...    ERROR
```

3. **`Run command on node ${node_id} and wait for output`**
   - Use for: Execute command and wait until expected output appears
   - Parameters: `${node_id}`, `${command}`, `${expected_output}`
   - Example:
```
Run command on node 0 and wait for output
...    journalctl -u k3s-agent  --no-pager
...    CNI plugin initialized
```

### Custom Kubernetes Commands
When the test requires **executing specific kubectl commands**, use the **kubectl command keyword set** from [e2e/keywords/common.resource](../e2e/keywords/common.resource):

**Available kubectl command keywords:**

1. **`Run command`**
   - Use for: Basic kubectl command execution
   - Parameters: `${command}`
   - Example:
```
Run command
...    kubectl taint node ${NODE_0} node-role.kubernetes.io/worker=true:NoExecute
```

2. **`Run command and expect output`**
   - Use for: Execute kubectl command and verify specific output is present
   - Parameters: `${command}`, `${expected_output}`
   - Example:
```
Run command and expect output
...    kubectl get csistoragecapacity -n longhorn-system
...    csisc
```

3. **`Run command and not expect output`**
   - Use for: Execute kubectl command and verify specific output is NOT present
   - Parameters: `${command}`, `${unexpected_output}`
   - Example:
```
Run command and not expect output
...    kubectl logs -l app=longhorn-csi-plugin -n longhorn-system -c longhorn-csi-plugin
...    InvalidArgument
```

4. **`Run command and wait for output`**
   - Use for: Execute kubectl command and wait until expected output appears
   - Parameters: `${command}`, `${expected_output}`
   - Example:
```
Run command and wait for output
...    kubectl get pods -n longhorn-system -l app=csi-snapshotter --field-selector=status.phase=Running -owide | grep -c ${NODE_2}
...    3
```

---

## Best Practices

### When to Use Custom Command Keywords

Use **host command keywords** (`Run command on node ...`) when:
- Executing system-level commands on specific nodes (systemctl, iptables, etc.)
- Checking host filesystem or process state
- Performing node-specific operations not covered by existing keywords
- Need to verify/retrieve command output from a particular node

Use **kubectl command keywords** (`Run command ...`) when:
- Running kubectl commands for Kubernetes resources
- Checking status of custom resources not covered by existing keywords
- Performing operations on namespaces, configmaps, secrets, etc.
- Validating Kubernetes API objects directly

### When NOT to Use Custom Command Keywords

**Avoid using custom command keywords when it's a normal Longhorn resource operation or a negative factor already covered by existing keywords:**

❌ **DON'T:**
```robot
Run command    kubectl create -f volume.yaml
Run command on node 0    systemctl restart kubelet
```

✅ **DO:**
```robot
Create volume 0 with    size=5Gi
Stop volume nodes kubelet for 10 seconds    statefulset 0
```
