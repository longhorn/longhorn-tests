---
title: Dependency setup for GKE cluster using Container-Optimized OS as base image
---

## Related issues

- https://github.com/longhorn/longhorn/issues/6165

## Test step

**Given** GKE cluster using Continer-Optimized OS (`COS_CONTAINER`) as the base image.

**When** Follow [instruction](https://github.com/longhorn/website/pull/884) to deploy the Longhorn GKE COS node agent.

**Then** Follow the [instruction](https://github.com/longhorn/website/pull/884) to verify dependency configuration/setup.  
**And** Integration tests should pass.
