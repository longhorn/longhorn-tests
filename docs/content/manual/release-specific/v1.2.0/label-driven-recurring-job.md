---
title: Test Label-driven Recurring Job
---

## Related issue
https://github.com/longhorn/longhorn/issues/467

## Test Recurring Job Concurrency

**Given** create `snapshot` recurring job with `concurrency` set to `2` and include `snapshot` recurring job `default` in groups.

**When** create volume `test-job-1`.  
*And* create volume `test-job-2`.  
*And* create volume `test-job-3`.  
*And* create volume `test-job-4`.  
*And* create volume `test-job-5`.

**Then** moniter the cron job pod log.  
*And* should see 2 jobs created concurrently.

**When** update `snapshot1` recurring job with `concurrency` set to `3`.  
**Then** moniter the cron job pod log.
*And* should see 3 jobs created concurrently.


## Test Upgrade Migration For Recurring Job

**Given** cluster with Longhorn version prior to v1.2.0.  
*And* storageclass with recurring job `snapshot` and `backup`.  
*And* volume `test-job-1` created, and attached.

**When** upgrade Longhorn to v1.2.0.

**Then** should have new recurring job CR created with format `<jobTask>-<jobRetain>-<hash(jobCron)>-<hash(jobLabelJSON)>`.  
*And* volume should be labeled with `recurring-job.longhorn.io/<jobTask>-<jobRetain>-<hash(jobCron)>-<hash(jobLabelJSON)>: enabled`.  
*And* recurringJob should be removed in volume spec.
*And* storageClass in `longhorn-storageclass` configMap should not have `recurringJobs`.  
*And* storageClass in `longhorn-storageclass` configMap should     have `recurringJobSelector`.
```
recurringJobSelector:{"name":"snapshot-1-97893a05-77074ba4","isGroup":fals{"name":"backup-1-954b3c8c-59467025","isGroup":false}]'
```

When create new PVC.  
And volume should be labeled with items in `recurringJobSelector`.  
And recurringJob should not exist in volume spec.
