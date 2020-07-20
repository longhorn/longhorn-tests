---
title: New Node with Custom Data Directory
---
1. Make sure that the default `Longhorn` setup has all nodes with
`/var/lib/rancher/longhorn/` as the default Longhorn disk under the `Node`
page. Additionally, check the `Setting` page and make sure that the "Default
Data Path" setting has been set to `/var/lib/rancher/longhorn/` by default.
2. Now, change the "Default Data Path" setting to something else, such as
`/home`, and save the new settings.
3. Add a new node to the cluster with the proper dependencies to run Longhorn.
This step will vary depending on how the cluster has been deployed.
4. Go back to the `Node` page. The page should now list the new `node`.
Expanding the node should show a default disk of whichever directory was
specified in step 2.
