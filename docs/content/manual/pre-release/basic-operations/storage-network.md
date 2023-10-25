---
title: Storage Network Test
---
## Related issue:
https://github.com/longhorn/longhorn/issues/2285

## Test Multus version below v4.0.0
**Given** Set up the Longhorn environment as mentioned [here](https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.3.0/test-storage-network/)
**When** Run Longhorn core tests on the environment.
**Then** All the tests should pass.

## Related issue:
https://github.com/longhorn/longhorn/issues/6953

## Test Multus version above v4.0.0
**Given** Set up the Longhorn environment as mentioned [here](https://longhorn.github.io/longhorn-tests/manual/release-specific/v1.6.0/test-storage-network/)
**When** Run Longhorn core tests on the environment.
**Then** All the tests should pass.
