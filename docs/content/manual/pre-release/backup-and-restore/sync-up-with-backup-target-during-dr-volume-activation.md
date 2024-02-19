---
title: "Sync up with backup target during DR volume activation"
---

#### Related Issue:
- https://github.com/longhorn/longhorn/issues/5292
- https://github.com/longhorn/longhorn/issues/7945

1. Launch 2 clusters and both have Longhorn installed
1. Set up a backup target.
1. Create a volume and write data in the `1st cluster`. Then create `1st backup`.
1. Restore the backup as a DR volume in the `2nd cluster`.
1. Modify the backup poll interval to a large value.
1. Write more data for the volume in the `1st cluster`, and create the `2nd backup`.
1. Activate the DR volume in the `2nd cluster`. Then verify the data
1. The activated DR volume should contain the latest data.
