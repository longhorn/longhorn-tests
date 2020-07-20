---
title: Volume Deletion UI Warnings
---
A number of cases need to be manually tested in `longhorn-ui`. To test these cases, create the `Volume` with the specified conditions in each case, and then try to delete it. What is observed should match what is described in the test case:
1. A regular `Volume`. Only the default deletion prompt should show up asking to confirm deletion.
2. A `Volume` with a `Persistent Volume`. The deletion prompt should tell the user that there is a `Persistent Volume` that will be deleted along with the `Volume`.
3. A `Volume` with a `Persistent Volume` and `Persistent Volume Claim`. The deletion prompt should tell the user that there is a `Persistent Volume` and `Persistent Volume Claim` that will be deleted along with the `Volume`.
4. A `Volume` that is `Attached`. The deletion prompt should indicate what `Node` the `Volume` is attached to and warn the user about errors that may occur as a result of deleting an attached `Volume`.
5. A `Volume` that is `Attached` and has a `Persistent Volume`. The deletion prompt should contain the information from both test cases 2 and 4.

Additionally, here are bulk deletion test cases that need testing:
1. 1+ regular `Volumes`. Only the default deletion prompt should show up asking to confirm deletion.
2. 1+ `Volumes` with a `Persistent Volume`.  The deletion prompt should list the `Persistent Volumes` associated with the `Volumes` and tell the user that these will also be deleted.
3. 0+ regular `Volumes` and 1+ `Volumes` that are `Attached`. The deletion prompt should list only `Volumes` that are `Attached` and tell the user that applications using them may encounter errors once the `Volumes` are deleted. **This test case has not been addressed in `longhorn-ui` yet and will likely fail.**
4. 0+ regular `Volumes`, 1+ `Volumes` with a `Persistent Volume`, and 1+ `Volumes` that are `Attached`. The information described in test cases 2 and 3 should be displayed. **This test case has not been addressed in `longhorn-ui` yet and will likely fail.**

Finally, there are some other test cases to check here:
1. Create a `Volume` and create a `Persistent Volume` and `Persistent Volume Claim` through the `longhorn-ui`. Delete the `Persistent Volume Claim` manually. Delete the `Volume`. The deletion prompt should not list the `Persistent Volume Claim` that was deleted in the list of resources to be deleted.
2. Create a `Disaster Recovery Volume`. Delete the `Disaster Recovery Volume`. The deletion prompt should not give a warning about errors that may occur from deleting an attached `Volume`. **This test case has not been addressed in `longhorn-ui` yet and will likely fail.**
3. Create a `Volume` from a `Backup`. While the `Volume` is still being restored, delete the `Volume`. The deletion prompt should not give a warning about errors that may occur from deleting an attached `Volume`. **This test case has not been addressed in `longhorn-ui` yet and will likely fail.**

Some of these test cases have not been addressed yet and will fail until addressed in a later PR.
