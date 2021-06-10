---
title: Test CronJob For Volumes That Are Detached For A Long Time
---

## Related issue
https://github.com/longhorn/longhorn/issues/2513

## Steps
1. Make sure the setting `Allow Recurring Job While Volume Is Detached` is `disabled`
1. Create a volume. Attach to a node. Create a recurring backup job that run every minute. 
1. Wait for the cronjob to be scheduled a few times.
1. Detach the volume.
1. Verify that the CronJob get deleted.
1. Wait 2 hours (> 100 mins).
1. Attach the volume to a node.
1. Verify that the CronJob get created.
1. Verify that Kubernetes schedules a run for the CronJob at the beginning of the next minute.
1. Make sure the setting `Allow Recurring Job While Volume Is Detached` is `enabled`.
1. Detach the volume.
1. Verify that the CronJob is not deleted.
1. Wait for Kubernetes to schedule a run for the CronJob at the beginning of the next minute. 
   Verify that the volume is attached, CronJob runs, then volume is detached.

