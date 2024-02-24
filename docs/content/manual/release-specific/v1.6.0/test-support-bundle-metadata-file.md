---
title: Test Support Bundle Metadata File
---

## Related issue
https://github.com/longhorn/longhorn/issues/6997

## Test

**Given** Longhorn installed on SUSE Linux  
**When** generated support-bundle with description and issue URL  
**Then** `issuedescription` has the description in the metadata.yaml  
**And** `issueurl` has the issue URL in the metadata.yaml  
