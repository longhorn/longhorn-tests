---
title: Longhorn installation multiple times
---
1. Create a cluster(3 worker nodes and 1 etc/control plane).
2. Deploy the longhorn app.
3. Once longhorn deployed successfully, uninstall longhorn.
4. Repeat the steps 2 and 3 multiple times.
5. Run the below script to install and uninstall longhorn continuously for some time.
```
installcount=0
while true;
 echo `date`
 do
  kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml

  pod=`kubectl get pods -n longhorn-system | grep -i 'longhorn-manager' | grep -i 'running' | awk -F ' ' '{print $2}' | grep '1/1' | wc -l`
  count=0
  while [ $pod != 3 ];
   do
    sleep 5
    pod=`kubectl get pods -n longhorn-system | grep -i 'longhorn-manager' | grep -i 'running' | awk -F ' ' '{print $2}' | grep '1/1' | wc -l`
    echo `kubectl get pods -n longhorn-system | grep -i 'longhorn-manager'`
    count=$((count+1))
    if [ $count -gt 59 ]
     then
      echo 'longhorn installation failed'
      exit
    fi
  done

  sleep 30
 
  kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/master/uninstall/uninstall.yaml

  poduninstall=`kubectl get job/longhorn-uninstall | grep '1/1' | wc -l`
  uninstall=0
 while [ $poduninstall = 0 ];
  do
   sleep 10
   poduninstall=`kubectl get job/longhorn-uninstall | grep '1/1' | wc -l`
   echo `kubectl get job/longhorn-uninstall`
   uninstall=$((uninstall+1))
   if [ $uninstall -gt 24 ]  
    then
     echo 'Problem in unistall'
     exit
   fi
 done
 
 kubectl delete -f https://raw.githubusercontent.com/longhorn/longhorn/master/deploy/longhorn.yaml
 sleep 3

 kubectl delete -f https://raw.githubusercontent.com/longhorn/longhorn/master/uninstall/uninstall.yaml

 nscount=0
 longhornns=`kubectl get namespace | grep -i 'longhorn-system' | wc -l`l
 while [ $longhornns != 0 ];
  do
   sleep 10
   longhornns=`kubectl get namespace | grep -i 'longhorn-system' | wc -l`
   nscount=$((nscount+1))
   if [ $nscount -gt 18 ]
    then
     echo 'longhorn-system termination stuck'
     exit
   fi
 done

 installcount=$((installcount+1))
 echo 'Installation count = '
 echo $installcount
done
```
 