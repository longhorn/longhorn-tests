# A stress test program to perform repeated operations in multiple processes.
# 
# 1. Write data between 0 and BATCH_SIZE blocks at a random offset
# 2. Read data between 0 and BATCH_SIZE blocks at a random offset
# 3. Remove a replica and add it back, causing a rebuild
#
# Test patterns are stored in shared memory for all processes to access, and is 
# used to validate the correctness of data after being read.
#

import subprocess
import time
import copy
import random
import sys
import threading
import time
import datetime
import os
import stat
from multiprocessing import Process, Manager, Array, current_process

SIZE = 20 * 1024 * 1024 * 1024
SIZE_STR = str(SIZE)
BLOCK_SIZE = 4096
BATCH_SIZE = 128

INIT_TIME = time.time()
MAX_SNAPSHOTS = 16
MAX_TIME_SLACK = 1000
MAX_BLOCKS = SIZE / BLOCK_SIZE

def wait_for_dev_ready(i, controller):
  dev = "/dev/longhorn/vol" + str(i)
  init_time = time.time()
  while time.time() - init_time < 60:
    if os.path.exists(dev):
      mode = os.stat(dev).st_mode
      if stat.S_ISBLK(mode):
        print "%s: Device ready after %.3f seconds" \
                % (datetime.datetime.now(), time.time() - init_time)
        return
    time.sleep(0.05)
  print "%s: FAIL TO WAIT FOR DEVICE READY, docker logs:" \
          % (datetime.datetime.now())
  subprocess.call("docker logs " + controller, shell=True)
  assert False

def gen_blockdata(blockoffset, nblocks, pattern):
  d = bytearray(nblocks * BLOCK_SIZE)
  for i in xrange(nblocks):
    d[i * BLOCK_SIZE + 0] = (blockoffset + i) & 0xFF
    d[i * BLOCK_SIZE + 1] = ((blockoffset + i) >> 8) & 0xFF
    d[i * BLOCK_SIZE + 2] = ((blockoffset + i) >> 16) & 0xFF
    d[i * BLOCK_SIZE + 3] = ((blockoffset + i) >> 24) & 0xFF
    d[i * BLOCK_SIZE + 4] = pattern & 0xFF
    d[i * BLOCK_SIZE + 5] = (pattern >> 8) & 0xFF
    d[i * BLOCK_SIZE + 6] = (pattern >> 16) & 0xFF
    d[i * BLOCK_SIZE + 7] = (pattern >> 24) & 0xFF
  return d

def create_testdata():
  return Array('i', MAX_BLOCKS * (MAX_SNAPSHOTS + 1))

def rebuild_replicas(controller, iterations):
  for iteration in xrange(iterations):
    if iteration % 1 == 0:
      subprocess.check_call("docker exec " + controller + " launch snapshots | tail -n +3 | xargs docker exec " + controller + " launch snapshot rm", shell = True)
    time.sleep(SIZE / 1024 / 1024 / 256)
    if random.random() > 0.5:
      replica_host = "172.18.0.2:9502"
    else:
      replica_host = "172.18.0.3:9502"
    print "%s Rebuild: %s " \
            % (datetime.datetime.now(), replica_host)
    subprocess.check_call(("docker exec " + controller + " launch rm tcp://" + replica_host).split())
    subprocess.check_call(("docker exec " + controller + " launch add tcp://" + replica_host).split())
    print "%s Rebuild %s complete" \
            % (datetime.datetime.now(), replica_host)


def gen_pattern():
  return int((time.time() - INIT_TIME) * 1000)

def random_write(snapshots, testdata, iterations):
  proc = current_process()
  print "%s Starting random write in %s pid = %d" \
            % (datetime.datetime.now(), str(proc), proc.pid)
  fd = open("/dev/longhorn/vol1", "r+")
  base = snapshots["livedata"]
  for iteration in xrange(iterations):
    if iteration % 1000 == 0:
      print "%s: Iteration %d random write in %s pid = %d" \
            % (datetime.datetime.now(), iteration, str(proc), proc.pid)
    blockoffset = int(MAX_BLOCKS * random.random())
    nblocks = int(BATCH_SIZE * random.random())
    if nblocks + blockoffset > MAX_BLOCKS:
      nblocks = MAX_BLOCKS - blockoffset
    pattern = gen_pattern()
    for i in xrange(nblocks):
      testdata[base + blockoffset + i] = pattern
    fd.seek(blockoffset * BLOCK_SIZE)
    fd.write(gen_blockdata(blockoffset, nblocks, pattern))
    fd.flush()
  print "%s: Completed random write in %s pid = %d" \
        % (datetime.datetime.now(), str(proc), proc.pid)
  fd.close()

def read_and_check(snapshots, testdata, iterations):
  data_blocks = 0
  hole_blocks = 0
  proc = current_process()
  print "%s: Starting read and check in %s pid = %d" \
        % (datetime.datetime.now(), str(proc), proc.pid)
  fd = open("/dev/longhorn/vol1", "r")
  base = snapshots["livedata"]
  for iteration in xrange(iterations):
    if iteration % 1000 == 0:
      print "%s: Iteration %d read and check in %s pid = %d" \
            % (datetime.datetime.now(), iteration, str(proc), proc.pid)
    blockoffset = int(MAX_BLOCKS * random.random())
    nblocks = int(BATCH_SIZE * random.random())
    if nblocks + blockoffset > MAX_BLOCKS:
      nblocks = MAX_BLOCKS - blockoffset
    fd.seek(blockoffset * BLOCK_SIZE)
    d = fd.read(BLOCK_SIZE * nblocks)
    if len(d) != BLOCK_SIZE * nblocks:
      time.sleep(1)
      subprocess.call(["killall", "python"])
    current_pattern = gen_pattern()
    for i in xrange(nblocks):
      stored_blockoffset = ord(d[BLOCK_SIZE * i + 0]) + (ord(d[BLOCK_SIZE * i + 1]) << 8) + (ord(d[BLOCK_SIZE * i + 2]) << 16) + (ord(d[BLOCK_SIZE * i + 3]) << 24)
      stored_pattern = ord(d[BLOCK_SIZE * i + 4]) + (ord(d[BLOCK_SIZE * i + 5]) << 8) + (ord(d[BLOCK_SIZE * i + 6]) << 16) + (ord(d[BLOCK_SIZE * i + 7]) << 24)
      pattern = testdata[base + blockoffset + i]
      # Skip entries that are too recent
      if current_pattern - pattern < MAX_TIME_SLACK or current_pattern - stored_pattern < MAX_TIME_SLACK:
        continue
      try:
        if stored_pattern != 0 or stored_blockoffset != 0:
          assert stored_blockoffset == blockoffset + i
          assert abs(stored_pattern - pattern) < MAX_TIME_SLACK
          data_blocks = data_blocks + 1
        else:
          assert stored_blockoffset == 0
          assert stored_pattern == 0
          hole_blocks = hole_blocks + 1
      except AssertionError:
        print ("%s: current_pattern = %d nblocks = %d blockoffset = %d " + \
            "i = %d stored_blockoffset = %d pattern = %d stored_pattern = %d") \
            % (datetime.datetime.now(), current_pattern, nblocks, blockoffset,
                    i, stored_blockoffset, pattern, stored_pattern)
  print "%s: data_blocks: %d hole_blocks: %d" \
        % (datetime.datetime.now(), data_blocks, hole_blocks)
  print "%s: Completed read and check in %s pid = %d" \
        % (datetime.datetime.now(), str(proc), proc.pid)
  fd.close()


subprocess.call("sudo iscsiadm -m node --logout", shell=True)
subprocess.call("sudo rm /dev/longhorn/vol1", shell=True)
subprocess.call("docker rm -fv `docker ps -a | grep rancher/longhorn | awk '{print $1}'`", shell=True)
subprocess.call("docker network create --subnet=172.18.0.0/16 longhorn-net", shell=True)
subprocess.call(("docker run -d --net longhorn-net --ip 172.18.0.2 --expose 9502-9504 -v /volume rancher/longhorn launch replica --listen 172.18.0.2:9502 --size " + SIZE_STR + " /volume").split())
subprocess.call(("docker run -d --net longhorn-net --ip 172.18.0.3 --expose 9502-9504 -v /volume rancher/longhorn launch replica --listen 172.18.0.3:9502 --size " + SIZE_STR + " /volume").split())
time.sleep(3)
controller = subprocess.check_output("docker run -d --net longhorn-net " +
        "--privileged -v /dev:/host/dev -v /proc:/host/proc rancher/longhorn " +
        "launch controller --frontend tgt --replica tcp://172.18.0.2:9502 " +
        "--replica tcp://172.18.0.3:9502 vol1", shell=True).rstrip()
print "controller = " + controller
wait_for_dev_ready(1, controller)

manager = Manager()
testdata = create_testdata()
snapshots = manager.dict()
snapshots["livedata"] = 0

workers = []

for i in range(10):
  p = Process(target = random_write, args = (snapshots, testdata, 2000000))
  workers.append(p)
  p.start()

for i in xrange(10):
  p = Process(target = read_and_check, args = (snapshots, testdata, 2000000))
  workers.append(p)
  p.start()

p = Process(target = rebuild_replicas, args = (controller, 1000))
workers.append(p)
p.start()


for p in workers:
  p.join()
