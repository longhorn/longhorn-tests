---
title: "Test timeout on loss of network connectivity"
---

## Ping Timeout

1. Create a docker network:

```shell
docker network create -d bridge --subnet 192.168.22.0/24 longhorn-network
```

2. Start a replica:

```shell
docker run --net longhorn-network --ip 192.168.22.2 \
         -v /volume longhornio/longhorn-engine:<tag> \
         longhorn replica --listen 192.168.22.2:9502 --size 10g /volume
```

3. Start another replica:

```shell
docker run --net longhorn-network --ip 192.168.22.3 \
         -v /volume longhornio/longhorn-engine:<tag> \
         longhorn replica --listen 192.168.22.3:9502 --size 10g /volume
```

4. In another terminal, start the controller:

```shell
docker run --net longhorn-network --ip 192.168.22.4 --privileged \
         -v /dev:/dev -v /proc:/host/proc \
         longhornio/longhorn-engine:<tag> \
         longhorn controller --replica tcp://192.168.22.2:9502 \
         --replica tcp://192.168.22.3:9502 \
         --frontend tgt-blockdev timeout-test
```

5. In another terminal, find the name of the container running the replica with `docker ps`

6. Disconnect the replica container from the network:

```shell
docker network disconnect longhorn-network <container id/name>
```

7. Note that the controller output displays "Backend tcp://192.168.22.2:9502 monitoring failed, mark as ERR: ping timeout" after eight seconds. 

## R/W Timeout Block Device

1. Perform steps 2-4 from the Ping Timeout Section.

2. In another terminal, perform I/O:

```shell
fio --name=random-writers --ioengine=libaio --rw=randwrite --bs=16k \
           --direct=1 --size=1000m --numjobs=1 \
           --filename=/dev/longhorn/timeout-test --iodepth=1
```
3. Stop the network on the replica with steps 5-6 in the Ping Timeout Section.

4. Note that the controller output displays "Setting replica tcp://192.168.22.2:9502 to ERR due to: r/w timeout" after eight seconds.

6. Check `dmesg` to verify that block device did not generate any kernel error messages.

## R/W Timeout Filesystem

1. Perform steps 2-4 from the Ping Timeout Section.

2. In another terminal, perform I/O:

```shell
mkfs.ext4 /dev/longhorn/timeout-test
mkdir /timeout-test
mount /dev/longhorn/timeout-test /timeout-test
fio --name=random-writers --ioengine=libaio --rw=randwrite --bs=16k \
           --direct=1 --size=1000m --numjobs=1 \
           --filename=/timeout-test/fio.dat --iodepth=1
```
3. Stop the network on the replica with steps 5-6 in the Ping Timeout Section.

4. Note that the controller output displays "Setting replica tcp://192.168.22.2:9502 to ERR due to: r/w timeout" after eight seconds.

5. Note that the fio operation continues to work and completes without error.

6. Check `dmesg` to verify that block device or filesystem did not generate any kernel error messages.
