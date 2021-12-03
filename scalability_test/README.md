How To Use Scalability Test Script

## Create a cluster for testing
The Terraform script in `./terraform` folder can be used to quickly create a cluster for testing. 
You can specify many options for the cluster. Take a look at the file `./terraform/variables.tf`
for detail about available options. The following example steps create a cluster of 1 controller node
and 3 worker nodes with an EBS volume attached to each worker nodes.

* `cd ./terraform`
* `terraform init`
* Create a `testing.tfvars` with content:
    ```
    lh_aws_access_key = "<YOUR-AWS-ACCESS-KEY>"
    lh_aws_secret_key = "<YOUR-AWS-SECRET-KEY>"
    
    aws_region = "us-west-2"
    aws_availability_zone = "us-west-2a"
    
    
    lh_aws_instance_type_controlplane = "m5.2xlarge"
    lh_aws_instance_type_worker = "m5.2xlarge"
    
    lh_aws_instance_count_controlplane = 1
    lh_aws_instance_count_worker = 3
    
    lh_aws_instance_root_block_device_size_worker = 20
    lh_aws_create_ebs_block_device = true
    lh_aws_ebs_block_device_settings = {
      device_name           = "/dev/sdh"
      os_device_name = "/dev/nvme1n1"
      volume_size           = 1200
      delete_on_termination = true
      volume_type = "gp3"
      iops = 6000
      throughput = 250
    }
    ```
* `terraform apply -var-file=./testing.tfvars`
* Enter `yes` to confirm the action

## Install Longhorn
The cluster created above has each EBS volume mounted at the path `/data`. 
Therefore, you need to modify the Longhorn installation to set `default-data-path` to `/data`.
For example:
* Download Longhorn deployment YAML by `wget https://raw.githubusercontent.com/longhorn/longhorn/v1.2.2/deploy/longhorn.yaml`
* Set the field `default-data-path: /data` in `default-setting.yaml`
* Install Longhorn `kubectl apply -f ./longhorn.yaml`

## Run the test script
### Overview of the test script
The goal of the test is finding out what is the maximum number of workload pods (each pod has a Longhorn volume) a cluster can support.

The test script is located at `./script/scale-test.py`. 
The constant variable `KUBE_CONFIG` inside the script specify the path to the kubeconfig file.
By default, `KUBE_CONFIG` is `None` means the script reads the kubeconfig file from the path `~/.kube/config`

The script queries the cluster to list all worker nodes. 
For each worker nodes, the script will deploy a StatefulSet that has `spec.template.spec.nodeName` set to the name of the node. 
See the file `./script/statefulset.yaml` for the format of each StatefulSet.
This makes sure the workload pods are spread evenly across the nodes.
Then the script scale up the number of replicas for each StatefulSet to a user-specified value.
Finally, it monitors the status of the workload pods and draw the graph.

In the graph drew by the script, there are 2 important events that you need to be aware of:
1. The point at which the maximum pod starting time is over the limit. 
   The script keeps track of the starting time for each workload pod. 
   When the script detects a pod that takes too long to start (e.g., more than `MAX_POD_STARTING_TIME` value), it will 
   mark yellow warning on the graph.
2. The point at which the pod crashing count is over the limit.
   The script counts the number of workload pod crashes during the testing.
   When the script detects the number of pod crashing exceeded the maximum value (`MAX_POD_CRASHING_COUNT`), it will
   mark red warning on the graph.

If you see either of the above event, the scale test is considered as completed with the maximum number of workload pods is the value at the event.

While the test script is running, it persists the collected data at `./script/monitor_data.txt`

### Operations

Once you run the test script, you can select one of the 4 operations:
1. `all`:
   
   This operation creates a StatefulSet for each worker nodes in the cluster.
   You can select the workload type for the workload pod (`non_io`, `io_1`, `io_2`, `io_3`).
   See more about the definition of each workload type in `./script/scale-test.py`.
   You can select the number of replicas per StatefulSet.
   The script then deploys and scales up the StatefulSet.
   Finally, the script collects and draw the graphs about workload statuses.
2. `scale`: 
   
   This operation quickly scales up each of the existing StatefulSet in the cluster to your provided value
3. `monitor`:
   
   This operation only start collecting and drawing graphs without deploying or scaling the workload StatefulSet.
   You can specify whether you want to preload the data with the previous values inside `./script/monitor_data.txt`.
   This is useful in case the script is break in the middle of a test and you want to resume monitoring.
4. `dry_draw`:
   
   This operation draw graph from the provided monitoring data file. 
   By default, if you don't specify the data file, the script will read the data from `./script/monitor_data.txt`
   
### Example
An example of a test run could be:
```bash
peterle@peters-mbp scale-test % python3 scale-test.py
Choose an operation (scale, monitor, all, dry_draw): all
How many replicas per StatefulSet? 80
Created 30 statefulsets
sleeping for 15s
Scaled 30 statefulsets so that each has 80 replicas
running monitoring loop ...
# The test ended
peterle@peters-mbp scale-test % python3 scale-test.py
Choose an operation (scale, monitor, all, dry_draw): dry_draw
Enter file name: # intentionally left empty. The script draws the graphs from recent collected data. You can use the UI to export the graphs to a a .png file.

```

## Clean up the cluster after testing
* `cd ./terraform`
* `terraform destroy -var-file=./testing.tfvars`
* Enter yes to confirm