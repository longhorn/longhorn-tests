--------
Release Testing for v1.4.2
--------


**Release Date :**  
v1.4.2 RC1: 24th Mar 2023

---
Issues targeted for this release - [List of Github issues](https://github.com/longhorn/longhorn/issues?q=is%3Aopen+is%3Aissue+milestone%3Av1.4.2)

QAs: @chriscchien @yangchiu @roger-ryao @khushboo-rancher

---

## e2e Pipelines

1. [ ] Analyze test result of SLES on 1.4.x (AMD) - @chriscchien

1. [ ] Analyze test result of SLES on 1.4.x (ARM) - @chriscchien

1. [ ] Analyze upgrade test result of SLES on 1.4.x (AMD) - @yangchiu

1. [ ] Analyze upgrade test result of SLES on 1.4.x (ARM) - @yangchiu

1. [ ] Analyze test result of SLE Micro on 1.4.x (AMD) - @roger-ryao

1. [ ] Analyze test result of SLE Micro on 1.4.x (ARM) - @roger-ryao

1. [ ] Analyze two stage test result of SLES on 1.4.x (AMD) 1.2.6 → 1.3.2 → 1.4.2-rc - @chriscchien

1. [ ] Analyze two stage test result of SLES on 1.4.x (ARM) 1.2.6 → 1.3.2 → 1.4.2-rc - @chriscchien

## Managed Kubernetes Distro Matrix support

1. [ ] Run e2e on GKE cluster - @yangchiu
1. [ ] Run e2e on AKS cluster - @yangchiu
1. [ ] Run e2e on EKS cluster - @yangchiu

## Non-e2e Pipelines

1. [ ] Benchmark (compare with 1.4.1) - @yangchiu

2. [ ] Air-Gap (manifest, helm chart, rancher chart) - @roger-ryao

3. [ ] Vulnerability scanning (trivy) - @yangchiu

## Manual Testing
**HA:**
1. [ ] [Replica Rebuilding](https://longhorn.github.io/longhorn-tests/manual/pre-release/ha/replica-rebuilding/)
1. [ ] [Single replica node down](https://longhorn.github.io/longhorn-tests/manual/pre-release/ha/single-replica-node-down/)
1. [ ] [Engine not deployed on all nodes - case 3](https://longhorn.github.io/longhorn-tests/manual/pre-release/ha/partial-engine-deployment/)

**Node:**
1. [ ] [Node disconnection test](https://longhorn.github.io/longhorn-tests/manual/pre-release/node/node-disconnection/)
1. [ ] [Node drain and deletion test](https://longhorn.github.io/longhorn-tests/manual/pre-release/node/node-drain-deletion/)
1. [ ] [Physical node down](https://longhorn.github.io/longhorn-tests/manual/pre-release/node/physical-node-down/)
1. [ ] [Consolidated node disruption Test](https://github.com/roger-ryao/longhorn-tests/commit/f7d70934bdc7ee7343574577bf878b81b6c53765)

**Resiliency:**
1. [ ] [Test Longhorn components recovery](https://longhorn.github.io/longhorn-tests/manual/pre-release/resiliency/test-longhorn-component-recovery/)
1. [ ] [Uninstallation Checks](https://longhorn.github.io/longhorn-tests/manual/pre-release/uninstallation/uninstallation-checks/)

**Upgrade:**
1. [ ] [Test Engine Crash During Live Upgrade](https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/auto-upgrade-engine/)
1. [ ] [Kubernetes upgrade test](https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/kubernetes-upgrade-test/)
1. [ ] [Longhorn upgrade test](https://longhorn.github.io/longhorn-tests/manual/pre-release/upgrade/longhorn-upgrade-test/)

## Chart Testing
1. [ ] v2.6.x Rancher - @chriscchien

       Prereq: Set Concurrent Automatic Engine Upgrade Per Node Limit to greater than 0
       Test steps:
       1. Fresh installation
       2. Uninstallation
       3. Upgrade from v1.3.3
       4. Upgrade from v1.4.1
    
1. [ ] v2.7.x Rancher - @yangchiu

       Prereq: Set Concurrent Automatic Engine Upgrade Per Node Limit to 0
       Test steps:
       1. Fresh installation
       2. Uninstallation
       3. Upgrade from v1.3.3
       4. Upgrade from v1.4.1

1. [ ] Longhorn Chart - @roger-ryao

       Prereq: Set Concurrent Automatic Engine Upgrade Per Node Limit to greater than 0
       Test steps:
       1. Fresh installation
       2. Uninstallation
       3. Upgrade from v1.3.3
       4. Upgrade from v1.4.1

## Checklist
1. [ ] Run the relevant tests from https://longhorn.github.io/longhorn-tests/manual/pre-release/
1. [ ] Issues targeted for the release are validated and closed.
1. [ ] Validate the Charts with the dev branch.
1. [ ] Make sure tests (integration/manual) are added for the closed issues for the release.
